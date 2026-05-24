"""Structured lifecycle payloads for marketplace ledger + domain events."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from services.datetime_utils import utc_now_naive
from services.lifecycle import RideStatus, normalize_ride_status
from services.metrics import record_event


def mask_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) < 4:
        return "***"
    return f"***-***-{digits[-4:]}"


def lifecycle_transition_payload(
    *,
    from_state: str,
    to_state: str,
    reason: str,
    actor: str,
    actor_id: int | None = None,
    client_timestamp: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "actor": actor,
        "actor_id": actor_id,
        "from_state": from_state,
        "to_state": to_state,
        "reason": reason,
        "client_timestamp": client_timestamp,
        "server_timestamp": utc_now_naive().isoformat() + "Z",
    }
    if extra:
        payload.update(extra)
    return payload


def record_ride_lifecycle_event(
    db: Session,
    *,
    ride_id: int,
    event_type: str,
    from_state: str | RideStatus,
    to_state: str | RideStatus,
    reason: str,
    actor: str,
    actor_id: int | None = None,
    client_timestamp: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Append domain + marketplace ledger event with structured transition truth."""
    from_value = (
        from_state.value if isinstance(from_state, RideStatus) else normalize_ride_status(from_state).value
    )
    to_value = to_state.value if isinstance(to_state, RideStatus) else normalize_ride_status(to_state).value
    record_event(
        db,
        entity_type="ride",
        entity_id=ride_id,
        event_type=event_type,
        actor_id=actor_id,
        payload=lifecycle_transition_payload(
            from_state=from_value,
            to_state=to_value,
            reason=reason,
            actor=actor,
            actor_id=actor_id,
            client_timestamp=client_timestamp,
            extra=extra,
        ),
    )


def serialize_lifecycle_history_event(
    *,
    occurred_at: str | None,
    event_type: str,
    source: str,
    actor_id: int | None = None,
    payload_json: str | None = None,
) -> dict[str, Any]:
    import json

    payload: dict[str, Any] = {}
    if payload_json:
        try:
            payload = json.loads(payload_json)
        except json.JSONDecodeError:
            payload = {}
    return {
        "occurred_at": occurred_at,
        "event_type": event_type,
        "source": source,
        "actor": payload.get("actor") or (f"user:{actor_id}" if actor_id else "system"),
        "from_state": payload.get("from_state"),
        "to_state": payload.get("to_state"),
        "reason": payload.get("reason"),
        "client_timestamp": payload.get("client_timestamp"),
        "server_timestamp": payload.get("server_timestamp") or occurred_at,
    }
