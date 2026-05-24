"""Driver ride-write idempotency (HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_03)."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

import models.driver_idempotency_replay  # noqa: F401
import models.ride  # noqa: F401
import models.user  # noqa: F401
from database import SessionLocal
from main import app
from models.ride import Ride
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.lifecycle import DriverStatus
from services.rate_limit import reset_rate_limits_for_tests


def _driver_headers(db) -> dict[str, str]:
    stamp = uuid.uuid4().hex[:10]
    user = create_user(
        db,
        f"idem_drv_{stamp}@example.com",
        "Idem Driver",
        "TestPw1",
        UserRole.DRIVER,
        f"IDM{stamp}",
        driver_approval_status="approved",
    )
    user.availability = DriverStatus.AVAILABLE.value
    db.commit()
    token = create_access_token(sub=user.email, role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


def _seed_requested_ride(db) -> int:
    ride = Ride(
        customer_name="Idem Rider",
        status="requested",
        pickup_location="P1",
        destination="D1",
        distance=4.0,
        duration=12,
    )
    db.add(ride)
    db.commit()
    db.refresh(ride)
    return int(ride.id)


def test_idempotency_replays_accept_response():
    reset_rate_limits_for_tests()
    db = SessionLocal()
    try:
        headers = _driver_headers(db)
        ride_id = _seed_requested_ride(db)
        key = f"slice03-accept-{uuid.uuid4().hex}"
        idem_headers = {**headers, "Idempotency-Key": key}
    finally:
        db.close()

    with TestClient(app) as client:
        r1 = client.post(f"/drivers/accept-ride/{ride_id}", headers=idem_headers)
        assert r1.status_code == 200, r1.text
        j1 = r1.json()

        r2 = client.post(f"/drivers/accept-ride/{ride_id}", headers=idem_headers)
        assert r2.status_code == 200, r2.text
        j2 = r2.json()

    assert j1 == j2
    assert j1["ride"]["status"] == "accepted"


def test_accept_without_idempotency_key_still_works():
    reset_rate_limits_for_tests()
    db = SessionLocal()
    try:
        headers = _driver_headers(db)
        ride_id = _seed_requested_ride(db)
    finally:
        db.close()

    with TestClient(app) as client:
        response = client.post(f"/drivers/accept-ride/{ride_id}", headers=headers)
    assert response.status_code == 200


def test_idempotency_in_progress_on_parallel_key():
    """Second in-flight key without completion returns 409."""
    reset_rate_limits_for_tests()
    db = SessionLocal()
    try:
        stamp = uuid.uuid4().hex[:10]
        user = create_user(
            db,
            f"idem_stuck_{stamp}@example.com",
            "Stuck Driver",
            "TestPw1",
            UserRole.DRIVER,
            f"STK{stamp}",
            driver_approval_status="approved",
        )
        user.availability = DriverStatus.AVAILABLE.value
        ride_id = _seed_requested_ride(db)
        from models.driver_idempotency_replay import DriverIdempotencyReplay

        row = DriverIdempotencyReplay(
            driver_id=user.id,
            idempotency_key="stuck-in-progress",
            endpoint="drivers.accept-ride",
            ride_id=ride_id,
            action="accept",
            state="in_progress",
        )
        db.add(row)
        db.commit()
        token = create_access_token(sub=user.email, role=user.role.value)
        idem_headers = {
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": "stuck-in-progress",
        }
    finally:
        db.close()

    with TestClient(app) as client:
        response = client.post(f"/drivers/accept-ride/{ride_id}", headers=idem_headers)
    assert response.status_code == 409
    assert response.json()["detail"] == "idempotency_in_progress"
