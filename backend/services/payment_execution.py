"""Payment execution layer — PSP-ready rows from locked ride_pricing only (HALFAPP_PAYMENTS_EXECUTION_01/02)."""

from __future__ import annotations

from sqlalchemy.orm import Session

import stripe

from models.driver_stripe_account import DriverStripeAccount
from models.payment_execution import (
    EXECUTION_TYPE_CHARGE_RIDER,
    EXECUTION_TYPE_DISPUTE,
    EXECUTION_TYPE_REFUND_RIDER,
    EXTERNAL_PROVIDER_STRIPE,
    PaymentExecution,
    STATUS_PENDING,
    STATUS_REQUIRES_DRIVER_CONNECT,
    STATUS_SUCCEEDED,
)
from models.ride_pricing import RidePricing
from services.datetime_utils import utc_now_naive
from services.stripe_client import (
    default_currency,
    platform_fee_amount,
    stripe_enabled,
    stripe_init,
)


def payments_enabled() -> bool:
    return stripe_enabled()


def _make_idempotency_key(prefix: str, ride_id: int) -> str:
    return f"{prefix}:{ride_id}"


def _refund_idempotency_key(ride_id: int, amount_cents: int) -> str:
    return f"{EXECUTION_TYPE_REFUND_RIDER}:{ride_id}:{amount_cents}"


def _sum_refunded_cents_for_ride(db: Session, ride_id: int) -> int:
    rows = (
        db.query(PaymentExecution)
        .filter(
            PaymentExecution.ride_id == ride_id,
            PaymentExecution.execution_type == EXECUTION_TYPE_REFUND_RIDER,
            PaymentExecution.status == STATUS_SUCCEEDED,
        )
        .all()
    )
    return sum(int(row.amount_cents) for row in rows)


def create_charge_intent_from_pricing(db: Session, ride_id: int) -> PaymentExecution:
    """
    Create a pending charge execution row from locked pricing. No PSP calls in Phase 1.
    Idempotent per ride via idempotency_key.
    """
    pricing = db.query(RidePricing).filter(RidePricing.ride_id == ride_id).one_or_none()
    if pricing is None:
        raise ValueError("pricing_not_found")
    if not pricing.financial_locked:
        raise ValueError("pricing_not_locked")

    key = _make_idempotency_key(EXECUTION_TYPE_CHARGE_RIDER, ride_id)
    existing = (
        db.query(PaymentExecution)
        .filter(PaymentExecution.idempotency_key == key)
        .one_or_none()
    )
    if existing is not None:
        return existing

    row = PaymentExecution(
        ride_id=ride_id,
        ride_pricing_id=pricing.ride_id,
        execution_type=EXECUTION_TYPE_CHARGE_RIDER,
        amount_cents=int(pricing.customer_total_cents or pricing.total_rider_charge_cents or 0),
        currency="usd",
        status=STATUS_PENDING,
        idempotency_key=key,
        external_provider=None,
        external_id=None,
        is_test=False,
    )
    db.add(row)
    db.flush()
    return row


def mark_execution_succeeded(db: Session, external_id: str) -> PaymentExecution | None:
    row = (
        db.query(PaymentExecution)
        .filter(PaymentExecution.external_id == external_id)
        .one_or_none()
    )
    if row is None:
        return None
    row.status = STATUS_SUCCEEDED
    row.updated_at = utc_now_naive()
    db.flush()
    return row


def get_charge_execution_for_ride(db: Session, ride_id: int) -> PaymentExecution | None:
    key = _make_idempotency_key(EXECUTION_TYPE_CHARGE_RIDER, ride_id)
    return (
        db.query(PaymentExecution)
        .filter(PaymentExecution.idempotency_key == key)
        .one_or_none()
    )


def start_stripe_destination_payment_intent(
    db: Session,
    execution_row: PaymentExecution,
    driver_id: int,
) -> tuple[PaymentExecution, str | None]:
    """
    Create Stripe PaymentIntent for an existing PaymentExecution (destination charge).
    Returns (execution_row, client_secret). No-op when PAYMENTS_ENABLED is off.
  """
    if not stripe_enabled():
        return execution_row, None

    if execution_row.external_provider == EXTERNAL_PROVIDER_STRIPE and execution_row.external_id:
        return execution_row, None

    stripe_init()

    acct = (
        db.query(DriverStripeAccount)
        .filter(DriverStripeAccount.driver_id == int(driver_id))
        .one_or_none()
    )
    if acct is None or not acct.charges_enabled:
        execution_row.status = STATUS_REQUIRES_DRIVER_CONNECT
        execution_row.updated_at = utc_now_naive()
        db.flush()
        return execution_row, None

    currency = (execution_row.currency or default_currency()).lower()
    fee = platform_fee_amount(int(execution_row.amount_cents))

    pi = stripe.PaymentIntent.create(
        amount=int(execution_row.amount_cents),
        currency=currency,
        automatic_payment_methods={"enabled": True},
        application_fee_amount=fee,
        transfer_data={"destination": acct.stripe_account_id},
        metadata={
            "ride_id": str(execution_row.ride_id),
            "payment_execution_id": str(execution_row.id),
            "execution_type": str(execution_row.execution_type),
        },
        idempotency_key=str(execution_row.idempotency_key),
    )

    execution_row.external_provider = EXTERNAL_PROVIDER_STRIPE
    execution_row.external_id = pi["id"]
    execution_row.status = str(pi.get("status") or STATUS_PENDING)
    execution_row.updated_at = utc_now_naive()
    db.flush()
    return execution_row, pi.get("client_secret")


def try_start_stripe_charge_for_ride(
    db: Session,
    execution_row: PaymentExecution,
    driver_id: int | None,
) -> None:
    """Best-effort PI creation after ride complete; never raises to caller."""
    if not stripe_enabled() or driver_id is None:
        return
    try:
        start_stripe_destination_payment_intent(db, execution_row, int(driver_id))
    except Exception:
        return


def create_refund_execution(
    db: Session,
    charge_execution: PaymentExecution,
    amount_cents: int | None = None,
) -> PaymentExecution:
    """Idempotent full or partial refund execution linked to a charge execution."""
    if charge_execution.execution_type != EXECUTION_TYPE_CHARGE_RIDER:
        raise ValueError("not_a_charge_execution")

    total = int(charge_execution.amount_cents)
    refund_amount = int(amount_cents) if amount_cents is not None else total
    if refund_amount <= 0 or refund_amount > total:
        raise ValueError("invalid_refund_amount")

    already_refunded = _sum_refunded_cents_for_ride(db, charge_execution.ride_id)
    if already_refunded + refund_amount > total:
        raise ValueError("refund_exceeds_charge")

    key = _refund_idempotency_key(charge_execution.ride_id, refund_amount)
    existing = (
        db.query(PaymentExecution)
        .filter(PaymentExecution.idempotency_key == key)
        .one_or_none()
    )
    if existing is not None:
        return existing

    refund = PaymentExecution(
        ride_id=charge_execution.ride_id,
        ride_pricing_id=charge_execution.ride_pricing_id,
        execution_type=EXECUTION_TYPE_REFUND_RIDER,
        amount_cents=refund_amount,
        currency=charge_execution.currency or default_currency(),
        status=STATUS_PENDING,
        idempotency_key=key,
        external_provider=None,
        external_id=None,
        is_test=charge_execution.is_test,
    )
    db.add(refund)
    db.flush()
    return refund


def execute_stripe_refund(
    db: Session,
    refund_execution: PaymentExecution,
    charge_execution: PaymentExecution,
) -> PaymentExecution:
    """Create Stripe Refund for a succeeded charge PaymentIntent."""
    if not stripe_enabled():
        return refund_execution

    if not charge_execution.external_id:
        raise ValueError("charge_missing_external_id")

    if refund_execution.external_provider == EXTERNAL_PROVIDER_STRIPE and refund_execution.external_id:
        return refund_execution

    stripe_init()
    refund = stripe.Refund.create(
        payment_intent=charge_execution.external_id,
        amount=int(refund_execution.amount_cents),
        idempotency_key=str(refund_execution.idempotency_key),
    )

    refund_execution.external_provider = EXTERNAL_PROVIDER_STRIPE
    refund_execution.external_id = refund["id"]
    refund_execution.status = str(refund.get("status") or STATUS_PENDING)
    refund_execution.updated_at = utc_now_naive()
    db.flush()
    return refund_execution


def upsert_dispute_execution(
    db: Session,
    charge_execution: PaymentExecution,
    *,
    stripe_dispute_id: str,
    amount_cents: int,
    currency: str,
    status: str,
) -> PaymentExecution:
    """Idempotent dispute row for a charge (chargeback tracking)."""
    key = f"{EXECUTION_TYPE_DISPUTE}:{stripe_dispute_id}"
    existing = (
        db.query(PaymentExecution)
        .filter(PaymentExecution.idempotency_key == key)
        .one_or_none()
    )
    if existing is not None:
        existing.status = status
        existing.amount_cents = int(amount_cents)
        existing.updated_at = utc_now_naive()
        db.flush()
        return existing

    row = PaymentExecution(
        ride_id=charge_execution.ride_id,
        ride_pricing_id=charge_execution.ride_pricing_id,
        execution_type=EXECUTION_TYPE_DISPUTE,
        amount_cents=int(amount_cents),
        currency=(currency or default_currency()).lower(),
        status=status,
        idempotency_key=key,
        external_provider=EXTERNAL_PROVIDER_STRIPE,
        external_id=stripe_dispute_id,
        is_test=charge_execution.is_test,
    )
    db.add(row)
    db.flush()
    return row


def get_charge_execution_for_ride(db: Session, ride_id: int) -> PaymentExecution | None:
    key = _make_idempotency_key(EXECUTION_TYPE_CHARGE_RIDER, ride_id)
    return (
        db.query(PaymentExecution)
        .filter(PaymentExecution.idempotency_key == key)
        .one_or_none()
    )
