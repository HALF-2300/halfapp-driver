"""HALFAPP_RIDE_CLAIM_LOCK_CONCURRENCY_01: row-locked claim and multi-driver race proof."""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi.testclient import TestClient

from database import SessionLocal
import models.metrics  # noqa: F401
import models.presence  # noqa: F401
import models.ride  # noqa: F401
import models.user  # noqa: F401
import routes.notifications  # noqa: F401
from main import app
from models.ride import Ride
from models.user import UserRole
from services.auth import create_access_token, create_user

COMPETING_DRIVER_COUNT = 10


def _driver_token(db, prefix: str) -> tuple[str, int]:
    uid = uuid.uuid4().hex[:10]
    user = create_user(
        db,
        f"{prefix}_{uid}@example.com",
        f"{prefix} Driver",
        "pw12345",
        UserRole.DRIVER,
        f"DL{uid}",
        driver_approval_status="approved",
    )
    db.commit()
    return create_access_token(sub=user.email, role=user.role.value), user.id


def _requested_ride(db) -> int:
    ride = Ride(
        customer_name="Lock Concurrency Rider",
        status="requested",
        pickup_location="Lock Pickup",
        destination="Lock Dropoff",
        pickup_latitude=45.501,
        pickup_longitude=-122.681,
        dropoff_latitude=45.551,
        dropoff_longitude=-122.611,
        distance=3.0,
        duration=8,
    )
    db.add(ride)
    db.commit()
    db.refresh(ride)
    return ride.id


def _claim(token: str, ride_id: int):
    with TestClient(app) as client:
        headers = {"Authorization": f"Bearer {token}"}
        client.patch(
            "/drivers/me/status",
            headers=headers,
            json={"online": True, "lat": 45.523064, "lng": -122.676483},
        )
        return client.post(
            f"/drivers/accept-ride/{ride_id}",
            headers={"Authorization": f"Bearer {token}"},
        )


def test_concurrent_ten_driver_claims_one_winner_nine_conflicts():
    db = SessionLocal()
    try:
        tokens = [_driver_token(db, f"race_{i}")[0] for i in range(COMPETING_DRIVER_COUNT)]
        ride_id = _requested_ride(db)
    finally:
        db.close()

    with ThreadPoolExecutor(max_workers=COMPETING_DRIVER_COUNT) as pool:
        futures = [pool.submit(_claim, token, ride_id) for token in tokens]
        responses = [future.result() for future in as_completed(futures)]

    winners = [r for r in responses if r.status_code == 200]
    losers = [r for r in responses if r.status_code == 409]
    other = [r for r in responses if r.status_code not in (200, 409)]

    assert not other, [r.status_code for r in other]
    assert len(winners) == 1, f"expected 1 winner, got {len(winners)}"
    assert len(losers) == COMPETING_DRIVER_COUNT - 1

    winner_body = winners[0].json()["ride"]
    assert winner_body["status"] == "accepted"
    assert winner_body["driver_id"] is not None

    for loser in losers:
        detail = loser.json()["detail"]
        assert detail["detail"] == "Ride already claimed"
        assert detail["claim_result"] == "lost"
        assert detail["truth_status"] == "backend_conflict"
        assert detail["reason"] == "ride_already_claimed"
        assert detail["state_changed"] is False
        assert detail["current_status"] == "accepted"
        assert detail["assigned_driver_id"] == winner_body["driver_id"]
        assert detail["ride_id"] == ride_id

    db = SessionLocal()
    try:
        ride = db.query(Ride).filter(Ride.id == ride_id).one()
        assert ride.driver_id == winner_body["driver_id"]
        assert ride.status == "accepted"
        assert db.query(Ride).filter(Ride.id == ride_id, Ride.status == "accepted").count() == 1
    finally:
        db.close()


def test_winner_and_loser_refresh_state_after_concurrent_claim():
    db = SessionLocal()
    try:
        winner_token, _ = _driver_token(db, "refresh_win")
        loser_token, _ = _driver_token(db, "refresh_lose")
        ride_id = _requested_ride(db)
    finally:
        db.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        winner_future = pool.submit(_claim, winner_token, ride_id)
        loser_future = pool.submit(_claim, loser_token, ride_id)
        winner_resp = winner_future.result()
        loser_resp = loser_future.result()

    responses = [winner_resp, loser_resp]
    winners = [r for r in responses if r.status_code == 200]
    losers = [r for r in responses if r.status_code == 409]
    assert len(winners) == 1 and len(losers) == 1

    win_resp = winner_resp if winner_resp.status_code == 200 else loser_resp
    lose_resp = loser_resp if winner_resp.status_code == 200 else winner_resp
    win_token = winner_token if winner_resp.status_code == 200 else loser_token
    lose_token = loser_token if winner_resp.status_code == 200 else winner_token
    winner_driver_id = win_resp.json()["ride"]["driver_id"]

    with TestClient(app) as client:
        winner_rides = client.get(
            "/drivers/my-rides",
            headers={"Authorization": f"Bearer {win_token}"},
        )
        loser_rides = client.get(
            "/drivers/my-rides",
            headers={"Authorization": f"Bearer {lose_token}"},
        )

    assert winner_rides.status_code == 200
    assert loser_rides.status_code == 200
    winner_list = winner_rides.json()
    loser_list = loser_rides.json()
    assert any(r["id"] == ride_id and r["status"] == "accepted" for r in winner_list)
    assert not any(r["id"] == ride_id for r in loser_list)
    assert lose_resp.json()["detail"]["state_changed"] is False

    db = SessionLocal()
    try:
        ride = db.query(Ride).filter(Ride.id == ride_id).one()
        assert ride.driver_id == winner_driver_id
    finally:
        db.close()
