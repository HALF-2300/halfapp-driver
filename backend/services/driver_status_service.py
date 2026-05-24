"""Driver online/offline persistence (DRIVER-001). Dispatch availability uses driver_approval."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from models.driver_status import DriverStatusRecord
from models.user import User
from services.driver_approval import (
    DriverApprovalDenied,
    assert_driver_approved_for_online,
    driver_has_active_ride,
)
from services.datetime_utils import utc_now_naive
from services.lifecycle import DriverStatus

# Dispatch treats drivers as unavailable if not seen within this window.
FRESHNESS_WINDOW_SECONDS = 300


def _validate_coordinates(lat: float, lng: float) -> None:
    if lat < -90 or lat > 90:
        raise ValueError("lat must be between -90 and 90")
    if lng < -180 or lng > 180:
        raise ValueError("lng must be between -180 and 180")


def get_or_create_driver_status(db: Session, driver: User) -> DriverStatusRecord:
    row = db.query(DriverStatusRecord).filter(DriverStatusRecord.driver_id == driver.id).first()
    if row:
        return row
    now = utc_now_naive()
    row = DriverStatusRecord(
        driver_id=driver.id,
        online=False,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    return row


def _sync_user_location(driver: User, *, lat: float, lng: float, now: datetime) -> None:
    driver.last_latitude = lat
    driver.last_longitude = lng
    driver.last_location_at = now


def _sync_profile_availability(driver: User, *, online: bool) -> None:
    driver.availability = DriverStatus.AVAILABLE.value if online else DriverStatus.OFFLINE.value


def _refresh_current_ride_id(db: Session, row: DriverStatusRecord, driver_id: int) -> None:
    if driver_has_active_ride(db, driver_id):
        from models.ride import Ride
        from services.lifecycle import RideStatus, to_storage_ride_status

        active = (
            db.query(Ride.id)
            .filter(
                Ride.driver_id == driver_id,
                Ride.status.in_(
                    {
                        to_storage_ride_status(RideStatus.ACCEPTED),
                        to_storage_ride_status(RideStatus.DRIVER_ARRIVED),
                        to_storage_ride_status(RideStatus.IN_PROGRESS),
                    }
                ),
            )
            .order_by(Ride.id.desc())
            .first()
        )
        row.current_ride_id = active[0] if active else None
    else:
        row.current_ride_id = None


def is_location_fresh(row: DriverStatusRecord, *, now: datetime | None = None) -> bool:
    if not row.last_seen_at:
        return False
    now = now or utc_now_naive()
    seen = row.last_seen_at.replace(tzinfo=None) if row.last_seen_at.tzinfo else row.last_seen_at
    return (now - seen).total_seconds() <= FRESHNESS_WINDOW_SECONDS


def driver_status_to_dict(row: DriverStatusRecord) -> dict:
    return {
        "driver_id": row.driver_id,
        "online": bool(row.online),
        "last_lat": row.last_lat,
        "last_lng": row.last_lng,
        "last_seen_at": row.last_seen_at.isoformat() if row.last_seen_at else None,
        "current_ride_id": row.current_ride_id,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def set_driver_online(
    db: Session,
    driver: User,
    *,
    lat: float,
    lng: float,
) -> DriverStatusRecord:
    assert_driver_approved_for_online(db, driver)
    _validate_coordinates(lat, lng)
    now = utc_now_naive()
    row = get_or_create_driver_status(db, driver)
    row.online = True
    row.last_lat = lat
    row.last_lng = lng
    row.last_seen_at = now
    row.updated_at = now
    _refresh_current_ride_id(db, row, driver.id)
    _sync_user_location(driver, lat=lat, lng=lng, now=now)
    _sync_profile_availability(driver, online=True)
    db.flush()
    return row


def set_driver_offline(db: Session, driver: User) -> DriverStatusRecord:
    """Go offline without cancelling an active ride; current_ride_id reflects active ride if any."""
    now = utc_now_naive()
    row = get_or_create_driver_status(db, driver)
    row.online = False
    row.updated_at = now
    _refresh_current_ride_id(db, row, driver.id)
    _sync_profile_availability(driver, online=False)
    db.flush()
    return row


def persist_driver_location(
    db: Session,
    driver: User,
    *,
    lat: float,
    lng: float,
) -> DriverStatusRecord:
    _validate_coordinates(lat, lng)
    row = get_or_create_driver_status(db, driver)
    if not row.online:
        raise ValueError("driver_offline")
    now = utc_now_naive()
    row.last_lat = lat
    row.last_lng = lng
    row.last_seen_at = now
    row.updated_at = now
    _sync_user_location(driver, lat=lat, lng=lng, now=now)
    db.flush()
    return row


def sync_from_presence(
    db: Session,
    driver: User,
    *,
    effective_state: str,
    lat: float | None = None,
    lng: float | None = None,
) -> DriverStatusRecord:
    """Keep driver_status aligned when legacy /drivers/presence endpoints are used."""
    row = get_or_create_driver_status(db, driver)
    now = utc_now_naive()
    if effective_state == "available":
        use_lat = lat if lat is not None else driver.last_latitude
        use_lng = lng if lng is not None else driver.last_longitude
        if use_lat is not None and use_lng is not None:
            try:
                return set_driver_online(db, driver, lat=use_lat, lng=use_lng)
            except DriverApprovalDenied:
                row.online = False
                row.updated_at = now
                db.flush()
                return row
        row.online = True
        row.updated_at = now
        if row.last_seen_at is None:
            row.last_seen_at = now
    else:
        row.online = False
        row.updated_at = now
        _refresh_current_ride_id(db, row, driver.id)
    db.flush()
    return row


def touch_heartbeat(db: Session, driver: User) -> DriverStatusRecord | None:
    """Refresh last_seen_at for online drivers (heartbeat / presence)."""
    row = db.query(DriverStatusRecord).filter(DriverStatusRecord.driver_id == driver.id).first()
    if not row or not row.online:
        return row
    now = utc_now_naive()
    row.last_seen_at = now
    row.updated_at = now
    db.flush()
    return row


def count_dispatch_available_drivers(db: Session) -> int:
    from models.user import UserRole
    from services.driver_approval import is_driver_dispatch_available

    drivers = db.query(User).filter(User.role == UserRole.DRIVER, User.is_active.is_(True)).all()
    return sum(1 for driver in drivers if is_driver_dispatch_available(db, driver))
