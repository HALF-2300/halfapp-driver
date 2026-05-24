"""HALFAPP_PAYMENTS_EXECUTION_05 — transfer/payout ingestion + driver payout endpoints."""

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
from models.stripe_payout import StripePayout
from models.stripe_payout_transfer import StripePayoutTransfer
from models.stripe_transfer import StripeTransfer
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.lifecycle import RideStatus, to_storage_ride_status
from services.payment_execution import create_charge_intent_from_pricing
from services.datetime_utils import utc_now_naive
from services.payment_reconciliation import enrich_reconciliation_with_payouts
from services.pricing_service import compute_financials


def _driver_connect_with_payouts(
    *,
    paid_cents: int = 0,
    pending_cents: int = 0,
    failed_cents: int = 0,
    last_status: str | None = None,
):
    """Returns (token, driver_id)."""
    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:8]
        driver = create_user(
            db,
            f"p51_{uid}@example.com",
            "P51",
            "pw12345",
            UserRole.DRIVER,
            f"DL{uid}",
            driver_approval_status="approved",
        )
        acct_id = f"acct_p51_{uid}"
        db.add(
            DriverStripeAccount(
                driver_id=driver.id,
                stripe_account_id=acct_id,
                charges_enabled=True,
                payouts_enabled=True,
            )
        )
        now = utc_now_naive()
        if paid_cents:
            db.add(
                StripePayout(
                    payout_id=f"po_paid_{uid}",
                    stripe_account_id=acct_id,
                    amount_cents=paid_cents,
                    currency="usd",
                    status="paid",
                    created_at=now,
                )
            )
        if pending_cents:
            db.add(
                StripePayout(
                    payout_id=f"po_pending_{uid}",
                    stripe_account_id=acct_id,
                    amount_cents=pending_cents,
                    currency="usd",
                    status="pending",
                    created_at=now,
                )
            )
        if failed_cents:
            db.add(
                StripePayout(
                    payout_id=f"po_failed_{uid}",
                    stripe_account_id=acct_id,
                    amount_cents=failed_cents,
                    currency="usd",
                    status="failed",
                    created_at=now,
                )
            )
        if last_status:
            db.add(
                StripePayout(
                    payout_id=f"po_last_{uid}",
                    stripe_account_id=acct_id,
                    amount_cents=111,
                    currency="usd",
                    status=last_status,
                    created_at=now,
                )
            )
        db.commit()
        token = create_access_token(user=driver)
        return token, driver.id
    finally:
        db.close()


def test_migration_creates_phase5_tables():
    inspector = inspect(engine)
    names = set(inspector.get_table_names())
    assert "stripe_transfers" in names
    assert "stripe_payouts" in names
    assert "stripe_payout_transfers" in names
    cols = {c["name"] for c in inspector.get_columns("payment_execution")}
    assert "external_charge_id" in cols


def test_payout_webhook_ingests_connected_account_payout(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PAYMENTS_ENABLED", "1")
    monkeypatch.setenv("PAYOUTS_ENABLED", "1")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_x")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test_secret")

    payload_dict = {
        "id": "evt_payout_1",
        "type": "payout.paid",
        "account": "acct_phase5_1",
        "data": {
            "object": {
                "id": "po_phase5_1",
                "amount": 5000,
                "currency": "usd",
                "status": "paid",
                "created": 1_700_000_000,
                "arrival_date": 1_700_086_400,
            }
        },
    }
    raw = json.dumps(payload_dict).encode("utf-8")

    def fake_construct(payload, sig_header, secret):
        return payload_dict

    def fake_balance_list(**kwargs):
        return {
            "data": [
                {"type": "transfer", "source": "tr_phase5_1"},
            ]
        }

    monkeypatch.setattr(stripe.Webhook, "construct_event", fake_construct)
    monkeypatch.setattr(stripe.BalanceTransaction, "list", fake_balance_list)

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

        dup = client.post(
            "/webhooks/stripe",
            content=raw,
            headers={
                "Content-Type": "application/json",
                "Stripe-Signature": "t=1,v1=fake",
            },
        )
        assert dup.json().get("duplicate") is True

    db = SessionLocal()
    try:
        payout = db.query(StripePayout).filter(StripePayout.payout_id == "po_phase5_1").one()
        assert payout.stripe_account_id == "acct_phase5_1"
        assert payout.amount_cents == 5000
        assert payout.status == "paid"
        link = (
            db.query(StripePayoutTransfer)
            .filter(
                StripePayoutTransfer.payout_id == "po_phase5_1",
                StripePayoutTransfer.transfer_id == "tr_phase5_1",
            )
            .one()
        )
        assert link.stripe_account_id == "acct_phase5_1"
    finally:
        db.close()


def test_transfer_webhook_links_charge_execution(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PAYMENTS_ENABLED", "1")
    monkeypatch.setenv("PAYOUTS_ENABLED", "1")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_x")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test_secret")

    b = compute_financials(driver_shareable_ride_fare_cents=2500, platform_service_fee_cents=150)
    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:8]
        driver = create_user(
            db,
            f"p5_{uid}@example.com",
            "P5",
            "pw12345",
            UserRole.DRIVER,
            f"DL{uid}",
            driver_approval_status="approved",
        )
        ride = Ride(
            customer_name="P5",
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
        execution = create_charge_intent_from_pricing(db, ride.id)
        execution.external_provider = EXTERNAL_PROVIDER_STRIPE
        execution.external_id = "pi_p5_link"
        execution.external_charge_id = "ch_p5_link"
        execution.status = "succeeded"
        db.commit()
        execution_id = execution.id
    finally:
        db.close()

    payload_dict = {
        "id": "evt_transfer_1",
        "type": "transfer.created",
        "data": {
            "object": {
                "id": "tr_p5_link",
                "amount": 900,
                "currency": "usd",
                "destination": "acct_p5_link",
                "source_transaction": "ch_p5_link",
                "reversed": False,
                "created": 1_700_000_000,
            }
        },
    }
    raw = json.dumps(payload_dict).encode("utf-8")
    monkeypatch.setattr(
        stripe.Webhook,
        "construct_event",
        lambda payload, sig_header, secret: payload_dict,
    )

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

    db = SessionLocal()
    try:
        transfer = db.query(StripeTransfer).filter(StripeTransfer.transfer_id == "tr_p5_link").one()
        assert transfer.payment_execution_id == execution_id
        assert transfer.destination_account_id == "acct_p5_link"
    finally:
        db.close()


def test_provider_payout_visible_true_without_payout_rows(monkeypatch: pytest.MonkeyPatch):
    """Visible when Connect account + flag — not when stripe_payouts rows exist."""
    monkeypatch.setenv("PAYOUTS_ENABLED", "1")

    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:8]
        driver = create_user(
            db,
            f"p5_vis_{uid}@example.com",
            "Visible",
            "pw12345",
            UserRole.DRIVER,
            f"DL{uid}",
            driver_approval_status="approved",
        )
        db.add(
            DriverStripeAccount(
                driver_id=driver.id,
                stripe_account_id="acct_p5_vis",
                charges_enabled=True,
                payouts_enabled=True,
            )
        )
        db.commit()
        token = create_access_token(user=driver)
        payout_count = db.query(StripePayout).count()
    finally:
        db.close()

    assert payout_count == 0

    with TestClient(app) as client:
        recon = client.get(
            "/drivers/me/payment-reconciliation",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert recon.status_code == 200
    body = recon.json()
    assert body["provider_payout_visible"] is True
    assert body["payout_paid_cents"] == 0
    assert body["payout_pending_cents"] == 0
    assert body["payout_failed_cents"] == 0
    assert body["payout_last_status"] is None
    assert body["payout_last_at"] is None

    with TestClient(app) as client:
        payouts = client.get(
            "/drivers/me/payouts",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert payouts.json()["items"] == []


def test_provider_payout_visible_false_when_flag_off(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PAYOUTS_ENABLED", "0")

    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:8]
        driver = create_user(
            db,
            f"p5_off_{uid}@example.com",
            "Flag Off",
            "pw12345",
            UserRole.DRIVER,
            f"DL{uid}",
            driver_approval_status="approved",
        )
        db.add(
            DriverStripeAccount(
                driver_id=driver.id,
                stripe_account_id="acct_p5_off",
                charges_enabled=True,
                payouts_enabled=True,
            )
        )
        db.commit()
        token = create_access_token(user=driver)
    finally:
        db.close()

    with TestClient(app) as client:
        recon = client.get(
            "/drivers/me/payment-reconciliation",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert recon.json()["provider_payout_visible"] is False


def test_provider_payout_visible_false_without_connect_account(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PAYOUTS_ENABLED", "1")

    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:8]
        driver = create_user(
            db,
            f"p5_noacct_{uid}@example.com",
            "No Acct",
            "pw12345",
            UserRole.DRIVER,
            f"DL{uid}",
            driver_approval_status="approved",
        )
        db.commit()
        token = create_access_token(user=driver)
    finally:
        db.close()

    with TestClient(app) as client:
        recon = client.get(
            "/drivers/me/payment-reconciliation",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert recon.json()["provider_payout_visible"] is False


def test_reconciliation_includes_failed_and_last_payout_fields(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PAYOUTS_ENABLED", "1")
    token, _driver_id = _driver_connect_with_payouts(
        paid_cents=1000,
        pending_cents=500,
        failed_cents=250,
        last_status="paid",
    )

    with TestClient(app) as client:
        recon = client.get(
            "/drivers/me/payment-reconciliation",
            headers={"Authorization": f"Bearer {token}"},
        )
    body = recon.json()
    assert body["payout_failed_cents"] == 250
    assert body["payout_last_status"] == "paid"
    assert body["payout_last_at"] is not None


def test_reconciliation_payout_contract_keys_when_visible(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PAYOUTS_ENABLED", "1")
    token, _ = _driver_connect_with_payouts()

    with TestClient(app) as client:
        body = client.get(
            "/drivers/me/payment-reconciliation",
            headers={"Authorization": f"Bearer {token}"},
        ).json()

    assert body["provider_payout_visible"] is True
    for key in (
        "payout_paid_cents",
        "payout_pending_cents",
        "payout_failed_cents",
        "payout_last_status",
        "payout_last_at",
    ):
        assert key in body


def test_driver_payout_endpoints(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PAYOUTS_ENABLED", "1")

    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:8]
        driver = create_user(
            db,
            f"p5_api_{uid}@example.com",
            "P5 API",
            "pw12345",
            UserRole.DRIVER,
            f"DL{uid}",
            driver_approval_status="approved",
        )
        db.add(
            DriverStripeAccount(
                driver_id=driver.id,
                stripe_account_id="acct_p5_api",
                charges_enabled=True,
                payouts_enabled=True,
            )
        )
        db.add(
            StripePayout(
                payout_id="po_api_1",
                stripe_account_id="acct_p5_api",
                amount_cents=4200,
                currency="usd",
                status="paid",
            )
        )
        db.add(
            StripePayout(
                payout_id="po_api_2",
                stripe_account_id="acct_p5_api",
                amount_cents=800,
                currency="usd",
                status="pending",
            )
        )
        db.commit()
        token = create_access_token(user=driver)
        driver_id = driver.id
    finally:
        db.close()

    with TestClient(app) as client:
        payouts = client.get(
            "/drivers/me/payouts",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert payouts.status_code == 200
        items = payouts.json()["items"]
        assert len(items) == 2
        assert {i["payout_id"] for i in items} == {"po_api_1", "po_api_2"}

        recon = client.get(
            "/drivers/me/payment-reconciliation",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert recon.status_code == 200
        body = recon.json()
        assert body["payout_paid_cents"] == 4200
        assert body["payout_pending_cents"] == 800
        assert body["provider_payout_visible"] is True

    db = SessionLocal()
    try:
        base = {"collected_cents": 0}
        enriched = enrich_reconciliation_with_payouts(db, driver_id, base)
        assert enriched["payout_paid_cents"] == 4200
    finally:
        db.close()
