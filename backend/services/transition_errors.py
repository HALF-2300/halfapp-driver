"""Structured HTTP details for invalid ride lifecycle transitions (RIDE-001)."""
from __future__ import annotations

from typing import Any


def invalid_state_transition_detail(
    *,
    ride_id: int,
    from_status: str,
    to_status: str,
    message: str | None = None,
) -> dict[str, Any]:
    return {
        "error": "invalid_state_transition",
        "code": "invalid_state_transition",
        "ride_id": ride_id,
        "from_status": from_status,
        "to_status": to_status,
        "state_changed": False,
        "message": message or f"Cannot transition ride from {from_status} to {to_status}",
    }


def target_status_for_action(action: str) -> str:
    mapping = {
        "accept": "accepted",
        "arrive": "driver_arrived",
        "start": "in_progress",
        "complete": "completed",
        "cancel": "cancelled",
    }
    return mapping.get(action, "unknown")
