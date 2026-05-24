"""SECURITY-001: auth endpoint rate limiting."""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from main import app
from services.rate_limit import reset_rate_limits_for_tests


def test_login_rate_limit_returns_429_with_retry_after():
    reset_rate_limits_for_tests()
    email = f"ratelimit_{uuid.uuid4().hex[:8]}@example.com"
    with TestClient(app) as client:
        for _ in range(10):
            response = client.post("/auth/login", json={"email": email, "password": "wrong"})
            assert response.status_code in (401, 403), response.text
        blocked = client.post("/auth/login", json={"email": email, "password": "wrong"})
    assert blocked.status_code == 429, blocked.text
    body = blocked.json()
    assert body["error"] == "too_many_requests"
    assert body["retry_after"] >= 1
    assert blocked.headers.get("retry-after") is not None


def test_register_rate_limit_returns_429():
    reset_rate_limits_for_tests()
    with TestClient(app) as client:
        for i in range(11):
            response = client.post(
                "/auth/register",
                json={
                    "email": f"reg_{uuid.uuid4().hex[:6]}@example.com",
                    "name": "Rate Limit",
                    "password": "secret12",
                    "role": "driver",
                    "license_no": f"RL{i:05d}",
                },
            )
            if i < 10:
                assert response.status_code in (200, 400), response.text
        blocked = client.post(
            "/auth/register",
            json={
                "email": f"reg_{uuid.uuid4().hex[:6]}@example.com",
                "name": "Rate Limit",
                "password": "secret12",
                "role": "driver",
                "license_no": "RL99999",
            },
        )
    assert blocked.status_code == 429
