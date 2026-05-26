"""Rider ride SSE payloads — status, driver location, ETA, fare (v0.1 honest estimates)."""

from __future__ import annotations

import json
from typing import Any, Optional

from sqlalchemy.orm import Session

from models.ride import Ride
from models.user import User
from services.lifecycle import RideStatus, normalize_ride_status
from services.ride_pricing import get_ride_pricing
from services.routing_service import _haversine_km

_AVG_SPEED_KMH = 30.0


def format_sse_event(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


def format_sse_data(payload: dict[str, Any]) -> str:
    """Unnamed message for legacy EventSource.onmessage handlers."""
    return f"data: {json.dumps(payload)}\n\n"


def _coords_pair(lat: Optional[float], lng: Optional[float]) -> Optional[tuple[float, float]]:
    if lat is None or lng is None:
        return None
    return (float(lat), float(lng))


def driver_location_payload(ride: Ride, db: Session) -> Optional[dict[str, Any]]:
    if ride.driver_id is None:
        return None
    driver = db.query(User).filter(User.id == ride.driver_id).first()
    if driver is None or driver.last_latitude is None or driver.last_longitude is None:
        return None
    return {
        "lat": float(driver.last_latitude),
        "lng": float(driver.last_longitude),
        "heading": None,
    }


def fare_update_payload(ride: Ride, db: Session) -> Optional[dict[str, Any]]:
    pricing = get_ride_pricing(db, ride.id)
    if pricing is None:
        return None
    cents = pricing.customer_total_cents or pricing.total_rider_charge_cents
    if cents is None:
        return None
    return {"fare_cents": int(cents)}


def _eta_seconds_haversine(origin: tuple[float, float], dest: tuple[float, float]) -> int:
    km = _haversine_km(origin[0], origin[1], dest[0], dest[1])
    if km <= 0:
        return 60
    minutes = max(1, int(round((km / _AVG_SPEED_KMH) * 60)))
    return minutes * 60


def eta_update_payload(ride: Ride, db: Session) -> Optional[dict[str, Any]]:
    status = normalize_ride_status(ride.status)
    pickup = _coords_pair(ride.pickup_latitude, ride.pickup_longitude)
    dropoff = _coords_pair(ride.dropoff_latitude, ride.dropoff_longitude)

    if status == RideStatus.REQUESTED:
        return {"eta_seconds": 300}

    if ride.driver_id is None:
        return None

    driver = db.query(User).filter(User.id == ride.driver_id).first()
    driver_coords = None
    if driver and driver.last_latitude is not None and driver.last_longitude is not None:
        driver_coords = (float(driver.last_latitude), float(driver.last_longitude))

    if status in {RideStatus.ACCEPTED, RideStatus.DRIVER_ARRIVED}:
        if driver_coords and pickup:
            return {"eta_seconds": _eta_seconds_haversine(driver_coords, pickup)}
        if ride.duration_minutes:
            return {"eta_seconds": max(60, int(ride.duration_minutes) * 60)}
        return {"eta_seconds": 420}

    if status == RideStatus.IN_PROGRESS:
        if driver_coords and dropoff:
            return {"eta_seconds": _eta_seconds_haversine(driver_coords, dropoff)}
        if pickup and dropoff:
            return {"eta_seconds": _eta_seconds_haversine(pickup, dropoff)}
        if ride.duration_minutes:
            return {"eta_seconds": max(60, int(ride.duration_minutes) * 60)}
        return {"eta_seconds": 600}

    return None


def collect_rider_stream_events(
    ride: Ride,
    db: Session,
    *,
    ride_id: int,
    last_status: Optional[str],
) -> list[tuple[str, dict[str, Any]]]:
    """Ordered SSE events for one poll tick."""
    events: list[tuple[str, dict[str, Any]]] = []
    normalized = normalize_ride_status(ride.status).value

    if normalized != last_status:
        payload = {"ride_id": ride_id, "status": normalized, "type": "status_change"}
        events.append(("status_change", payload))

    loc = driver_location_payload(ride, db)
    if loc:
        events.append(("driver_location", loc))

    fare = fare_update_payload(ride, db)
    if fare:
        events.append(("fare_update", fare))

    eta = eta_update_payload(ride, db)
    if eta:
        events.append(("eta_update", eta))

    return events
