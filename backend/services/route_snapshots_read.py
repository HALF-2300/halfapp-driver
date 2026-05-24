"""Read-only driver route snapshot / route truth projection (HALFAPP_ROUTE_SNAPSHOT_READ_UI_01)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from models.ride import Ride
from services.map_route_foundation import map_foundation_dict
from services.route_snapshots import list_route_snapshots_for_ride, route_snapshot_public_view
from services.osrm_runtime_truth import (
    osrm_runtime_claim,
    production_routing_claim,
)
from services.routing_service import HAVERSINE_FALLBACK_PROVIDER

OSRM_RUNTIME_CLAIM = "not_proved"
PRODUCTION_ROUTING_CLAIM = "not_proved"

ROUTE_SNAPSHOT_READ_COPY = {
    "osrm_status": "OSRM runtime not proved",
    "estimate_note": "Straight-line estimate — not a live road-network route.",
}


def build_route_snapshots_driver_read(db: Session, *, ride_id: int) -> dict[str, Any] | None:
    ride = db.query(Ride).filter(Ride.id == ride_id).first()
    if ride is None:
        return None

    rows = list_route_snapshots_for_ride(db, ride_id=ride_id)
    map_meta = map_foundation_dict(ride)
    current_provider = ride.route_provider or map_meta.get("route_provider")
    used_fallback = current_provider == HAVERSINE_FALLBACK_PROVIDER or any(
        bool(row.used_fallback) for row in rows
    )
    routing_label = (
        "Straight-line estimate" if used_fallback else str(current_provider or "unknown")
    )

    return {
        "ride_id": ride_id,
        "route_truth": {
            "current_provider": current_provider,
            "used_fallback": used_fallback,
            "osrm_runtime_claim": osrm_runtime_claim(),
            "production_routing_claim": production_routing_claim(),
            "traffic_provider": map_meta.get("traffic_provider"),
            "route_confidence": map_meta.get("route_confidence"),
            "route_calculated_at": map_meta.get("route_calculated_at"),
        },
        "snapshots": [route_snapshot_public_view(row) for row in rows],
        "copy": {
            "routing_label": routing_label,
            "osrm_status": ROUTE_SNAPSHOT_READ_COPY["osrm_status"],
            "estimate_note": ROUTE_SNAPSHOT_READ_COPY["estimate_note"] if used_fallback else None,
        },
        "truth_labels": [
            "BACKEND_OWNED",
            "READ_ONLY_ROUTE_SNAPSHOTS",
            "NO_PRODUCTION_OSRM_CLAIM",
        ],
    }
