"""ADMIN-001: minimal admin operations skeleton."""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models.ride import Ride
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.lifecycle import RideStatus


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _admin_token(db) -> str:
    uid = uuid.uuid4().hex[:8]
    user = create_user(db, f"admin_{uid}@example.com", "Admin", "pw12345", UserRole.ADMIN)
    db.commit()
    return create_access_token(sub=user.email, role=user.role.value)


def _driver_token(db) -> str:
    uid = uuid.uuid4().hex[:8]
    user = create_user(
        db,
        f"drv_{uid}@example.com",
        "Driver",
        "pw12345",
        UserRole.DRIVER,
        f"DL{uid}",
        driver_approval_status="approved",
    )
    db.commit()
    return create_access_token(sub=user.email, role=user.role.value)


def test_admin_lists_active_rides_rider_cannot():
    db = SessionLocal()
    try:
        admin_token = _admin_token(db)
        driver_token = _driver_token(db)
        ride = Ride(
            customer_name="Active",
            status=RideStatus.IN_PROGRESS.value,
            distance=2.0,
        )
        db.add(ride)
        db.commit()
        ride_id = ride.id
    finally:
        db.close()

    with TestClient(app) as client:
        admin_resp = client.get("/admin/rides?status=active", headers=_headers(admin_token))
        driver_resp = client.get("/admin/rides?status=active", headers=_headers(driver_token))

    assert admin_resp.status_code == 200, admin_resp.text
    assert any(row["id"] == ride_id for row in admin_resp.json()["rides"])
    assert driver_resp.status_code == 403


def test_admin_completed_rides_pagination_and_support_note():
    db = SessionLocal()
    try:
        admin_token = _admin_token(db)
        rides = [
            Ride(customer_name=f"Done {i}", status=RideStatus.COMPLETED.value, distance=1.0)
            for i in range(3)
        ]
        db.add_all(rides)
        db.commit()
        ride_id = rides[0].id
    finally:
        db.close()

    with TestClient(app) as client:
        page = client.get("/admin/rides?status=completed&page=1&page_size=2", headers=_headers(admin_token))
        note = client.post(
            f"/admin/rides/{ride_id}/notes",
            headers=_headers(admin_token),
            json={"note": "Customer called support"},
        )

    assert page.status_code == 200, page.text
    body = page.json()
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert len(body["rides"]) == 2
    assert note.status_code == 200, note.text
    assert "Customer called support" in note.json()["notes"]
