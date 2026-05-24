"""Dispatch + FSM helpers for the dossier marketplace slice."""
from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from database import engine
from services.datetime_utils import utc_now_naive

TRIP_STATE_IDLE = "IDLE"
TRIP_STATE_MATCHING = "MATCHING"
TRIP_STATE_DRIVER_EN_ROUTE = "DRIVER_EN_ROUTE"
TRIP_STATE_TRIP_COMPLETED = "TRIP_COMPLETED"
TRIP_STATE_CANCELED = "CANCELED"

DRIVER_STATUS_AVAILABLE = "AVAILABLE"
DRIVER_STATUS_DISPATCHED = "DISPATCHED"

MAX_MATCH_RADIUS_METERS = 5000
MAX_PLAUSIBLE_SPEED_MPS = 55.0


class DispatchError(Exception):
    pass


class ImpossibleMovementError(DispatchError):
    pass


def _is_postgres() -> bool:
    return engine.dialect.name == "postgresql"


def append_trip_event(
    db: Session,
    *,
    trip_id: str,
    rider_id: str | None,
    driver_id: str | None,
    from_state: str | None,
    to_state: str,
    trigger_event: str,
    idempotency_key: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    if idempotency_key:
        existing = db.execute(
            text(
                """
                SELECT id FROM trip_lifecycle_events
                WHERE idempotency_key = :idempotency_key
                """
            ),
            {"idempotency_key": idempotency_key},
        ).fetchone()
        if existing:
            return

    db.execute(
        text(
            """
            INSERT INTO trip_lifecycle_events (
                trip_id, rider_id, driver_id, from_state, to_state,
                trigger_event, idempotency_key, payload_json, occurred_at
            )
            VALUES (
                :trip_id, :rider_id, :driver_id, :from_state, :to_state,
                :trigger_event, :idempotency_key, :payload_json, :occurred_at
            )
            """
        ),
        {
            "trip_id": trip_id,
            "rider_id": rider_id,
            "driver_id": driver_id,
            "from_state": from_state,
            "to_state": to_state,
            "trigger_event": trigger_event,
            "idempotency_key": idempotency_key,
            "payload_json": json.dumps(payload or {}),
            "occurred_at": utc_now_naive(),
        },
    )


def get_trip_state(db: Session, trip_id: str) -> str | None:
    row = db.execute(
        text(
            """
            SELECT to_state FROM trip_lifecycle_events
            WHERE trip_id = :trip_id
            ORDER BY id DESC
            LIMIT 1
            """
        ),
        {"trip_id": trip_id},
    ).fetchone()
    return row[0] if row else None


def allowed_actions_for_state(state: str | None) -> list[str]:
    if state in {None, TRIP_STATE_IDLE}:
        return ["REQUEST_SUBMITTED"]
    if state == TRIP_STATE_MATCHING:
        return ["CANCEL"]
    if state == TRIP_STATE_DRIVER_EN_ROUTE:
        return ["DRIVER_ARRIVED", "CANCEL"]
    if state == TRIP_STATE_TRIP_COMPLETED:
        return []
    if state == TRIP_STATE_CANCELED:
        return []
    return []


def upsert_active_driver(
    db: Session,
    *,
    driver_id: str,
    latitude: float,
    longitude: float,
    heading: float | None,
    velocity_mps: float | None,
    device_timestamp,
    vehicle_type: str,
    available_seats: int,
    has_child_seat: bool,
    wheelchair_access: bool,
) -> None:
    prior = db.execute(
        text(
            """
            SELECT latitude, longitude, location_updated_at, velocity_mps
            FROM active_drivers WHERE id = :driver_id
            """
        ),
        {"driver_id": driver_id},
    ).fetchone()

    if prior and prior[0] is not None and prior[1] is not None and velocity_mps is not None:
        _validate_movement_plausibility(
            prior_lat=prior[0],
            prior_lng=prior[1],
            prior_at=prior[2],
            prior_velocity=prior[3],
            new_lat=latitude,
            new_lng=longitude,
            new_velocity=velocity_mps,
        )

    now = utc_now_naive()
    if _is_postgres():
        db.execute(
            text(
                """
                INSERT INTO active_drivers (
                    id, status, vehicle_type, latitude, longitude, location,
                    heading, velocity_mps, device_timestamp, location_updated_at,
                    available_seats, has_child_seat, wheelchair_access, updated_at
                )
                VALUES (
                    :driver_id, 'AVAILABLE', :vehicle_type, :latitude, :longitude,
                    ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326),
                    :heading, :velocity_mps, :device_timestamp, :location_updated_at,
                    :available_seats, :has_child_seat, :wheelchair_access, :updated_at
                )
                ON CONFLICT (id) DO UPDATE SET
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    location = EXCLUDED.location,
                    heading = EXCLUDED.heading,
                    velocity_mps = EXCLUDED.velocity_mps,
                    device_timestamp = EXCLUDED.device_timestamp,
                    location_updated_at = EXCLUDED.location_updated_at,
                    vehicle_type = EXCLUDED.vehicle_type,
                    available_seats = EXCLUDED.available_seats,
                    has_child_seat = EXCLUDED.has_child_seat,
                    wheelchair_access = EXCLUDED.wheelchair_access,
                    updated_at = EXCLUDED.updated_at
                """
            ),
            {
                "driver_id": driver_id,
                "vehicle_type": vehicle_type,
                "latitude": latitude,
                "longitude": longitude,
                "heading": heading,
                "velocity_mps": velocity_mps,
                "device_timestamp": device_timestamp,
                "location_updated_at": now,
                "available_seats": available_seats,
                "has_child_seat": int(has_child_seat),
                "wheelchair_access": int(wheelchair_access),
                "updated_at": now,
            },
        )
        return

    db.execute(
        text(
            """
            INSERT INTO active_drivers (
                id, status, vehicle_type, latitude, longitude,
                heading, velocity_mps, device_timestamp, location_updated_at,
                available_seats, has_child_seat, wheelchair_access, updated_at
            )
            VALUES (
                :driver_id, 'AVAILABLE', :vehicle_type, :latitude, :longitude,
                :heading, :velocity_mps, :device_timestamp, :location_updated_at,
                :available_seats, :has_child_seat, :wheelchair_access, :updated_at
            )
            ON CONFLICT (id) DO UPDATE SET
                latitude = excluded.latitude,
                longitude = excluded.longitude,
                heading = excluded.heading,
                velocity_mps = excluded.velocity_mps,
                device_timestamp = excluded.device_timestamp,
                location_updated_at = excluded.location_updated_at,
                vehicle_type = excluded.vehicle_type,
                available_seats = excluded.available_seats,
                has_child_seat = excluded.has_child_seat,
                wheelchair_access = excluded.wheelchair_access,
                updated_at = excluded.updated_at
            """
        ),
        {
            "driver_id": driver_id,
            "vehicle_type": vehicle_type,
            "latitude": latitude,
            "longitude": longitude,
            "heading": heading,
            "velocity_mps": velocity_mps,
            "device_timestamp": device_timestamp,
            "location_updated_at": now,
            "available_seats": available_seats,
            "has_child_seat": int(has_child_seat),
            "wheelchair_access": int(wheelchair_access),
            "updated_at": now,
        },
    )


def _validate_movement_plausibility(
    *,
    prior_lat: float,
    prior_lng: float,
    prior_at,
    prior_velocity: float | None,
    new_lat: float,
    new_lng: float,
    new_velocity: float,
) -> None:
    if prior_at is None:
        return

    elapsed_seconds = max((utc_now_naive() - prior_at).total_seconds(), 1.0)
    distance_meters = _haversine_meters(prior_lat, prior_lng, new_lat, new_lng)
    implied_speed = distance_meters / elapsed_seconds
    if implied_speed > MAX_PLAUSIBLE_SPEED_MPS or new_velocity > MAX_PLAUSIBLE_SPEED_MPS:
        raise ImpossibleMovementError(
            f"Rejected implausible movement (implied_speed_mps={implied_speed:.2f})"
        )
    if prior_velocity is not None and abs(new_velocity - prior_velocity) > 25:
        raise ImpossibleMovementError("Rejected implausible velocity delta")


def _haversine_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    from math import asin, cos, radians, sin, sqrt

    r = 6371000.0
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return 2 * r * asin(sqrt(a))


def match_driver_for_request(
    db: Session,
    *,
    trip_id: str,
    rider_id: str,
    pickup_latitude: float,
    pickup_longitude: float,
    vehicle_type: str,
    idempotency_key: str,
) -> dict[str, Any]:
    current_state = get_trip_state(db, trip_id)
    if current_state is None:
        append_trip_event(
            db,
            trip_id=trip_id,
            rider_id=rider_id,
            driver_id=None,
            from_state=TRIP_STATE_IDLE,
            to_state=TRIP_STATE_MATCHING,
            trigger_event="REQUEST_SUBMITTED",
            idempotency_key=f"{idempotency_key}:matching",
        )
    elif current_state != TRIP_STATE_MATCHING:
        return {
            "status": "INVALID_TRANSITION",
            "current_state": current_state,
            "allowed_actions": allowed_actions_for_state(current_state),
        }

    driver_row = _select_and_lock_driver(
        db,
        pickup_latitude=pickup_latitude,
        pickup_longitude=pickup_longitude,
        vehicle_type=vehicle_type,
    )
    if not driver_row:
        return {
            "status": "NO_DRIVERS_AVAILABLE",
            "current_state": TRIP_STATE_MATCHING,
            "allowed_actions": ["CANCEL"],
        }

    driver_id = driver_row[0]
    db.execute(
        text(
            """
            UPDATE active_drivers
            SET status = :dispatched, assigned_trip_id = :trip_id, updated_at = :updated_at
            WHERE id = :driver_id
            """
        ),
        {
            "dispatched": DRIVER_STATUS_DISPATCHED,
            "trip_id": trip_id,
            "driver_id": driver_id,
            "updated_at": utc_now_naive(),
        },
    )
    append_trip_event(
        db,
        trip_id=trip_id,
        rider_id=rider_id,
        driver_id=driver_id,
        from_state=TRIP_STATE_MATCHING,
        to_state=TRIP_STATE_DRIVER_EN_ROUTE,
        trigger_event="DRIVER_ACCEPTED",
        idempotency_key=f"{idempotency_key}:accepted",
        payload={"driver_id": driver_id},
    )
    return {
        "status": "DRIVER_EN_ROUTE",
        "current_state": TRIP_STATE_DRIVER_EN_ROUTE,
        "driver_id": driver_id,
        "allowed_actions": allowed_actions_for_state(TRIP_STATE_DRIVER_EN_ROUTE),
    }


def _select_and_lock_driver(
    db: Session,
    *,
    pickup_latitude: float,
    pickup_longitude: float,
    vehicle_type: str,
) -> tuple[str,] | None:
    if _is_postgres():
        return db.execute(
            text(
                """
                SELECT id
                FROM active_drivers
                WHERE status = :available
                  AND vehicle_type = :vehicle_type
                  AND location IS NOT NULL
                  AND ST_DWithin(
                        location,
                        ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
                        :radius
                  )
                ORDER BY ST_Distance(
                    location,
                    ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography
                ) ASC
                LIMIT 1
                FOR NO KEY UPDATE SKIP LOCKED
                """
            ),
            {
                "available": DRIVER_STATUS_AVAILABLE,
                "vehicle_type": vehicle_type,
                "lat": pickup_latitude,
                "lng": pickup_longitude,
                "radius": MAX_MATCH_RADIUS_METERS,
            },
        ).fetchone()

    return db.execute(
        text(
            """
            SELECT id
            FROM active_drivers
            WHERE status = :available
              AND vehicle_type = :vehicle_type
              AND latitude IS NOT NULL
              AND longitude IS NOT NULL
              AND (
                ((latitude - :lat) * 111000.0) * ((latitude - :lat) * 111000.0)
                + ((longitude - :lng) * 111000.0 * cos(radians(:lat)))
                  * ((longitude - :lng) * 111000.0 * cos(radians(:lat)))
              ) <= (:radius * :radius)
            ORDER BY
              ((latitude - :lat) * (latitude - :lat))
              + ((longitude - :lng) * (longitude - :lng)) ASC
            LIMIT 1
            """
        ),
        {
            "available": DRIVER_STATUS_AVAILABLE,
            "vehicle_type": vehicle_type,
            "lat": pickup_latitude,
            "lng": pickup_longitude,
            "radius": MAX_MATCH_RADIUS_METERS,
        },
    ).fetchone()


def complete_trip(
    db: Session,
    *,
    trip_id: str,
    idempotency_key: str,
) -> dict[str, Any]:
    current_state = get_trip_state(db, trip_id)
    if current_state != TRIP_STATE_DRIVER_EN_ROUTE:
        return {
            "status": "INVALID_TRANSITION",
            "current_state": current_state,
            "allowed_actions": allowed_actions_for_state(current_state),
        }

    driver_id = db.execute(
        text(
            """
            SELECT driver_id FROM trip_lifecycle_events
            WHERE trip_id = :trip_id AND to_state = :en_route
            ORDER BY id DESC
            LIMIT 1
            """
        ),
        {"trip_id": trip_id, "en_route": TRIP_STATE_DRIVER_EN_ROUTE},
    ).scalar()

    append_trip_event(
        db,
        trip_id=trip_id,
        rider_id=None,
        driver_id=driver_id,
        from_state=TRIP_STATE_DRIVER_EN_ROUTE,
        to_state=TRIP_STATE_TRIP_COMPLETED,
        trigger_event="DESTINATION_REACHED",
        idempotency_key=f"{idempotency_key}:completed",
    )

    if driver_id:
        db.execute(
            text(
                """
                UPDATE active_drivers
                SET status = :available, assigned_trip_id = NULL, updated_at = :updated_at
                WHERE id = :driver_id
                """
            ),
            {
                "available": DRIVER_STATUS_AVAILABLE,
                "driver_id": driver_id,
                "updated_at": utc_now_naive(),
            },
        )

    return {
        "status": "TRIP_COMPLETED",
        "current_state": TRIP_STATE_TRIP_COMPLETED,
        "driver_id": driver_id,
        "allowed_actions": [],
    }


def new_trip_id() -> str:
    return str(uuid.uuid4())
