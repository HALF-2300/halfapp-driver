"""Load active pricing policy from DB or fall back to launch defaults."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from models.pricing_policy import PricingPolicy
from services.pricing_service import DEFAULT_US_LAUNCH_POLICY, PricingPolicyRates


def policy_row_to_rates(row: PricingPolicy) -> PricingPolicyRates:
    return PricingPolicyRates(
        id=row.id,
        market_id=row.market_id,
        pricing_version=row.pricing_version,
        currency=row.currency,
        base_fare_cents=row.base_fare_cents,
        per_mile_cents=row.per_mile_cents,
        per_minute_cents=row.per_minute_cents,
        minimum_ride_fare_cents=row.minimum_ride_fare_cents,
        platform_service_fee_cents=row.platform_service_fee_cents,
        commission_rate_bps=row.commission_rate_bps,
        driver_share_bps=row.driver_share_bps,
        wait_fee_per_minute_cents=row.wait_fee_per_minute_cents,
        wait_grace_period_minutes=row.wait_grace_period_minutes,
        cancellation_fee_cents=row.cancellation_fee_cents,
        city_fee_cents=row.city_fee_cents,
        accessibility_fee_cents=row.accessibility_fee_cents,
        airport_fee_cents=row.airport_fee_cents,
        demand_multiplier_bps=row.demand_multiplier_bps,
        traffic_aware_pricing=bool(row.traffic_aware_pricing),
    )


def get_active_pricing_policy(
    db: Session,
    *,
    market_id: Optional[str] = None,
    policy_id: Optional[str] = None,
) -> PricingPolicyRates:
    query = db.query(PricingPolicy).filter(PricingPolicy.is_active.is_(True))
    if policy_id:
        row = query.filter(PricingPolicy.id == policy_id).first()
    elif market_id:
        row = query.filter(PricingPolicy.market_id == market_id).order_by(PricingPolicy.created_at.desc()).first()
    else:
        row = query.filter(PricingPolicy.id == DEFAULT_US_LAUNCH_POLICY.id).first()
        if row is None:
            row = query.order_by(PricingPolicy.created_at.desc()).first()
    if row is None:
        return DEFAULT_US_LAUNCH_POLICY
    return policy_row_to_rates(row)
