"""Production proof gate — driver payment endpoint backed by ride_payments table."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models.payment import RidePayment
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
        "PayGate1!",
        role,
        license_no,
        **kwargs,
    )
    if role == UserRole.DRIVER:
        user.availability = DriverStatus.AVAILABLE.value
        user.last_latitude = 45.524
        user.last_longitude = -122.675
    db.commit()
    return create_access_token(user=user), user.id


def _ride_body():
    return {
        "pickup_location": "Gate A",
        "dropoff_location": "Gate B",
        "pickup_latitude": 45.523,
        "pickup_longitude": -122.676,
        "dropoff_latitude": 45.530,
        "dropoff_longitude": -122.650,
    }


@pytest.fixture(autouse=True)
def _auto_assign(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HALFAPP_AUTO_ASSIGN", "1")
    monkeypatch.setenv("HALFAPP_OPEN_BOARD_DISPATCH", "1")


def test_driver_payment_endpoint_returns_persisted_ride_payments_row():
    """GET /drivers/rides/{id}/payment must read ride_payments, not client-side math."""
    db = SessionLocal()
    try:
        rider_token, _ = _token(db, role=UserRole.CUSTOMER, prefix="gate_r")
        driver_token, driver_id = _token(db, role=UserRole.DRIVER, prefix="gate_d")
    finally:
        db.close()

    with TestClient(app) as client:
        client.put(
            "/drivers/presence",
            headers={"Authorization": f"Bearer {driver_token}"},
            json={"state": "available"},
        )
        created = client.post(
            "/rides/",
            headers={"Authorization": f"Bearer {rider_token}"},
            json=_ride_body(),
        )
        assert created.status_code == 200
        ride_id = created.json()["ride"]["id"]

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

        resp = client.get(
            f"/drivers/rides/{ride_id}/payment",
            headers={"Authorization": f"Bearer {driver_token}"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()["payment"]

        db2 = SessionLocal()
        try:
            row = db2.query(RidePayment).filter(RidePayment.ride_id == ride_id).one()
            assert row.status == "captured"
            assert row.driver_id == driver_id
            assert body["status"] == row.status
            assert body["amount_cents"] == row.amount_cents
            assert body["driver_payout_cents"] == row.driver_payout_cents
            assert body["ride_id"] == ride_id
            stored = get_ride_payment(db2, ride_id)
            assert stored is not None
            assert stored.id == row.id
        finally:
            db2.close()


def test_driver_payment_endpoint_404_when_no_ride_payments_row():
    db = SessionLocal()
    try:
        driver_token, _ = _token(db, role=UserRole.DRIVER, prefix="gate_d2")
    finally:
        db.close()

    with TestClient(app) as client:
        missing = client.get(
            "/drivers/rides/999999/payment",
            headers={"Authorization": f"Bearer {driver_token}"},
        )
        assert missing.status_code == 404
