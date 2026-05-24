"""Pydantic views for v0.1 ride pricing ledger."""
from typing import Optional

from pydantic import BaseModel, Field


class RidePricingView(BaseModel):
    pricing_policy_id: Optional[str] = None
    pricing_version: Optional[str] = None
    market_id: Optional[str] = None
    base_fare_cents: int = Field(0, ge=0)
    distance_fare_cents: int = Field(0, ge=0)
    time_fare_cents: int = Field(0, ge=0)
    wait_fee_cents: int = Field(0, ge=0)
    driver_shareable_fare_cents: int = Field(..., ge=0)
    platform_service_fee_cents: int = Field(..., ge=0)
    tip_cents: int = Field(..., ge=0)
    city_fee_cents: int = Field(..., ge=0)
    airport_fee_cents: int = Field(..., ge=0)
    toll_cents: int = Field(..., ge=0)
    accessibility_fee_cents: int = Field(..., ge=0)
    tax_cents: int = Field(..., ge=0)
    platform_commission_cents: int = Field(..., ge=0)
    driver_commission_cents: int = Field(..., ge=0, description="Alias: driver_ride_payout_cents")
    driver_ride_payout_cents: int = Field(..., ge=0)
    driver_earnings_cents: int = Field(..., ge=0, description="Alias: driver_total_payout_cents")
    driver_total_payout_cents: int = Field(..., ge=0)
    platform_earnings_cents: int = Field(..., ge=0, description="Alias: platform_revenue_cents")
    platform_revenue_cents: int = Field(..., ge=0)
    pass_through_total_cents: int = Field(..., ge=0)
    total_rider_charge_cents: int = Field(..., ge=0, description="Alias: customer_total_cents")
    customer_total_cents: int = Field(..., ge=0)
    financial_locked: bool = False
    locked_at: Optional[str] = None
    fare_locked_at: Optional[str] = None


class CompleteRidePricingBody(BaseModel):
    """Optional rider-side fees and tip at completion — all integer cents."""

    platform_service_fee_cents: Optional[int] = Field(None, ge=0)
    tip_cents: int = Field(0, ge=0)
    city_fee_cents: int = Field(0, ge=0)
    airport_fee_cents: int = Field(0, ge=0)
    toll_cents: int = Field(0, ge=0)
    accessibility_fee_cents: int = Field(0, ge=0)
    tax_cents: int = Field(0, ge=0)
