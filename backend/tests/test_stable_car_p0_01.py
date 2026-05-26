"""
HALFAPP_DRIVER_STABLE_CAR_P0_01 — delivery execution car (API spine).

Proves on SQLite (default dev DB):
  requester job → accept → arrive → start → complete → receipt → ops visibility

Does not cover: push, POD, merchant, real PSP, batching, ML dispatch.
PostgreSQL claim-race: tests/test_postgres_claim_race_proof_01.py (separate marker).
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.lifecycle import DriverStatus


def _token(db, *, role: UserRole, prefix: str) -> str:
    uid = uuid.uuid4().hex[:8]
    email = f"{prefix}_{uid}@example.com"
    license_no = f"SC{uid}" if role == UserRole.DRIVER else None
    kwargs = {}
    if role == UserRole.DRIVER:
        kwargs["driver_approval_status"] = "approved"
    user = create_user(
        db,
        email,
        f"{prefix} User",
        "StableCar1!",
        role,
        license_no,
        **kwargs,
    )
    if role == UserRole.DRIVER:
        user.availability = DriverStatus.AVAILABLE.value
    db.commit()
    return create_access_token(sub=user.email, role=user.role.value)


def _admin_token(db) -> str:
    uid = uuid.uuid4().hex[:8]
    user = create_user(db, f"admin_sc_{uid}@example.com", "Ops", "StableCar1!", UserRole.ADMIN)
    db.commit()
    return create_access_token(sub=user.email, role=user.role.value)


def test_stable_car_full_loop_receipt_and_ops_visibility():
    db = SessionLocal()
    try:
        rider_token = _token(db, role=UserRole.CUSTOMER, prefix="sc_rider")
        driver_token = _token(db, role=UserRole.DRIVER, prefix="sc_driver")
        admin_token = _admin_token(db)
    finally:
        db.close()

    with TestClient(app) as client:
        created = client.post(
            "/rides/",
            headers={"Authorization": f"Bearer {rider_token}"},
            json={
                "pickup_location": "Stable Pickup",
                "dropoff_location": "Stable Dropoff",
                "pickup_latitude": 45.501,
                "pickup_longitude": -122.678,
                "dropoff_latitude": 45.515,
                "dropoff_longitude": -122.655,
                "distance_km": 2.5,
            },
        )
        assert created.status_code == 200, created.text
        ride_id = created.json()["ride"]["id"]

        client.put(
            "/drivers/presence",
            headers={"Authorization": f"Bearer {driver_token}"},
            json={"state": "available"},
        )

        accept = client.post(
            f"/drivers/accept-ride/{ride_id}",
            headers={"Authorization": f"Bearer {driver_token}"},
        )
        assert accept.status_code == 200, accept.text

        active = client.get(
            "/drivers/me/active-ride",
            headers={"Authorization": f"Bearer {driver_token}"},
        )
        assert active.status_code == 200
        assert active.json()["ride"]["id"] == ride_id
        assert active.json()["lifecycle_stage"] == "accepted"

        client.post(
            f"/drivers/arrive-pickup/{ride_id}",
            headers={"Authorization": f"Bearer {driver_token}"},
        )
        client.post(
            f"/drivers/start-ride/{ride_id}",
            headers={"Authorization": f"Bearer {driver_token}"},
        )
        done = client.post(
            f"/drivers/complete-ride/{ride_id}",
            headers={"Authorization": f"Bearer {driver_token}"},
            json={"tip_cents": 0},
        )
        assert done.status_code == 200, done.text
        assert done.json()["ride"]["status"] == "completed"

        rider_status = client.get(
            f"/rides/{ride_id}",
            headers={"Authorization": f"Bearer {rider_token}"},
        )
        assert rider_status.status_code == 200
        assert rider_status.json()["ride"]["status"] == "completed"

        payment = client.get(
            f"/rides/{ride_id}/payment",
            headers={"Authorization": f"Bearer {rider_token}"},
        )
        assert payment.status_code == 200, payment.text
        pay_body = payment.json()
        assert pay_body.get("payment") is not None
        assert pay_body["payment"]["status"] in ("captured", "authorized")

        admin_list = client.get("/admin/rides", headers={"Authorization": f"Bearer {admin_token}"})
        assert admin_list.status_code == 200, admin_list.text
        rows = admin_list.json().get("rides", admin_list.json())
        assert any(r["id"] == ride_id for r in rows)

        admin_detail = client.get(
            f"/admin/rides/{ride_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert admin_detail.status_code == 200, admin_detail.text
        detail = admin_detail.json()
        assert detail["status"] == "completed"
        assert "lifecycle_events" in detail
