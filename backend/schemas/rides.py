from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from services.lifecycle import RideAction, RideStatus


class RideCreateRequest(BaseModel):
    pickup_location: str = Field(..., min_length=1, max_length=500)
    dropoff_location: str = Field(..., min_length=1, max_length=500)

    # Existing product fields kept in the explicit contract for current rider flows.
    customer_name: Optional[str] = Field(None, max_length=120)
    destination: Optional[str] = Field(None, max_length=500)
    pickup_latitude: Optional[float] = Field(None, ge=-90, le=90)
    pickup_longitude: Optional[float] = Field(None, ge=-180, le=180)
    dropoff_latitude: Optional[float] = Field(None, ge=-90, le=90)
    dropoff_longitude: Optional[float] = Field(None, ge=-180, le=180)
    distance_km: Optional[float] = Field(None, ge=0, le=10_000)
    duration_minutes: Optional[int] = Field(None, ge=0, le=24 * 60)


class RideActionRequest(BaseModel):
    action: RideAction


class RideResponse(BaseModel):
    id: int
    rider_id: Optional[int] = None
    driver_id: Optional[int] = None
    pickup_location: Optional[str] = None
    dropoff_location: Optional[str] = None
    status: RideStatus
    created_at: Optional[datetime | str] = None
    updated_at: Optional[datetime | str] = None

    # Existing fields already exposed by the active product surface.
    customer_name: Optional[str] = None
    destination: Optional[str] = None
    pickup_latitude: Optional[float] = None
    pickup_longitude: Optional[float] = None
    dropoff_latitude: Optional[float] = None
    dropoff_longitude: Optional[float] = None
    fare_amount: Optional[float] = None
    distance_km: Optional[float] = None
    duration_minutes: Optional[int] = None
    accepted_at: Optional[str] = None
    arrived_pickup_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    cancelled_at: Optional[str] = None
    lifecycle_reason: Optional[str] = None
    ordering_rank: Optional[int] = Field(None, description="Deterministic dispatch rank for this driver when listed")
    policy_version: Optional[str] = Field(None, description="Dispatch policy version that generated this view")
    generated_at: Optional[str] = Field(None, description="Server timestamp for the dispatch view")
