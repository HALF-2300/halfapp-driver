"""Driver-scoped trip listing, filters, and CSV export (HALFAPP_DRIVER_TRIPS_FILTERS)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from models.ride import Ride


@dataclass
class TripFilters:
    from_dt: Optional[datetime] = None
    to_dt: Optional[datetime] = None
    status: Optional[str] = None
    q: Optional[str] = None


def parse_filter_datetime(value: str | None, *, end_of_day: bool = False) -> Optional[datetime]:
    """Parse ISO date or datetime for query filters (naive UTC-aligned datetimes)."""
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    if len(raw) == 10:
        dt = datetime.fromisoformat(raw)
        if end_of_day:
            dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        return dt
    dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    return dt


def build_trip_filters(
    *,
    from_date: str | None = None,
    to_date: str | None = None,
    status: str | None = None,
    q: str | None = None,
) -> TripFilters:
    to_raw = to_date.strip() if to_date else None
    return TripFilters(
        from_dt=parse_filter_datetime(from_date),
        to_dt=parse_filter_datetime(to_raw, end_of_day=bool(to_raw and len(to_raw) == 10)),
        status=status.strip().lower() if status else None,
        q=q.strip() if q else None,
    )


def list_driver_trips(
    db: Session,
    driver_id: int,
    filters: TripFilters,
    *,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Ride], int]:
    limit = max(1, min(int(limit), 5000))
    offset = max(0, int(offset))

    qry = db.query(Ride).filter(Ride.driver_id == int(driver_id))

    if filters.from_dt is not None:
        qry = qry.filter(Ride.created_at >= filters.from_dt)
    if filters.to_dt is not None:
        qry = qry.filter(Ride.created_at <= filters.to_dt)
    if filters.status:
        qry = qry.filter(Ride.status == filters.status)

    if filters.q:
        needle = filters.q
        if needle.isdigit():
            qry = qry.filter(Ride.id == int(needle))
        else:
            like = f"%{needle}%"
            qry = qry.filter(
                or_(
                    Ride.pickup_location.ilike(like),
                    Ride.destination.ilike(like),
                    Ride.customer_name.ilike(like),
                )
            )

    total = qry.count()
    items = (
        qry.order_by(Ride.created_at.desc()).offset(offset).limit(limit).all()
    )
    return items, total


def trip_row_for_csv(ride: Ride, *, fare_amount: float | None = None) -> list:
    """CSV row aligned to Ride model fields."""
    return [
        ride.id,
        ride.status or "",
        ride.created_at.isoformat() if ride.created_at else "",
        ride.distance if ride.distance is not None else "",
        ride.duration if ride.duration is not None else "",
        fare_amount if fare_amount is not None else (ride.fare_amount or ""),
        ride.pickup_location or "",
        ride.destination or "",
        ride.completed_at.isoformat() if ride.completed_at else "",
    ]


CSV_HEADER = [
    "ride_id",
    "status",
    "created_at",
    "distance_km",
    "duration_minutes",
    "fare_amount",
    "pickup",
    "destination",
    "completed_at",
]
