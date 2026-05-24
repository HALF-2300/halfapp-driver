from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from database import Base
from services.datetime_utils import utc_now_naive


class RidePricing(Base):
    """Per-ride financial ledger row — integer cents, locked when ride completes."""

    __tablename__ = "ride_pricing"

    ride_id = Column(Integer, ForeignKey("rides.id", ondelete="CASCADE"), primary_key=True)
    pricing_policy_id = Column(String, nullable=True)
    pricing_version = Column(String, nullable=True)
    market_id = Column(String, nullable=True)
    base_fare_cents = Column(Integer, nullable=False, default=0)
    distance_fare_cents = Column(Integer, nullable=False, default=0)
    time_fare_cents = Column(Integer, nullable=False, default=0)
    wait_fee_cents = Column(Integer, nullable=False, default=0)
    driver_shareable_fare_cents = Column(Integer, nullable=False, default=0)
    platform_service_fee_cents = Column(Integer, nullable=False, default=150)
    tip_cents = Column(Integer, nullable=False, default=0)
    city_fee_cents = Column(Integer, nullable=False, default=0)
    airport_fee_cents = Column(Integer, nullable=False, default=0)
    toll_cents = Column(Integer, nullable=False, default=0)
    accessibility_fee_cents = Column(Integer, nullable=False, default=0)
    tax_cents = Column(Integer, nullable=False, default=0)
    cancellation_fee_cents = Column(Integer, nullable=False, default=0)
    driver_commission_cents = Column(Integer, nullable=False, default=0)
    platform_commission_cents = Column(Integer, nullable=False, default=0)
    driver_ride_payout_cents = Column(Integer, nullable=False, default=0)
    driver_earnings_cents = Column(Integer, nullable=False, default=0)
    platform_earnings_cents = Column(Integer, nullable=False, default=0)
    platform_revenue_cents = Column(Integer, nullable=False, default=0)
    pass_through_total_cents = Column(Integer, nullable=False, default=0)
    total_rider_charge_cents = Column(Integer, nullable=False, default=0)
    customer_total_cents = Column(Integer, nullable=False, default=0)
    financial_locked = Column(Boolean, nullable=False, default=False)
    locked_at = Column(DateTime, nullable=True)
    fare_locked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now_naive, nullable=False)
    updated_at = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive, nullable=False)
