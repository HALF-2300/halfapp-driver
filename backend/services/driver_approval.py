"""Driver approval workflow (DRIVER-002)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from models.driver_approval import DriverApproval, DriverApprovalStatus
from models.ride import Ride
from models.user import User, UserRole
from services.datetime_utils import utc_now_naive
from services.lifecycle import RideStatus, to_storage_ride_status

_ACTIVE_RIDE_STATUSES = frozenset(
    {
        to_storage_ride_status(RideStatus.ACCEPTED),
        to_storage_ride_status(RideStatus.DRIVER_ARRIVED),
        to_storage_ride_status(RideStatus.IN_PROGRESS),
    }
)

ADMIN_MUTABLE_STATUSES = frozenset(
    {
        DriverApprovalStatus.APPROVED,
        DriverApprovalStatus.REJECTED,
        DriverApprovalStatus.SUSPENDED,
    }
)


class DriverApprovalDenied(Exception):
    def __init__(self, error_code: str, message: str) -> None:
        self.error_code = error_code
        self.message = message
        super().__init__(message)


def _approval_status_str(approval: DriverApproval) -> str:
    raw = approval.status
    return raw.value if isinstance(raw, DriverApprovalStatus) else str(raw)


def _default_approval_status_for_new_driver() -> DriverApprovalStatus:
    return DriverApprovalStatus.PENDING


def get_driver_approval(db: Session, driver_id: int) -> DriverApproval | None:
    return db.query(DriverApproval).filter(DriverApproval.driver_id == driver_id).first()


def get_or_create_driver_approval(db: Session, driver_id: int) -> DriverApproval:
    row = get_driver_approval(db, driver_id)
    if row:
        return row
    now = utc_now_naive()
    row = DriverApproval(
        driver_id=driver_id,
        status=_default_approval_status_for_new_driver().value,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    return row


def create_default_driver_approval(db: Session, user: User) -> DriverApproval | None:
    if user.role != UserRole.DRIVER:
        return None
    return get_or_create_driver_approval(db, user.id)


def approval_status_value(approval: DriverApproval | None) -> str:
    if approval is None:
        return DriverApprovalStatus.PENDING.value
    return _approval_status_str(approval)


def approval_public_dict(approval: DriverApproval | None) -> dict:
    if approval is None:
        return {
            "status": DriverApprovalStatus.PENDING.value,
            "reason": None,
            "reviewed_by": None,
            "reviewed_at": None,
        }
    return {
        "status": _approval_status_str(approval),
        "reason": approval.reason,
        "reviewed_by": approval.reviewed_by,
        "reviewed_at": approval.reviewed_at.isoformat() if approval.reviewed_at else None,
    }


def set_driver_approval(
    db: Session,
    *,
    driver_id: int,
    status: DriverApprovalStatus,
    reason: str | None,
    reviewed_by: int,
) -> DriverApproval:
    if status not in ADMIN_MUTABLE_STATUSES:
        raise ValueError(f"Admin cannot set approval status to {status.value}")

    driver = db.query(User).filter(User.id == driver_id, User.role == UserRole.DRIVER).first()
    if not driver:
        raise LookupError("driver_not_found")

    approval = get_or_create_driver_approval(db, driver_id)
    now = utc_now_naive()
    approval.status = status.value
    if reason is not None:
        approval.reason = reason.strip() or None
    approval.reviewed_by = reviewed_by
    approval.reviewed_at = now
    approval.updated_at = now
    db.flush()
    return approval


def is_driver_dispatch_available(db: Session, driver: User, *, now: datetime | None = None) -> bool:
    """Dispatch pool: approved + driver_status.online + last_seen within FRESHNESS_WINDOW_SECONDS."""
    from services.driver_status_service import get_or_create_driver_status, is_location_fresh

    if driver.role != UserRole.DRIVER or not driver.is_active:
        return False
    approval = get_driver_approval(db, driver.id)
    if approval is None or _approval_status_str(approval) != DriverApprovalStatus.APPROVED.value:
        return False
    row = get_or_create_driver_status(db, driver)
    if not row.online:
        return False
    return is_location_fresh(row, now=now)


def driver_has_active_ride(db: Session, driver_id: int) -> bool:
    return (
        db.query(Ride.id)
        .filter(Ride.driver_id == driver_id, Ride.status.in_(_ACTIVE_RIDE_STATUSES))
        .first()
        is not None
    )


def assert_driver_approved_for_online(db: Session, driver: User) -> None:
    if not driver.is_active:
        raise DriverApprovalDenied("account_deactivated", "Driver account is not active")

    approval = get_or_create_driver_approval(db, driver.id)
    status = _approval_status_str(approval)
    if status == DriverApprovalStatus.PENDING.value:
        raise DriverApprovalDenied("driver_not_approved", "Driver approval is pending")
    if status == DriverApprovalStatus.REJECTED.value:
        raise DriverApprovalDenied("driver_rejected", "Driver application was rejected")
    if status == DriverApprovalStatus.SUSPENDED.value:
        raise DriverApprovalDenied("driver_suspended", "Driver account is suspended")


def assert_driver_approved_for_claim(db: Session, driver: User) -> None:
    assert_driver_approved_for_online(db, driver)


def assert_driver_can_perform_ride_action(
    db: Session,
    *,
    driver: User,
    ride_id: int,
    action: str,
) -> None:
    """Block new marketplace actions for suspended drivers; allow in-flight ride completion."""
    if not driver.is_active:
        raise DriverApprovalDenied("account_deactivated", "Driver account is not active")

    approval = get_or_create_driver_approval(db, driver.id)
    status = _approval_status_str(approval)
    if status == DriverApprovalStatus.PENDING.value:
        raise DriverApprovalDenied("driver_not_approved", "Driver approval is pending")
    if status == DriverApprovalStatus.REJECTED.value:
        raise DriverApprovalDenied("driver_rejected", "Driver application was rejected")

    if status == DriverApprovalStatus.SUSPENDED.value:
        ride = db.query(Ride).filter(Ride.id == ride_id, Ride.driver_id == driver.id).first()
        if ride is None:
            raise DriverApprovalDenied("driver_suspended", "Driver account is suspended")
        if action in {"accept", "decline", "hide"}:
            raise DriverApprovalDenied("driver_suspended", "Suspended drivers cannot accept new rides")
        # arrive/start/complete on an assigned active ride remain allowed (no ride corruption).


def query_dispatch_available_driver_ids(db: Session) -> list[int]:
    now = utc_now_naive()
    drivers = (
        db.query(User)
        .join(DriverApproval, DriverApproval.driver_id == User.id)
        .filter(
            User.role == UserRole.DRIVER,
            User.is_active.is_(True),
            DriverApproval.status == DriverApprovalStatus.APPROVED.value,
        )
        .all()
    )
    eligible: list[int] = []
    for driver in drivers:
        if is_driver_dispatch_available(db, driver, now=now):
            eligible.append(driver.id)
    return eligible
