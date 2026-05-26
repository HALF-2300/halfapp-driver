"""Phase 4 — ops console backend: admin login, ride detail, cancel, assign."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models.ride import Ride
from models.user import UserRole
from services.auth import create_access_token, create_user, get_password_hash
from services.lifecycle import RideStatus


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _admin_token(db) -> str:
    uid = uuid.uuid4().hex[:8]
    user = create_user(db, f"admin_{uid}@example.com", "Admin", "pw12345", UserRole.ADMIN)
    db.commit()
    return create_access_token(sub=user.email, role=user.role.value)


def _driver_token(db) -> tuple[str, int]:
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
    return create_access_token(sub=user.email, role=user.role.value), user.id


def test_admin_login_and_ride_detail_with_payment_fields():
    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:8]
        admin = create_user(db, f"ops_{uid}@example.com", "Ops", "secret123", UserRole.ADMIN)
        db.commit()
        ride = Ride(customer_name="Detail", status=RideStatus.REQUESTED.value, distance=3.0, customer_id=1)
        db.add(ride)
        db.commit()
        ride_id = ride.id
        admin_email = admin.email
    finally:
        db.close()

    with TestClient(app) as client:
        login = client.post("/auth/admin/login", json={"email": admin_email, "password": "secret123"})
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]
        assert login.json()["role"] == "admin"

        detail = client.get(f"/admin/rides/{ride_id}", headers=_headers(token))
        assert detail.status_code == 200, detail.text
        body = detail.json()
        assert body["id"] == ride_id
        assert "lifecycle_events" in body
        assert body["payment_status"] in (None, "pending")


def test_admin_cancel_ride():
    db = SessionLocal()
    try:
        admin_token = _admin_token(db)
        _, driver_id = _driver_token(db)
        ride = Ride(
            customer_name="Cancel me",
            status=RideStatus.ACCEPTED.value,
            distance=1.0,
            driver_id=driver_id,
        )
        db.add(ride)
        db.flush()
        from services.ride_payment import create_payment_for_ride, authorize_payment_for_ride

        create_payment_for_ride(db, ride)
        authorize_payment_for_ride(db, ride)
        db.commit()
        ride_id = ride.id
    finally:
        db.close()

    with TestClient(app) as client:
        resp = client.post(
            f"/admin/rides/{ride_id}/cancel",
            headers=_headers(admin_token),
            json={"reason": "ops test cancel"},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ride"]["status"] == RideStatus.CANCELLED.value
    assert body["ride"]["payment_status"] == "failed"


def test_admin_assign_unassigned_ride():
    db = SessionLocal()
    try:
        admin_token = _admin_token(db)
        driver_token, driver_id = _driver_token(db)
        ride = Ride(customer_name="Assign me", status=RideStatus.REQUESTED.value, distance=2.0)
        db.add(ride)
        db.commit()
        ride_id = ride.id
    finally:
        db.close()

    with TestClient(app) as client:
        client.put("/drivers/presence", headers=_headers(driver_token), json={"state": "available"})
        client.patch(
            "/drivers/me/status",
            headers=_headers(driver_token),
            json={"online": True, "lat": 45.52, "lng": -122.67},
        )
        resp = client.post(
            f"/admin/rides/{ride_id}/assign",
            headers=_headers(admin_token),
            json={"driver_id": driver_id},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ride"]["driver_id"] == driver_id
    assert body["ride"]["status"] == RideStatus.ACCEPTED.value
    assert body["ride"]["payment_status"] == "authorized"


def test_admin_drivers_include_presence_fields():
    db = SessionLocal()
    try:
        admin_token = _admin_token(db)
        _driver_token(db)
    finally:
        db.close()

    with TestClient(app) as client:
        resp = client.get("/admin/drivers", headers=_headers(admin_token))

    assert resp.status_code == 200, resp.text
    assert resp.json()
    row = resp.json()[0]
    assert "presence" in row
    assert "online" in row
    assert "active_ride_id" in row
    assert "availability_label" in row
    assert "readiness" in row
    assert "vehicle" in row
    assert "insurance" in row


def test_admin_updates_driver_readiness_fields():
    db = SessionLocal()
    try:
        admin_token = _admin_token(db)
        driver_token, driver_id = _driver_token(db)
    finally:
        db.close()

    with TestClient(app) as client:
        resp = client.patch(
            f"/admin/drivers/{driver_id}/readiness",
            headers=_headers(admin_token),
            json={
                "vehicle_make": "Toyota",
                "vehicle_model": "Prius",
                "vehicle_year": 2021,
                "license_plate": "OPS-123",
                "insurance_policy": "POL-OPS-1",
                "insurance_expires_at": "2027-05-25T00:00:00Z",
                "vehicle_ready": True,
                "reason": "ops readiness review",
            },
        )
        profile = client.get("/drivers/profile", headers=_headers(driver_token))

    assert resp.status_code == 200, resp.text
    body = resp.json()["driver"]
    assert body["readiness"]["vehicle_ready"] is True
    assert body["insurance"]["expires_at"].startswith("2027-05-25")
    assert profile.status_code == 200, profile.text
    profile_body = profile.json()
    assert profile_body["vehicle_ready"] is True
    assert profile_body["insurance_expires_at"].startswith("2027-05-25")
