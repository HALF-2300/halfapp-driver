"""GET /drivers/me/active-ride — cockpit session recovery."""

from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models.ride import Ride
from models.user import UserRole
from services.lifecycle import RideStatus, to_storage_ride_status
from tests.test_marketplace_ledger_events import _create_rider_ride, _headers, _user


def test_active_ride_returns_full_recovery_payload():
    db = SessionLocal()
    try:
        rider_token, _ = _user(db, UserRole.CUSTOMER, "active_ride_rider")
        driver_token, driver_id = _user(db, UserRole.DRIVER, "active_ride_driver")
    finally:
        db.close()

    with TestClient(app) as client:
        ride_id = _create_rider_ride(client, rider_token)
        assert client.get("/drivers/available-rides", headers=_headers(driver_token)).status_code == 200
        assert client.post(f"/drivers/accept-ride/{ride_id}", headers=_headers(driver_token)).status_code == 200

        response = client.get("/drivers/me/active-ride", headers=_headers(driver_token))
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["ride"]["id"] == ride_id
        assert body["ride"]["driver_id"] == driver_id
        assert body["lifecycle_stage"] == "accepted"
        assert body["lifecycle"]["current"] == "accepted"
        assert body["lifecycle"]["available_actions"] == ["arrive"]
        assert isinstance(body["lifecycle"]["history"], list)
        assert body["customer"]["name"]
        assert body["route"]["route_provider"] is not None
        assert body["navigation"] is not None

        assert client.post(f"/drivers/arrive-pickup/{ride_id}", headers=_headers(driver_token)).status_code == 200
        arrived = client.get("/drivers/me/active-ride", headers=_headers(driver_token)).json()
        assert arrived["lifecycle_stage"] == "driver_arrived"
        assert arrived["lifecycle"]["available_actions"] == ["start"]


def test_drivers_me_active_ride_returns_single_non_terminal():
    """Among terminal history, return the one active (non-terminal) job for this driver."""
    db = SessionLocal()
    try:
        driver_token, driver_id = _user(db, UserRole.DRIVER, "active_ride_multi")
        completed_a = Ride(
            customer_name="Done A",
            driver_id=driver_id,
            status=to_storage_ride_status(RideStatus.COMPLETED),
            pickup_location="A",
            destination="B",
        )
        completed_b = Ride(
            customer_name="Done B",
            driver_id=driver_id,
            status=to_storage_ride_status(RideStatus.COMPLETED),
            pickup_location="C",
            destination="D",
        )
        active = Ride(
            customer_name="Active",
            driver_id=driver_id,
            status=to_storage_ride_status(RideStatus.IN_PROGRESS),
            pickup_location="E",
            destination="F",
            pickup_latitude=45.52,
            pickup_longitude=-122.68,
        )
        db.add_all([completed_a, completed_b, active])
        db.commit()
        active_id = active.id
    finally:
        db.close()

    with TestClient(app) as client:
        response = client.get("/drivers/me/active-ride", headers=_headers(driver_token))
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["ride"] is not None
        assert body["ride"]["id"] == active_id
        assert body["ride"]["driver_id"] == driver_id
        assert body["lifecycle_stage"] == "in_progress"
        assert body["lifecycle"]["current"] == "in_progress"


def test_active_ride_null_when_no_active_trip():
    db = SessionLocal()
    try:
        driver_token, _ = _user(db, UserRole.DRIVER, "active_ride_idle")
    finally:
        db.close()

    with TestClient(app) as client:
        response = client.get("/drivers/me/active-ride", headers=_headers(driver_token))
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["ride"] is None
        assert body["lifecycle"] is None
