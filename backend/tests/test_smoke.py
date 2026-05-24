"""Driver-app alignment smoke tests.

These cover the routes the driver-app depends on and the ones added during the
driver-app/backend alignment pass (`PUT /drivers/profile`,
`POST /drivers/update-location`). `conftest.py` already pins `DATABASE_URL` to
a temp SQLite file before app import, so no Docker / Postgres needed.

Run from ``backend/`` directory:
    ../.venv/Scripts/python.exe -m pytest tests/test_smoke.py -v
"""
from __future__ import annotations

import uuid

import models.user  # noqa: F401
import models.ride  # noqa: F401
import routes.notifications  # noqa: F401

from fastapi.testclient import TestClient

from main import app
from services.rate_limit import reset_rate_limits_for_tests


def _driver_payload():
    stamp = uuid.uuid4().hex[:10]
    return {
        "email": f"smoke_drv_{stamp}@example.com",
        "name": "Smoke Driver",
        "password": "TestPw1",
        "role": "driver",
        "license_no": f"DLS{stamp}",
    }


def test_health():
    with TestClient(app) as client:
        r = client.get("/health")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("status") == "ok"


def test_register_login_profile_location():
    reset_rate_limits_for_tests()
    payload = _driver_payload()

    with TestClient(app) as client:
        reg = client.post("/auth/register", json=payload)
        assert reg.status_code == 200, reg.text
        reg_body = reg.json()
        assert reg_body["role"] == "driver"
        assert reg_body.get("access_token")
        assert reg_body["user"]["availability"] == "offline"

        login = client.post(
            "/auth/login",
            json={"email": payload["email"], "password": payload["password"]},
        )
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        prof = client.put(
            "/drivers/profile",
            headers=headers,
            json={
                "phone": "555-0100",
                "vehicle_make": "Toyota",
                "vehicle_model": "Prius",
                "vehicle_year": 2020,
                "license_plate": "ABC123",
                "availability": "available",
            },
        )
        assert prof.status_code == 200, prof.text

        loc = client.post(
            "/drivers/update-location",
            headers=headers,
            json={"latitude": 37.7749, "longitude": -122.4194},
        )
        assert loc.status_code == 200, loc.text

        me = client.get("/auth/me", headers=headers)
        assert me.status_code == 200, me.text
        me_body = me.json()
        assert me_body.get("phone") == "555-0100"
        assert me_body.get("vehicle_make") == "Toyota"
        assert me_body.get("availability") == "available"
        assert me_body.get("last_latitude") == 37.7749
        assert me_body.get("last_longitude") == -122.4194

        offline = client.put(
            "/drivers/profile",
            headers=headers,
            json={"availability": "offline"},
        )
        assert offline.status_code == 200, offline.text

        me = client.get("/auth/me", headers=headers)
        assert me.status_code == 200, me.text
        assert me.json().get("availability") == "offline"
