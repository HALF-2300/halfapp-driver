"""RIDE-002: driver eligibility and claim guards (403 / 409, no ride mutation when ineligible)."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from database import SessionLocal
import models.metrics  # noqa: F401
import models.presence  # noqa: F401
import models.ride  # noqa: F401
import models.user  # noqa: F401
import routes.notifications  # noqa: F401
from main import app
from models.ride import Ride
from models.user import User, UserRole
from services.auth import create_access_token, create_user
from services.lifecycle import DriverStatus, RideStatus


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _driver_token(
    db,
    prefix: str,
    *,
    driver_approval_status: str = "approved",
    is_active: bool = True,
) -> tuple[str, int]:
    uid = uuid.uuid4().hex[:10]
    user = create_user(
        db,
        f"{prefix}_{uid}@example.com",
        f"{prefix} Driver",
        "pw12345",
        UserRole.DRIVER,
        f"DL{uid}",
        driver_approval_status=driver_approval_status,
    )
    user.is_active = is_active
    db.commit()
    return create_access_token(sub=user.email, role=user.role.value), user.id


def _rider_token(db) -> str:
    uid = uuid.uuid4().hex[:10]
    user = create_user(
        db,
        f"rider_{uid}@example.com",
        "Rider",
        "pw12345",
        UserRole.CUSTOMER,
    )
    db.commit()
    return create_access_token(sub=user.email, role=user.role.value)


def _requested_ride(db) -> int:
    ride = Ride(
        customer_name="Eligibility Rider",
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
    return client.post(f"/drivers/accept-ride/{ride_id}", headers=headers)


def test_offline_driver_accept_returns_409_and_does_not_claim():
    db = SessionLocal()
    try:
        token, _ = _driver_token(db, "offline")
        ride_id = _requested_ride(db)
    finally:
        db.close()

    with TestClient(app) as client:
        response = _accept(client, token, ride_id, presence="offline")

    assert response.status_code == 409, response.text
    assert response.json()["detail"]["reason"] == "presence_offline"
    assert response.json()["detail"]["state_changed"] is False

    db = SessionLocal()
    try:
        ride = db.query(Ride).filter(Ride.id == ride_id).one()
        assert ride.driver_id is None
        assert ride.status == RideStatus.REQUESTED.value
    finally:
        db.close()


@pytest.mark.parametrize("approval_status", ["pending", "rejected", "suspended"])
def test_unapproved_driver_accept_returns_403(approval_status: str):
    db = SessionLocal()
    try:
        token, _ = _driver_token(db, f"approval_{approval_status}", driver_approval_status=approval_status)
        ride_id = _requested_ride(db)
    finally:
        db.close()

    with TestClient(app) as client:
        response = _accept(client, token, ride_id)

    assert response.status_code == 403, response.text

    db = SessionLocal()
    try:
        ride = db.query(Ride).filter(Ride.id == ride_id).one()
        assert ride.driver_id is None
    finally:
        db.close()


def test_busy_driver_with_active_ride_accept_returns_409():
    db = SessionLocal()
    try:
        token, driver_id = _driver_token(db, "busy_active", driver_approval_status="approved")
        driver = db.query(User).filter(User.id == driver_id).one()
        driver.availability = DriverStatus.AVAILABLE.value
        db.commit()
        active = Ride(
            customer_name="Active",
            status=RideStatus.ACCEPTED.value,
            driver_id=driver_id,
            distance=1.0,
        )
        db.add(active)
        db.commit()
        ride_id = _requested_ride(db)
    finally:
        db.close()

    with TestClient(app) as client:
        response = _accept(client, token, ride_id)

    assert response.status_code == 409, response.text
    assert response.json()["detail"]["reason"] == "driver_already_on_active_ride"

    db = SessionLocal()
    try:
        pool_ride = db.query(Ride).filter(Ride.id == ride_id).one()
        assert pool_ride.driver_id is None
    finally:
        db.close()


def test_rider_token_accept_returns_403():
    db = SessionLocal()
    try:
        rider_token = _rider_token(db)
        ride_id = _requested_ride(db)
    finally:
        db.close()

    with TestClient(app) as client:
        response = client.post(
            f"/drivers/accept-ride/{ride_id}",
            headers=_headers(rider_token),
        )

    assert response.status_code == 403, response.text

    db = SessionLocal()
    try:
        ride = db.query(Ride).filter(Ride.id == ride_id).one()
        assert ride.driver_id is None
    finally:
        db.close()


def test_second_accept_after_success_returns_409():
    db = SessionLocal()
    try:
        token, driver_id = _driver_token(db, "double_accept")
        ride_id = _requested_ride(db)
    finally:
        db.close()

    with TestClient(app) as client:
        first = _accept(client, token, ride_id)
        second = _accept(client, token, ride_id)

    assert first.status_code == 200, first.text
    assert second.status_code == 409, second.text
    conflict = second.json()["detail"]
    assert conflict["reason"] == "ride_already_claimed"
    assert conflict["ride_id"] == ride_id
    assert conflict["assigned_driver_id"] == driver_id
    assert conflict["state_changed"] is False


def test_decline_on_unassigned_requested_does_not_claim_ride():
    db = SessionLocal()
    try:
        token, _ = _driver_token(db, "decline_pool")
        ride_id = _requested_ride(db)
    finally:
        db.close()

    with TestClient(app) as client:
        client.put("/drivers/presence", headers=_headers(token), json={"state": "available"})
        response = client.post(
            f"/drivers/decline-ride/{ride_id}",
            headers=_headers(token),
            json={"reason": "not_for_me"},
        )

    assert response.status_code == 409, response.text

    db = SessionLocal()
    try:
        ride = db.query(Ride).filter(Ride.id == ride_id).one()
        assert ride.driver_id is None
        assert ride.status == RideStatus.REQUESTED.value
    finally:
        db.close()
