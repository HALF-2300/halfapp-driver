"""In-process ride pool SSE broadcast (v0.1). Replace event_bus backend with Redis pub/sub for multi-worker."""

from __future__ import annotations

import json
from typing import Any

from services.event_bus import event_bus

RIDE_POOL_TOPIC = "ride_pool"

# Event names consumed by driver cockpit SSE clients.
POOL_EVENT_CREATED = "ride.created"
POOL_EVENT_CLAIMED = "ride.claimed"
POOL_EVENT_CANCELLED = "ride.cancelled"


def pool_delta_payload(
    *,
    event: str,
    ride_id: int,
    ride: dict[str, Any] | None = None,
    removed: bool = False,
) -> dict[str, Any]:
    return {
        "type": "pool_delta",
        "event": event,
        "ride_id": ride_id,
        "removed": removed,
        "ride": ride,
    }


def emit_pool_delta(
    *,
    event: str,
    ride_id: int,
    ride: dict[str, Any] | None = None,
    removed: bool = False,
) -> None:
    event_bus.publish_sync(
        RIDE_POOL_TOPIC,
        pool_delta_payload(event=event, ride_id=ride_id, ride=ride, removed=removed),
    )


def format_sse(data: dict[str, Any]) -> str:
    return f"data: {json.dumps(data, default=str)}\n\n"


def format_sse_event(event_type: str, data: Any) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data, default=str)}\n\n"
