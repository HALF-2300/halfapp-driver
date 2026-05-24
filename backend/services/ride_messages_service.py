"""Ride-scoped messaging for drivers."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.ride import Ride
from models.ride_message import RideMessage
from services.datetime_utils import utc_now_naive


def _driver_can_access_ride(db: Session, ride_id: int, driver_id: int) -> Ride | None:
    return (
        db.query(Ride)
        .filter(Ride.id == ride_id, Ride.driver_id == driver_id)
        .one_or_none()
    )


def list_ride_messages(db: Session, *, ride_id: int, driver_id: int, limit: int = 200) -> list[dict]:
    ride = _driver_can_access_ride(db, ride_id, driver_id)
    if ride is None:
        return None
    rows = (
        db.query(RideMessage)
        .filter(RideMessage.ride_id == ride_id)
        .order_by(RideMessage.created_at.asc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": row.id,
            "ride_id": row.ride_id,
            "sender_role": row.sender_role,
            "sender_id": row.sender_id,
            "body": row.body,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


def send_driver_ride_message(db: Session, *, ride_id: int, driver_id: int, body: str) -> int | None:
    ride = _driver_can_access_ride(db, ride_id, driver_id)
    if ride is None:
        return None
    text = (body or "").strip()
    if not text:
        return None
    row = RideMessage(
        ride_id=ride_id,
        sender_role="driver",
        sender_id=driver_id,
        body=text[:4000],
    )
    db.add(row)
    db.flush()
    return row.id
