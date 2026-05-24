"""Driver app profile/settings persistence (HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_02)."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

import models.driver_app_settings  # noqa: F401
import models.driver_profile  # noqa: F401
import models.user  # noqa: F401
from main import app
from services.rate_limit import reset_rate_limits_for_tests


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _register_driver(client: TestClient) -> dict[str, str]:
    stamp = uuid.uuid4().hex[:10]
    payload = {
        "email": f"slice02_{stamp}@example.com",
        "name": "Slice02 Driver",
        "password": "TestPw1",
        "role": "driver",
        "license_no": f"S02{stamp}",
        "driver_approval_status": "approved",
    }
    reg = client.post("/auth/register", json=payload)
    assert reg.status_code == 200, reg.text
    return _headers(reg.json()["access_token"])


def test_get_settings_defaults():
    reset_rate_limits_for_tests()
    with TestClient(app) as client:
        headers = _register_driver(client)
        response = client.get("/drivers/me/settings", headers=headers)

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["units"] in ("mi", "km")
    assert data["theme"] in ("light", "dark", "system")
    assert "notif_push_enabled" in data
    assert data["notif_sound_enabled"] is True


def test_put_settings_persists():
    reset_rate_limits_for_tests()
    with TestClient(app) as client:
        headers = _register_driver(client)
        response = client.put(
            "/drivers/me/settings",
            json={"units": "km", "theme": "dark", "notif_push_enabled": True},
            headers=headers,
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["units"] == "km"
        assert data["theme"] == "dark"
        assert data["notif_push_enabled"] is True

        again = client.get("/drivers/me/settings", headers=headers)
    assert again.status_code == 200
    assert again.json()["units"] == "km"


def test_put_settings_rejects_invalid_units():
    reset_rate_limits_for_tests()
    with TestClient(app) as client:
        headers = _register_driver(client)
        response = client.put(
            "/drivers/me/settings",
            json={"units": "nautical"},
            headers=headers,
        )
    assert response.status_code == 400


def test_profile_roundtrip():
    reset_rate_limits_for_tests()
    with TestClient(app) as client:
        headers = _register_driver(client)
        get_resp = client.get("/drivers/me/profile", headers=headers)
        assert get_resp.status_code == 200

        put_resp = client.put(
            "/drivers/me/profile",
            json={"display_name": "Test Driver", "phone_e164": "+15551234567"},
            headers=headers,
        )
        assert put_resp.status_code == 200, put_resp.text
        body = put_resp.json()
        assert body["display_name"] == "Test Driver"
        assert body["phone_e164"] == "+15551234567"


def test_legacy_driver_profile_unchanged():
    """GET /drivers/profile contract must remain for Slice 01 read path."""
    reset_rate_limits_for_tests()
    with TestClient(app) as client:
        headers = _register_driver(client)
        response = client.get("/drivers/profile", headers=headers)
    assert response.status_code == 200
    assert response.json().get("read_only") is True
    assert "email" in response.json()
