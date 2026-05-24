"""HALFAPP_PAYMENTS_EXECUTION_03 — partial refunds, disputes, reconciliation."""

from __future__ import annotations

import json
import uuid

import pytest
import stripe
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from database import SessionLocal, engine
from main import app
from models.payment_execution import (
    EXECUTION_TYPE_CHARGE_RIDER,
    EXECUTION_TYPE_DISPUTE,
    EXECUTION_TYPE_REFUND_RIDER,
    EXTERNAL_PROVIDER_STRIPE,
    PaymentExecution,
    STATUS_SUCCEEDED,
)
from models.ride import Ride
from models.ride_pricing import RidePricing
from models.user import User, UserRole
from services.auth import create_access_token, create_user
from services.lifecycle import RideStatus, to_storage_ride_status
from services.payment_execution import (
    create_charge_intent_from_pricing,
    create_refund_execution,
    upsert_dispute_execution,
)
from services.payment_reconciliation import compute_driver_payment_reconciliation
from services.pricing_service import compute_financials


def _driver_with_charge():
    b = compute_financials(driver_shareable_ride_fare_cents=2500, platform_service_fee_cents=150)
    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:8]
        driver = create_user(
            db,
            f"phase3_{uid}@example.com",
            "Phase3 Driver",
            "pw12345",
            UserRole.DRIVER,
            f"DL{uid}",
            driver_approval_status="approved",
        )
        ride = Ride(
            customer_name="Phase3 Rider",
            status=to_storage_ride_status(RideStatus.COMPLETED),
            driver_id=driver.id,
            distance=5.0,
            duration=12,
        )
        db.add(ride)
        db.flush()
        pricing = RidePricing(ride_id=ride.id)
        pricing.driver_shareable_fare_cents = b.driver_shareable_ride_fare_cents
        pricing.platform_service_fee_cents = b.platform_service_fee_cents
        pricing.platform_commission_cents = b.platform_commission_cents
        pricing.driver_ride_payout_cents = b.driver_ride_payout_cents
        pricing.driver_commission_cents = b.driver_ride_payout_cents
        pricing.driver_earnings_cents = b.driver_total_payout_cents
        pricing.platform_revenue_cents = b.platform_revenue_cents
        pricing.platform_earnings_cents = b.platform_revenue_cents
        pricing.customer_total_cents = b.customer_total_cents
        pricing.total_rider_charge_cents = b.customer_total_cents
        pricing.financial_locked = True
        db.add(pricing)
        db.commit()

        charge = create_charge_intent_from_pricing(db, ride.id)
        charge.external_provider = EXTERNAL_PROVIDER_STRIPE
        charge.external_id = f"pi_phase3_{ride.id}"
        charge.status = STATUS_SUCCEEDED
        db.commit()
        return driver.id, ride.id, charge.id, charge.amount_cents, charge.external_id
    finally:
        db.close()


def test_partial_refund():
    _driver_id, ride_id, charge_id, charge_amount, _pi = _driver_with_charge()
    db = SessionLocal()
    try:
        charge = db.query(PaymentExecution).filter(PaymentExecution.id == charge_id).one()
        partial = create_refund_execution(db, charge, amount_cents=500)
        db.commit()
        assert partial.amount_cents == 500
        assert partial.idempotency_key == f"{EXECUTION_TYPE_REFUND_RIDER}:{charge.ride_id}:500"

        partial.status = STATUS_SUCCEEDED
        db.commit()

        with pytest.raises(ValueError, match="refund_exceeds_charge"):
            create_refund_execution(db, charge, amount_cents=charge_amount)
    finally:
        db.close()


def test_dispute_upsert_idempotent():
    _driver_id, _ride_id, charge_id, _amount, _pi = _driver_with_charge()
    db = SessionLocal()
    try:
        charge = db.query(PaymentExecution).filter(PaymentExecution.id == charge_id).one()
        d1 = upsert_dispute_execution(
            db,
            charge,
            stripe_dispute_id="dp_test_1",
            amount_cents=1000,
            currency="usd",
            status="needs_response",
        )
        db.commit()
        d2 = upsert_dispute_execution(
            db,
            charge,
            stripe_dispute_id="dp_test_1",
            amount_cents=1000,
            currency="usd",
            status="under_review",
        )
        db.commit()
        assert d1.id == d2.id
        assert d2.execution_type == EXECUTION_TYPE_DISPUTE
        assert d2.status == "under_review"
    finally:
        db.close()


def test_earnings_reconciliation_math():
    driver_id, _ride_id, _charge_id, charge_amount, _pi = _driver_with_charge()
    db = SessionLocal()
    try:
        result = compute_driver_payment_reconciliation(db, driver_id)
        assert result["pricing_earned_cents"] > 0
        assert result["execution_collected_cents"] == charge_amount
        assert "execution_net_collected_cents" in result
        assert "payment_execution_not_implemented_in_audit_copy" in result["truth_labels"]
    finally:
        db.close()


def test_driver_payment_reconciliation_endpoint():
    driver_id, _ride_id, _charge_id, _amount, _pi = _driver_with_charge()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == driver_id).one()
        token = create_access_token(user=user)
    finally:
        db.close()

    with TestClient(app) as client:
        response = client.get(
            "/drivers/me/payment-reconciliation",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["pricing_earned_cents"] > 0
    assert body["execution_collected_cents"] > 0


def test_dispute_webhook_creates_row(monkeypatch: pytest.MonkeyPatch):
    _driver_id, _ride_id, _charge_id, _amount, pi_id = _driver_with_charge()
    monkeypatch.setenv("PAYMENTS_ENABLED", "1")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_x")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")

    payload_dict = {
        "id": "evt_dispute_1",
        "type": "charge.dispute.created",
        "data": {
            "object": {
                "id": "dp_webhook_1",
                    "payment_intent": pi_id,
                "amount": 500,
                "currency": "usd",
                "status": "needs_response",
            }
        },
    }
    raw = json.dumps(payload_dict).encode("utf-8")

    def fake_construct(payload, sig_header, secret):
        return payload_dict

    monkeypatch.setattr(stripe.Webhook, "construct_event", fake_construct)

    with TestClient(app) as client:
        response = client.post(
            "/webhooks/stripe",
            content=raw,
            headers={"Content-Type": "application/json", "Stripe-Signature": "t=1,v1=x"},
        )
    assert response.status_code == 200

    db = SessionLocal()
    try:
        row = (
            db.query(PaymentExecution)
            .filter(PaymentExecution.external_id == "dp_webhook_1")
            .one()
        )
        assert row.execution_type == EXECUTION_TYPE_DISPUTE
        assert row.amount_cents == 500
    finally:
        db.close()
