"""
Pydantic models for driver ride lifecycle — OpenAPI is generated from these + route annotations.
See docs/RIDE_LIFECYCLE_CONTRACT.md.
"""
from typing import Optional

from pydantic import BaseModel, Field

from schemas.ride_pricing import RidePricingView

class RideDriverView(BaseModel):
    """Single ride as returned in lists and transition bodies."""

    id: int
    rider_id: Optional[int] = None
    driver_id: Optional[int] = None
    customer_name: str
    status: str = Field(..., description="Ride lifecycle status (storage contract)")
    v01_lifecycle_status: Optional[str] = Field(
        None,
        description="v0.1 product label: requested|priced|driver_assigned|driver_arriving|in_progress|completed|cancelled",
    )
    pickup_location: Optional[str] = None
    dropoff_location: Optional[str] = None
    destination: Optional[str] = None
    pickup_latitude: Optional[float] = Field(None, ge=-90, le=90)
    pickup_longitude: Optional[float] = Field(None, ge=-180, le=180)
    dropoff_latitude: Optional[float] = Field(None, ge=-90, le=90)
    dropoff_longitude: Optional[float] = Field(None, ge=-180, le=180)
    fare_amount: Optional[float] = Field(
        None,
        description=(
            "Display dollars for the driver app: driver_total_payout_cents/100 when "
            "pricing exists. Not the customer total. Legacy rows may store pre-split totals."
        ),
    )
    driver_shareable_fare_cents: Optional[int] = Field(
        None, description="Top-level mirror of pricing.driver_shareable_fare_cents when quoted."
    )
    driver_total_payout_cents: Optional[int] = Field(
        None, description="Top-level mirror of pricing.driver_total_payout_cents (commission + tips)."
    )
    customer_total_cents: Optional[int] = Field(
        None, description="Top-level mirror of pricing.customer_total_cents."
    )
    platform_revenue_cents: Optional[int] = Field(
        None, description="Top-level mirror of pricing.platform_revenue_cents."
    )
    distance_km: Optional[float] = None
    duration_minutes: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    accepted_at: Optional[str] = None
    arrived_pickup_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    cancelled_at: Optional[str] = None
    lifecycle_reason: Optional[str] = None
    ride_visibility_id: Optional[int] = Field(None, description="Backend visibility record proving this ride was exposed to this driver")
    visibility_correlation_id: Optional[str] = Field(None, description="Correlation ID for the visibility/audit chain")
    visibility_reason: Optional[str] = Field(None, description="Backend reason this ride was visible to this driver")
    ordering_rank: Optional[int] = Field(None, description="Deterministic dispatch rank for this driver when listed")
    ordering_score: Optional[float] = Field(None, description="Dispatch ordering score for this driver when listed")
    why_this_rank: Optional[dict] = Field(None, description="Backend explanation for the available-ride rank")
    dispatch_policy_id: Optional[str] = Field(None, description="Stable dispatch policy identifier")
    dispatch_policy_name: Optional[str] = Field(None, description="Human-readable dispatch policy name")
    ordered_by: Optional[list[str]] = Field(None, description="Ordered list of backend sort keys used by the dispatch policy")
    policy_version: Optional[str] = Field(None, description="Dispatch policy version that generated this view")
    generated_at: Optional[str] = Field(None, description="Server timestamp for the dispatch view")
    dispatch_expires_at: Optional[str] = Field(
        None, description="ISO timestamp when the current sequential dispatch offer expires (RIDE-003)"
    )
    dispatch_timeout_seconds: Optional[int] = Field(
        None, description="Configured offer timeout in seconds for the driver request card countdown"
    )
    pricing: Optional[RidePricingView] = Field(None, description="v0.1 integer-cent pricing ledger")
    route_provider: Optional[str] = Field(None, description="Map route provider id (v0.1: leaflet_osm)")
    traffic_provider: Optional[str] = Field(
        None, description="Traffic signal provider (odot_tripcheck, wsdot, or none)"
    )
    traffic_aware: Optional[bool] = Field(
        None, description="Route-level live traffic timing (false in v0.1 — no paid/Google traffic)"
    )
    traffic_signal_aware: Optional[bool] = Field(
        None, description="Official incident/flow warnings applied to this ride view"
    )
    route_confidence: Optional[str] = Field(None, description="Route confidence label from backend")
    route_calculated_at: Optional[str] = Field(None, description="When route metadata was stamped")
    google_maps_fallback_enabled: bool = Field(False, description="Google routing fallback (off in v0.1)")
    mapbox_traffic_enabled: bool = Field(False, description="Mapbox Traffic (off in v0.1)")

    model_config = {"json_schema_extra": {"examples": [{"id": 1, "customer_name": "Ada", "status": "requested"}]}}


class RideTransitionResponse(BaseModel):
    message: str
    ride: RideDriverView


class CompleteRideResponse(BaseModel):
    message: str
    fare_earned: float = Field(
        ...,
        description="Driver total payout in dollars (driver_total_payout_cents/100). Not customer total.",
    )
    ride: RideDriverView


class DeclineRideBody(BaseModel):
    reason: Optional[str] = Field(None, max_length=500)
