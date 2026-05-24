"""AUTH-001: JWT role claims, structured 401 errors, and lane guards."""

from __future__ import annotations

import datetime as dt
import uuid

import jwt
from fastapi.testclient import TestClient

from config import SECRET_KEY
from main import app
from models.user import UserRole
from services.auth import ALGORITHM, create_access_token, create_user, decode_token
from services.auth_errors import (
    AUTH_ERROR_INVALID_TOKEN,
    AUTH_ERROR_TOKEN_EXPIRED,
    AUTH_ERROR_UNAUTHENTICATED,
)
from database import SessionLocal


def _token_for(role: UserRole) -> str:
    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:10]
        license_no = f"AUTH{uid}" if role == UserRole.DRIVER else None
        kwargs = {}
        if role == UserRole.DRIVER:
            kwargs["driver_approval_status"] = "approved"
        user = create_user(
            db,
            f"auth001_{role.value}_{uid}@example.com",
            f"AUTH {role.value}",
            "pw12345",
            role,
            license_no,
            **kwargs,
        )
        return create_access_token(user=user)
    finally:
        db.close()


def _headers(token: str | None) -> dict[str, str]:
    if token is None:
        return {}
    return {"Authorization": f"Bearer {token}"}


def _detail_error(response) -> str:
    detail = response.json().get("detail")
    if isinstance(detail, dict):
        return detail.get("error", "")
    return str(detail)


def test_missing_token_returns_unauthenticated():
    with TestClient(app) as client:
        response = client.get("/drivers/my-rides")
    assert response.status_code == 401
    assert _detail_error(response) == AUTH_ERROR_UNAUTHENTICATED


def test_invalid_token_returns_invalid_token():
    with TestClient(app) as client:
        response = client.get("/drivers/my-rides", headers=_headers("not-a-real-token"))
    assert response.status_code == 401
    assert _detail_error(response) == AUTH_ERROR_INVALID_TOKEN


def test_expired_token_returns_token_expired():
    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:10]
        user = create_user(
            db,
            f"auth001_expired_{uid}@example.com",
            "Expired",
            "pw12345",
            UserRole.DRIVER,
            f"EXP{uid}",
            driver_approval_status="approved",
        )
        email = user.email
        user_id = user.id
    finally:
        db.close()

    issued_at = dt.datetime.utcnow() - dt.timedelta(hours=2)
    expire = issued_at - dt.timedelta(minutes=5)
    payload = {
        "sub": email,
        "email": email,
        "user_id": user_id,
        "role": "driver",
        "iat": issued_at,
        "exp": expire,
    }
    expired_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    with TestClient(app) as client:
        response = client.get("/drivers/my-rides", headers=_headers(expired_token))
    assert response.status_code == 401
    assert _detail_error(response) == AUTH_ERROR_TOKEN_EXPIRED


def test_jwt_payload_includes_required_claims():
    token = _token_for(UserRole.DRIVER)
    payload = decode_token(token)
    assert payload is not None
    assert payload.get("user_id") is not None
    assert payload.get("role") == "driver"
    assert payload.get("email")
    assert payload.get("iat") is not None
    assert payload.get("exp") is not None


def test_rider_token_on_driver_endpoint_returns_403():
    rider_token = _token_for(UserRole.CUSTOMER)
    with TestClient(app) as client:
        response = client.get("/drivers/available-rides", headers=_headers(rider_token))
    assert response.status_code == 403


def test_driver_token_on_rider_endpoint_returns_403():
    driver_token = _token_for(UserRole.DRIVER)
    payload = {
        "pickup_location": "Origin",
        "dropoff_location": "Dest",
        "pickup_latitude": 45.501,
        "pickup_longitude": -122.681,
        "dropoff_latitude": 45.551,
        "dropoff_longitude": -122.611,
        "distance_km": 3.5,
    }
    with TestClient(app) as client:
        response = client.post("/rides/", headers=_headers(driver_token), json=payload)
    assert response.status_code == 403


def test_driver_token_on_admin_endpoint_returns_403():
    driver_token = _token_for(UserRole.DRIVER)
    with TestClient(app) as client:
        response = client.get("/internal/system-health", headers=_headers(driver_token))
    assert response.status_code == 403


def test_admin_token_on_admin_endpoint_returns_200():
    admin_token = _token_for(UserRole.ADMIN)
    with TestClient(app) as client:
        response = client.get("/internal/system-health", headers=_headers(admin_token))
    assert response.status_code == 200, response.text
