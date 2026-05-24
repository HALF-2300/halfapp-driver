from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy.orm import Session

from models.ledger import MarketplaceLedgerEntry, MarketplaceLedgerEvent
from models.metrics import RideVisibility
from services.datetime_utils import utc_now_naive
from services.metrics import DISPATCH_POLICY_VERSION


class MarketplaceLedgerEventType(str, Enum):
    RIDE_CREATED = "ride.created"
    RIDE_ACCEPTED = "ride.accepted"
    RIDE_ARRIVED_PICKUP = "ride.arrived_pickup"
    RIDE_STARTED = "ride.started"
    RIDE_COMPLETED = "ride.completed"
    RIDE_CANCELLED = "ride.cancelled"
    RIDE_HIDDEN = "ride.hidden"
    PRESENCE_CHANGED = "presence.changed"
    PRESENCE_HEARTBEAT = "presence.heartbeat"
    DISPATCH_RIDE_VISIBLE = "dispatch.ride_visible"
    DISPATCH_CLAIM_ATTEMPTED = "dispatch.claim_attempted"
    DISPATCH_CLAIM_WON = "dispatch.claim_won"
    DISPATCH_CLAIM_LOST = "dispatch.claim_lost"
    DISPATCH_CLAIM_RELEASED = "dispatch.claim_released"
    EARNING_CALCULATED = "earning.calculated"


_LEGACY_CLAIM_EVENT_TYPES = {
    "claim_attempted": MarketplaceLedgerEventType.DISPATCH_CLAIM_ATTEMPTED.value,
    "claim_won": MarketplaceLedgerEventType.DISPATCH_CLAIM_WON.value,
    "claim_lost": MarketplaceLedgerEventType.DISPATCH_CLAIM_LOST.value,
    "claim_released": MarketplaceLedgerEventType.DISPATCH_CLAIM_RELEASED.value,
}


def _canonical_payload(value: dict[str, Any] | None) -> str:
    return json.dumps(value or {}, sort_keys=True, separators=(",", ":"))


def _entry_hash(
    *,
    occurred_at: datetime,
    event_type: str,
    ride_id: int | None,
    actor_id: int | None,
    driver_id: int | None,
    outcome: str | None,
    reason: str | None,
    payload_json: str,
    prior_hash: str | None,
    policy_version: str | None,
) -> str:
    material = {
        "actor_id": actor_id,
        "driver_id": driver_id,
        "event_type": event_type,
        "occurred_at": occurred_at.isoformat(),
        "outcome": outcome,
        "payload_json": payload_json,
        "policy_version": policy_version,
        "prior_hash": prior_hash,
        "reason": reason,
        "ride_id": ride_id,
    }
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _marketplace_event_hash(
    *,
    occurred_at: datetime,
    event_type: str,
    entity_type: str,
    entity_id: int | None,
    ride_id: int | None,
    actor_id: int | None,
    driver_id: int | None,
    source: str,
    idempotency_key: str | None,
    correlation_id: str | None,
    payload_json: str,
    previous_event_hash: str | None,
    policy_version: str | None,
) -> str:
    material = {
        "actor_id": actor_id,
        "correlation_id": correlation_id,
        "driver_id": driver_id,
        "entity_id": entity_id,
        "entity_type": entity_type,
        "event_type": event_type,
        "idempotency_key": idempotency_key,
        "occurred_at": occurred_at.isoformat(),
        "payload_json": payload_json,
        "policy_version": policy_version,
        "previous_event_hash": previous_event_hash,
        "ride_id": ride_id,
        "source": source,
    }
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _visibility_correlation_id(db: Session, *, ride_id: int | None, driver_id: int | None) -> str | None:
    if ride_id is None or driver_id is None:
        return None
    return (
        db.query(RideVisibility.correlation_id)
        .filter(RideVisibility.ride_id == ride_id, RideVisibility.driver_id == driver_id)
        .order_by(RideVisibility.id.desc())
        .limit(1)
        .scalar()
    )


def append_marketplace_event(
    db: Session,
    *,
    event_type: MarketplaceLedgerEventType | str,
    entity_type: str,
    entity_id: int | None,
    ride_id: int | None = None,
    actor_id: int | None = None,
    driver_id: int | None = None,
    source: str = "halfapp.backend",
    idempotency_key: str | None = None,
    correlation_id: str | None = None,
    payload: dict[str, Any] | None = None,
    policy_version: str | None = DISPATCH_POLICY_VERSION,
) -> MarketplaceLedgerEvent:
    event_type_value = event_type.value if isinstance(event_type, MarketplaceLedgerEventType) else event_type
    if idempotency_key:
        existing = (
            db.query(MarketplaceLedgerEvent)
            .filter(MarketplaceLedgerEvent.idempotency_key == idempotency_key)
            .first()
        )
        if existing:
            return existing

    previous_event_hash = (
        db.query(MarketplaceLedgerEvent.event_hash)
        .order_by(MarketplaceLedgerEvent.id.desc())
        .limit(1)
        .scalar()
    )
    occurred_at = utc_now_naive()
    payload_json = _canonical_payload(payload)
    event = MarketplaceLedgerEvent(
        occurred_at=occurred_at,
        event_type=event_type_value,
        entity_type=entity_type,
        entity_id=entity_id,
        ride_id=ride_id,
        actor_id=actor_id,
        driver_id=driver_id,
        source=source,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
        payload_json=payload_json,
        previous_event_hash=previous_event_hash,
        event_hash=_marketplace_event_hash(
            occurred_at=occurred_at,
            event_type=event_type_value,
            entity_type=entity_type,
            entity_id=entity_id,
            ride_id=ride_id,
            actor_id=actor_id,
            driver_id=driver_id,
            source=source,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            payload_json=payload_json,
            previous_event_hash=previous_event_hash,
            policy_version=policy_version,
        ),
        policy_version=policy_version,
    )
    db.add(event)
    db.flush()
    return event


def record_ledger_entry(
    db: Session,
    *,
    event_type: str,
    ride_id: int | None,
    actor_id: int | None,
    driver_id: int | None = None,
    outcome: str | None = None,
    reason: str | None = None,
    payload: dict[str, Any] | None = None,
    policy_version: str | None = DISPATCH_POLICY_VERSION,
    correlation_id: str | None = None,
    idempotency_key: str | None = None,
) -> MarketplaceLedgerEntry:
    prior_hash = (
        db.query(MarketplaceLedgerEntry.entry_hash)
        .order_by(MarketplaceLedgerEntry.id.desc())
        .limit(1)
        .scalar()
    )
    occurred_at = utc_now_naive()
    payload_json = _canonical_payload(payload)
    entry = MarketplaceLedgerEntry(
        occurred_at=occurred_at,
        event_type=event_type,
        ride_id=ride_id,
        actor_id=actor_id,
        driver_id=driver_id,
        outcome=outcome,
        reason=reason,
        payload_json=payload_json,
        prior_hash=prior_hash,
        entry_hash=_entry_hash(
            occurred_at=occurred_at,
            event_type=event_type,
            ride_id=ride_id,
            actor_id=actor_id,
            driver_id=driver_id,
            outcome=outcome,
            reason=reason,
            payload_json=payload_json,
            prior_hash=prior_hash,
            policy_version=policy_version,
        ),
        policy_version=policy_version,
    )
    db.add(entry)
    marketplace_event_type = _LEGACY_CLAIM_EVENT_TYPES.get(event_type)
    if marketplace_event_type is not None:
        event_payload = {
            "legacy_marketplace_ledger": {
                "event_type": event_type,
                "outcome": outcome,
                "reason": reason,
            },
            "details": payload or {},
        }
        effective_correlation_id = correlation_id or _visibility_correlation_id(
            db, ride_id=ride_id, driver_id=driver_id
        )
        append_marketplace_event(
            db,
            event_type=marketplace_event_type,
            entity_type="dispatch_claim",
            entity_id=ride_id or (payload or {}).get("requested_ride_id"),
            ride_id=ride_id,
            actor_id=actor_id,
            driver_id=driver_id,
            idempotency_key=idempotency_key,
            correlation_id=effective_correlation_id,
            payload=event_payload,
            policy_version=policy_version,
        )
    return entry
