"""HALFAPP_PAYMENTS_EXECUTION_02 — Stripe Connect, PI idempotency, signed webhooks."""

from __future__ import annotations

import json
import uuid

import pytest
import stripe
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from database import SessionLocal, engine
from main import app
from models.driver_stripe_account import DriverStripeAccount
from models.payment_execution import EXTERNAL_PROVIDER_STRIPE, PaymentExecution
from models.ride import Ride
from models.ride_pricing import RidePricing
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.lifecycle import RideStatus, to_storage_ride_status
from services.payment_execution import (
    create_charge_intent_from_pricing,
    start_stripe_destination_payment_intent,
)
from services.pricing_service import compute_financials


def _locked_ride_and_driver():
    b = compute_financials(driver_shareable_ride_fare_cents=2500, platform_service_fee_cents=150)
    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:8]
        driver = create_user(
            db,
            f"stripe_{uid}@example.com",
            "Stripe Driver",
            "pw12345",
            UserRole.DRIVER,
            f"DL{uid}",
            driver_approval_status="approved",
        )
        ride = Ride(
            customer_name="Stripe Rider",
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
        return ride.id, driver.id
    finally:
        db.close()


def test_migration_creates_driver_stripe_accounts_table():
    inspector = inspect(engine)
    assert "driver_stripe_accounts" in inspector.get_table_names()


def test_stripe_webhook_rejects_without_signature(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PAYMENTS_ENABLED", "1")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_x")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test_secret")

    with TestClient(app) as client:
        response = client.post(
            "/webhooks/stripe",
            content=b'{"id":"evt_test","type":"payment_intent.succeeded"}',
            headers={"Content-Type": "application/json"},
        )
    assert response.status_code == 400
    assert response.json()["detail"] == "missing_signature"


def test_stripe_webhook_updates_execution_on_verified_event(monkeypatch: pytest.MonkeyPatch):
    ride_id, _driver_id = _locked_ride_and_driver()
    db = SessionLocal()
    try:
        execution = create_charge_intent_from_pricing(db, ride_id)
        execution.external_provider = EXTERNAL_PROVIDER_STRIPE
        execution.external_id = "pi_webhook_test_1"
        execution.status = "requires_payment_method"
        db.commit()
    finally:
        db.close()

    monkeypatch.setenv("PAYMENTS_ENABLED", "1")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_x")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test_secret")

    payload_dict = {
        "id": "evt_test_1",
        "type": "payment_intent.succeeded",
        "data": {"object": {"id": "pi_webhook_test_1", "status": "succeeded"}},
    }
    raw = json.dumps(payload_dict).encode("utf-8")

    def fake_construct(payload, sig_header, secret):
        return payload_dict

    monkeypatch.setattr(stripe.Webhook, "construct_event", fake_construct)

    with TestClient(app) as client:
        response = client.post(
            "/webhooks/stripe",
            content=raw,
            headers={
                "Content-Type": "application/json",
                "Stripe-Signature": "t=1,v1=fake",
            },
        )
    assert response.status_code == 200
    assert response.json()["ok"] is True

    db = SessionLocal()
    try:
        row = (
            db.query(PaymentExecution)
            .filter(PaymentExecution.external_id == "pi_webhook_test_1")
            .one()
        )
        assert row.status == "succeeded"
    finally:
        db.close()


def test_stripe_pi_create_uses_idempotency_key(monkeypatch: pytest.MonkeyPatch):
    ride_id, driver_id = _locked_ride_and_driver()
    monkeypatch.setenv("PAYMENTS_ENABLED", "1")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_x")
    monkeypatch.setenv("PLATFORM_FEE_BPS", "800")

    captured: dict = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return {
            "id": "pi_test_1",
            "status": "requires_payment_method",
            "client_secret": "pi_test_1_secret",
        }

    monkeypatch.setattr(stripe.PaymentIntent, "create", fake_create)
    monkeypatch.setattr(stripe, "api_key", "sk_test_x")

    db = SessionLocal()
    try:
        db.add(
            DriverStripeAccount(
                driver_id=driver_id,
                stripe_account_id="acct_test_1",
                charges_enabled=True,
                payouts_enabled=True,
            )
        )
        db.commit()

        execution = create_charge_intent_from_pricing(db, ride_id)
        idem_key = execution.idempotency_key
        execution, client_secret = start_stripe_destination_payment_intent(
            db, execution, driver_id
        )
        external_id = execution.external_id
        db.commit()
    finally:
        db.close()

    assert captured["idempotency_key"] == idem_key
    assert captured["transfer_data"] == {"destination": "acct_test_1"}
    assert captured["application_fee_amount"] > 0
    assert external_id == "pi_test_1"
    assert client_secret == "pi_test_1_secret"


def test_connect_start_requires_payments_enabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PAYMENTS_ENABLED", "0")
    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:8]
        driver = create_user(
            db,
            f"stripe_off_{uid}@example.com",
            "Stripe Off",
            "pw12345",
            UserRole.DRIVER,
            f"DL{uid}",
            driver_approval_status="approved",
        )
        token = create_access_token(user=driver)
    finally:
        db.close()

    with TestClient(app) as client:
        response = client.post(
            "/drivers/stripe/connect/start",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 409
    assert response.json()["detail"] == "payments_disabled"
