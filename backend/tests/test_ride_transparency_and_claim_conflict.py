"""Ride transparency endpoint and first-claim-wins 409 conflict proof."""

import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from database import SessionLocal
import models.metrics  # noqa: F401
import models.presence  # noqa: F401
import models.ride  # noqa: F401
import models.user  # noqa: F401
import routes.notifications  # noqa: F401
from main import app
from models.ledger import MarketplaceLedgerEntry
from models.metrics import RideClaimAttempt, RideVisibility
from models.ride import Ride
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.ledger import MarketplaceLedgerEventType


def _driver_token(db, prefix: str = "transparency") -> tuple[str, int]:
    uid = uuid.uuid4().hex[:10]
    user = create_user(
        db,
        f"{prefix}_driver_{uid}@example.com",
        "Transparency Driver",
        "pw12345",
        UserRole.DRIVER,
        f"TDL{uid}",
        driver_approval_status="approved",
    )
    db.commit()
    return create_access_token(sub=user.email, role=user.role.value), user.id


def _requested_ride(db, name: str = "Transparency Rider") -> int:
    ride = Ride(
        customer_name=name,
        status="requested",
        pickup_location="Transparency Pickup",
        destination="Transparency Dropoff",
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


def test_transparency_returns_visibility_proof_for_visible_ride():
    db = SessionLocal()
    try:
        token, driver_id = _driver_token(db, "visible")
        ride_id = _requested_ride(db)
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {token}"}
    with TestClient(app) as client:
        client.put("/drivers/presence", headers=headers, json={"state": "available"})
        client.get("/drivers/available-rides", headers=headers)
        response = client.get(f"/drivers/rides/{ride_id}/transparency", headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ride_id"] == str(ride_id)
    assert body["driver_id"] == str(driver_id)
    assert body["visibility"]["visible"] is True
    assert body["visibility"]["visibility_record_id"]
    assert body["visibility"]["source"] in ("open_board", "dispatch_policy", "simulation", "unknown")
    assert body["claim"]["claimable"] is True
    assert body["claim"]["current_status"] == "requested"
    assert "BACKEND_OWNED" in body["truth_labels"]
    assert body["dispatch_proof"]["driver_visibility"]


def test_transparency_shows_hidden_dismissal_for_driver():
    db = SessionLocal()
    try:
        token, driver_id = _driver_token(db, "hidden")
        ride_id = _requested_ride(db, "Hidden Transparency Rider")
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {token}"}
    with TestClient(app) as client:
        client.put("/drivers/presence", headers=headers, json={"state": "available"})
        client.get("/drivers/available-rides", headers=headers)
        client.post(f"/drivers/rides/{ride_id}/hide", headers=headers, json={"reason": "not_now"})
        response = client.get(f"/drivers/rides/{ride_id}/transparency", headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["visibility"]["visible"] is False
    assert body["dismissal"]["hidden_for_this_driver"] is True
    assert body["dismissal"]["reason"] == "not_now"
    assert body["claim"]["claimable"] is False
    assert "RIDE_HIDDEN_FOR_DRIVER" in body["truth_labels"]


def test_sequential_second_claim_returns_409_with_conflict_proof():
    db = SessionLocal()
    try:
        winner_token, winner_id = _driver_token(db, "winner")
        loser_token, loser_id = _driver_token(db, "loser")
        ride_id = _requested_ride(db, "Conflict Rider")
    finally:
        db.close()

    winner_headers = {"Authorization": f"Bearer {winner_token}"}
    loser_headers = {"Authorization": f"Bearer {loser_token}"}

    with TestClient(app) as client:
        for headers in (winner_headers, loser_headers):
            client.put("/drivers/presence", headers=headers, json={"state": "available"})

        first = client.post(f"/drivers/accept-ride/{ride_id}", headers=winner_headers)
        second = client.post(f"/drivers/accept-ride/{ride_id}", headers=loser_headers)

    assert first.status_code == 200, first.text
    assert second.status_code == 409, second.text
    conflict = second.json()["detail"]
    assert conflict["detail"] == "Ride already claimed"
    assert conflict["ride_id"] == ride_id
    assert conflict["claim_result"] == "lost"
    assert conflict["truth_status"] == "backend_conflict"
    assert conflict["reason"] == "ride_already_claimed"
    assert conflict["state_changed"] is False
    assert conflict["current_status"] == "accepted"
    assert conflict["assigned_driver_id"] == winner_id

    db = SessionLocal()
    try:
        attempts = (
            db.query(RideClaimAttempt)
            .filter(RideClaimAttempt.ride_id == ride_id)
            .order_by(RideClaimAttempt.id.asc())
            .all()
        )
        assert len(attempts) == 2
        assert attempts[0].driver_id == winner_id and attempts[0].outcome == "won"
        assert attempts[1].driver_id == loser_id and attempts[1].outcome == "conflict"

        ledger_types = [
            row[0]
            for row in db.query(MarketplaceLedgerEntry.event_type)
            .filter(MarketplaceLedgerEntry.ride_id == ride_id)
            .all()
        ]
        assert ledger_types.count("claim_attempted") == 2
        assert ledger_types.count("claim_won") == 1
        assert ledger_types.count("claim_lost") == 1
    finally:
        db.close()

    with TestClient(app) as client:
        transparency = client.get(
            f"/drivers/rides/{ride_id}/transparency",
            headers=loser_headers,
        )
    assert transparency.status_code == 200, transparency.text
    loser_view = transparency.json()
    assert loser_view["claim"]["last_claim_result"] == "lost"
    assert loser_view["claim"]["truth_status"] == "backend_conflict"
    assert loser_view["claim"]["claimable"] is False
    assert "CLAIM_CONFLICT_PROOF" in loser_view["truth_labels"]
    assert loser_view["claim"]["claimed_by_driver_id"] == str(winner_id)
    assert loser_view["audit"]["ledger_event_ids"]
    assert "email" not in str(loser_view).lower()

    marketplace_events = loser_view["dispatch_proof"].get("marketplace_ledger_events", [])
    assert marketplace_events
    driver_event_types = {
        row["event_type"]
        for row in marketplace_events
        if row["driver_id"] == loser_id
    }
    assert MarketplaceLedgerEventType.DISPATCH_CLAIM_ATTEMPTED.value in driver_event_types
    assert MarketplaceLedgerEventType.DISPATCH_CLAIM_LOST.value in driver_event_types


def test_concurrent_claims_produce_one_winner_and_one_409():
    db = SessionLocal()
    try:
        first_token, _ = _driver_token(db, "race_a")
        second_token, _ = _driver_token(db, "race_b")
        ride_id = _requested_ride(db, "Concurrent Rider")
    finally:
        db.close()

    def claim(token: str):
        with TestClient(app) as client:
            client.put("/drivers/presence", headers={"Authorization": f"Bearer {token}"}, json={"state": "available"})
            return client.post(
                f"/drivers/accept-ride/{ride_id}",
                headers={"Authorization": f"Bearer {token}"},
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = list(pool.map(claim, [first_token, second_token]))

    winners = [r for r in (first, second) if r.status_code == 200]
    losers = [r for r in (first, second) if r.status_code == 409]
    assert len(winners) == 1
    assert len(losers) == 1
    detail = losers[0].json()["detail"]
    assert detail["truth_status"] == "backend_conflict"
    assert detail["state_changed"] is False
    assert detail["current_status"] == "accepted"
    assert detail["assigned_driver_id"] is not None


def test_transparency_forbidden_when_driver_never_saw_ride():
    db = SessionLocal()
    try:
        token, _ = _driver_token(db, "stranger")
        ride_id = _requested_ride(db)
    finally:
        db.close()

    with TestClient(app) as client:
        response = client.get(
            f"/drivers/rides/{ride_id}/transparency",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 403
