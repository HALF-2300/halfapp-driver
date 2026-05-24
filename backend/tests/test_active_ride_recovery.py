"""GET /drivers/me/active-ride — cockpit session recovery."""

from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models.user import UserRole
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
