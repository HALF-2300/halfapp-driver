"""HALFAPP_PAYMENTS_EXECUTION_01 Phase 1 — execution rows from locked pricing only."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from database import SessionLocal, engine
from main import app
from models.payment_execution import (
    EXECUTION_TYPE_CHARGE_RIDER,
    PaymentExecution,
    STATUS_PENDING,
    STATUS_SUCCEEDED,
)
from models.ride import Ride
from models.ride_pricing import RidePricing
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.lifecycle import RideStatus, to_storage_ride_status
from services.payment_execution import (
    create_charge_intent_from_pricing,
    get_charge_execution_for_ride,
    mark_execution_succeeded,
)
from services.pricing_service import compute_financials


def _locked_pricing_ride():
    b = compute_financials(driver_shareable_ride_fare_cents=2500, platform_service_fee_cents=150)
    db = SessionLocal()
    try:
        ride = Ride(
            customer_name="PayExec",
            status=to_storage_ride_status(RideStatus.COMPLETED),
            distance=5.0,
            duration=12,
        )
        db.add(ride)
        db.flush()
        row = RidePricing(ride_id=ride.id)
        row.driver_shareable_fare_cents = b.driver_shareable_ride_fare_cents
        row.platform_service_fee_cents = b.platform_service_fee_cents
        row.platform_commission_cents = b.platform_commission_cents
        row.driver_ride_payout_cents = b.driver_ride_payout_cents
        row.driver_commission_cents = b.driver_ride_payout_cents
        row.driver_earnings_cents = b.driver_total_payout_cents
        row.platform_revenue_cents = b.platform_revenue_cents
        row.platform_earnings_cents = b.platform_revenue_cents
        row.customer_total_cents = b.customer_total_cents
        row.total_rider_charge_cents = b.customer_total_cents
        row.financial_locked = True
        db.add(row)
        db.commit()
        db.refresh(ride)
        return ride.id
    finally:
        db.close()


def test_migration_creates_payment_execution_table():
    inspector = inspect(engine)
    assert "payment_execution" in inspector.get_table_names()


def test_create_charge_execution_from_locked_pricing():
    ride_id = _locked_pricing_ride()
    db = SessionLocal()
    try:
        row = create_charge_intent_from_pricing(db, ride_id)
        db.commit()
        assert row.amount_cents > 0
        assert row.status == STATUS_PENDING
        assert row.execution_type == EXECUTION_TYPE_CHARGE_RIDER
        assert row.ride_pricing_id == ride_id
    finally:
        db.close()


def test_idempotent_execution():
    ride_id = _locked_pricing_ride()
    db = SessionLocal()
    try:
        r1 = create_charge_intent_from_pricing(db, ride_id)
        db.commit()
        r2 = create_charge_intent_from_pricing(db, ride_id)
        db.commit()
        assert r1.id == r2.id
    finally:
        db.close()


def test_pricing_not_locked_raises():
    db = SessionLocal()
    try:
        ride = Ride(customer_name="Unlocked", status="completed")
        db.add(ride)
        db.flush()
        db.add(RidePricing(ride_id=ride.id, financial_locked=False, customer_total_cents=1000))
        db.commit()
        with pytest.raises(ValueError, match="pricing_not_locked"):
            create_charge_intent_from_pricing(db, ride.id)
    finally:
        db.close()


def test_mark_execution_succeeded_by_external_id():
    ride_id = _locked_pricing_ride()
    db = SessionLocal()
    try:
        row = create_charge_intent_from_pricing(db, ride_id)
        row.external_id = "pi_test_123"
        db.commit()
        updated = mark_execution_succeeded(db, "pi_test_123")
        db.commit()
        assert updated is not None
        assert updated.status == STATUS_SUCCEEDED
    finally:
        db.close()


def _driver_flow_tokens(db):
    uid = uuid.uuid4().hex[:8]
    driver = create_user(
        db,
        f"payexec_{uid}@example.com",
        "Pay Exec Driver",
        "pw12345",
        UserRole.DRIVER,
        f"DL{uid}",
        driver_approval_status="approved",
    )
    rider = create_user(
        db,
        f"payexec_r_{uid}@example.com",
        "Pay Exec Rider",
        "pw12345",
        UserRole.CUSTOMER,
        None,
    )
    db.commit()
    return (
        create_access_token(user=driver),
        create_access_token(user=rider),
    )


def test_complete_ride_creates_pending_charge_execution():
    db = SessionLocal()
    try:
        driver_token, rider_token = _driver_flow_tokens(db)
    finally:
        db.close()

    with TestClient(app) as client:
        ride_resp = client.post(
            "/rides/",
            headers={"Authorization": f"Bearer {rider_token}"},
            json={
                "pickup_location": "PayExec Pickup",
                "dropoff_location": "PayExec Dropoff",
                "pickup_latitude": 45.52,
                "pickup_longitude": -122.68,
                "dropoff_latitude": 45.53,
                "dropoff_longitude": -122.67,
                "distance_km": 3.0,
            },
        )
        assert ride_resp.status_code == 200, ride_resp.text
        ride_id = ride_resp.json()["ride"]["id"]
        headers = {"Authorization": f"Bearer {driver_token}"}
        assert client.put(
            "/drivers/presence",
            headers=headers,
            json={"state": "available"},
        ).status_code == 200
        assert client.post(f"/drivers/accept-ride/{ride_id}", headers=headers).status_code == 200
        assert client.post(f"/drivers/arrive-pickup/{ride_id}", headers=headers).status_code == 200
        assert client.post(f"/drivers/start-ride/{ride_id}", headers=headers).status_code == 200
        complete = client.post(f"/drivers/complete-ride/{ride_id}", headers=headers)
        assert complete.status_code == 200, complete.text

        audit = client.get(f"/drivers/rides/{ride_id}/audit", headers=headers)
        assert audit.status_code == 200
        assert audit.json()["copy"]["payment_execution"] == "not_implemented"

    db = SessionLocal()
    try:
        execution = get_charge_execution_for_ride(db, ride_id)
        assert execution is not None
        assert execution.status == STATUS_PENDING
        assert execution.amount_cents > 0
    finally:
        db.close()
