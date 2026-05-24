"""v0.1 product lifecycle labels — maps storage statuses to foundation vocabulary."""
from __future__ import annotations

from typing import Optional

from models.ride import Ride
from models.ride_pricing import RidePricing
from services.lifecycle import RideStatus, normalize_ride_status

V01_REQUESTED = "requested"
V01_PRICED = "priced"
V01_DRIVER_ASSIGNED = "driver_assigned"
V01_DRIVER_ARRIVING = "driver_arriving"
V01_IN_PROGRESS = "in_progress"
V01_COMPLETED = "completed"
V01_CANCELLED = "cancelled"

V01_LIFECYCLE_STATUSES = frozenset(
    {
        V01_REQUESTED,
        V01_PRICED,
        V01_DRIVER_ASSIGNED,
        V01_DRIVER_ARRIVING,
        V01_IN_PROGRESS,
        V01_COMPLETED,
        V01_CANCELLED,
    }
)


def resolve_v01_lifecycle_status(
    ride: Ride,
    pricing_row: Optional[RidePricing] = None,
) -> str:
    """
    Map canonical storage statuses (accepted, driver_arrived, …) to v0.1 labels.
    Storage `status` remains the API contract for transitions; this field is display/ops truth.
    """
    storage = normalize_ride_status(ride.status)

    if storage == RideStatus.CANCELLED:
        return V01_CANCELLED
    if storage == RideStatus.COMPLETED:
        return V01_COMPLETED
    if storage == RideStatus.IN_PROGRESS:
        return V01_IN_PROGRESS
    if storage == RideStatus.DRIVER_ARRIVED:
        return V01_DRIVER_ARRIVING
    if storage == RideStatus.ACCEPTED:
        return V01_DRIVER_ASSIGNED
    if storage == RideStatus.REQUESTED:
        has_quote = pricing_row is not None and (pricing_row.driver_shareable_fare_cents or 0) > 0
        return V01_PRICED if has_quote else V01_REQUESTED

    # offered and other pre-pool states surface as requested until priced
    return V01_REQUESTED
