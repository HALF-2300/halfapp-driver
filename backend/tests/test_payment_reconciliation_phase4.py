"""HALFAPP_PAYMENTS_EXECUTION_04 — reconciliation UI payload + scoped executions list."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models.payment_execution import EXTERNAL_PROVIDER_STRIPE, PaymentExecution
from models.ride import Ride
from models.ride_pricing import RidePricing
from models.user import User, UserRole
from services.auth import create_access_token, create_user
from services.lifecycle import RideStatus, to_storage_ride_status
from services.payment_execution import create_charge_intent_from_pricing
from services.payment_reconciliation import (
    compute_driver_payment_reconciliation,
    list_driver_payment_executions,
)
from services.pricing_service import compute_financials


def _driver_with_charge():
    b = compute_financials(driver_shareable_ride_fare_cents=2500, platform_service_fee_cents=150)
    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:8]
        driver = create_user(
            db,
            f"p4_{uid}@example.com",
            "P4 Driver",
            "pw12345",
            UserRole.DRIVER,
            f"DL{uid}",
            driver_approval_status="approved",
        )
        other = create_user(
            db,
            f"p4_other_{uid}@example.com",
            "Other",
            "pw12345",
            UserRole.DRIVER,
            f"DLX{uid}",
            driver_approval_status="approved",
        )
        ride = Ride(
            customer_name="P4",
            status=to_storage_ride_status(RideStatus.COMPLETED),
            driver_id=driver.id,
        )
        db.add(ride)
        db.flush()
        pricing = RidePricing(ride_id=ride.id)
        pricing.driver_shareable_fare_cents = b.driver_shareable_ride_fare_cents
        pricing.platform_service_fee_cents = b.platform_service_fee_cents
        pricing.driver_earnings_cents = b.driver_total_payout_cents
        pricing.customer_total_cents = b.customer_total_cents
        pricing.total_rider_charge_cents = b.customer_total_cents
        pricing.financial_locked = True
        db.add(pricing)
        db.flush()
        charge = create_charge_intent_from_pricing(db, ride.id)
        charge.external_provider = EXTERNAL_PROVIDER_STRIPE
        charge.external_id = f"pi_p4_{ride.id}"
        charge.status = "succeeded"
        other_ride = Ride(
            customer_name="Other",
            status=to_storage_ride_status(RideStatus.COMPLETED),
            driver_id=other.id,
        )
        db.add(other_ride)
        db.flush()
        other_pricing = RidePricing(ride_id=other_ride.id)
        other_pricing.customer_total_cents = 999
        other_pricing.total_rider_charge_cents = 999
        other_pricing.financial_locked = True
        db.add(other_pricing)
        db.flush()
        other_charge = create_charge_intent_from_pricing(db, other_ride.id)
        other_charge.status = "succeeded"
        db.commit()
        return driver.id, ride.id, other.id
    finally:
        db.close()


def test_reconciliation_includes_phase4_ui_aliases():
    driver_id, _ride_id, _other = _driver_with_charge()
    db = SessionLocal()
    try:
        payload = compute_driver_payment_reconciliation(db, driver_id)
    finally:
        db.close()
    assert payload["collected_cents"] == payload["execution_collected_cents"]
    assert payload["available_cents"] == payload["execution_refundable_cents"]
    assert "display_note" in payload
    assert "not a bank deposit" in payload["display_note"].lower()


def test_payment_executions_list_scoped_to_driver():
    driver_id, ride_id, _other_driver_id = _driver_with_charge()
    db = SessionLocal()
    try:
        items = list_driver_payment_executions(db, driver_id)
        assert len(items) >= 1
        for item in items:
            ride = db.query(Ride).filter(Ride.id == item["ride_id"]).one()
            assert ride.driver_id == driver_id
        other_items = list_driver_payment_executions(db, _other_driver_id)
        other_ride_ids = {i["ride_id"] for i in other_items}
    finally:
        db.close()
    assert ride_id not in other_ride_ids


def test_driver_payment_reconciliation_endpoint():
    driver_id, _ride_id, _other = _driver_with_charge()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == driver_id).one()
        token = create_access_token(user=user)
    finally:
        db.close()

    with TestClient(app) as client:
        recon = client.get(
            "/drivers/me/payment-reconciliation",
            headers={"Authorization": f"Bearer {token}"},
        )
        executions = client.get(
            "/drivers/me/payment-executions",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert recon.status_code == 200
    assert recon.json()["collected_cents"] >= 0
    assert executions.status_code == 200
    assert isinstance(executions.json()["items"], list)
