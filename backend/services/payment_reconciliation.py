"""Driver payment reconciliation — pricing vs execution (HALFAPP_PAYMENTS_EXECUTION_03)."""

from __future__ import annotations

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from models.payment_execution import (
    EXECUTION_TYPE_CHARGE_RIDER,
    EXECUTION_TYPE_DISPUTE,
    EXECUTION_TYPE_REFUND_RIDER,
    PaymentExecution,
    STATUS_SUCCEEDED,
)
from models.driver_stripe_account import DriverStripeAccount
from models.ride import Ride
from models.ride_pricing import RidePricing
from models.stripe_payout import StripePayout
from services.lifecycle import RideStatus, to_storage_ride_status
from services.stripe_client import payouts_enabled


def _execution_sum(
    db: Session,
    driver_id: int,
    execution_type: str,
    *,
    statuses: tuple[str, ...] | None = None,
) -> int:
    query = (
        db.query(func.coalesce(func.sum(PaymentExecution.amount_cents), 0))
        .join(Ride, Ride.id == PaymentExecution.ride_id)
        .filter(
            Ride.driver_id == int(driver_id),
            PaymentExecution.execution_type == execution_type,
        )
    )
    if statuses:
        query = query.filter(PaymentExecution.status.in_(statuses))
    return int(query.scalar() or 0)


def compute_driver_payment_reconciliation(db: Session, driver_id: int) -> dict:
    """
    Earned vs collected vs refunded vs disputed for one driver.
    pricing_earned_cents = locked ride_pricing driver earnings (obligation truth).
    execution_* = PSP execution rows only — not a payout guarantee.
    """
    pricing_earned = (
        db.query(func.coalesce(func.sum(RidePricing.driver_earnings_cents), 0))
        .join(Ride, Ride.id == RidePricing.ride_id)
        .filter(
            Ride.driver_id == int(driver_id),
            Ride.status == to_storage_ride_status(RideStatus.COMPLETED),
            RidePricing.financial_locked.is_(True),
        )
        .scalar()
    )

    collected = _execution_sum(
        db,
        driver_id,
        EXECUTION_TYPE_CHARGE_RIDER,
        statuses=(STATUS_SUCCEEDED,),
    )
    refunded = _execution_sum(
        db,
        driver_id,
        EXECUTION_TYPE_REFUND_RIDER,
        statuses=(STATUS_SUCCEEDED,),
    )
    disputed = _execution_sum(db, driver_id, EXECUTION_TYPE_DISPUTE)

    pending_collection = _execution_sum(
        db,
        driver_id,
        EXECUTION_TYPE_CHARGE_RIDER,
        statuses=("pending", "processing", "requires_action", "requires_payment_method"),
    )

    refundable = max(0, collected - refunded - disputed)
    net_collected = max(0, collected - refunded)

    return {
        "driver_id": int(driver_id),
        "pricing_earned_cents": int(pricing_earned or 0),
        "execution_collected_cents": collected,
        "execution_refunded_cents": refunded,
        "execution_disputed_cents": disputed,
        "execution_pending_collection_cents": pending_collection,
        "execution_refundable_cents": refundable,
        "execution_net_collected_cents": net_collected,
        # Phase 4 UI aliases (same backend values — not payout semantics)
        "collected_cents": collected,
        "refunded_cents": refunded,
        "disputed_cents": disputed,
        "pending_cents": pending_collection,
        "available_cents": refundable,
        "display_note": (
            "Shows processed and pending payment execution amounts from the provider. "
            "Not a bank deposit, payout guarantee, or instant transfer."
        ),
        "truth_labels": [
            "pricing_earned_is_obligation_not_payout",
            "execution_collected_is_psp_not_bank_deposit",
            "payment_execution_not_implemented_in_audit_copy",
        ],
    }


def list_driver_payment_executions(
    db: Session,
    driver_id: int,
    *,
    limit: int = 50,
) -> list[dict]:
    rows = (
        db.query(PaymentExecution)
        .join(Ride, Ride.id == PaymentExecution.ride_id)
        .filter(Ride.driver_id == int(driver_id))
        .order_by(PaymentExecution.created_at.desc())
        .limit(max(1, min(int(limit), 200)))
        .all()
    )
    items = []
    for row in rows:
        created = row.created_at.isoformat() if row.created_at else None
        items.append(
            {
                "id": row.id,
                "ride_id": row.ride_id,
                "execution_type": row.execution_type,
                "amount_cents": int(row.amount_cents),
                "status": row.status,
                "external_provider": row.external_provider,
                "external_id": row.external_id,
                "created_at": created,
            }
        )
    return items


def _sum_payouts_for_account(
    db: Session,
    stripe_account_id: str,
    statuses: tuple[str, ...],
) -> int:
    return int(
        db.query(func.coalesce(func.sum(StripePayout.amount_cents), 0))
        .filter(
            StripePayout.stripe_account_id == stripe_account_id,
            StripePayout.status.in_(statuses),
        )
        .scalar()
        or 0
    )


def _payout_last_at_iso(row: StripePayout | None) -> str | None:
    if row is None:
        return None
    if row.created_at:
        return row.created_at.isoformat()
    if row.arrival_date:
        return row.arrival_date.isoformat()
    return None


def _latest_payout_for_account(db: Session, stripe_account_id: str) -> StripePayout | None:
    return (
        db.query(StripePayout)
        .filter(StripePayout.stripe_account_id == stripe_account_id)
        .order_by(
            desc(StripePayout.created_at),
            desc(StripePayout.arrival_date),
            desc(StripePayout.id),
        )
        .first()
    )


def enrich_reconciliation_with_payouts(db: Session, driver_id: int, base: dict) -> dict:
    """
    Add provider payout buckets when PAYOUTS_ENABLED and driver has Connect account.
    Status values are Stripe payout object statuses — not bank-deposit confirmation.
    """
    base = dict(base)
    payout_defaults = {
        "payout_paid_cents": 0,
        "payout_pending_cents": 0,
        "payout_failed_cents": 0,
        "payout_last_status": None,
        "payout_last_at": None,
        "provider_payout_visible": False,
    }
    if not payouts_enabled():
        base.update(payout_defaults)
        return base

    acct = (
        db.query(DriverStripeAccount)
        .filter(DriverStripeAccount.driver_id == int(driver_id))
        .one_or_none()
    )
    if acct is None:
        base.update(payout_defaults)
        return base

    account_id = acct.stripe_account_id
    paid = _sum_payouts_for_account(db, account_id, ("paid",))
    pending = _sum_payouts_for_account(db, account_id, ("pending", "in_transit"))
    failed = _sum_payouts_for_account(db, account_id, ("failed",))
    last = _latest_payout_for_account(db, account_id)
    base.update(
        {
            "payout_paid_cents": paid,
            "payout_pending_cents": pending,
            "payout_failed_cents": failed,
            "payout_last_status": last.status if last else None,
            "payout_last_at": _payout_last_at_iso(last),
            "provider_payout_visible": True,
            "provider_stripe_account_id": account_id,
        }
    )
    return base


def list_driver_payouts(db: Session, driver_id: int, *, limit: int = 50) -> list[dict]:
    if not payouts_enabled():
        return []

    acct = (
        db.query(DriverStripeAccount)
        .filter(DriverStripeAccount.driver_id == int(driver_id))
        .one_or_none()
    )
    if acct is None:
        return []

    rows = (
        db.query(StripePayout)
        .filter(StripePayout.stripe_account_id == acct.stripe_account_id)
        .order_by(StripePayout.created_at.desc())
        .limit(max(1, min(int(limit), 200)))
        .all()
    )
    items = []
    for row in rows:
        items.append(
            {
                "payout_id": row.payout_id,
                "amount_cents": int(row.amount_cents),
                "currency": row.currency,
                "status": row.status,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "arrival_date": row.arrival_date.isoformat() if row.arrival_date else None,
            }
        )
    return items
