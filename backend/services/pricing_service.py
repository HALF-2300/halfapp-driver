"""U.S. ride pricing ledger v0.1 — integer cents only, policy-driven."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# Launch defaults (configurable per pricing policy row)
DEFAULT_COMMISSION_RATE_BPS = 2000  # 20% platform share of driver-shareable fare
DEFAULT_DRIVER_SHARE_BPS = 8000  # 80% driver share of driver-shareable fare
DEFAULT_PLATFORM_SERVICE_FEE_CENTS = 150
DEFAULT_DEMAND_MULTIPLIER_BPS = 10000  # 1.0x — surge disabled
KM_PER_MILE = 0.621371


def round_money(cents: int) -> int:
    """Integer cents are already whole units; keep hook for future fractional bps."""
    return int(cents)


@dataclass(frozen=True)
class PricingPolicyRates:
    id: str
    market_id: str
    pricing_version: str
    currency: str
    base_fare_cents: int
    per_mile_cents: int
    per_minute_cents: int
    minimum_ride_fare_cents: int
    platform_service_fee_cents: int
    commission_rate_bps: int
    driver_share_bps: int
    wait_fee_per_minute_cents: int
    wait_grace_period_minutes: int
    cancellation_fee_cents: int
    city_fee_cents: int
    accessibility_fee_cents: int
    airport_fee_cents: int
    demand_multiplier_bps: int
    traffic_aware_pricing: bool


# Launch default — seeded in DB migration; used when no policy row exists.
DEFAULT_US_LAUNCH_POLICY = PricingPolicyRates(
    id="us-launch-v0-1",
    market_id="US-DEFAULT",
    pricing_version="v0.1",
    currency="USD",
    base_fare_cents=500,
    per_mile_cents=150,  # ~$1.50/km equivalent at demo scale
    per_minute_cents=25,
    minimum_ride_fare_cents=800,
    platform_service_fee_cents=DEFAULT_PLATFORM_SERVICE_FEE_CENTS,
    commission_rate_bps=DEFAULT_COMMISSION_RATE_BPS,
    driver_share_bps=DEFAULT_DRIVER_SHARE_BPS,
    wait_fee_per_minute_cents=0,
    wait_grace_period_minutes=2,
    cancellation_fee_cents=0,
    city_fee_cents=0,
    accessibility_fee_cents=0,
    airport_fee_cents=0,
    demand_multiplier_bps=DEFAULT_DEMAND_MULTIPLIER_BPS,
    traffic_aware_pricing=False,
)


@dataclass(frozen=True)
class RideFareComponents:
    base_fare_cents: int
    distance_fare_cents: int
    time_fare_cents: int
    wait_fee_cents: int
    driver_shareable_ride_fare_cents: int


@dataclass(frozen=True)
class RideFinancialBreakdown:
    """All amounts in integer cents — matches v0.1 ledger spec."""
    pricing_policy_id: str
    pricing_version: str
    market_id: str
    currency: str
    base_fare_cents: int
    distance_fare_cents: int
    time_fare_cents: int
    wait_fee_cents: int
    driver_shareable_ride_fare_cents: int
    platform_service_fee_cents: int
    city_fee_cents: int
    accessibility_fee_cents: int
    airport_fee_cents: int
    toll_cents: int
    tip_cents: int
    cancellation_fee_cents: int
    platform_commission_cents: int
    driver_ride_payout_cents: int
    driver_total_payout_cents: int
    platform_revenue_cents: int
    customer_total_cents: int
    traffic_aware: bool


def km_to_miles(distance_km: float) -> float:
    return max(0.0, float(distance_km or 0.0)) * KM_PER_MILE


def compute_fare_components(
    *,
    distance_km: float,
    duration_minutes: int,
    wait_minutes: int = 0,
    policy: PricingPolicyRates = DEFAULT_US_LAUNCH_POLICY,
) -> RideFareComponents:
    miles = km_to_miles(distance_km)
    minutes = max(0, int(duration_minutes or 0))
    billable_wait = max(0, wait_minutes - policy.wait_grace_period_minutes)

    base = policy.base_fare_cents
    distance_fare = int(round(miles * policy.per_mile_cents))
    time_fare = minutes * policy.per_minute_cents
    wait_fee = billable_wait * policy.wait_fee_per_minute_cents

    subtotal = base + distance_fare + time_fare + wait_fee
    if policy.demand_multiplier_bps != 10000:
        subtotal = (subtotal * policy.demand_multiplier_bps) // 10_000

    shareable = max(subtotal, policy.minimum_ride_fare_cents)
    return RideFareComponents(
        base_fare_cents=base,
        distance_fare_cents=distance_fare,
        time_fare_cents=time_fare,
        wait_fee_cents=wait_fee,
        driver_shareable_ride_fare_cents=shareable,
    )


def compute_financials(
    *,
    driver_shareable_ride_fare_cents: int,
    platform_service_fee_cents: Optional[int] = None,
    tip_cents: int = 0,
    city_fee_cents: int = 0,
    airport_fee_cents: int = 0,
    toll_cents: int = 0,
    accessibility_fee_cents: int = 0,
    cancellation_fee_cents: int = 0,
    driver_reimbursed_tolls_cents: int = 0,
    policy: PricingPolicyRates = DEFAULT_US_LAUNCH_POLICY,
    components: Optional[RideFareComponents] = None,
) -> RideFinancialBreakdown:
    """
    Commission applies only to driver-shareable ride fare (80/20 bps split).
    Service fee, pass-through fees, and tips are excluded from commission.
    """
    shareable = max(0, int(driver_shareable_ride_fare_cents))
    service_fee = (
        policy.platform_service_fee_cents
        if platform_service_fee_cents is None
        else max(0, int(platform_service_fee_cents))
    )
    tip = max(0, int(tip_cents))
    city = max(0, int(city_fee_cents))
    airport = max(0, int(airport_fee_cents))
    toll = max(0, int(toll_cents))
    accessibility = max(0, int(accessibility_fee_cents))
    cancel_fee = max(0, int(cancellation_fee_cents))
    reimbursed_tolls = max(0, int(driver_reimbursed_tolls_cents))

    platform_commission = round_money((shareable * policy.commission_rate_bps) // 10_000)
    driver_ride_payout = shareable - platform_commission
    driver_total = driver_ride_payout + tip + reimbursed_tolls
    platform_revenue = platform_commission + service_fee
    customer_total = (
        shareable
        + service_fee
        + city
        + accessibility
        + airport
        + toll
        + tip
        + cancel_fee
    )

    comp = components or RideFareComponents(
        base_fare_cents=0,
        distance_fare_cents=0,
        time_fare_cents=0,
        wait_fee_cents=0,
        driver_shareable_ride_fare_cents=shareable,
    )

    return RideFinancialBreakdown(
        pricing_policy_id=policy.id,
        pricing_version=policy.pricing_version,
        market_id=policy.market_id,
        currency=policy.currency,
        base_fare_cents=comp.base_fare_cents,
        distance_fare_cents=comp.distance_fare_cents,
        time_fare_cents=comp.time_fare_cents,
        wait_fee_cents=comp.wait_fee_cents,
        driver_shareable_ride_fare_cents=shareable,
        platform_service_fee_cents=service_fee,
        city_fee_cents=city,
        accessibility_fee_cents=accessibility,
        airport_fee_cents=airport,
        toll_cents=toll,
        tip_cents=tip,
        cancellation_fee_cents=cancel_fee,
        platform_commission_cents=platform_commission,
        driver_ride_payout_cents=driver_ride_payout,
        driver_total_payout_cents=driver_total,
        platform_revenue_cents=platform_revenue,
        customer_total_cents=customer_total,
        traffic_aware=policy.traffic_aware_pricing,
    )


def compute_ride_financials_from_trip(
    *,
    distance_km: float,
    duration_minutes: int,
    wait_minutes: int = 0,
    platform_service_fee_cents: Optional[int] = None,
    tip_cents: int = 0,
    city_fee_cents: int = 0,
    airport_fee_cents: int = 0,
    toll_cents: int = 0,
    accessibility_fee_cents: int = 0,
    cancellation_fee_cents: int = 0,
    driver_reimbursed_tolls_cents: int = 0,
    policy: PricingPolicyRates = DEFAULT_US_LAUNCH_POLICY,
) -> RideFinancialBreakdown:
    components = compute_fare_components(
        distance_km=distance_km,
        duration_minutes=duration_minutes,
        wait_minutes=wait_minutes,
        policy=policy,
    )
    return compute_financials(
        driver_shareable_ride_fare_cents=components.driver_shareable_ride_fare_cents,
        platform_service_fee_cents=platform_service_fee_cents,
        tip_cents=tip_cents,
        city_fee_cents=city_fee_cents or policy.city_fee_cents,
        airport_fee_cents=airport_fee_cents or policy.airport_fee_cents,
        toll_cents=toll_cents,
        accessibility_fee_cents=accessibility_fee_cents or policy.accessibility_fee_cents,
        cancellation_fee_cents=cancellation_fee_cents,
        driver_reimbursed_tolls_cents=driver_reimbursed_tolls_cents,
        policy=policy,
        components=components,
    )
