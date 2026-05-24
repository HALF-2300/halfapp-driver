from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from models.presence import DriverPresence
from models.user import User
from services.driver_approval import DriverApprovalDenied, assert_driver_approved_for_online
from services.datetime_utils import utc_now_naive
from services.driver_status_service import sync_from_presence, touch_heartbeat

PRESENCE_STATES = frozenset({"available", "offline", "paused", "stale", "disconnected"})
ACTIVE_REQUESTED_STATES = frozenset({"available", "paused"})
STALE_AFTER_SECONDS = 90
DISCONNECTED_AFTER_SECONDS = 300


def _seconds_since(value: datetime | None, now: datetime) -> float | None:
    if value is None:
        return None
    return max((now - value.replace(tzinfo=None)).total_seconds(), 0.0)


def validate_presence_state(state: str) -> str:
    cleaned = (state or "").strip().lower()
    if cleaned not in PRESENCE_STATES:
        allowed = ", ".join(sorted(PRESENCE_STATES))
        raise ValueError(f"presence state must be one of: {allowed}")
    return cleaned


def get_or_create_presence(db: Session, driver: User) -> DriverPresence:
    presence = db.query(DriverPresence).filter(DriverPresence.driver_id == driver.id).first()
    if presence:
        return presence
    now = utc_now_naive()
    initial = driver.availability if driver.availability in PRESENCE_STATES else "offline"
    presence = DriverPresence(
        driver_id=driver.id,
        requested_state=initial,
        effective_state=initial,
        state_changed_at=now,
        heartbeat_at=now if initial in ACTIVE_REQUESTED_STATES else None,
        updated_at=now,
    )
    db.add(presence)
    db.flush()
    return presence


def derive_effective_presence(presence: DriverPresence, *, now: datetime | None = None) -> DriverPresence:
    now = now or utc_now_naive()
    requested = validate_presence_state(presence.requested_state)
    effective = requested
    reason = None

    if requested in ACTIVE_REQUESTED_STATES:
        age = _seconds_since(presence.heartbeat_at, now)
        if age is None:
            effective = "stale"
            reason = "heartbeat_missing"
        elif age >= DISCONNECTED_AFTER_SECONDS:
            effective = "disconnected"
            reason = f"heartbeat_older_than_{DISCONNECTED_AFTER_SECONDS}s"
        elif age >= STALE_AFTER_SECONDS:
            effective = "stale"
            reason = f"heartbeat_older_than_{STALE_AFTER_SECONDS}s"

    presence.effective_state = effective
    presence.stale_reason = reason
    presence.updated_at = now
    return presence


def set_presence_state(db: Session, driver: User, state: str) -> DriverPresence:
    now = utc_now_naive()
    requested = validate_presence_state(state)
    if requested == "available":
        assert_driver_approved_for_online(db, driver)
    presence = get_or_create_presence(db, driver)
    presence.requested_state = requested
    presence.state_changed_at = now
    presence.heartbeat_at = now if requested in ACTIVE_REQUESTED_STATES else presence.heartbeat_at
    derive_effective_presence(presence, now=now)
    driver.availability = "available" if presence.effective_state == "available" else "offline"
    sync_from_presence(db, driver, effective_state=presence.effective_state)
    db.flush()
    return presence


def record_heartbeat(db: Session, driver: User) -> DriverPresence:
    now = utc_now_naive()
    presence = get_or_create_presence(db, driver)
    presence.heartbeat_at = now
    if presence.requested_state in {"stale", "disconnected"}:
        presence.requested_state = "available"
        presence.state_changed_at = now
    derive_effective_presence(presence, now=now)
    driver.availability = "available" if presence.effective_state == "available" else "offline"
    touch_heartbeat(db, driver)
    db.flush()
    return presence


def presence_to_dict(presence: DriverPresence) -> dict:
    return {
        "driver_id": presence.driver_id,
        "requested_state": presence.requested_state,
        "effective_state": presence.effective_state,
        "state": presence.effective_state,
        "state_changed_at": presence.state_changed_at.isoformat() if presence.state_changed_at else None,
        "heartbeat_at": presence.heartbeat_at.isoformat() if presence.heartbeat_at else None,
        "stale_reason": presence.stale_reason,
        "updated_at": presence.updated_at.isoformat() if presence.updated_at else None,
        "stale_after_seconds": STALE_AFTER_SECONDS,
        "disconnected_after_seconds": DISCONNECTED_AFTER_SECONDS,
    }
