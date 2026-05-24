"""Persist v0.1 ride pricing ledger rows — delegates math to pricing_service."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from models.ride_pricing import RidePricing
from services.datetime_utils import utc_now_naive
from services.pricing_policy_loader import get_active_pricing_policy
from services.pricing_service import (
    RideFinancialBreakdown,
    compute_financials,
    compute_ride_financials_from_trip,
)


class PricingLockedError(ValueError):
    pass


def get_ride_pricing(db: Session, ride_id: int) -> Optional[RidePricing]:
    return db.query(RidePricing).filter(RidePricing.ride_id == ride_id).first()


def _apply_breakdown_to_row(row: RidePricing, breakdown: RideFinancialBreakdown) -> None:
    row.pricing_policy_id = breakdown.pricing_policy_id
    row.pricing_version = breakdown.pricing_version
    row.market_id = breakdown.market_id
    row.base_fare_cents = breakdown.base_fare_cents
    row.distance_fare_cents = breakdown.distance_fare_cents
    row.time_fare_cents = breakdown.time_fare_cents
    row.wait_fee_cents = breakdown.wait_fee_cents
    row.driver_shareable_fare_cents = breakdown.driver_shareable_ride_fare_cents
    row.platform_service_fee_cents = breakdown.platform_service_fee_cents
    row.tip_cents = breakdown.tip_cents
    row.city_fee_cents = breakdown.city_fee_cents
    row.airport_fee_cents = breakdown.airport_fee_cents
    row.toll_cents = breakdown.toll_cents
    row.accessibility_fee_cents = breakdown.accessibility_fee_cents
    row.cancellation_fee_cents = breakdown.cancellation_fee_cents
    row.driver_commission_cents = breakdown.driver_ride_payout_cents
    row.driver_ride_payout_cents = breakdown.driver_ride_payout_cents
    row.platform_commission_cents = breakdown.platform_commission_cents
    row.driver_earnings_cents = breakdown.driver_total_payout_cents
    row.platform_earnings_cents = breakdown.platform_revenue_cents
    row.platform_revenue_cents = breakdown.platform_revenue_cents
    row.pass_through_total_cents = (
        breakdown.city_fee_cents
        + breakdown.airport_fee_cents
        + breakdown.toll_cents
        + breakdown.accessibility_fee_cents
    )
    row.total_rider_charge_cents = breakdown.customer_total_cents
    row.customer_total_cents = breakdown.customer_total_cents
    row.tax_cents = 0


def quote_ride_pricing(
    db: Session,
    *,
    ride_id: int,
    distance_km: float,
    duration_minutes: int,
    wait_minutes: int = 0,
    market_id: Optional[str] = None,
) -> RidePricing:
    """Estimate and persist unlocked pricing (priced state) for a ride."""
    existing = get_ride_pricing(db, ride_id)
    if existing and existing.financial_locked:
        raise PricingLockedError(f"Ride {ride_id} pricing is locked")

    policy = get_active_pricing_policy(db, market_id=market_id)
    breakdown = compute_ride_financials_from_trip(
        distance_km=distance_km,
        duration_minutes=duration_minutes,
        wait_minutes=wait_minutes,
        policy=policy,
    )
    row = existing or RidePricing(ride_id=ride_id)
    _apply_breakdown_to_row(row, breakdown)
    if existing is None:
        db.add(row)
    db.flush()
    return row


def finalize_ride_pricing(
    db: Session,
    *,
    ride_id: int,
    distance_km: float,
    duration_minutes: int = 0,
    platform_service_fee_cents: Optional[int] = None,
    tip_cents: int = 0,
    city_fee_cents: int = 0,
    airport_fee_cents: int = 0,
    toll_cents: int = 0,
    accessibility_fee_cents: int = 0,
    tax_cents: int = 0,
    lock: bool = False,
    market_id: Optional[str] = None,
) -> RidePricing:
    existing = get_ride_pricing(db, ride_id)
    if existing and existing.financial_locked:
        raise PricingLockedError(f"Ride {ride_id} pricing is locked")

    policy = get_active_pricing_policy(db, market_id=market_id)
    if existing and existing.driver_shareable_fare_cents and not distance_km:
        breakdown = compute_financials(
            driver_shareable_ride_fare_cents=existing.driver_shareable_fare_cents,
            platform_service_fee_cents=platform_service_fee_cents,
            tip_cents=tip_cents,
            city_fee_cents=city_fee_cents,
            airport_fee_cents=airport_fee_cents,
            toll_cents=toll_cents,
            accessibility_fee_cents=accessibility_fee_cents,
            policy=policy,
        )
        breakdown = RideFinancialBreakdown(
            pricing_policy_id=existing.pricing_policy_id or breakdown.pricing_policy_id,
            pricing_version=existing.pricing_version or breakdown.pricing_version,
            market_id=existing.market_id or breakdown.market_id,
            currency=breakdown.currency,
            base_fare_cents=existing.base_fare_cents,
            distance_fare_cents=existing.distance_fare_cents,
            time_fare_cents=existing.time_fare_cents,
            wait_fee_cents=existing.wait_fee_cents,
            driver_shareable_ride_fare_cents=existing.driver_shareable_fare_cents,
            platform_service_fee_cents=breakdown.platform_service_fee_cents,
            city_fee_cents=breakdown.city_fee_cents,
            accessibility_fee_cents=breakdown.accessibility_fee_cents,
            airport_fee_cents=breakdown.airport_fee_cents,
            toll_cents=breakdown.toll_cents,
            tip_cents=breakdown.tip_cents,
            cancellation_fee_cents=breakdown.cancellation_fee_cents,
            platform_commission_cents=breakdown.platform_commission_cents,
            driver_ride_payout_cents=breakdown.driver_ride_payout_cents,
            driver_total_payout_cents=breakdown.driver_total_payout_cents,
            platform_revenue_cents=breakdown.platform_revenue_cents,
            customer_total_cents=breakdown.customer_total_cents,
            traffic_aware=breakdown.traffic_aware,
        )
    else:
        breakdown = compute_ride_financials_from_trip(
            distance_km=distance_km,
            duration_minutes=duration_minutes or 0,
            platform_service_fee_cents=platform_service_fee_cents,
            tip_cents=tip_cents,
            city_fee_cents=city_fee_cents,
            airport_fee_cents=airport_fee_cents,
            toll_cents=toll_cents,
            accessibility_fee_cents=accessibility_fee_cents,
            policy=policy,
        )

    row = existing or RidePricing(ride_id=ride_id)
    _apply_breakdown_to_row(row, breakdown)
    if tax_cents:
        row.tax_cents = max(0, int(tax_cents))
        row.pass_through_total_cents += row.tax_cents
        row.customer_total_cents += row.tax_cents
        row.total_rider_charge_cents = row.customer_total_cents

    if lock:
        now = utc_now_naive()
        row.financial_locked = True
        row.locked_at = now
        row.fare_locked_at = now

    if existing is None:
        db.add(row)
    db.flush()
    return row


def cents_to_display_dollars(cents: int) -> float:
    return round(cents / 100.0, 2)
