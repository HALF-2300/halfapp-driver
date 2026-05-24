"""DRIVER-001B: presence hardening, active-ride busy guard, dispatch pool exclusion."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from database import SessionLocal
import models.metrics  # noqa: F401
import models.presence  # noqa: F401
import models.ride  # noqa: F401
import models.user  # noqa: F401
import routes.notifications  # noqa: F401
from main import app
from models.presence import DriverPresence
from models.ride import Ride
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.datetime_utils import utc_now_naive
from services.lifecycle import DriverStatus, RideStatus


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _driver_token(db, prefix: str, *, availability: str | None = None) -> tuple[str, int]:
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
    if availability is not None:
        user.availability = availability
    db.commit()
    return create_access_token(sub=user.email, role=user.role.value), user.id


def _requested_ride(db, name: str = "Pool Rider") -> int:
    ride = Ride(
        customer_name=name,
        status=RideStatus.REQUESTED.value,
        pickup_location="Pickup",
        destination="Dropoff",
        distance=2.0,
    )
    db.add(ride)
    db.commit()
    db.refresh(ride)
    return ride.id


def _prime_online(client: TestClient, token: str) -> None:
    client.patch(
        "/drivers/me/status",
        headers=_headers(token),
        json={"online": True, "lat": 45.523064, "lng": -122.676483},
    )


def _accept(client: TestClient, token: str, ride_id: int, *, presence: str | None = "available"):
    headers = _headers(token)
    if presence == "available":
        _prime_online(client, token)
    elif presence is not None:
        client.put("/drivers/presence", headers=headers, json={"state": presence})
    else:
        _prime_online(client, token)
    return client.post(f"/drivers/accept-ride/{ride_id}", headers=headers)


def _assert_pool_ride_unchanged(ride_id: int) -> None:
    db = SessionLocal()
    try:
        ride = db.query(Ride).filter(Ride.id == ride_id).one()
        assert ride.driver_id is None
        assert ride.status == RideStatus.REQUESTED.value
    finally:
        db.close()


def _assert_blocked_409(response, *, reason: str, ride_id: int) -> None:
    assert response.status_code == 409, response.text
    detail = response.json()["detail"]
    assert detail["reason"] == reason
    assert detail["ride_id"] == ride_id
    assert detail["claim_result"] == "blocked"
    assert detail["truth_status"] == "driver_ineligible"
    assert detail["state_changed"] is False


@pytest.mark.parametrize(
    "presence_state,expected_reason",
    [
        ("offline", "presence_offline"),
        ("paused", "presence_paused"),
    ],
)
def test_non_available_presence_cannot_accept(presence_state: str, expected_reason: str):
    db = SessionLocal()
    try:
        token, _ = _driver_token(db, f"presence_{presence_state}")
        ride_id = _requested_ride(db)
    finally:
        db.close()

    with TestClient(app) as client:
        response = _accept(client, token, ride_id, presence=presence_state)

    _assert_blocked_409(response, reason=expected_reason, ride_id=ride_id)
    assert response.json()["detail"]["effective_presence_state"] == presence_state
    _assert_pool_ride_unchanged(ride_id)


def test_stale_presence_cannot_accept():
    db = SessionLocal()
    try:
        token, driver_id = _driver_token(db, "stale_accept")
        ride_id = _requested_ride(db)
    finally:
        db.close()

    headers = _headers(token)
    with TestClient(app) as client:
        _prime_online(client, token)
        client.post("/drivers/heartbeat", headers=headers)

    db = SessionLocal()
    try:
        row = db.query(DriverPresence).filter(DriverPresence.driver_id == driver_id).one()
        row.heartbeat_at = utc_now_naive() - timedelta(seconds=120)
        db.commit()
    finally:
        db.close()

    with TestClient(app) as client:
        response = client.post(f"/drivers/accept-ride/{ride_id}", headers=headers)

    _assert_blocked_409(response, reason="presence_stale", ride_id=ride_id)
    assert response.json()["detail"]["effective_presence_state"] == "stale"
    _assert_pool_ride_unchanged(ride_id)


def test_disconnected_presence_cannot_accept():
    db = SessionLocal()
    try:
        token, driver_id = _driver_token(db, "disc_accept")
        ride_id = _requested_ride(db)
    finally:
        db.close()

    headers = _headers(token)
    with TestClient(app) as client:
        _prime_online(client, token)
        client.post("/drivers/heartbeat", headers=headers)

    db = SessionLocal()
    try:
        row = db.query(DriverPresence).filter(DriverPresence.driver_id == driver_id).one()
        row.heartbeat_at = utc_now_naive() - timedelta(seconds=360)
        db.commit()
    finally:
        db.close()

    with TestClient(app) as client:
        response = client.post(f"/drivers/accept-ride/{ride_id}", headers=headers)

    _assert_blocked_409(response, reason="presence_disconnected", ride_id=ride_id)
    assert response.json()["detail"]["effective_presence_state"] == "disconnected"
    _assert_pool_ride_unchanged(ride_id)


def test_available_presence_can_accept_when_no_active_ride():
    db = SessionLocal()
    try:
        token, driver_id = _driver_token(db, "available_ok")
        ride_id = _requested_ride(db)
    finally:
        db.close()

    with TestClient(app) as client:
        response = _accept(client, token, ride_id, presence="available")

    assert response.status_code == 200, response.text
    assert response.json()["ride"]["driver_id"] == driver_id
    assert response.json()["ride"]["status"] == RideStatus.ACCEPTED.value


@pytest.mark.parametrize("active_status", ["accepted", "driver_arrived", "in_progress"])
def test_driver_with_active_ride_cannot_accept_second(active_status: str):
    db = SessionLocal()
    try:
        token, driver_id = _driver_token(db, f"active_{active_status}")
        active = Ride(
            customer_name="On trip",
            status=active_status,
            driver_id=driver_id,
            distance=1.0,
        )
        db.add(active)
        db.commit()
        db.refresh(active)
        active_ride_id = active.id
        pool_ride_id = _requested_ride(db, "Second pool ride")
    finally:
        db.close()

    with TestClient(app) as client:
        response = _accept(client, token, pool_ride_id, presence="available")

    _assert_blocked_409(response, reason="driver_already_on_active_ride", ride_id=pool_ride_id)
    assert response.json()["detail"]["active_ride_id"] == active_ride_id
    _assert_pool_ride_unchanged(pool_ride_id)

    db = SessionLocal()
    try:
        still_active = db.query(Ride).filter(Ride.id == active_ride_id).one()
        assert still_active.status == active_status
        assert still_active.driver_id == driver_id
    finally:
        db.close()


def test_profile_busy_without_active_ride_returns_409():
    db = SessionLocal()
    try:
        token, driver_id = _driver_token(db, "profile_busy", availability=DriverStatus.BUSY.value)
        ride_id = _requested_ride(db)
        row = db.query(DriverPresence).filter(DriverPresence.driver_id == driver_id).first()
        if row is None:
            row = DriverPresence(
                driver_id=driver_id,
                requested_state="available",
                effective_state="available",
                state_changed_at=utc_now_naive(),
                heartbeat_at=utc_now_naive(),
                updated_at=utc_now_naive(),
            )
            db.add(row)
        else:
            row.requested_state = "available"
            row.effective_state = "available"
            row.heartbeat_at = utc_now_naive()
        db.commit()
    finally:
        db.close()

    with TestClient(app) as client:
        response = client.post(f"/drivers/accept-ride/{ride_id}", headers=_headers(token))

    _assert_blocked_409(response, reason="driver_busy", ride_id=ride_id)
    _assert_pool_ride_unchanged(ride_id)


def test_available_rides_empty_when_driver_has_active_ride():
    db = SessionLocal()
    try:
        token, driver_id = _driver_token(db, "dispatch_busy")
        active = Ride(
            customer_name="Blocks pool",
            status=RideStatus.ACCEPTED.value,
            driver_id=driver_id,
            distance=1.0,
        )
        pool = Ride(
            customer_name="Should not list",
            status=RideStatus.REQUESTED.value,
            distance=2.0,
        )
        db.add_all([active, pool])
        db.commit()
        pool_id = pool.id
    finally:
        db.close()

    with TestClient(app) as client:
        _prime_online(client, token)
        listed = client.get("/drivers/available-rides", headers=_headers(token))

    assert listed.status_code == 200, listed.text
    assert pool_id not in [r["id"] for r in listed.json()]


def test_available_rides_empty_when_presence_stale():
    db = SessionLocal()
    try:
        token, driver_id = _driver_token(db, "dispatch_stale")
        pool_id = _requested_ride(db)
    finally:
        db.close()

    headers = _headers(token)
    with TestClient(app) as client:
        _prime_online(client, token)
        client.post("/drivers/heartbeat", headers=headers)

    db = SessionLocal()
    try:
        row = db.query(DriverPresence).filter(DriverPresence.driver_id == driver_id).one()
        row.heartbeat_at = utc_now_naive() - timedelta(seconds=120)
        db.commit()
    finally:
        db.close()

    with TestClient(app) as client:
        listed = client.get("/drivers/available-rides", headers=headers)

    assert listed.status_code == 200, listed.text
    assert pool_id not in [r["id"] for r in listed.json()]
