"""Extended gap-fill: messages, navigation, support, change-password."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

import models.driver_support_ticket  # noqa: F401
import models.ride_message  # noqa: F401
import models.user  # noqa: F401
from database import SessionLocal
from main import app
from models.ride import Ride
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.lifecycle import RideStatus, to_storage_ride_status
from services.rate_limit import reset_rate_limits_for_tests


def _driver_headers(db) -> tuple[dict[str, str], int]:
    stamp = uuid.uuid4().hex[:10]
    user = create_user(
        db,
        f"ext_drv_{stamp}@example.com",
        "Ext Driver",
        "TestPw1",
        UserRole.DRIVER,
        f"EXT{stamp}",
        driver_approval_status="approved",
    )
    db.commit()
    token = create_access_token(sub=user.email, role=user.role.value)
    return {"Authorization": f"Bearer {token}"}, user.id


def test_ride_messages_and_support_ticket():
    reset_rate_limits_for_tests()
    db = SessionLocal()
    try:
        headers, driver_id = _driver_headers(db)
        ride = Ride(
            customer_name="Rider",
            status=to_storage_ride_status(RideStatus.ACCEPTED),
            pickup_location="A",
            destination="B",
            pickup_latitude=45.5,
            pickup_longitude=-122.6,
            dropoff_latitude=45.51,
            dropoff_longitude=-122.61,
            distance=2.0,
            duration=10,
            driver_id=driver_id,
        )
        db.add(ride)
        db.commit()
        db.refresh(ride)
        ride_id = ride.id
    finally:
        db.close()

    with TestClient(app) as client:
        post = client.post(
            f"/drivers/rides/{ride_id}/messages",
            headers=headers,
            json={"body": "On my way"},
        )
        assert post.status_code == 200, post.text
        listing = client.get(f"/drivers/rides/{ride_id}/messages", headers=headers)
        assert listing.status_code == 200
        assert len(listing.json()["items"]) == 1

        nav = client.get(f"/drivers/rides/{ride_id}/navigation", headers=headers)
        assert nav.status_code == 200
        assert nav.json().get("external_url")

        ticket = client.post(
            f"/drivers/rides/{ride_id}/support-ticket",
            headers=headers,
            json={"message": "Wrong pickup pin", "category": "trip_issue"},
        )
        assert ticket.status_code == 200, ticket.text


def test_change_password_revokes_and_updates():
    reset_rate_limits_for_tests()
    stamp = uuid.uuid4().hex[:10]
    email = f"chgpw_{stamp}@example.com"
    db = SessionLocal()
    try:
        user = create_user(
            db,
            email,
            "Pw Driver",
            "OldPw12345",
            UserRole.DRIVER,
            f"CPW{stamp}",
            driver_approval_status="approved",
        )
        db.commit()
    finally:
        db.close()

    with TestClient(app) as client:
        login = client.post("/auth/login", json={"email": email, "password": "OldPw12345"})
        assert login.status_code == 200
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        change = client.post(
            "/auth/change-password",
            headers=headers,
            json={"current_password": "OldPw12345", "new_password": "NewPw12345"},
        )
        assert change.status_code == 200, change.text

        bad_old = client.post("/auth/login", json={"email": email, "password": "OldPw12345"})
        assert bad_old.status_code == 401

        good = client.post("/auth/login", json={"email": email, "password": "NewPw12345"})
        assert good.status_code == 200
