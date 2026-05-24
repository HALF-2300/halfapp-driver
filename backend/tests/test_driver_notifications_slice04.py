"""In-app driver notifications (HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_04)."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

import models.user  # noqa: F401
import routes.notifications  # noqa: F401
from database import SessionLocal
from main import app
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.driver_in_app_notifications import notify_driver_in_app
from services.lifecycle import NotificationType
from services.rate_limit import reset_rate_limits_for_tests


def _driver_headers(db) -> dict[str, str]:
    stamp = uuid.uuid4().hex[:10]
    user = create_user(
        db,
        f"notif_drv_{stamp}@example.com",
        "Notif Driver",
        "TestPw1",
        UserRole.DRIVER,
        f"NTF{stamp}",
        driver_approval_status="approved",
    )
    user.availability = "available"
    db.commit()
    token = create_access_token(sub=user.email, role=user.role.value)
    return {"Authorization": f"Bearer {token}"}, user.id


def test_list_and_mark_notification_read():
    reset_rate_limits_for_tests()
    db = SessionLocal()
    try:
        headers, driver_id = _driver_headers(db)
        notify_driver_in_app(
            db,
            driver_id=driver_id,
            title="Test alert",
            message="Hello driver",
            notif_type=NotificationType.SYSTEM,
        )
        db.commit()
    finally:
        db.close()

    with TestClient(app) as client:
        listing = client.get("/notifications/", headers=headers)
        assert listing.status_code == 200, listing.text
        body = listing.json()
        assert body["unread_count"] >= 1
        notif = body["notifications"][0]
        notif_id = notif["id"]

        read_resp = client.post(f"/notifications/{notif_id}/read", headers=headers)
        assert read_resp.status_code == 200, read_resp.text

        again = client.get("/notifications/", headers=headers)
        assert again.status_code == 200
        refreshed = next(n for n in again.json()["notifications"] if n["id"] == notif_id)
        assert refreshed["read"] is True


def test_accept_ride_creates_in_app_notification():
    reset_rate_limits_for_tests()
    db = SessionLocal()
    try:
        headers, _driver_id = _driver_headers(db)
        from models.ride import Ride

        ride = Ride(
            customer_name="Notif Rider",
            status="requested",
            pickup_location="P1",
            destination="D1",
            distance=3.0,
            duration=10,
        )
        db.add(ride)
        db.commit()
        db.refresh(ride)
        ride_id = ride.id
    finally:
        db.close()

    with TestClient(app) as client:
        accept = client.post(f"/drivers/accept-ride/{ride_id}", headers=headers)
        assert accept.status_code == 200, accept.text

        listing = client.get("/notifications/", headers=headers)
        assert listing.status_code == 200
        titles = [n["title"] for n in listing.json()["notifications"]]
        assert any("accepted" in t.lower() for t in titles)
