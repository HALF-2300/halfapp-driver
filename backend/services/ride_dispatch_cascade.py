"""RIDE-003: sequential dispatch offers with timeout cascade (v0.1 in-process)."""
from __future__ import annotations

import os
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from models.ride import Ride
from models.ride_dispatch_log import (
    DISPATCH_RESULT_ACCEPTED,
    DISPATCH_RESULT_DECLINED,
    DISPATCH_RESULT_PENDING,
    DISPATCH_RESULT_SENT,
    DISPATCH_RESULT_SKIPPED_INELIGIBLE,
    DISPATCH_RESULT_TIMEOUT,
    RideDispatchLog,
)
from models.user import User, UserRole
from services.claim_eligibility import driver_active_ride_id
from services.datetime_utils import utc_now_naive
from services.driver_approval import is_driver_dispatch_available
from services.lifecycle import RideStatus, to_storage_ride_status
from services.metrics import _haversine_km, record_event
from services.presence import derive_effective_presence, get_or_create_presence

DISPATCH_TIMEOUT_SECONDS = int(
    os.getenv(
        "DISPATCH_REQUEST_TIMEOUT_SECONDS",
        os.getenv("HALFAPP_DISPATCH_TIMEOUT_SECONDS", "30"),
    )
)
MAX_DISPATCH_ATTEMPTS = int(
    os.getenv("DISPATCH_MAX_ATTEMPTS", os.getenv("HALFAPP_MAX_DISPATCH_ATTEMPTS", "3"))
)


def _now(now: datetime | None) -> datetime:
    return now or utc_now_naive()


def _log_skipped_ineligible(db: Session, ride_id: int, driver_id: int, reason: str) -> None:
    db.add(
        RideDispatchLog(
            ride_id=ride_id,
            driver_id=driver_id,
            sent_at=_now(None),
            result=DISPATCH_RESULT_SKIPPED_INELIGIBLE,
            attempt_number=0,
            reason=reason,
        )
    )


def _candidate_sort_key(db: Session, ride: Ride, driver_id: int) -> tuple[float, int]:
    driver = db.query(User).filter(User.id == driver_id).first()
    distance = _haversine_km(
        ride.pickup_latitude,
        ride.pickup_longitude,
        driver.last_latitude if driver else None,
        driver.last_longitude if driver else None,
    )
    if distance is None:
        distance = float("inf")
    return (distance, driver_id)


def eligible_dispatch_driver_ids(db: Session, ride_id: int) -> list[int]:
    """Approved, online, fresh drivers without active ride, not yet attempted on this ride."""
    ride = db.query(Ride).filter(Ride.id == ride_id).first()
    if not ride:
        return []
    declined_or_sent = {
        row[0]
        for row in db.query(RideDispatchLog.driver_id)
        .filter(
            RideDispatchLog.ride_id == ride_id,
            RideDispatchLog.result.in_(
                (DISPATCH_RESULT_SENT, DISPATCH_RESULT_PENDING, DISPATCH_RESULT_DECLINED, DISPATCH_RESULT_TIMEOUT)
            ),
        )
        .all()
    }
    pool_ids = {
        row[0]
        for row in db.query(User.id).filter(User.role == UserRole.DRIVER, User.is_active.is_(True)).all()
    }
    candidates: list[int] = []
    for driver_id in sorted(pool_ids):
        if driver_id in declined_or_sent:
            continue
        driver = db.query(User).filter(User.id == driver_id, User.role == UserRole.DRIVER).first()
        if not driver:
            continue
        if not is_driver_dispatch_available(db, driver):
            _log_skipped_ineligible(db, ride_id, driver_id, "dispatch_unavailable")
            continue
        if driver_active_ride_id(db, driver_id) is not None:
            _log_skipped_ineligible(db, ride_id, driver_id, "driver_busy")
            continue
        presence = derive_effective_presence(get_or_create_presence(db, driver))
        if presence.effective_state != "available":
            _log_skipped_ineligible(db, ride_id, driver_id, f"presence_{presence.effective_state}")
            continue
        candidates.append(driver_id)
    return sorted(candidates, key=lambda did: _candidate_sort_key(db, ride, did))


def ride_visible_to_driver(ride: Ride, driver_id: int) -> bool:
    if ride.status != to_storage_ride_status(RideStatus.REQUESTED) or ride.driver_id is not None:
        return False
    if ride.dispatch_driver_id is None:
        return True
    return ride.dispatch_driver_id == driver_id


def _finalize_no_drivers(db: Session, ride: Ride) -> None:
    """Terminal dispatch exhaustion — storage uses cancelled + explicit reason (v0.1)."""
    ride.status = to_storage_ride_status(RideStatus.CANCELLED)
    ride.dispatch_driver_id = None
    ride.dispatch_expires_at = None
    ride.cancelled_at = _now(None)
    ride.lifecycle_reason = "no_drivers_available"
    record_event(
        db,
        entity_type="ride",
        entity_id=ride.id,
        event_type="ride.dispatch_exhausted",
        actor_id=None,
        payload={"attempts": ride.dispatch_attempt_count},
    )


def _offer_to_driver(db: Session, ride: Ride, driver_id: int, *, now: datetime) -> RideDispatchLog:
    attempt_number = (ride.dispatch_attempt_count or 0) + 1
    ride.dispatch_driver_id = driver_id
    ride.dispatch_expires_at = now + timedelta(seconds=DISPATCH_TIMEOUT_SECONDS)
    ride.dispatch_attempt_count = attempt_number
    row = RideDispatchLog(
        ride_id=ride.id,
        driver_id=driver_id,
        sent_at=now,
        result=DISPATCH_RESULT_SENT,
        attempt_number=attempt_number,
    )
    db.add(row)
    record_event(
        db,
        entity_type="ride",
        entity_id=ride.id,
        event_type="ride.dispatch_offered",
        actor_id=driver_id,
        payload={"attempt_number": attempt_number, "expires_at": ride.dispatch_expires_at.isoformat()},
    )
    db.flush()
    return row


def start_dispatch_for_ride(db: Session, ride_id: int, *, now: datetime | None = None) -> None:
    """Begin or refresh sequential dispatch for a requested unassigned ride."""
    if os.getenv("HALFAPP_OPEN_BOARD_DISPATCH", "").strip().lower() in {"1", "true", "yes"}:
        return
    current = _now(now)
    ride = db.query(Ride).filter(Ride.id == ride_id).first()
    if not ride or ride.status != to_storage_ride_status(RideStatus.REQUESTED) or ride.driver_id is not None:
        return
    if ride.dispatch_driver_id is not None:
        return
    drivers = eligible_dispatch_driver_ids(db, ride.id)
    if not drivers:
        db.flush()
        return
    _offer_to_driver(db, ride, drivers[0], now=current)


def _close_pending_log(
    db: Session,
    ride_id: int,
    driver_id: int,
    *,
    result: str,
    now: datetime,
) -> None:
    row = (
        db.query(RideDispatchLog)
        .filter(
            RideDispatchLog.ride_id == ride_id,
            RideDispatchLog.driver_id == driver_id,
            RideDispatchLog.result.in_((DISPATCH_RESULT_SENT, DISPATCH_RESULT_PENDING)),
        )
        .order_by(RideDispatchLog.id.desc())
        .first()
    )
    if row:
        row.result = result
        row.responded_at = now


def advance_after_failed_attempt(db: Session, ride: Ride, *, now: datetime) -> None:
    if ride.status != to_storage_ride_status(RideStatus.REQUESTED) or ride.driver_id is not None:
        return
    if (ride.dispatch_attempt_count or 0) >= MAX_DISPATCH_ATTEMPTS:
        _finalize_no_drivers(db, ride)
        db.flush()
        return
    ride.dispatch_driver_id = None
    ride.dispatch_expires_at = None
    drivers = eligible_dispatch_driver_ids(db, ride.id)
    if not drivers:
        if (ride.dispatch_attempt_count or 0) >= MAX_DISPATCH_ATTEMPTS:
            _finalize_no_drivers(db, ride)
        db.flush()
        return
    _offer_to_driver(db, ride, drivers[0], now=now)


def refresh_open_dispatch_offers(db: Session, *, now: datetime | None = None) -> None:
    """Process expirations and start offers for requested rides without an active target."""
    current = _now(now)
    process_dispatch_timeouts(db, now=current)
    pending = (
        db.query(Ride)
        .filter(
            Ride.status == to_storage_ride_status(RideStatus.REQUESTED),
            Ride.driver_id.is_(None),
            Ride.dispatch_driver_id.is_(None),
        )
        .all()
    )
    for ride in pending:
        start_dispatch_for_ride(db, ride.id, now=current)
    db.flush()


def process_dispatch_timeouts(db: Session, *, now: datetime | None = None) -> None:
    """Expire offers whose deadline passed; v0.1 runs synchronously (scheduler later)."""
    current = _now(now)
    rides = (
        db.query(Ride)
        .filter(
            Ride.status == to_storage_ride_status(RideStatus.REQUESTED),
            Ride.driver_id.is_(None),
            Ride.dispatch_driver_id.isnot(None),
            Ride.dispatch_expires_at.isnot(None),
            Ride.dispatch_expires_at < current,
        )
        .all()
    )
    for ride in rides:
        driver_id = ride.dispatch_driver_id
        if driver_id is None:
            continue
        _close_pending_log(db, ride.id, driver_id, result=DISPATCH_RESULT_TIMEOUT, now=current)
        advance_after_failed_attempt(db, ride, now=current)
    db.flush()


def clear_dispatch_offer(db: Session, ride: Ride) -> None:
    ride.dispatch_driver_id = None
    ride.dispatch_expires_at = None


def record_dispatch_accepted(db: Session, ride: Ride, driver_id: int, *, now: datetime | None = None) -> None:
    current = _now(now)
    _close_pending_log(db, ride.id, driver_id, result=DISPATCH_RESULT_ACCEPTED, now=current)
    clear_dispatch_offer(db, ride)


def record_dispatch_declined(db: Session, ride_id: int, driver_id: int, *, now: datetime | None = None) -> None:
    current = _now(now)
    ride = db.query(Ride).filter(Ride.id == ride_id).first()
    if not ride:
        return
    active_offer = ride.dispatch_driver_id == driver_id
    sent_offer = (
        db.query(RideDispatchLog)
        .filter(
            RideDispatchLog.ride_id == ride_id,
            RideDispatchLog.driver_id == driver_id,
            RideDispatchLog.result.in_((DISPATCH_RESULT_SENT, DISPATCH_RESULT_PENDING)),
        )
        .first()
    )
    if not active_offer and sent_offer is None:
        return
    _close_pending_log(db, ride_id, driver_id, result=DISPATCH_RESULT_DECLINED, now=current)
    advance_after_failed_attempt(db, ride, now=current)


def dispatch_next_candidate(db: Session, ride_id: int, *, now: datetime | None = None) -> None:
    """Offer the next eligible driver when the ride is still in the pool."""
    start_dispatch_for_ride(db, ride_id, now=now)


def expire_current_attempt_and_cascade(db: Session, ride_id: int, *, now: datetime | None = None) -> None:
    """Mark the active offer timed out and advance to the next candidate."""
    current = _now(now)
    ride = db.query(Ride).filter(Ride.id == ride_id).first()
    if not ride or ride.dispatch_driver_id is None:
        return
    driver_id = ride.dispatch_driver_id
    _close_pending_log(db, ride_id, driver_id, result=DISPATCH_RESULT_TIMEOUT, now=current)
    advance_after_failed_attempt(db, ride, now=current)
    db.flush()


def process_expired_dispatches(db: Session, *, now: datetime | None = None) -> None:
    """Deterministic timeout processor (alias for in-process v0.1 scheduler)."""
    process_dispatch_timeouts(db, now=now)


def sequential_dispatch_enabled() -> bool:
    return os.getenv("HALFAPP_OPEN_BOARD_DISPATCH", "").strip().lower() not in {"1", "true", "yes"}
