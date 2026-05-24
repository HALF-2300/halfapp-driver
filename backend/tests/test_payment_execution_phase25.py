"""HALFAPP_PAYMENTS_EXECUTION_02_5 — webhook dedupe + refund execution."""

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
    EXECUTION_TYPE_REFUND_RIDER,
    EXTERNAL_PROVIDER_STRIPE,
    PaymentExecution,
)
from models.ride import Ride
from models.ride_pricing import RidePricing
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.lifecycle import RideStatus, to_storage_ride_status
from services.payment_events import record_event_once
from services.payment_execution import (
    create_charge_intent_from_pricing,
    create_refund_execution,
    execute_stripe_refund,
)
from services.pricing_service import compute_financials


def _charge_execution():
    b = compute_financials(driver_shareable_ride_fare_cents=2500, platform_service_fee_cents=150)
    db = SessionLocal()
    try:
        ride = Ride(
            customer_name="Refund Rider",
            status=to_storage_ride_status(RideStatus.COMPLETED),
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
        charge.external_id = "pi_refund_test_1"
        charge.status = "succeeded"
        db.commit()
        db.refresh(charge)
        return charge
    finally:
        db.close()


def test_migration_creates_payment_events_table():
    inspector = inspect(engine)
    assert "payment_events" in inspector.get_table_names()


def test_event_dedupe():
    db = SessionLocal()
    try:
        assert record_event_once(db, "evt_dedupe_1", "payment_intent.succeeded") is True
        db.commit()
        assert record_event_once(db, "evt_dedupe_1", "payment_intent.succeeded") is False
    finally:
        db.close()


def test_refund_idempotent():
    charge = _charge_execution()
    db = SessionLocal()
    try:
        r1 = create_refund_execution(db, charge)
        db.commit()
        r2 = create_refund_execution(db, charge)
        db.commit()
        assert r1.id == r2.id
        assert r1.execution_type == EXECUTION_TYPE_REFUND_RIDER
        assert r1.idempotency_key == f"{EXECUTION_TYPE_REFUND_RIDER}:{charge.ride_id}:{charge.amount_cents}"
    finally:
        db.close()


def test_execute_stripe_refund_uses_idempotency(monkeypatch: pytest.MonkeyPatch):
    charge = _charge_execution()
    monkeypatch.setenv("PAYMENTS_ENABLED", "1")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_x")

    captured: dict = {}

    def fake_refund_create(**kwargs):
        captured.update(kwargs)
        return {"id": "re_test_1", "status": "succeeded"}

    monkeypatch.setattr(stripe.Refund, "create", fake_refund_create)

    db = SessionLocal()
    try:
        refund = create_refund_execution(db, charge)
        idem = refund.idempotency_key
        refund = execute_stripe_refund(db, refund, charge)
        db.commit()
        external_id = refund.external_id
        status = refund.status
    finally:
        db.close()

    assert captured["payment_intent"] == "pi_refund_test_1"
    assert captured["idempotency_key"] == idem
    assert external_id == "re_test_1"
    assert status == "succeeded"


def test_webhook_skips_duplicate_event(monkeypatch: pytest.MonkeyPatch):
    charge = _charge_execution()
    monkeypatch.setenv("PAYMENTS_ENABLED", "1")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_x")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")

    payload_dict = {
        "id": "evt_dup_test",
        "type": "payment_intent.succeeded",
        "data": {"object": {"id": charge.external_id, "status": "succeeded"}},
    }
    raw = json.dumps(payload_dict).encode("utf-8")

    def fake_construct(payload, sig_header, secret):
        return payload_dict

    monkeypatch.setattr(stripe.Webhook, "construct_event", fake_construct)

    with TestClient(app) as client:
        first = client.post(
            "/webhooks/stripe",
            content=raw,
            headers={"Content-Type": "application/json", "Stripe-Signature": "t=1,v1=x"},
        )
        second = client.post(
            "/webhooks/stripe",
            content=raw,
            headers={"Content-Type": "application/json", "Stripe-Signature": "t=1,v1=x"},
        )

    assert first.status_code == 200
    assert first.json()["ok"] is True
    assert second.status_code == 200
    assert second.json().get("duplicate") is True


def test_admin_refund_requires_payments_enabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PAYMENTS_ENABLED", "0")
    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:8]
        admin = create_user(
            db,
            f"admin_refund_{uid}@example.com",
            "Admin",
            "pw12345",
            UserRole.ADMIN,
            None,
        )
        token = create_access_token(user=admin)
        charge = _charge_execution()
        ride_id = charge.ride_id
    finally:
        db.close()

    with TestClient(app) as client:
        response = client.post(
            f"/payments/admin/rides/{ride_id}/refund",
            headers={"Authorization": f"Bearer {token}"},
            json={},
        )
    assert response.status_code == 409
