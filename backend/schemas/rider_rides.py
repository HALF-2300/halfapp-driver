"""
Pydantic models for rider-side ride lifecycle endpoints.

Stage 3 polish adds the minimum a rider needs to drive the cancelled state honestly:

* `POST /rides/` — customer creates a ride request (status starts at `requested`).
* `POST /rides/{ride_id}/cancel` — customer cancels their own ride, allowed only from
  `requested` or `accepted`. Sets `status=cancelled`, `cancelled_at`, and optional
  `lifecycle_reason`. The driver's `my-rides` view still surfaces the ride so the
  driver can see why it disappeared from their active trip.
"""
from pydantic import BaseModel, Field

from schemas.rides import RideCreateRequest
from schemas.ride_lifecycle import RideDriverView


class RiderRideCreate(RideCreateRequest):
    """Minimal request body for a customer to open a ride request.

    `customer_name` is preserved for backward compatibility with existing rows; when
    omitted, the server uses the authenticated customer's `name`.
    """

    pickup_latitude: float = Field(..., ge=-90, le=90)
    pickup_longitude: float = Field(..., ge=-180, le=180)
    dropoff_latitude: float = Field(..., ge=-90, le=90)
    dropoff_longitude: float = Field(..., ge=-180, le=180)


class RiderCancelBody(BaseModel):
    """Optional `reason` text the rider supplies; stored verbatim in `lifecycle_reason`."""

    reason: str | None = Field(None, max_length=500)


class RiderRideResponse(BaseModel):
    """Server response for rider create/cancel — uses the same `RideDriverView` shape
    drivers see so both sides can render the same ride object identically."""

    message: str
    ride: RideDriverView
    create_request_contract: RideCreateRequest | None = None


class RiderRidesListResponse(BaseModel):
    message: str
    rides: list[RideDriverView]
