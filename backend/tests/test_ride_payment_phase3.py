"""Phase 3 — ride payment lifecycle."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.lifecycle import DriverStatus
from services.ride_payment import get_ride_payment


def _token(db, *, role: UserRole, prefix: str) -> str:
    uid = uuid.uuid4().hex[:8]
    license_no = f"DL{uid}" if role == UserRole.DRIVER else None
    kwargs = {}
    if role == UserRole.DRIVER:
        kwargs["driver_approval_status"] = "approved"
    user = create_user(
        db,
        f"{prefix}_{uid}@example.com",
        f"{prefix} User",
        "PayLoop1!",
        role,
        license_no,
        **kwargs,
    )
    if role == UserRole.DRIVER:
        user.availability = DriverStatus.AVAILABLE.value
        user.last_latitude = 45.524
        user.last_longitude = -122.675
    db.commit()
    return create_access_token(user=user)


def _ride_body():
    return {
        "pickup_location": "A",
        "dropoff_location": "B",
        "pickup_latitude": 45.523,
        "pickup_longitude": -122.676,
        "dropoff_latitude": 45.530,
        "dropoff_longitude": -122.650,
    }


@pytest.fixture(autouse=True)
def _auto_assign(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HALFAPP_AUTO_ASSIGN", "1")
    monkeypatch.setenv("HALFAPP_OPEN_BOARD_DISPATCH", "1")


def test_payment_lifecycle_pending_authorized_captured():
    db = SessionLocal()
    try:
        rider_token = _token(db, role=UserRole.CUSTOMER, prefix="pay_r")
        driver_token = _token(db, role=UserRole.DRIVER, prefix="pay_d")
    finally:
        db.close()

    with TestClient(app) as client:
        client.put(
            "/drivers/presence",
            headers={"Authorization": f"Bearer {driver_token}"},
            json={"state": "available"},
        )

        estimate = client.post(
            "/rides/estimate",
            headers={"Authorization": f"Bearer {rider_token}"},
            json=_ride_body(),
        )
        assert estimate.status_code == 200
        assert estimate.json()["amount_cents"] > 0

        created = client.post(
            "/rides/",
            headers={"Authorization": f"Bearer {rider_token}"},
            json=_ride_body(),
        )
        assert created.status_code == 200
        ride_id = created.json()["ride"]["id"]

        db2 = SessionLocal()
        try:
            payment = get_ride_payment(db2, ride_id)
            assert payment is not None
            assert payment.status == "authorized"
        finally:
            db2.close()

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
            json={},
        )
        assert done.status_code == 200

        rider_payment = client.get(
            f"/rides/{ride_id}/payment",
            headers={"Authorization": f"Bearer {rider_token}"},
        )
        assert rider_payment.status_code == 200
        body = rider_payment.json()["payment"]
        assert body["status"] == "captured"
        assert body["amount_cents"] > 0

        driver_payments = client.get(
            "/drivers/me/ride-payments",
            headers={"Authorization": f"Bearer {driver_token}"},
        )
        assert driver_payments.status_code == 200
        assert driver_payments.json()["total_captured_cents"] >= body["driver_payout_cents"]
