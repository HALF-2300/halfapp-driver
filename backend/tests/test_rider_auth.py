"""Rider-app auth endpoints — customer register/login lane."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models.user import UserRole
from services.auth import create_user


def test_rider_register_and_login():
    uid = uuid.uuid4().hex[:8]
    email = f"rider_auth_{uid}@example.com"
    password = "RiderAuth1!"

    with TestClient(app) as client:
        registered = client.post(
            "/auth/rider/register",
            json={"email": email, "name": "Rider Auth", "password": password},
        )
        assert registered.status_code == 200, registered.text
        body = registered.json()
        assert body["role"] == "customer"
        assert body["user"]["role"] == "customer"
        assert body["access_token"]

        logged_in = client.post(
            "/auth/rider/login",
            json={"email": email, "password": password},
        )
        assert logged_in.status_code == 200
        assert logged_in.json()["role"] == "customer"


def test_driver_cannot_use_rider_login():
    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:8]
        email = f"driver_rider_lane_{uid}@example.com"
        create_user(
            db,
            email,
            "Driver Only",
            "DriverLane1!",
            UserRole.DRIVER,
            f"DL{uid}",
            driver_approval_status="approved",
        )
        db.commit()
    finally:
        db.close()

    with TestClient(app) as client:
        response = client.post(
            "/auth/rider/login",
            json={"email": email, "password": "DriverLane1!"},
        )
    assert response.status_code == 403


def test_rider_auth_create_fetch_cancel():
    uid = uuid.uuid4().hex[:8]
    email = f"rider_loop_{uid}@example.com"
    password = "RiderLoop1!"

    with TestClient(app) as client:
        auth = client.post(
            "/auth/rider/register",
            json={"email": email, "name": "Loop Rider", "password": password},
        )
        token = auth.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        created = client.post(
            "/rides/",
            headers=headers,
            json={
                "pickup_location": "Pickup A",
                "dropoff_location": "Dropoff B",
                "pickup_latitude": 45.523,
                "pickup_longitude": -122.676,
                "dropoff_latitude": 45.530,
                "dropoff_longitude": -122.650,
            },
        )
        assert created.status_code == 200, created.text
        ride_id = created.json()["ride"]["id"]
        assert created.json()["ride"]["status"] == "requested"

        fetched = client.get(f"/rides/{ride_id}", headers=headers)
        assert fetched.status_code == 200
        assert fetched.json()["ride"]["id"] == ride_id

        cancelled = client.post(f"/rides/{ride_id}/cancel", headers=headers, json={})
        assert cancelled.status_code == 200
        assert cancelled.json()["ride"]["status"] == "cancelled"

        listed = client.get("/rides/my-rides", headers=headers)
        assert listed.status_code == 200, listed.text
        rides = listed.json()["rides"]
        assert any(r["id"] == ride_id for r in rides)
