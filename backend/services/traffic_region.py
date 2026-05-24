"""Geographic region hints for free official traffic signal providers (v0.1)."""
from __future__ import annotations

from typing import Literal

TrafficRegion = Literal["odot_tripcheck", "wsdot", "none"]


def traffic_region_for_point(lat: float, lng: float) -> TrafficRegion:
    """
    Pick the official traffic provider for a coordinate.
    Portland metro (~45.52, -122.68) -> ODOT; Vancouver WA (~45.63, -122.67) -> WSDOT.
    """
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return "none"

    # Clark County / Vancouver WA (north of Columbia, east of Portland core)
    if 45.58 <= lat <= 49.05 and -122.95 <= lng <= -122.35:
        return "wsdot"

    # Oregon (includes Portland metro)
    if 41.99 <= lat <= 46.30 and -124.85 <= lng <= -116.45:
        return "odot_tripcheck"

    # Remaining Washington
    if 45.50 <= lat <= 49.05 and -124.90 <= lng <= -116.90:
        return "wsdot"

    return "none"


def traffic_region_for_route(
    origin: tuple[float, float],
    destination: tuple[float, float],
) -> TrafficRegion:
    """Prefer destination region, then origin, for mixed short routes."""
    for point in (destination, origin):
        region = traffic_region_for_point(point[0], point[1])
        if region != "none":
            return region
    return "none"
