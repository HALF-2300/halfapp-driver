"""Read-only driver ride audit — pricing, settlement obligations, ledger events, route truth."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.ledger import MarketplaceLedgerEvent
from models.metrics import Event
from models.ride import Ride
from models.ride_pricing import RidePricing
from services.ride_settlement import list_settlement_entries, settlement_public_view
from services.osrm_runtime_truth import osrm_runtime_claim
from services.route_snapshots import list_route_snapshots_for_ride

# Lifecycle + earning events safe for driver audit (from services.ledger.MarketplaceLedgerEventType).
_DRIVER_AUDIT_LEDGER_EVENT_TYPES = frozenset(
    {
        "ride.created",
        "ride.accepted",
        "ride.arrived_pickup",
        "ride.started",
        "ride.completed",
        "earning.calculated",
    }
)

AUDIT_COPY = {
    "payment_execution": "not_implemented",
    "driver_payment_label": "Recorded obligation does not mean payout.",
    "settlement_meaning": "Obligation rows record backend-computed amounts — not bank or PSP movement.",
}

TRUTH_LABELS = (
    "backend_owned",
    "ride_pricing_ledger",
    "settlement_obligation_only",
    "no_payment_execution",
    "marketplace_ledger_events",
)


def _iso(value) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        text = value.isoformat()
        if value.tzinfo is None and not text.endswith("Z"):
            return text + "Z"
        return text
    return str(value)


def _pricing_block(pricing: RidePricing | None) -> dict[str, Any] | None:
    if pricing is None:
        return None
    pass_through = (
        int(pricing.city_fee_cents or 0)
        + int(pricing.airport_fee_cents or 0)
        + int(pricing.toll_cents or 0)
        + int(pricing.accessibility_fee_cents or 0)
        + int(pricing.tax_cents or 0)
    )
    driver_payout = int(
        pricing.driver_earnings_cents
        or pricing.driver_ride_payout_cents
        or pricing.driver_commission_cents
        or 0
    )
    return {
        "customer_total_cents": int(pricing.customer_total_cents or pricing.total_rider_charge_cents or 0),
        "driver_payout_cents": driver_payout,
        "driver_ride_payout_cents": int(pricing.driver_ride_payout_cents or pricing.driver_commission_cents or 0),
        "platform_commission_cents": int(pricing.platform_commission_cents or 0),
        "platform_service_fee_cents": int(pricing.platform_service_fee_cents or 0),
        "tip_cents": int(pricing.tip_cents or 0),
        "pass_through_fees_cents": pass_through,
        "driver_shareable_fare_cents": int(pricing.driver_shareable_fare_cents or 0),
        "financial_locked": bool(pricing.financial_locked),
        "locked_at": _iso(pricing.locked_at or pricing.fare_locked_at),
    }


def _lifecycle_block(ride: Ride) -> dict[str, Any]:
    return {
        "created_at": _iso(ride.created_at),
        "accepted_at": _iso(ride.accepted_at),
        "arrived_pickup_at": _iso(ride.arrived_pickup_at),
        "started_at": _iso(ride.started_at),
        "completed_at": _iso(ride.completed_at),
        "cancelled_at": _iso(ride.cancelled_at),
    }


def _route_truth_block(ride: Ride, snapshots: list) -> dict[str, Any]:
    used_fallback = ride.route_provider == "haversine_fallback"
    block: dict[str, Any] = {
        "route_provider": ride.route_provider,
        "traffic_provider": ride.traffic_provider,
        "traffic_aware": bool(ride.traffic_aware) if ride.traffic_aware is not None else False,
        "used_fallback": used_fallback,
        "route_confidence": ride.route_confidence,
        "route_calculated_at": _iso(ride.route_calculated_at),
        "osrm_runtime_claim": osrm_runtime_claim(),
    }
    if snapshots:
        block["snapshots"] = [
            {
                "snapshot_role": row.snapshot_role,
                "route_provider": row.route_provider,
                "used_fallback": bool(row.used_fallback),
                "created_at": _iso(row.created_at),
            }
            for row in snapshots
        ]
    return block


def _lifecycle_events_block(db: Session, *, ride: Ride) -> list[dict[str, Any]]:
    """Merged lifecycle timeline: ride milestones, domain events, marketplace ledger."""
    rows: list[dict[str, Any]] = []
    milestones = [
        ("ride.lifecycle.requested", ride.created_at),
        ("ride.lifecycle.accepted", ride.accepted_at),
        ("ride.lifecycle.arrived_pickup", ride.arrived_pickup_at),
        ("ride.lifecycle.started", ride.started_at),
        ("ride.lifecycle.completed", ride.completed_at),
        ("ride.lifecycle.cancelled", ride.cancelled_at),
    ]
    for event_type, ts in milestones:
        if ts is None:
            continue
        rows.append(
            {
                "occurred_at": _iso(ts),
                "event_type": event_type,
                "source": "rides.timestamps",
            }
        )
    domain = (
        db.query(Event)
        .filter(Event.entity_type == "ride", Event.entity_id == ride.id)
        .order_by(Event.occurred_at.asc(), Event.event_id.asc())
        .all()
    )
    for event in domain:
        rows.append(
            {
                "occurred_at": _iso(event.occurred_at),
                "event_type": event.event_type,
                "source": "events",
                "actor_id": event.actor_id,
            }
        )
    ledger = (
        db.query(MarketplaceLedgerEvent)
        .filter(MarketplaceLedgerEvent.ride_id == ride.id)
        .order_by(MarketplaceLedgerEvent.occurred_at.asc(), MarketplaceLedgerEvent.id.asc())
        .all()
    )
    for event in ledger:
        rows.append(
            {
                "occurred_at": _iso(event.occurred_at),
                "event_type": event.event_type,
                "source": "marketplace_ledger_events",
                "actor_id": event.actor_id,
                "driver_id": event.driver_id,
            }
        )
    rows.sort(key=lambda item: (item.get("occurred_at") or "", item.get("event_type") or ""))
    return rows


def _ledger_events_block(db: Session, *, ride_id: int) -> list[dict[str, Any]]:
    rows = (
        db.query(MarketplaceLedgerEvent)
        .filter(
            MarketplaceLedgerEvent.ride_id == ride_id,
            MarketplaceLedgerEvent.event_type.in_(_DRIVER_AUDIT_LEDGER_EVENT_TYPES),
        )
        .order_by(MarketplaceLedgerEvent.id.asc())
        .all()
    )
    return [
        {
            "event_type": row.event_type,
            "occurred_at": _iso(row.occurred_at),
            "correlation_id": row.correlation_id,
            "idempotency_key": row.idempotency_key,
            "event_hash": row.event_hash,
        }
        for row in rows
    ]


def build_driver_ride_audit(db: Session, *, ride_id: int, driver_user_id: int) -> dict[str, Any]:
    ride = db.query(Ride).filter(Ride.id == ride_id).first()
    if ride is None:
        raise HTTPException(status_code=404, detail="Ride not found")
    if ride.driver_id != driver_user_id:
        raise HTTPException(status_code=403, detail="Ride audit is available only to the assigned driver")

    pricing = db.query(RidePricing).filter(RidePricing.ride_id == ride_id).first()
    settlement_rows = list_settlement_entries(db, ride_id=ride_id)
    snapshots = list_route_snapshots_for_ride(db, ride_id=ride_id)

    return {
        "ride_id": ride.id,
        "status": ride.status,
        "lifecycle_reason": ride.lifecycle_reason,
        "financial_locked": bool(pricing.financial_locked) if pricing else False,
        "truth_labels": list(TRUTH_LABELS),
        "lifecycle": _lifecycle_block(ride),
        "lifecycle_events": _lifecycle_events_block(db, ride=ride),
        "pricing": _pricing_block(pricing),
        "settlement_entries": [settlement_public_view(row) for row in settlement_rows],
        "ledger_events": _ledger_events_block(db, ride_id=ride_id),
        "route_truth": _route_truth_block(ride, snapshots),
        "copy": dict(AUDIT_COPY),
    }
