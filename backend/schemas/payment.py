"""Pydantic schemas for Phase 3 ride payments."""

from pydantic import BaseModel, Field


class FareEstimateRequest(BaseModel):
    pickup_latitude: float = Field(..., ge=-90, le=90)
    pickup_longitude: float = Field(..., ge=-180, le=180)
    dropoff_latitude: float = Field(..., ge=-90, le=90)
    dropoff_longitude: float = Field(..., ge=-180, le=180)
    distance_km: float | None = Field(None, ge=0)
    duration_minutes: int | None = Field(None, ge=0)


class FareEstimateResponse(BaseModel):
    amount_cents: int
    driver_payout_cents: int
    currency: str = "USD"
    formula: str = "base_fare + distance_rate + time_rate (v0.1 policy)"


class RidePaymentView(BaseModel):
    id: int
    ride_id: int
    rider_id: int | None = None
    driver_id: int | None = None
    amount_cents: int
    driver_payout_cents: int
    currency: str
    status: str
    created_at: str | None = None
    authorized_at: str | None = None
    captured_at: str | None = None
    failed_at: str | None = None


class RidePaymentResponse(BaseModel):
    message: str
    payment: RidePaymentView


class DriverRidePaymentsResponse(BaseModel):
    message: str
    payments: list[RidePaymentView]
    total_captured_cents: int
