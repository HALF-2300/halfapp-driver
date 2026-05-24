"""Routing provider abstraction — self-hosted OSRM with honest haversine fallback."""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

from services.datetime_utils import utc_now_naive
from services import traffic_signals_service
from services import osrm_self_hosted_provider

OSRM_PROVIDER_ID = osrm_self_hosted_provider.PROVIDER_ID

def _routing_provider() -> str:
    return os.getenv("ROUTING_PROVIDER", "osrm_self_hosted").strip().lower()


def _traffic_provider() -> str:
    return os.getenv("TRAFFIC_PROVIDER", "none").strip().lower()


def _routing_fallback_enabled() -> bool:
    return os.getenv("ROUTING_FALLBACK_ENABLED", "true").lower() in {"1", "true", "yes"}


def _google_maps_fallback_enabled() -> bool:
    return os.getenv("GOOGLE_MAPS_FALLBACK_ENABLED", "false").lower() == "true"


def _mapbox_traffic_enabled() -> bool:
    return os.getenv("MAPBOX_TRAFFIC_ENABLED", "false").lower() == "true"

HAVERSINE_FALLBACK_PROVIDER = "haversine_fallback"
KM_PER_MILE = 0.621371

_ROUTE_CACHE: dict[str, tuple[datetime, "RouteEstimate"]] = {}
_ROUTE_CACHE_TTL_SECONDS = 60
_ROUTE_CALL_COUNT = 0
_OSRM_CALL_COUNT = 0


@dataclass(frozen=True)
class RouteEstimate:
    distance_km: float
    duration_minutes: int
    route_provider: str
    traffic_provider: str
    traffic_aware: bool
    traffic_signal_aware: bool
    route_confidence: str
    route_calculated_at: datetime
    distance_miles: float = 0.0
    eta_traffic_buffer_minutes: int = 0
    traffic_signal_count: int = 0
    used_fallback: bool = False


def _cache_key(origin: tuple[float, float], destination: tuple[float, float]) -> str:
    return f"{origin[0]:.5f},{origin[1]:.5f}->{destination[0]:.5f},{destination[1]:.5f}"


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    from math import asin, cos, radians, sin, sqrt

    r = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return max(0.0, r * c * 1.25)


def _haversine_estimate(
    origin: tuple[float, float],
    destination: tuple[float, float],
) -> RouteEstimate:
    lat1, lon1 = origin
    lat2, lon2 = destination
    distance_km = round(_haversine_km(lat1, lon1, lat2, lon2), 3)
    duration_minutes = max(1, int(round((distance_km / 30.0) * 60))) if distance_km > 0 else 0
    return RouteEstimate(
        distance_km=distance_km,
        duration_minutes=duration_minutes,
        distance_miles=round(distance_km * KM_PER_MILE, 3),
        route_provider=HAVERSINE_FALLBACK_PROVIDER,
        traffic_provider="none",
        traffic_aware=False,
        traffic_signal_aware=False,
        route_confidence="low",
        route_calculated_at=utc_now_naive(),
        used_fallback=True,
    )


def _try_osrm_route(
    origin: tuple[float, float],
    destination: tuple[float, float],
) -> Optional[RouteEstimate]:
    global _OSRM_CALL_COUNT

    try:
        result = osrm_self_hosted_provider.fetch_osrm_route(origin, destination)
        _OSRM_CALL_COUNT += 1
        return RouteEstimate(
            distance_km=result.distance_km,
            duration_minutes=result.duration_minutes,
            distance_miles=result.distance_miles,
            route_provider=OSRM_PROVIDER_ID,
            traffic_provider="none",
            traffic_aware=False,
            traffic_signal_aware=False,
            route_confidence="medium",
            route_calculated_at=utc_now_naive(),
            used_fallback=False,
        )
    except Exception:
        return None


def _apply_traffic_signals(
    estimate: RouteEstimate,
    origin: tuple[float, float],
    destination: tuple[float, float],
) -> RouteEstimate:
    traffic = estimate.traffic_provider
    traffic_aware = estimate.traffic_aware
    traffic_signal_aware = estimate.traffic_signal_aware
    route_confidence = estimate.route_confidence
    duration_minutes = estimate.duration_minutes
    eta_buffer = 0
    signal_count = 0

    use_signals = traffic_signals_service.TRAFFIC_SIGNALS_ENABLED or _traffic_provider() in (
        "odot_tripcheck",
        "wsdot",
        "regional",
        "free_official",
    )
    if use_signals and not _mapbox_traffic_enabled():
        signals_result = traffic_signals_service.resolve_traffic_signals_for_route(
            origin, destination
        )
        if signals_result.provider != "none":
            traffic = signals_result.provider
        traffic_signal_aware = signals_result.traffic_signal_aware
        if not estimate.used_fallback:
            route_confidence = signals_result.route_confidence
        eta_buffer = signals_result.eta_buffer_minutes
        signal_count = len(signals_result.signals)
        duration_minutes = max(duration_minutes, duration_minutes + eta_buffer)

    return RouteEstimate(
        distance_km=estimate.distance_km,
        duration_minutes=duration_minutes,
        distance_miles=estimate.distance_miles,
        route_provider=estimate.route_provider,
        traffic_provider=traffic,
        traffic_aware=traffic_aware,
        traffic_signal_aware=traffic_signal_aware,
        route_confidence=route_confidence,
        route_calculated_at=estimate.route_calculated_at,
        eta_traffic_buffer_minutes=eta_buffer,
        traffic_signal_count=signal_count,
        used_fallback=estimate.used_fallback,
    )


def _resolve_route_estimate(
    origin: tuple[float, float],
    destination: tuple[float, float],
) -> RouteEstimate:
    if _google_maps_fallback_enabled():
        raise RuntimeError("Google Maps routing is disabled in v0.1 unless explicitly enabled")
    if _mapbox_traffic_enabled():
        raise RuntimeError("Mapbox Traffic routing is disabled in v0.1 unless explicitly approved")

    provider = _routing_provider()

    if provider in ("osrm_self_hosted", "current_or_osrm"):
        osrm_est = _try_osrm_route(origin, destination)
        if osrm_est is not None:
            return osrm_est
        if _routing_fallback_enabled():
            return _haversine_estimate(origin, destination)
        raise RuntimeError("OSRM self-hosted routing unavailable and ROUTING_FALLBACK_ENABLED=false")

    if provider == "haversine_fallback":
        return _haversine_estimate(origin, destination)

    if provider == "valhalla_self_hosted":
        raise RuntimeError("valhalla_self_hosted is not wired in v0.1; use osrm_self_hosted")

    osrm_est = _try_osrm_route(origin, destination)
    if osrm_est is not None:
        return osrm_est
    return _haversine_estimate(origin, destination)


def route(
    origin: tuple[float, float],
    destination: tuple[float, float],
    *,
    options: Optional[dict[str, Any]] = None,
) -> RouteEstimate:
    global _ROUTE_CALL_COUNT
    _ROUTE_CALL_COUNT += 1

    key = _cache_key(origin, destination)
    cached = _ROUTE_CACHE.get(key)
    now = utc_now_naive()
    if cached and cached[0] > now - timedelta(seconds=_ROUTE_CACHE_TTL_SECONDS):
        return cached[1]

    estimate = _resolve_route_estimate(origin, destination)
    estimate = _apply_traffic_signals(estimate, origin, destination)
    _ROUTE_CACHE[key] = (now, estimate)
    return estimate


def estimate_distance_miles(
    origin: tuple[float, float],
    destination: tuple[float, float],
    *,
    options: Optional[dict[str, Any]] = None,
) -> float:
    return route(origin, destination, options=options).distance_miles


def estimate_duration_minutes(
    origin: tuple[float, float],
    destination: tuple[float, float],
    *,
    options: Optional[dict[str, Any]] = None,
) -> int:
    return route(origin, destination, options=options).duration_minutes


def estimate_eta(
    origin: tuple[float, float],
    destination: tuple[float, float],
    *,
    options: Optional[dict[str, Any]] = None,
) -> int:
    return estimate_duration_minutes(origin, destination, options=options)


def get_traffic_for_route(route_estimate: RouteEstimate) -> Optional[dict[str, Any]]:
    if route_estimate.traffic_signal_aware or route_estimate.traffic_provider not in (
        "",
        "none",
        "disabled",
    ):
        return {
            "status": "signals_only",
            "provider": route_estimate.traffic_provider,
            "traffic_signal_aware": route_estimate.traffic_signal_aware,
            "traffic_aware": False,
            "signal_count": route_estimate.traffic_signal_count,
            "eta_buffer_minutes": route_estimate.eta_traffic_buffer_minutes,
            "disclaimer": "Official incident/flow signals only — not live street traffic",
        }
    return None


def routing_call_count() -> int:
    return _ROUTE_CALL_COUNT


def osrm_call_count() -> int:
    return _OSRM_CALL_COUNT


def reset_routing_cache_for_tests() -> None:
    _ROUTE_CACHE.clear()
    global _ROUTE_CALL_COUNT, _OSRM_CALL_COUNT
    _ROUTE_CALL_COUNT = 0
    _OSRM_CALL_COUNT = 0
