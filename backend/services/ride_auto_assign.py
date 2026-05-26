"""Phase 2: deterministic auto-assignment on rider ride create (HALFAPP_AUTO_ASSIGN)."""

from __future__ import annotations

import os
from typing import Literal

from sqlalchemy.orm import Session

from models.ride import Ride
from services.dispatch import OpenBoardDispatchPolicy, RideAlreadyClaimed, RideNotAvailable, RideNotFound
from services.driver_in_app_notifications import notify_driver_in_app
from services.lifecycle import NotificationType, RideStatus, to_storage_ride_status
from services.ledger import record_ledger_entry
from services.map_route_foundation import stamp_route_calculated
from services.metrics import record_accept_metrics, record_claim_attempt, record_event
from services.ride_dispatch_cascade import (
    clear_dispatch_offer,
    eligible_dispatch_driver_ids,
    record_dispatch_accepted,
)
from services.ride_lifecycle_events import record_ride_lifecycle_event

AUTO_ASSIGNED_REASON = "auto_assigned"
AssignMode = Literal["nearest", "first_available"]


def auto_assign_enabled() -> bool:
    return os.getenv("HALFAPP_AUTO_ASSIGN", "").strip().lower() in {"1", "true", "yes"}


def auto_assign_mode() -> AssignMode:
    raw = os.getenv("HALFAPP_AUTO_ASSIGN_MODE", "nearest").strip().lower()
    if raw in {"first_available", "first", "fifo"}:
        return "first_available"
    return "nearest"


def _pick_driver_id(driver_ids: list[int], mode: AssignMode) -> int | None:
    if not driver_ids:
        return None
    if mode == "first_available":
        return min(driver_ids)
    return driver_ids[0]


def _assign_ride_to_driver(
    db: Session,
    ride: Ride,
    driver_id: int,
    *,
    reason: str,
    actor: str,
    actor_id: int | None,
) -> Ride:
    """Atomic claim + lifecycle bookkeeping (auto-assign and ops assign)."""
    policy = OpenBoardDispatchPolicy()
    ride = policy.claim_ride(db, ride.id, driver_id)
    if not ride.lifecycle_reason:
        ride.lifecycle_reason = reason
    record_claim_attempt(db, ride_id=ride.id, driver_id=driver_id, outcome="won")
    record_ledger_entry(
        db,
        event_type="claim_attempted",
        ride_id=ride.id,
        actor_id=actor_id or driver_id,
        driver_id=driver_id,
        outcome="won",
        reason=reason,
    )
    record_ledger_entry(
        db,
        event_type="claim_won",
        ride_id=ride.id,
        actor_id=actor_id or driver_id,
        driver_id=driver_id,
        outcome="won",
        reason=reason,
    )
    record_accept_metrics(db, ride=ride, driver_id=driver_id)
    record_event(
        db,
        entity_type="ride",
        entity_id=ride.id,
        event_type="ride.assigned",
        actor_id=actor_id,
        payload={"driver_id": driver_id, "reason": reason, "actor": actor},
    )
    record_ride_lifecycle_event(
        db,
        ride_id=ride.id,
        event_type="ride.accepted",
        from_state=RideStatus.REQUESTED,
        to_state=RideStatus.ACCEPTED,
        reason=reason,
        actor=actor,
        actor_id=actor_id or driver_id,
    )
    clear_dispatch_offer(db, ride)
    record_dispatch_accepted(db, ride, driver_id)
    stamp_route_calculated(ride)
    notify_driver_in_app(
        db,
        driver_id=driver_id,
        title="Ride assigned to you",
        message=f"Ride #{ride.id} was assigned. Head to pickup when ready.",
        notif_type=NotificationType.RIDE_ACCEPTED,
    )
    db.flush()
    return ride


def assign_ride_to_driver(
    db: Session,
    ride_id: int,
    driver_id: int,
    *,
    reason: str = "ops_assigned",
    actor: str = "admin",
    actor_id: int | None = None,
) -> Ride:
    """Ops/manual assign — only unassigned requested rides."""
    ride = db.query(Ride).filter(Ride.id == ride_id).first()
    if not ride:
        raise ValueError("ride_not_found")
    if ride.driver_id is not None:
        raise ValueError("ride_already_assigned")
    if ride.status != to_storage_ride_status(RideStatus.REQUESTED):
        raise ValueError("ride_not_assignable")
    return _assign_ride_to_driver(
        db,
        ride,
        driver_id,
        reason=reason,
        actor=actor,
        actor_id=actor_id,
    )


def try_auto_assign_ride(db: Session, ride_id: int) -> Ride | None:
    """Assign the nearest (or first-available) eligible driver; returns ride or None."""
    if not auto_assign_enabled():
        return None

    ride = db.query(Ride).filter(Ride.id == ride_id).first()
    if not ride:
        return None
    if ride.status != to_storage_ride_status(RideStatus.REQUESTED) or ride.driver_id is not None:
        return None

    driver_ids = eligible_dispatch_driver_ids(db, ride_id)
    driver_id = _pick_driver_id(driver_ids, auto_assign_mode())
    if driver_id is None:
        return None

    try:
        return _assign_ride_to_driver(
            db,
            ride,
            driver_id,
            reason=AUTO_ASSIGNED_REASON,
            actor="system",
            actor_id=driver_id,
        )
    except (RideNotFound, RideAlreadyClaimed, RideNotAvailable):
        return None
