"""HALFAPP_AUTH_REFRESH_REVOCATION_01 — refresh mint, rotation, reuse detection."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models.refresh_token import RefreshToken
from models.user import UserRole
from services.auth import create_user


def _seed_driver(email: str | None = None, password: str = "Passw0rd!"):
    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:8]
        address = email or f"refresh_{uid}@example.com"
        user = create_user(
            db,
            address,
            "Refresh Driver",
            password,
            UserRole.DRIVER,
            f"DL{uid}",
            driver_approval_status="approved",
        )
        return user.email, password, user.id
    finally:
        db.close()


def test_login_returns_refresh_token():
    email, password, _user_id = _seed_driver()
    with TestClient(app) as client:
        response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_refresh_rotation_happy_path():
    email, password, _user_id = _seed_driver()
    with TestClient(app) as client:
        login = client.post("/auth/login", json={"email": email, "password": password})
        assert login.status_code == 200
        old_refresh = login.json()["refresh_token"]

        refreshed = client.post("/auth/refresh", json={"refresh_token": old_refresh})
        assert refreshed.status_code == 200
        body = refreshed.json()
        assert body["access_token"]
        assert body["refresh_token"] != old_refresh

        reuse = client.post("/auth/refresh", json={"refresh_token": old_refresh})
        assert reuse.status_code == 401
        assert reuse.json()["detail"] == "refresh_revoked"


def test_refresh_reuse_revokes_all_active_tokens():
    email, password, user_id = _seed_driver()
    with TestClient(app) as client:
        login = client.post("/auth/login", json={"email": email, "password": password})
        first_refresh = login.json()["refresh_token"]

        rotated = client.post("/auth/refresh", json={"refresh_token": first_refresh})
        assert rotated.status_code == 200
        second_refresh = rotated.json()["refresh_token"]

        reuse_first = client.post("/auth/refresh", json={"refresh_token": first_refresh})
        assert reuse_first.status_code == 401

        reuse_second = client.post("/auth/refresh", json={"refresh_token": second_refresh})
        assert reuse_second.status_code == 401

    db = SessionLocal()
    try:
        active = (
            db.query(RefreshToken)
            .filter(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .count()
        )
        assert active == 0
    finally:
        db.close()


def test_logout_all_revokes_refresh_tokens():
    email, password, user_id = _seed_driver()
    with TestClient(app) as client:
        login = client.post("/auth/login", json={"email": email, "password": password})
        access = login.json()["access_token"]
        refresh = login.json()["refresh_token"]

        logout = client.post(
            "/auth/logout-all",
            headers={"Authorization": f"Bearer {access}"},
        )
        assert logout.status_code == 200
        assert logout.json()["ok"] is True

        after = client.post("/auth/refresh", json={"refresh_token": refresh})
        assert after.status_code == 401

    db = SessionLocal()
    try:
        active = (
            db.query(RefreshToken)
            .filter(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .count()
        )
        assert active == 0
    finally:
        db.close()


def test_refresh_disabled_returns_409(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUTH_REFRESH_ENABLED", "0")
    email, password, _user_id = _seed_driver()
    with TestClient(app) as client:
        login = client.post("/auth/login", json={"email": email, "password": password})
        assert login.status_code == 200
        assert "refresh_token" not in login.json()

        response = client.post(
            "/auth/refresh",
            json={"refresh_token": "anything"},
        )
    assert response.status_code == 409
    assert response.json()["detail"] == "refresh_disabled"
