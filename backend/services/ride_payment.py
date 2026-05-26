"""Phase 3 — ride payment lifecycle (simulated, persisted)."""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from models.payment import (
    PAYMENT_STATUS_AUTHORIZED,
    PAYMENT_STATUS_CAPTURED,
    PAYMENT_STATUS_FAILED,
    PAYMENT_STATUS_PENDING,
    RidePayment,
)
from models.ride import Ride
from services.datetime_utils import utc_now_naive
from services.pricing_policy_loader import get_active_pricing_policy
from services.pricing_service import compute_ride_financials_from_trip
from services.ride_pricing import get_ride_pricing

# Deterministic Phase 3 formula: base + distance * rate (integer cents).
PHASE3_BASE_FARE_CENTS = 500
PHASE3_PER_KM_CENTS = 150


def estimate_fare_cents(
    db: Session,
    *,
    distance_km: float,
    duration_minutes: int = 0,
) -> tuple[int, int]:
    """Return (customer_total_cents, driver_payout_cents) using v0.1 policy math."""
    policy = get_active_pricing_policy(db, market_id=None)
    breakdown = compute_ride_financials_from_trip(
        distance_km=max(0.0, float(distance_km or 0)),
        duration_minutes=max(0, int(duration_minutes or 0)),
        policy=policy,
    )
    return breakdown.customer_total_cents, breakdown.driver_total_payout_cents


def _amounts_from_ride(db: Session, ride: Ride) -> tuple[int, int]:
    pricing = get_ride_pricing(db, ride.id)
    if pricing and pricing.customer_total_cents:
        return pricing.customer_total_cents, pricing.driver_earnings_cents or pricing.driver_ride_payout_cents or 0
    customer, driver = estimate_fare_cents(
        db,
        distance_km=ride.distance or 0.0,
        duration_minutes=ride.duration or 0,
    )
    return customer, driver


def get_ride_payment(db: Session, ride_id: int) -> Optional[RidePayment]:
    return db.query(RidePayment).filter(RidePayment.ride_id == ride_id).first()


def create_payment_for_ride(db: Session, ride: Ride) -> RidePayment:
    existing = get_ride_payment(db, ride.id)
    if existing:
        return existing
    amount, driver_payout = _amounts_from_ride(db, ride)
    row = RidePayment(
        ride_id=ride.id,
        rider_id=ride.customer_id,
        driver_id=ride.driver_id,
        amount_cents=amount,
        driver_payout_cents=driver_payout,
        currency="USD",
        status=PAYMENT_STATUS_PENDING,
    )
    db.add(row)
    db.flush()
    return row


def authorize_payment_for_ride(db: Session, ride: Ride) -> Optional[RidePayment]:
    payment = get_ride_payment(db, ride.id)
    if not payment:
        payment = create_payment_for_ride(db, ride)
    if payment.status not in {PAYMENT_STATUS_PENDING, PAYMENT_STATUS_FAILED}:
        return payment
    amount, driver_payout = _amounts_from_ride(db, ride)
    payment.amount_cents = amount
    payment.driver_payout_cents = driver_payout
    payment.driver_id = ride.driver_id
    payment.status = PAYMENT_STATUS_AUTHORIZED
    payment.authorized_at = utc_now_naive()
    payment.failed_at = None
    db.flush()
    return payment


def capture_payment_for_ride(db: Session, ride: Ride) -> Optional[RidePayment]:
    payment = get_ride_payment(db, ride.id)
    if not payment:
        payment = create_payment_for_ride(db, ride)
    if payment.status == PAYMENT_STATUS_CAPTURED:
        return payment
    amount, driver_payout = _amounts_from_ride(db, ride)
    payment.amount_cents = amount
    payment.driver_payout_cents = driver_payout
    payment.driver_id = ride.driver_id
    payment.status = PAYMENT_STATUS_CAPTURED
    payment.captured_at = utc_now_naive()
    db.flush()
    return payment


def fail_payment_for_ride(db: Session, ride: Ride) -> Optional[RidePayment]:
    payment = get_ride_payment(db, ride.id)
    if not payment:
        return None
    if payment.status == PAYMENT_STATUS_CAPTURED:
        return payment
    payment.status = PAYMENT_STATUS_FAILED
    payment.failed_at = utc_now_naive()
    db.flush()
    return payment


def payment_to_dict(payment: RidePayment) -> dict:
    return {
        "id": payment.id,
        "ride_id": payment.ride_id,
        "rider_id": payment.rider_id,
        "driver_id": payment.driver_id,
        "amount_cents": payment.amount_cents,
        "driver_payout_cents": payment.driver_payout_cents,
        "currency": payment.currency,
        "status": payment.status,
        "created_at": payment.created_at.isoformat() + "Z" if payment.created_at else None,
        "authorized_at": payment.authorized_at.isoformat() + "Z" if payment.authorized_at else None,
        "captured_at": payment.captured_at.isoformat() + "Z" if payment.captured_at else None,
        "failed_at": payment.failed_at.isoformat() + "Z" if payment.failed_at else None,
    }
