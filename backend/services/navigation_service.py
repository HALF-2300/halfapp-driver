"""Driver navigation bundle — external maps link + snapshot metadata (no in-app engine)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.ride import Ride
from models.route_snapshot import RouteSnapshot
from services.lifecycle import RideStatus, normalize_ride_status


def _google_maps_dir_url(lat: float, lng: float) -> str:
    return (
        "https://www.google.com/maps/dir/?api=1&"
        f"destination={lat},{lng}"
    )


def _latest_snapshot(db: Session, ride_id: int) -> RouteSnapshot | None:
    return (
        db.query(RouteSnapshot)
        .filter(RouteSnapshot.ride_id == ride_id)
        .order_by(RouteSnapshot.created_at.desc())
        .first()
    )


def get_navigation_bundle(db: Session, *, ride_id: int, driver_id: int) -> dict:
    ride = db.query(Ride).filter(Ride.id == ride_id, Ride.driver_id == driver_id).first()
    if ride is None:
        return None

    status = normalize_ride_status(ride.status)
    en_route = status in {RideStatus.IN_PROGRESS}
    if en_route:
        lat, lng = ride.dropoff_latitude, ride.dropoff_longitude
        label = ride.destination or "Dropoff"
        leg = "dropoff"
    else:
        lat, lng = ride.pickup_latitude, ride.pickup_longitude
        label = ride.pickup_location or "Pickup"
        leg = "pickup"

    external_url = None
    if lat is not None and lng is not None:
        external_url = _google_maps_dir_url(float(lat), float(lng))

    snap = _latest_snapshot(db, ride_id)
    steps: list[dict] = []
    note = (
        "Open in your maps app for turn-by-turn directions. "
        "In-app step lists require OSRM step snapshots (not proved in all environments)."
    )

    return {
        "ride_id": ride_id,
        "leg": leg,
        "destination_label": label,
        "external_url": external_url,
        "distance_meters": snap.distance_meters if snap else None,
        "duration_seconds": snap.duration_seconds if snap else None,
        "route_provider": snap.route_provider if snap else None,
        "used_fallback": bool(snap.used_fallback) if snap else None,
        "steps": steps,
        "note": note,
    }
