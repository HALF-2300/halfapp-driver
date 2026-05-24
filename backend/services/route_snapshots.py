"""Persist durable route evidence rows — honest provider/fallback, no secrets."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Optional

from sqlalchemy.orm import Session

from models.ride import Ride
from models.ride_pricing import RidePricing
from models.route_snapshot import (
    ALLOWED_SNAPSHOT_ROLES,
    SNAPSHOT_ROLE_ACCEPT,
    SNAPSHOT_ROLE_COMPLETE,
    SNAPSHOT_ROLE_DIAGNOSTIC,
    SNAPSHOT_ROLE_QUOTE,
    SNAPSHOT_ROLE_REFRESH,
    RouteSnapshot,
)
from services.datetime_utils import utc_now_naive
from services.map_route_foundation import apply_map_foundation_defaults
from services.routing_service import HAVERSINE_FALLBACK_PROVIDER, RouteEstimate

_SECRET_KEY_PATTERN = re.compile(
    r"(api[_-]?key|secret|authorization|password|token|access[_-]?token|bearer)",
    re.IGNORECASE,
)
_SENSITIVE_URL_KEYS = frozenset({"url", "base_url", "endpoint", "osrm_url"})


def validate_snapshot_role(role: str) -> str:
    normalized = (role or "").strip().lower()
    if normalized not in ALLOWED_SNAPSHOT_ROLES:
        raise ValueError(f"Unknown snapshot_role: {role}")
    return normalized


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def stable_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def sanitize_provenance(provenance: Optional[dict[str, Any]]) -> dict[str, Any]:
    if not provenance:
        return {}

    def _walk(value: Any, key: str = "") -> Any:
        if isinstance(value, dict):
            cleaned: dict[str, Any] = {}
            for child_key, child_value in value.items():
                if _SECRET_KEY_PATTERN.search(child_key):
                    continue
                if child_key.lower() in _SENSITIVE_URL_KEYS:
                    cleaned[child_key] = "<redacted>"
                    continue
                cleaned[child_key] = _walk(child_value, child_key)
            return cleaned
        if isinstance(value, list):
            return [_walk(item) for item in value]
        if isinstance(value, str) and _SECRET_KEY_PATTERN.search(key):
            return "<redacted>"
        return value

    return _walk(provenance) if isinstance(provenance, dict) else {}


def _km_to_meters(distance_km: float) -> int:
    return max(0, int(round(float(distance_km or 0.0) * 1000)))


def _minutes_to_seconds(duration_minutes: int) -> int:
    return max(0, int(duration_minutes or 0) * 60)


def _build_request_payload(
    ride: Ride,
    *,
    origin: Optional[tuple[float, float]] = None,
    destination: Optional[tuple[float, float]] = None,
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ride_id": ride.id,
        "pickup_latitude": origin[0] if origin else ride.pickup_latitude,
        "pickup_longitude": origin[1] if origin else ride.pickup_longitude,
        "dropoff_latitude": destination[0] if destination else ride.dropoff_latitude,
        "dropoff_longitude": destination[1] if destination else ride.dropoff_longitude,
    }
    if extra:
        payload.update(extra)
    return payload


def _build_response_payload(
    *,
    route_provider: str,
    used_fallback: bool,
    distance_meters: int,
    duration_seconds: int,
    route_confidence: Optional[str] = None,
    traffic_provider: Optional[str] = None,
) -> dict[str, Any]:
    return {
        "route_provider": route_provider,
        "used_fallback": used_fallback,
        "distance_meters": distance_meters,
        "duration_seconds": duration_seconds,
        "route_confidence": route_confidence,
        "traffic_provider": traffic_provider,
    }


def _fields_from_estimate(estimate: RouteEstimate) -> dict[str, Any]:
    return {
        "route_provider": estimate.route_provider,
        "used_fallback": bool(estimate.used_fallback),
        "distance_meters": _km_to_meters(estimate.distance_km),
        "duration_seconds": _minutes_to_seconds(estimate.duration_minutes),
        "route_confidence": estimate.route_confidence,
        "traffic_provider": estimate.traffic_provider,
        "route_calculated_at": estimate.route_calculated_at.isoformat() + "Z",
    }


def _fields_from_ride(ride: Ride) -> dict[str, Any]:
    apply_map_foundation_defaults(ride)
    provider = ride.route_provider or HAVERSINE_FALLBACK_PROVIDER
    used_fallback = provider == HAVERSINE_FALLBACK_PROVIDER
    return {
        "route_provider": provider,
        "used_fallback": used_fallback,
        "distance_meters": _km_to_meters(ride.distance or 0.0),
        "duration_seconds": _minutes_to_seconds(ride.duration or 0),
        "route_confidence": ride.route_confidence,
        "traffic_provider": ride.traffic_provider,
        "route_calculated_at": (
            ride.route_calculated_at.isoformat() + "Z" if ride.route_calculated_at else None
        ),
    }


def create_route_snapshot(
    db: Session,
    *,
    ride: Ride,
    route_result: Optional[RouteEstimate] = None,
    snapshot_role: str,
    pricing: Optional[RidePricing] = None,
    provenance: Optional[dict[str, Any]] = None,
    geometry_polyline: Optional[str] = None,
    origin: Optional[tuple[float, float]] = None,
    destination: Optional[tuple[float, float]] = None,
) -> RouteSnapshot:
    role = validate_snapshot_role(snapshot_role)
    safe_provenance = sanitize_provenance(provenance)

    if route_result is not None:
        fields = _fields_from_estimate(route_result)
    else:
        apply_map_foundation_defaults(ride)
        fields = _fields_from_ride(ride)
        if safe_provenance.get("estimate_skipped"):
            fields["used_fallback"] = True

    request_payload = _build_request_payload(ride, origin=origin, destination=destination)
    response_payload = _build_response_payload(
        route_provider=fields["route_provider"],
        used_fallback=fields["used_fallback"],
        distance_meters=fields["distance_meters"],
        duration_seconds=fields["duration_seconds"],
        route_confidence=fields.get("route_confidence"),
        traffic_provider=fields.get("traffic_provider"),
    )

    geometry_hash = None
    if geometry_polyline:
        geometry_hash = stable_hash({"geometry_polyline": geometry_polyline})

    provenance_blob = {
        **safe_provenance,
        "route_confidence": fields.get("route_confidence"),
        "traffic_provider": fields.get("traffic_provider"),
        "route_calculated_at": fields.get("route_calculated_at"),
    }

    row = RouteSnapshot(
        ride_id=ride.id,
        snapshot_role=role,
        route_provider=fields["route_provider"],
        used_fallback=fields["used_fallback"],
        distance_meters=fields["distance_meters"],
        duration_seconds=fields["duration_seconds"],
        geometry_polyline=geometry_polyline,
        geometry_hash=geometry_hash,
        request_hash=stable_hash(request_payload),
        response_hash=stable_hash(response_payload),
        provenance_json=_canonical_json(provenance_blob) if provenance_blob else None,
        pricing_id=pricing.ride_id if pricing is not None else None,
        created_at=utc_now_naive(),
    )
    db.add(row)
    db.flush()
    return row


def list_route_snapshots_for_ride(db: Session, *, ride_id: int) -> list[RouteSnapshot]:
    return (
        db.query(RouteSnapshot)
        .filter(RouteSnapshot.ride_id == ride_id)
        .order_by(RouteSnapshot.created_at.asc(), RouteSnapshot.id.asc())
        .all()
    )


def route_snapshot_public_view(row: RouteSnapshot) -> dict[str, Any]:
    created = row.created_at
    if created and created.tzinfo is None:
        created_at = created.isoformat() + "Z"
    else:
        created_at = created.isoformat() if created else None
    return {
        "id": row.id,
        "snapshot_role": row.snapshot_role,
        "route_provider": row.route_provider,
        "used_fallback": bool(row.used_fallback),
        "distance_meters": row.distance_meters,
        "duration_seconds": row.duration_seconds,
        "geometry_hash": row.geometry_hash,
        "request_hash": row.request_hash,
        "response_hash": row.response_hash,
        "pricing_id": row.pricing_id,
        "created_at": created_at,
    }
