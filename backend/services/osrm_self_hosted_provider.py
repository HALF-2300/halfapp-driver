"""Self-hosted OSRM point-to-point routing (OpenStreetMap / Portland metro proof)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional
import httpx

PROVIDER_ID = "osrm_self_hosted"
KM_PER_MILE = 0.621371
DEFAULT_OSRM_BASE_URL = "http://127.0.0.1:5000"
OSRM_REQUEST_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True)
class OsrmRouteResult:
    distance_km: float
    duration_minutes: int
    distance_miles: float
    route_provider: str = PROVIDER_ID
    raw_distance_meters: float = 0.0
    raw_duration_seconds: float = 0.0


def get_osrm_base_url() -> str:
    return (os.getenv("OSRM_BASE_URL") or DEFAULT_OSRM_BASE_URL).rstrip("/")


def _coord_pair(lat: float, lng: float) -> tuple[float, float]:
    la = float(lat)
    ln = float(lng)
    if not (-90 <= la <= 90 and -180 <= ln <= 180):
        raise ValueError("Invalid lat/lng for OSRM request")
    return la, ln


def build_route_url(
    origin: tuple[float, float],
    destination: tuple[float, float],
    *,
    base_url: Optional[str] = None,
) -> str:
    """OSRM driving profile — coordinates are lon,lat in the path."""
    lat1, lon1 = _coord_pair(origin[0], origin[1])
    lat2, lon2 = _coord_pair(destination[0], destination[1])
    root = (base_url or get_osrm_base_url()).rstrip("/")
    path = f"/route/v1/driving/{lon1},{lat1};{lon2},{lat2}"
    return f"{root}{path}?overview=false&steps=false"


def parse_osrm_route_response(payload: dict[str, Any]) -> OsrmRouteResult:
    if payload.get("code") != "Ok":
        message = payload.get("message") or payload.get("code") or "unknown"
        raise ValueError(f"OSRM route failed: {message}")
    routes = payload.get("routes") or []
    if not routes:
        raise ValueError("OSRM returned no routes")
    leg = routes[0]
    distance_m = float(leg.get("distance") or 0)
    duration_s = float(leg.get("duration") or 0)
    if distance_m <= 0:
        raise ValueError("OSRM returned zero distance")
    distance_km = distance_m / 1000.0
    duration_minutes = max(1, int(round(duration_s / 60.0))) if duration_s > 0 else 1
    distance_miles = distance_km * KM_PER_MILE
    return OsrmRouteResult(
        distance_km=round(distance_km, 3),
        duration_minutes=duration_minutes,
        distance_miles=round(distance_miles, 3),
        raw_distance_meters=distance_m,
        raw_duration_seconds=duration_s,
    )


def fetch_osrm_route(
    origin: tuple[float, float],
    destination: tuple[float, float],
    *,
    base_url: Optional[str] = None,
    client: Optional[httpx.Client] = None,
) -> OsrmRouteResult:
    url = build_route_url(origin, destination, base_url=base_url)
    owns_client = client is None
    http = client or httpx.Client(timeout=OSRM_REQUEST_TIMEOUT_SECONDS)
    try:
        response = http.get(url)
        response.raise_for_status()
        return parse_osrm_route_response(response.json())
    finally:
        if owns_client:
            http.close()


def estimate_distance_miles(
    origin: tuple[float, float],
    destination: tuple[float, float],
    *,
    base_url: Optional[str] = None,
    client: Optional[httpx.Client] = None,
) -> float:
    return fetch_osrm_route(origin, destination, base_url=base_url, client=client).distance_miles


def estimate_duration_minutes(
    origin: tuple[float, float],
    destination: tuple[float, float],
    *,
    base_url: Optional[str] = None,
    client: Optional[httpx.Client] = None,
) -> int:
    return fetch_osrm_route(origin, destination, base_url=base_url, client=client).duration_minutes
