"""Ground ride route metadata from the configured routing provider (OSRM v0.1)."""
from __future__ import annotations

from typing import Optional

from models.ride import Ride
from services.map_route_foundation import apply_route_estimate, stamp_route_calculated
from services.routing_service import RouteEstimate, route


def ride_has_routable_coordinates(ride: Ride) -> bool:
    return (
        ride.pickup_latitude is not None
        and ride.pickup_longitude is not None
        and ride.dropoff_latitude is not None
        and ride.dropoff_longitude is not None
    )


def ground_ride_route(ride: Ride) -> Optional[RouteEstimate]:
    """Resolve distance/duration from OSRM (or honest fallback) and stamp the ride row."""
    if not ride_has_routable_coordinates(ride):
        stamp_route_calculated(ride)
        return None
    origin = (float(ride.pickup_latitude), float(ride.pickup_longitude))
    destination = (float(ride.dropoff_latitude), float(ride.dropoff_longitude))
    estimate = route(origin, destination)
    apply_route_estimate(ride, estimate)
    stamp_route_calculated(ride)
    return estimate
