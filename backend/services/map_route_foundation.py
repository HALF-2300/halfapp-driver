"""v0.1 map route foundation metadata — OSM/Leaflet only; paid providers disabled by default."""
from __future__ import annotations

from typing import Optional

from config import (
    GOOGLE_MAPS_FALLBACK_ENABLED,
    MAPBOX_TRAFFIC_ENABLED,
    MAP_DISPLAY_PROVIDER,
    ROUTING_PROVIDER,
    TRAFFIC_PROVIDER,
)
from models.ride import Ride
from services.datetime_utils import utc_now_naive
from services.routing_service import RouteEstimate

V01_ROUTE_PROVIDER = ROUTING_PROVIDER or "osrm_self_hosted"
V01_MAP_DISPLAY_PROVIDER = MAP_DISPLAY_PROVIDER or "current_osm_leaflet"
V01_TRAFFIC_PROVIDER = TRAFFIC_PROVIDER if TRAFFIC_PROVIDER else "none"
V01_ROUTE_CONFIDENCE = "medium"


def apply_map_foundation_defaults(ride: Ride) -> None:
    """Set provider fields when absent; never enables Google or Mapbox Traffic unless env allows."""
    if not ride.route_provider:
        ride.route_provider = V01_ROUTE_PROVIDER
    if not ride.traffic_provider:
        ride.traffic_provider = V01_TRAFFIC_PROVIDER
    if ride.traffic_aware is None:
        ride.traffic_aware = (
            V01_TRAFFIC_PROVIDER not in ("", "none", "disabled")
            and MAPBOX_TRAFFIC_ENABLED
        )
    if ride.traffic_signal_aware is None:
        ride.traffic_signal_aware = False
    if ride.route_confidence is None:
        ride.route_confidence = V01_ROUTE_CONFIDENCE
    if ride.google_maps_fallback_enabled is None:
        ride.google_maps_fallback_enabled = GOOGLE_MAPS_FALLBACK_ENABLED
    if ride.mapbox_traffic_enabled is None:
        ride.mapbox_traffic_enabled = MAPBOX_TRAFFIC_ENABLED


def apply_route_estimate(ride: Ride, estimate: RouteEstimate) -> None:
    ride.distance = estimate.distance_km
    ride.duration = estimate.duration_minutes
    ride.route_provider = estimate.route_provider
    ride.traffic_provider = estimate.traffic_provider
    ride.traffic_aware = estimate.traffic_aware
    ride.traffic_signal_aware = estimate.traffic_signal_aware
    ride.route_confidence = estimate.route_confidence
    ride.route_calculated_at = estimate.route_calculated_at
    ride.google_maps_fallback_enabled = GOOGLE_MAPS_FALLBACK_ENABLED
    ride.mapbox_traffic_enabled = MAPBOX_TRAFFIC_ENABLED


def stamp_route_calculated(ride: Ride) -> None:
    apply_map_foundation_defaults(ride)
    if ride.route_calculated_at is None:
        ride.route_calculated_at = utc_now_naive()


def map_foundation_dict(ride: Ride) -> dict:
    apply_map_foundation_defaults(ride)
    calculated = ride.route_calculated_at
    return {
        "route_provider": ride.route_provider or V01_ROUTE_PROVIDER,
        "traffic_provider": ride.traffic_provider or V01_TRAFFIC_PROVIDER,
        "traffic_aware": bool(ride.traffic_aware),
        "traffic_signal_aware": bool(ride.traffic_signal_aware),
        "route_confidence": ride.route_confidence,
        "route_calculated_at": calculated.isoformat() + "Z" if calculated else None,
        "google_maps_fallback_enabled": bool(ride.google_maps_fallback_enabled),
        "mapbox_traffic_enabled": bool(ride.mapbox_traffic_enabled),
        "map_display_provider": V01_MAP_DISPLAY_PROVIDER,
    }


def external_routing_enabled(ride: Ride) -> bool:
    """True when a paid or Google routing provider would be used — must stay false in v0.1 default."""
    return bool(ride.google_maps_fallback_enabled or ride.mapbox_traffic_enabled)
