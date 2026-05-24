"""Driver eligibility for ride claim and dispatch pool visibility (DRIVER-001B + DRIVER-002)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from models.ride import Ride
from models.user import User
from services.driver_approval import (
    DriverApprovalDenied,
    assert_driver_approved_for_claim,
    driver_has_active_ride as approval_driver_has_active_ride,
)
from services.lifecycle import DriverStatus, RideStatus, to_storage_ride_status

# Profile ``busy`` is a compatibility guard; approval state is ``driver_approvals.status``.
_BLOCKED_PROFILE_AVAILABILITY = frozenset()

_ACTIVE_RIDE_STATUSES = frozenset(
    {
        to_storage_ride_status(RideStatus.ACCEPTED),
        to_storage_ride_status(RideStatus.DRIVER_ARRIVED),
        to_storage_ride_status(RideStatus.IN_PROGRESS),
    }
)

_CLAIM_BLOCK_409_REASONS = frozenset(
    {
        "presence_offline",
        "presence_paused",
        "presence_stale",
        "presence_disconnected",
        "driver_already_on_active_ride",
        "driver_busy",
        "driver_offline",
        "driver_stale",
    }
)


class DriverClaimIneligible(Exception):
    """Driver cannot claim; ride must not be mutated."""

    def __init__(self, reason: str, message: str) -> None:
        self.reason = reason
        self.message = message
        super().__init__(message)


def driver_claim_blocked_detail(
    *,
    ride_id: int,
    reason: str,
    message: str,
    state_changed: bool = False,
    effective_presence_state: str | None = None,
    active_ride_id: int | None = None,
) -> dict[str, Any]:
    """Canonical 409 when the driver cannot claim and the pool ride must not change."""
    body: dict[str, Any] = {
        "detail": message,
        "ride_id": ride_id,
        "reason": reason,
        "claim_result": "blocked",
        "truth_status": "driver_ineligible",
        "state_changed": state_changed,
    }
    if effective_presence_state is not None:
        body["effective_presence_state"] = effective_presence_state
    if active_ride_id is not None:
        body["active_ride_id"] = active_ride_id
    return body


def claim_block_uses_409(reason: str) -> bool:
    return reason in _CLAIM_BLOCK_409_REASONS or reason.startswith("presence_")


def driver_active_ride_id(db: Session, driver_id: int) -> int | None:
    row = (
        db.query(Ride.id)
        .filter(Ride.driver_id == driver_id, Ride.status.in_(_ACTIVE_RIDE_STATUSES))
        .order_by(Ride.id.asc())
        .first()
    )
    return row[0] if row else None


def driver_is_dispatch_eligible(
    db: Session,
    *,
    driver: User,
    effective_presence_state: str,
    profile_availability: str | None = None,
) -> bool:
    """Whether ``GET /drivers/available-rides`` may expose the open-board pool."""
    try:
        assert_driver_eligible_for_claim(
            db,
            driver=driver,
            effective_presence_state=effective_presence_state,
            profile_availability=profile_availability,
        )
        return True
    except DriverClaimIneligible:
        return False


def assert_driver_eligible_for_claim(
    db: Session,
    *,
    driver: User,
    effective_presence_state: str,
    profile_availability: str | None = None,
) -> None:
    """Raise DriverClaimIneligible when the driver must not claim (no ride writes).

    On-trip busy uses active-ride lookup (``accepted``, ``driver_arrived``, ``in_progress``)
    as source of truth. ``users.availability=busy`` is an extra profile guard.
    """
    try:
        assert_driver_approved_for_claim(db, driver)
    except DriverApprovalDenied as exc:
        raise DriverClaimIneligible(exc.error_code, exc.message) from exc

    raw_availability = (profile_availability if profile_availability is not None else driver.availability or "")
    raw_availability = raw_availability.strip().lower()
    if raw_availability in _BLOCKED_PROFILE_AVAILABILITY:
        raise DriverClaimIneligible(
            f"driver_{raw_availability}",
            f"Driver profile availability blocks marketplace claims ({raw_availability})",
        )

    if raw_availability == DriverStatus.BUSY.value:
        raise DriverClaimIneligible("driver_busy", "Driver is marked busy and cannot accept new rides")

    if effective_presence_state != "available":
        raise DriverClaimIneligible(
            f"presence_{effective_presence_state}",
            f"Driver must be online (available) to accept a ride; current presence is {effective_presence_state}",
        )

    from services.driver_status_service import (
        FRESHNESS_WINDOW_SECONDS,
        get_or_create_driver_status,
        is_location_fresh,
    )

    status_row = get_or_create_driver_status(db, driver)
    if not status_row.online:
        raise DriverClaimIneligible("driver_offline", "Driver must be online to accept a ride")
    if not is_location_fresh(status_row):
        raise DriverClaimIneligible(
            "driver_stale",
            f"Driver location is stale; last seen must be within {FRESHNESS_WINDOW_SECONDS}s",
        )

    if approval_driver_has_active_ride(db, driver.id):
        raise DriverClaimIneligible(
            "driver_already_on_active_ride",
            "Driver already has an active ride and cannot accept another",
        )
