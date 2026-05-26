"""Read-only GET /drivers/profile (HALFAPP_DRIVER_PROFILE_SETTINGS_READONLY_01)."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

import models.driver_approval  # noqa: F401
import models.user  # noqa: F401
import routes.notifications  # noqa: F401
from database import SessionLocal
from main import app
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.rate_limit import reset_rate_limits_for_tests


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _register_driver(client: TestClient, *, approval_status: str = "approved") -> tuple[dict, dict[str, str]]:
    stamp = uuid.uuid4().hex[:10]
    payload = {
        "email": f"prof_drv_{stamp}@example.com",
        "name": "Profile Driver",
        "password": "TestPw1",
        "role": "driver",
        "license_no": f"DLP{stamp}",
        "driver_approval_status": approval_status,
    }
    reg = client.post("/auth/register", json=payload)
    assert reg.status_code == 200, reg.text
    token = reg.json()["access_token"]
    return payload, _headers(token)


def test_driver_profile_read_success():
    reset_rate_limits_for_tests()
    with TestClient(app) as client:
        payload, headers = _register_driver(client)
        response = client.get("/drivers/profile", headers=headers)

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["email"] == payload["email"]
    assert data["name"] == payload["name"]
    assert data["role"] == "driver"
    assert "approval_status" in data
    assert data["read_only"] is True
    assert "vehicle" in data
    assert data["vehicle"]["make"] == "Not registered"
    assert data["vehicle_ready"] is False
    assert data["insurance_expires_at"] is None


def test_driver_profile_requires_driver():
    reset_rate_limits_for_tests()
    db = SessionLocal()
    try:
        stamp = uuid.uuid4().hex[:10]
        rider = create_user(
            db,
            f"rider_prof_{stamp}@example.com",
            "Rider",
            "pw12345",
            UserRole.CUSTOMER,
        )
        db.commit()
        rider_token = create_access_token(sub=rider.email, role=rider.role.value)
    finally:
        db.close()

    with TestClient(app) as client:
        response = client.get("/drivers/profile", headers=_headers(rider_token))

    assert response.status_code == 403, response.text


def test_driver_profile_requires_auth():
    reset_rate_limits_for_tests()
    with TestClient(app) as client:
        response = client.get("/drivers/profile")
    assert response.status_code == 401, response.text
