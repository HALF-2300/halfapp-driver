"""Rider ride SSE — named events for location, ETA, fare."""

from __future__ import annotations

import json
import uuid

from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models.ride import Ride
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.rider_ride_stream import collect_rider_stream_events


def _customer_token(db) -> str:
    uid = uuid.uuid4().hex[:8]
    user = create_user(
        db,
        f"rider_sse_{uid}@example.com",
        "Rider SSE",
        "RiderSse1!",
        UserRole.CUSTOMER,
    )
    db.commit()
    return create_access_token(sub=user.email, role=user.role.value)


def _driver_with_location(db) -> str:
    uid = uuid.uuid4().hex[:8]
    user = create_user(
        db,
        f"driver_sse_{uid}@example.com",
        "Driver SSE",
        "DriverSse1!",
        UserRole.DRIVER,
        f"DL{uid}",
        driver_approval_status="approved",
    )
    user.last_latitude = 45.52
    user.last_longitude = -122.67
    user.availability = "available"
    db.commit()
    return create_access_token(sub=user.email, role=user.role.value)


def test_collect_rider_stream_events_payloads():
    db = SessionLocal()
    try:
        rider_token = _customer_token(db)
        driver_token = _driver_with_location(db)
    finally:
        db.close()

    with TestClient(app) as client:
        created = client.post(
            "/rides/",
            headers={"Authorization": f"Bearer {rider_token}"},
            json={
                "pickup_location": "A",
                "dropoff_location": "B",
                "pickup_latitude": 45.501,
                "pickup_longitude": -122.678,
                "dropoff_latitude": 45.515,
                "dropoff_longitude": -122.65,
            },
        )
        assert created.status_code == 200
        ride_id = created.json()["ride"]["id"]
        client.post(
            f"/drivers/accept-ride/{ride_id}",
            headers={"Authorization": f"Bearer {driver_token}"},
        )

    db = SessionLocal()
    try:
        ride = db.query(Ride).filter(Ride.id == ride_id).first()
        events = collect_rider_stream_events(ride, db, ride_id=ride_id, last_status=None)
        names = [name for name, _ in events]
        assert "status_change" in names
        assert "driver_location" in names
        assert "fare_update" in names
        assert "eta_update" in names
        loc = next(p for n, p in events if n == "driver_location")
        assert loc["lat"] == 45.52
    finally:
        db.close()


def test_rider_stream_http_emits_named_events():
    db = SessionLocal()
    try:
        rider_token = _customer_token(db)
        driver_token = _driver_with_location(db)
    finally:
        db.close()

    with TestClient(app) as client:
        created = client.post(
            "/rides/",
            headers={"Authorization": f"Bearer {rider_token}"},
            json={
                "pickup_location": "A",
                "dropoff_location": "B",
                "pickup_latitude": 45.501,
                "pickup_longitude": -122.678,
                "dropoff_latitude": 45.515,
                "dropoff_longitude": -122.65,
            },
        )
        ride_id = created.json()["ride"]["id"]
        headers = {"Authorization": f"Bearer {driver_token}"}
        for path in [
            f"/drivers/accept-ride/{ride_id}",
            f"/drivers/arrive-pickup/{ride_id}",
            f"/drivers/start-ride/{ride_id}",
            f"/drivers/complete-ride/{ride_id}",
        ]:
            client.post(path, headers=headers, json={"tip_cents": 0, "toll_cents": 0, "city_fee_cents": 0})

        with client.stream(
            "GET",
            f"/rides/{ride_id}/stream?access_token={rider_token}",
            headers={"Authorization": f"Bearer {rider_token}"},
        ) as resp:
            assert resp.status_code == 200
            body = resp.read().decode()
        assert "event: status_change" in body
        assert "event: driver_location" in body
        assert "event: fare_update" in body
        # eta_update is omitted when ride is already terminal (completed)
