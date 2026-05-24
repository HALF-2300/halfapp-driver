"""v0.1 lifecycle display labels and rider create pricing exposure."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models.ride import Ride
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.lifecycle import RideStatus
from services.ride_pricing import quote_ride_pricing
from services.v01_lifecycle import (
    V01_DRIVER_ARRIVING,
    V01_DRIVER_ASSIGNED,
    V01_PRICED,
    V01_REQUESTED,
    resolve_v01_lifecycle_status,
)


def test_resolve_v01_lifecycle_status_mapping():
    ride = Ride(customer_name="X", status="requested")
    assert resolve_v01_lifecycle_status(ride, None) == V01_REQUESTED

    db = SessionLocal()
    try:
        ride = Ride(customer_name="X", status="requested", distance=2.0, duration=8)
        db.add(ride)
        db.commit()
        db.refresh(ride)
        row = quote_ride_pricing(db, ride_id=ride.id, distance_km=2.0, duration_minutes=8)
        db.commit()
        assert resolve_v01_lifecycle_status(ride, row) == V01_PRICED

        ride.status = "accepted"
        ride.driver_id = 1
        assert resolve_v01_lifecycle_status(ride, row) == V01_DRIVER_ASSIGNED

        ride.status = "driver_arrived"
        assert resolve_v01_lifecycle_status(ride, row) == V01_DRIVER_ARRIVING
    finally:
        db.close()


def test_rider_create_returns_pricing_and_v01_status():
    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:8]
        rider = create_user(
            db,
            f"rider_v01_{uid}@example.com",
            "Rider V01",
            "pw12345",
            UserRole.CUSTOMER,
        )
        db.commit()
        token = create_access_token(sub=rider.email, role=rider.role.value)
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {token}"}
    with TestClient(app) as client:
        created = client.post(
            "/rides/",
            headers=headers,
            json={
                "pickup_location": "100 Main St",
                "dropoff_location": "200 Oak Ave",
                "pickup_latitude": 45.501,
                "pickup_longitude": -73.567,
                "dropoff_latitude": 45.52,
                "dropoff_longitude": -73.58,
            },
        )
        assert created.status_code == 200
        ride = created.json()["ride"]
        assert ride["v01_lifecycle_status"] == V01_PRICED
        assert ride["pricing"] is not None
        assert ride["pricing"]["driver_shareable_fare_cents"] >= 800
        assert ride["pricing"]["platform_service_fee_cents"] == 150
        assert ride["status"] == RideStatus.REQUESTED.value
