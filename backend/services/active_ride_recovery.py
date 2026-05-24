"""Build full cockpit session-recovery payload for GET /drivers/me/active-ride."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from models.ride import Ride
from services.lifecycle import RideStatus, next_actions_for, normalize_ride_status
from services.ride_audit import _lifecycle_events_block, _route_truth_block
from services.ride_lifecycle_events import mask_phone, serialize_lifecycle_history_event
from services.route_snapshots import list_route_snapshots_for_ride


def build_active_ride_recovery(db: Session, *, ride: Ride) -> dict[str, Any]:
    stage = normalize_ride_status(ride.status).value
    snapshots = list_route_snapshots_for_ride(db, ride_id=ride.id)
    history_raw = _lifecycle_events_block(db, ride=ride)[-10:]
    history = [
        serialize_lifecycle_history_event(
            occurred_at=item.get("occurred_at"),
            event_type=item.get("event_type") or "",
            source=item.get("source") or "unknown",
            actor_id=item.get("actor_id"),
        )
        for item in history_raw
    ]
    return {
        "lifecycle_stage": stage,
        "lifecycle": {
            "current": stage,
            "available_actions": next_actions_for(ride.status),
            "history": history,
        },
        "route": _route_truth_block(ride, snapshots),
        "customer": {
            "name": ride.customer_name,
            "phone_masked": mask_phone(getattr(ride, "customer_phone", None)),
        },
    }
