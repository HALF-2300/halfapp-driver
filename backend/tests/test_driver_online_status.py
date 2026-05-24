"""DRIVER-001: persistent driver online/offline and dispatch availability."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from database import SessionLocal
import models.driver_approval  # noqa: F401
import models.driver_status  # noqa: F401
import models.metrics  # noqa: F401
import models.presence  # noqa: F401
import models.ride  # noqa: F401
import models.user  # noqa: F401
import routes.notifications  # noqa: F401
from main import app
from models.driver_status import DriverStatusRecord
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.datetime_utils import utc_now_naive
from services.driver_status_service import FRESHNESS_WINDOW_SECONDS


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _driver_token(db, prefix: str) -> tuple[str, int]:
    uid = uuid.uuid4().hex[:10]
    user = create_user(
        db,
        f"{prefix}_{uid}@example.com",
        f"{prefix} Driver",
        "pw12345",
        UserRole.DRIVER,
        f"DL{uid}",
        driver_approval_status="approved",
    )
    db.commit()
    return create_access_token(sub=user.email, role=user.role.value), user.id


def _rider_token(db) -> str:
    uid = uuid.uuid4().hex[:10]
    user = create_user(
        db,
        f"rider_{uid}@example.com",
        "Rider",
        "pw12345",
        UserRole.CUSTOMER,
    )
    db.commit()
    return create_access_token(sub=user.email, role=user.role.value)


def _admin_token(db) -> str:
    uid = uuid.uuid4().hex[:10]
    user = create_user(
        db,
        f"admin_{uid}@example.com",
        "Admin",
        "pw12345",
        UserRole.ADMIN,
    )
    db.commit()
    return create_access_token(sub=user.email, role=user.role.value)


def test_driver_goes_online_with_valid_coordinates():
    db = SessionLocal()
    try:
        token, driver_id = _driver_token(db, "online")
        with TestClient(app) as client:
            response = client.patch(
                "/drivers/me/status",
                headers=_headers(token),
                json={"online": True, "lat": 45.52, "lng": -122.68},
            )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["online"] is True
        assert body["last_lat"] == pytest.approx(45.52)
        assert body["last_lng"] == pytest.approx(-122.68)
        assert body["last_seen_at"] is not None

        row = db.query(DriverStatusRecord).filter(DriverStatusRecord.driver_id == driver_id).one()
        assert row.online is True
        assert row.last_lat == pytest.approx(45.52)
    finally:
        db.close()


def test_driver_goes_offline():
    db = SessionLocal()
    try:
        token, driver_id = _driver_token(db, "offline")
        with TestClient(app) as client:
            client.patch(
                "/drivers/me/status",
                headers=_headers(token),
                json={"online": True, "lat": 40.0, "lng": -74.0},
            )
            response = client.patch(
                "/drivers/me/status",
                headers=_headers(token),
                json={"online": False},
            )
        assert response.status_code == 200, response.text
        assert response.json()["online"] is False

        row = db.query(DriverStatusRecord).filter(DriverStatusRecord.driver_id == driver_id).one()
        assert row.online is False
    finally:
        db.close()


def test_online_driver_in_dispatch_available_query():
    db = SessionLocal()
    try:
        token, driver_id = _driver_token(db, "dispatch_on")
        admin = _admin_token(db)
        with TestClient(app) as client:
            client.patch(
                "/drivers/me/status",
                headers=_headers(token),
                json={"online": True, "lat": 37.77, "lng": -122.42},
            )
            available = client.get("/internal/available-drivers", headers=_headers(admin))
        assert available.status_code == 200, available.text
        assert driver_id in available.json()["driver_ids"]
    finally:
        db.close()


def test_offline_driver_not_in_dispatch_available_query():
    db = SessionLocal()
    try:
        token, driver_id = _driver_token(db, "dispatch_off")
        admin = _admin_token(db)
        with TestClient(app) as client:
            client.patch(
                "/drivers/me/status",
                headers=_headers(token),
                json={"online": True, "lat": 37.77, "lng": -122.42},
            )
            client.patch(
                "/drivers/me/status",
                headers=_headers(token),
                json={"online": False},
            )
            available = client.get("/internal/available-drivers", headers=_headers(admin))
        assert available.status_code == 200, available.text
        assert driver_id not in available.json()["driver_ids"]
    finally:
        db.close()


def test_stale_last_seen_treated_unavailable():
    db = SessionLocal()
    try:
        token, driver_id = _driver_token(db, "stale")
        admin = _admin_token(db)
        with TestClient(app) as client:
            client.patch(
                "/drivers/me/status",
                headers=_headers(token),
                json={"online": True, "lat": 37.77, "lng": -122.42},
            )
        row = db.query(DriverStatusRecord).filter(DriverStatusRecord.driver_id == driver_id).one()
        row.last_seen_at = utc_now_naive() - timedelta(seconds=FRESHNESS_WINDOW_SECONDS + 60)
        db.commit()

        with TestClient(app) as client:
            available = client.get("/internal/available-drivers", headers=_headers(admin))
        assert driver_id not in available.json()["driver_ids"]
    finally:
        db.close()


def test_location_update_while_offline_returns_400():
    db = SessionLocal()
    try:
        token, _ = _driver_token(db, "loc_off")
        with TestClient(app) as client:
            response = client.patch(
                "/drivers/me/location",
                headers=_headers(token),
                json={"lat": 45.0, "lng": -122.0},
            )
        assert response.status_code == 400, response.text
    finally:
        db.close()


def test_rider_cannot_use_driver_status_endpoint():
    db = SessionLocal()
    try:
        rider = _rider_token(db)
        with TestClient(app) as client:
            response = client.patch(
                "/drivers/me/status",
                headers=_headers(rider),
                json={"online": True, "lat": 1.0, "lng": 2.0},
            )
        assert response.status_code == 403, response.text
    finally:
        db.close()


def test_get_me_status_survives_refresh():
    db = SessionLocal()
    try:
        token, _ = _driver_token(db, "refresh")
        with TestClient(app) as client:
            client.patch(
                "/drivers/me/status",
                headers=_headers(token),
                json={"online": True, "lat": 33.45, "lng": -112.07},
            )
            read = client.get("/drivers/me/status", headers=_headers(token))
        assert read.status_code == 200, read.text
        assert read.json()["online"] is True
        assert read.json()["last_lat"] == pytest.approx(33.45)
    finally:
        db.close()
