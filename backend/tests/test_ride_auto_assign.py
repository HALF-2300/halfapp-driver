"""Phase 2: HALFAPP_AUTO_ASSIGN on rider ride create."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.lifecycle import DriverStatus


def _token(db, *, role: UserRole, prefix: str, lat: float | None = None, lng: float | None = None) -> str:
    uid = uuid.uuid4().hex[:8]
    email = f"{prefix}_{uid}@example.com"
    license_no = f"DL{uid}" if role == UserRole.DRIVER else None
    kwargs = {}
    if role == UserRole.DRIVER:
        kwargs["driver_approval_status"] = "approved"
    user = create_user(
        db,
        email,
        f"{prefix} User",
        "AutoAssign1!",
        role,
        license_no,
        **kwargs,
    )
    if role == UserRole.DRIVER:
        user.availability = DriverStatus.AVAILABLE.value
        if lat is not None and lng is not None:
            user.last_latitude = lat
            user.last_longitude = lng
    db.commit()
    return create_access_token(user=user)


def _ride_body(**overrides):
    body = {
        "pickup_location": "Pickup",
        "dropoff_location": "Dropoff",
        "pickup_latitude": 45.523,
        "pickup_longitude": -122.676,
        "dropoff_latitude": 45.530,
        "dropoff_longitude": -122.650,
    }
    body.update(overrides)
    return body


@pytest.fixture(autouse=True)
def _enable_auto_assign(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HALFAPP_AUTO_ASSIGN", "1")
    monkeypatch.setenv("HALFAPP_OPEN_BOARD_DISPATCH", "1")
    monkeypatch.setenv("HALFAPP_AUTO_ASSIGN_MODE", "nearest")


def test_rider_create_auto_assigns_nearest_online_driver():
    db = SessionLocal()
    try:
        rider_token = _token(db, role=UserRole.CUSTOMER, prefix="aa_rider")
        near_token = _token(db, role=UserRole.DRIVER, prefix="aa_near", lat=45.524, lng=-122.675)
        far_token = _token(db, role=UserRole.DRIVER, prefix="aa_far", lat=45.600, lng=-122.800)
    finally:
        db.close()

    with TestClient(app) as client:
        for token in (near_token, far_token):
            client.put(
                "/drivers/presence",
                headers={"Authorization": f"Bearer {token}"},
                json={"state": "available"},
            )

        created = client.post(
            "/rides/",
            headers={"Authorization": f"Bearer {rider_token}"},
            json=_ride_body(),
        )
        assert created.status_code == 200, created.text
        ride = created.json()["ride"]
        assert ride["status"] == "accepted"
        assert ride["driver_id"] is not None
        assert ride.get("lifecycle_reason") == "auto_assigned"
        ride_id = ride["id"]

        near_me = client.get("/drivers/my-rides", headers={"Authorization": f"Bearer {near_token}"})
        far_me = client.get("/drivers/my-rides", headers={"Authorization": f"Bearer {far_token}"})
        near_ids = {r["id"] for r in near_me.json()}
        far_ids = {r["id"] for r in far_me.json()}
        assert ride_id in near_ids
        assert ride_id not in far_ids

        available_far = client.get(
            "/drivers/available-rides",
            headers={"Authorization": f"Bearer {far_token}"},
        )
        assert all(r["id"] != ride_id for r in available_far.json())


def test_second_driver_cannot_claim_auto_assigned_ride():
    db = SessionLocal()
    try:
        rider_token = _token(db, role=UserRole.CUSTOMER, prefix="aa_r2")
        d1 = _token(db, role=UserRole.DRIVER, prefix="aa_d1", lat=45.524, lng=-122.675)
        d2 = _token(db, role=UserRole.DRIVER, prefix="aa_d2", lat=45.525, lng=-122.676)
    finally:
        db.close()

    with TestClient(app) as client:
        for token in (d1, d2):
            client.put(
                "/drivers/presence",
                headers={"Authorization": f"Bearer {token}"},
                json={"state": "available"},
            )
        created = client.post(
            "/rides/",
            headers={"Authorization": f"Bearer {rider_token}"},
            json=_ride_body(),
        )
        ride_id = created.json()["ride"]["id"]
        conflict = client.post(
            f"/drivers/accept-ride/{ride_id}",
            headers={"Authorization": f"Bearer {d2}"},
        )
        assert conflict.status_code == 409


def test_no_online_driver_leaves_ride_requested(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HALFAPP_AUTO_ASSIGN", "1")

    def _no_drivers(db, ride_id: int):
        return []

    monkeypatch.setattr(
        "services.ride_auto_assign.eligible_dispatch_driver_ids",
        _no_drivers,
    )
    db = SessionLocal()
    try:
        rider_token = _token(db, role=UserRole.CUSTOMER, prefix="aa_none")
    finally:
        db.close()

    with TestClient(app) as client:
        created = client.post(
            "/rides/",
            headers={"Authorization": f"Bearer {rider_token}"},
            json=_ride_body(),
        )
        assert created.status_code == 200
        ride = created.json()["ride"]
        assert ride["status"] == "requested"
        assert ride.get("driver_id") is None
