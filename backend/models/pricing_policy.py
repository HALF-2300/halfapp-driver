"""Per-market pricing policy — integer cents and bps only."""
from sqlalchemy import Boolean, Column, DateTime, Integer, String

from database import Base
from services.datetime_utils import utc_now_naive


class PricingPolicy(Base):
    __tablename__ = "pricing_policies"

    id = Column(String, primary_key=True)
    market_id = Column(String, nullable=False, index=True)
    city_code = Column(String, nullable=True, index=True)
    pricing_version = Column(String, nullable=False)
    currency = Column(String, nullable=False, default="USD")
    base_fare_cents = Column(Integer, nullable=False)
    per_mile_cents = Column(Integer, nullable=False)
    per_minute_cents = Column(Integer, nullable=False)
    minimum_ride_fare_cents = Column(Integer, nullable=False)
    platform_service_fee_cents = Column(Integer, nullable=False)
    commission_rate_bps = Column(Integer, nullable=False)
    driver_share_bps = Column(Integer, nullable=False)
    wait_fee_per_minute_cents = Column(Integer, nullable=False, default=0)
    wait_grace_period_minutes = Column(Integer, nullable=False, default=2)
    cancellation_fee_cents = Column(Integer, nullable=False, default=0)
    city_fee_cents = Column(Integer, nullable=False, default=0)
    accessibility_fee_cents = Column(Integer, nullable=False, default=0)
    airport_fee_cents = Column(Integer, nullable=False, default=0)
    demand_multiplier_bps = Column(Integer, nullable=False, default=10000)
    traffic_aware_pricing = Column(Boolean, nullable=False, default=False)
    active_from = Column(DateTime, nullable=True)
    active_to = Column(DateTime, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=utc_now_naive, nullable=False)
