"""Driver gap-fill: settings, trips filter, password reset."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

import models.password_reset_token  # noqa: F401
import models.user  # noqa: F401
from database import SessionLocal
from main import app
from models.ride import Ride
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.lifecycle import to_storage_ride_status, RideStatus
from services.rate_limit import reset_rate_limits_for_tests


def _driver_headers(db) -> dict[str, str]:
    stamp = uuid.uuid4().hex[:10]
    user = create_user(
        db,
        f"gap_drv_{stamp}@example.com",
        "Gap Driver",
        "TestPw1",
        UserRole.DRIVER,
        f"GAP{stamp}",
        driver_approval_status="approved",
    )
    user.availability = "available"
    db.commit()
    token = create_access_token(sub=user.email, role=user.role.value)
    return {"Authorization": f"Bearer {token}"}, user.id


def test_password_reset_flow():
    reset_rate_limits_for_tests()
    stamp = uuid.uuid4().hex[:10]
    email = f"reset_{stamp}@example.com"
    db = SessionLocal()
    try:
        create_user(
            db,
            email,
            "Reset Driver",
            "OldPw12345",
            UserRole.DRIVER,
            f"RST{stamp}",
            driver_approval_status="approved",
        )
        db.commit()
    finally:
        db.close()

    with TestClient(app) as client:
        forgot = client.post("/auth/forgot-password", json={"email": email})
        assert forgot.status_code == 200, forgot.text
        token = forgot.json().get("reset_token")
        assert token

        reset = client.post(
            "/auth/reset-password",
            json={"token": token, "new_password": "NewPw12345"},
        )
        assert reset.status_code == 200, reset.text

        login = client.post("/auth/login", json={"email": email, "password": "NewPw12345"})
        assert login.status_code == 200, login.text


def test_my_rides_status_filter():
    reset_rate_limits_for_tests()
    db = SessionLocal()
    try:
        headers, driver_id = _driver_headers(db)
        completed = Ride(
            customer_name="Done",
            status=to_storage_ride_status(RideStatus.COMPLETED),
            pickup_location="A",
            destination="B",
            distance=2.0,
            duration=5,
            driver_id=driver_id,
        )
        open_ride = Ride(
            customer_name="Open",
            status=to_storage_ride_status(RideStatus.ACCEPTED),
            pickup_location="C",
            destination="D",
            distance=1.0,
            duration=4,
            driver_id=driver_id,
        )
        db.add_all([completed, open_ride])
        db.commit()
    finally:
        db.close()

    with TestClient(app) as client:
        only_completed = client.get(
            "/drivers/my-rides?status=completed",
            headers=headers,
        )
        assert only_completed.status_code == 200
        statuses = {r["status"] for r in only_completed.json()}
        assert statuses == {"completed"}
