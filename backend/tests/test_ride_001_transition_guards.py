"""RIDE-001: formal state machine guards with structured 409 responses."""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models.metrics import Event
from models.ride import Ride
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.lifecycle import RideStatus


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_user_token(role: UserRole, *, availability: str | None = None):
    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:10]
        license_no = f"SM{uid}" if role == UserRole.DRIVER else None
        kwargs = {}
        if role == UserRole.DRIVER:
            kwargs["driver_approval_status"] = "approved"
        user = create_user(
            db,
            f"ride001_{role.value}_{uid}@example.com",
            f"Ride001 {role.value}",
            "pw12345",
            role,
            license_no,
            **kwargs,
        )
        if availability is not None and role == UserRole.DRIVER:
            user.availability = availability
            db.commit()
        token = create_access_token(sub=user.email, role=user.role.value)
        user_id = user.id
    finally:
        db.close()
    return user_id, token


def _go_online(client: TestClient, token: str) -> None:
    client.patch(
        "/drivers/me/status",
        headers=_headers(token),
        json={"online": True, "lat": 45.52, "lng": -122.68},
    )
    client.put("/drivers/presence", headers=_headers(token), json={"state": "available"})


def _ride_payload() -> dict:
    return {
        "pickup_location": "Origin",
        "dropoff_location": "Destination",
        "pickup_latitude": 45.501,
        "pickup_longitude": -122.681,
        "dropoff_latitude": 45.551,
        "dropoff_longitude": -122.611,
        "distance_km": 3.5,
    }


def _create_requested_ride(client: TestClient, rider_token: str) -> int:
    response = client.post("/rides/", headers=_headers(rider_token), json=_ride_payload())
    assert response.status_code == 200, response.text
    return response.json()["ride"]["id"]


def _assert_invalid_transition(response, *, ride_id: int, from_status: str, to_status: str) -> None:
    assert response.status_code == 409, response.text
    detail = response.json()["detail"]
    assert detail["error"] == "invalid_state_transition"
    assert detail["code"] == "invalid_state_transition"
    assert detail["ride_id"] == ride_id
    assert detail["from_status"] == from_status
    assert detail["to_status"] == to_status
    assert detail["state_changed"] is False
    assert "message" in detail


def test_requested_to_cancelled_succeeds():
    _, rider_token = _create_user_token(UserRole.CUSTOMER)
    with TestClient(app) as client:
        ride_id = _create_requested_ride(client, rider_token)
        response = client.post(f"/rides/{ride_id}/cancel", headers=_headers(rider_token), json={})
    assert response.status_code == 200, response.text
    assert response.json()["ride"]["status"] == "cancelled"


def test_accepted_to_cancelled_succeeds():
    _, rider_token = _create_user_token(UserRole.CUSTOMER)
    _, driver_token = _create_user_token(UserRole.DRIVER, availability="available")
    with TestClient(app) as client:
        ride_id = _create_requested_ride(client, rider_token)
        _go_online(client, driver_token)
        client.post(f"/drivers/accept-ride/{ride_id}", headers=_headers(driver_token))
        response = client.post(f"/rides/{ride_id}/cancel", headers=_headers(rider_token), json={})
    assert response.status_code == 200, response.text
    assert response.json()["ride"]["status"] == "cancelled"


def test_invalid_transition_does_not_mutate_ride_status():
    _, rider_token = _create_user_token(UserRole.CUSTOMER)
    _, driver_token = _create_user_token(UserRole.DRIVER, availability="available")
    with TestClient(app) as client:
        ride_id = _create_requested_ride(client, rider_token)
        _go_online(client, driver_token)
        client.post(f"/drivers/complete-ride/{ride_id}", headers=_headers(driver_token))
        db = SessionLocal()
        try:
            ride = db.query(Ride).filter(Ride.id == ride_id).first()
            assert ride.status == "requested"
        finally:
            db.close()


def test_completed_financial_lock_remains_intact():
    from models.ride_pricing import RidePricing

    _, rider_token = _create_user_token(UserRole.CUSTOMER)
    driver_id, driver_token = _create_user_token(UserRole.DRIVER, availability="available")
    with TestClient(app) as client:
        ride_id = _create_requested_ride(client, rider_token)
        _go_online(client, driver_token)
        client.post(f"/drivers/accept-ride/{ride_id}", headers=_headers(driver_token))
        client.post(f"/drivers/arrive-pickup/{ride_id}", headers=_headers(driver_token))
        client.post(f"/drivers/start-ride/{ride_id}", headers=_headers(driver_token))
        first = client.post(f"/drivers/complete-ride/{ride_id}", headers=_headers(driver_token))
        assert first.status_code == 200, first.text
        db = SessionLocal()
        try:
            pricing = db.query(RidePricing).filter(RidePricing.ride_id == ride_id).first()
            assert pricing is not None
            assert pricing.financial_locked is True
        finally:
            db.close()
        second = client.post(f"/drivers/complete-ride/{ride_id}", headers=_headers(driver_token))
    assert second.status_code == 409, second.text
    detail = second.json()["detail"]
    if isinstance(detail, dict):
        assert detail["error"] == "invalid_state_transition"
        assert detail["state_changed"] is False
    else:
        assert "locked" in str(detail).lower()
    db = SessionLocal()
    try:
        pricing = db.query(RidePricing).filter(RidePricing.ride_id == ride_id).first()
        assert pricing.financial_locked is True
    finally:
        db.close()


def test_completed_to_in_progress_rejected():
    driver_id, driver_token = _create_user_token(UserRole.DRIVER, availability="available")
    db = SessionLocal()
    try:
        ride = Ride(
            customer_name="Done",
            status=RideStatus.COMPLETED.value,
            driver_id=driver_id,
            distance=1.0,
        )
        db.add(ride)
        db.commit()
        ride_id = ride.id
    finally:
        db.close()
    with TestClient(app) as client:
        response = client.post(f"/drivers/start-ride/{ride_id}", headers=_headers(driver_token))
    _assert_invalid_transition(response, ride_id=ride_id, from_status="completed", to_status="in_progress")


def test_cancelled_to_in_progress_rejected():
    driver_id, driver_token = _create_user_token(UserRole.DRIVER, availability="available")
    db = SessionLocal()
    try:
        ride = Ride(
            customer_name="Cancelled",
            status=RideStatus.CANCELLED.value,
            driver_id=driver_id,
            distance=1.0,
        )
        db.add(ride)
        db.commit()
        ride_id = ride.id
    finally:
        db.close()
    with TestClient(app) as client:
        response = client.post(f"/drivers/start-ride/{ride_id}", headers=_headers(driver_token))
    _assert_invalid_transition(response, ride_id=ride_id, from_status="cancelled", to_status="in_progress")


def test_completed_to_accepted_returns_structured_conflict():
    _, driver_token = _create_user_token(UserRole.DRIVER, availability="available")
    db = SessionLocal()
    try:
        completed = Ride(customer_name="Done", status=RideStatus.COMPLETED.value, distance=1.0)
        db.add(completed)
        db.commit()
        ride_id = completed.id
    finally:
        db.close()
    with TestClient(app) as client:
        _go_online(client, driver_token)
        response = client.post(f"/drivers/accept-ride/{ride_id}", headers=_headers(driver_token))
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail.get("error") == "invalid_state_transition" or detail.get("reason")


def test_requested_to_completed_rejected():
    _, rider_token = _create_user_token(UserRole.CUSTOMER)
    _, driver_token = _create_user_token(UserRole.DRIVER, availability="available")
    with TestClient(app) as client:
        ride_id = _create_requested_ride(client, rider_token)
        _go_online(client, driver_token)
        response = client.post(f"/drivers/complete-ride/{ride_id}", headers=_headers(driver_token))
    _assert_invalid_transition(response, ride_id=ride_id, from_status="requested", to_status="completed")


def test_requested_to_accepted_succeeds():
    _, rider_token = _create_user_token(UserRole.CUSTOMER)
    _, driver_token = _create_user_token(UserRole.DRIVER, availability="available")
    with TestClient(app) as client:
        ride_id = _create_requested_ride(client, rider_token)
        _go_online(client, driver_token)
        response = client.post(f"/drivers/accept-ride/{ride_id}", headers=_headers(driver_token))
    assert response.status_code == 200, response.text
    assert response.json()["ride"]["status"] == "accepted"


def test_accepted_to_driver_arrived_succeeds():
    _, rider_token = _create_user_token(UserRole.CUSTOMER)
    _, driver_token = _create_user_token(UserRole.DRIVER, availability="available")
    with TestClient(app) as client:
        ride_id = _create_requested_ride(client, rider_token)
        _go_online(client, driver_token)
        client.post(f"/drivers/accept-ride/{ride_id}", headers=_headers(driver_token))
        response = client.post(f"/drivers/arrive-pickup/{ride_id}", headers=_headers(driver_token))
    assert response.status_code == 200, response.text
    assert response.json()["ride"]["status"] == "driver_arrived"


def test_accepted_to_completed_rejected():
    _, rider_token = _create_user_token(UserRole.CUSTOMER)
    _, driver_token = _create_user_token(UserRole.DRIVER, availability="available")
    with TestClient(app) as client:
        ride_id = _create_requested_ride(client, rider_token)
        _go_online(client, driver_token)
        client.post(f"/drivers/accept-ride/{ride_id}", headers=_headers(driver_token))
        response = client.post(f"/drivers/complete-ride/{ride_id}", headers=_headers(driver_token))
    _assert_invalid_transition(response, ride_id=ride_id, from_status="accepted", to_status="completed")


def test_driver_arrived_to_in_progress_succeeds():
    _, rider_token = _create_user_token(UserRole.CUSTOMER)
    _, driver_token = _create_user_token(UserRole.DRIVER, availability="available")
    with TestClient(app) as client:
        ride_id = _create_requested_ride(client, rider_token)
        _go_online(client, driver_token)
        client.post(f"/drivers/accept-ride/{ride_id}", headers=_headers(driver_token))
        client.post(f"/drivers/arrive-pickup/{ride_id}", headers=_headers(driver_token))
        response = client.post(f"/drivers/start-ride/{ride_id}", headers=_headers(driver_token))
    assert response.status_code == 200, response.text
    assert response.json()["ride"]["status"] == "in_progress"


def test_driver_arrived_to_completed_rejected():
    _, rider_token = _create_user_token(UserRole.CUSTOMER)
    _, driver_token = _create_user_token(UserRole.DRIVER, availability="available")
    with TestClient(app) as client:
        ride_id = _create_requested_ride(client, rider_token)
        _go_online(client, driver_token)
        client.post(f"/drivers/accept-ride/{ride_id}", headers=_headers(driver_token))
        client.post(f"/drivers/arrive-pickup/{ride_id}", headers=_headers(driver_token))
        response = client.post(f"/drivers/complete-ride/{ride_id}", headers=_headers(driver_token))
    _assert_invalid_transition(response, ride_id=ride_id, from_status="driver_arrived", to_status="completed")


def test_in_progress_to_completed_succeeds():
    _, rider_token = _create_user_token(UserRole.CUSTOMER)
    _, driver_token = _create_user_token(UserRole.DRIVER, availability="available")
    with TestClient(app) as client:
        ride_id = _create_requested_ride(client, rider_token)
        _go_online(client, driver_token)
        client.post(f"/drivers/accept-ride/{ride_id}", headers=_headers(driver_token))
        client.post(f"/drivers/arrive-pickup/{ride_id}", headers=_headers(driver_token))
        client.post(f"/drivers/start-ride/{ride_id}", headers=_headers(driver_token))
        response = client.post(f"/drivers/complete-ride/{ride_id}", headers=_headers(driver_token))
    assert response.status_code == 200, response.text
    assert response.json()["ride"]["status"] == "completed"


def test_completed_to_cancelled_rejected():
    _, rider_token = _create_user_token(UserRole.CUSTOMER)
    _, driver_token = _create_user_token(UserRole.DRIVER, availability="available")
    with TestClient(app) as client:
        ride_id = _create_requested_ride(client, rider_token)
        _go_online(client, driver_token)
        client.post(f"/drivers/accept-ride/{ride_id}", headers=_headers(driver_token))
        client.post(f"/drivers/arrive-pickup/{ride_id}", headers=_headers(driver_token))
        client.post(f"/drivers/start-ride/{ride_id}", headers=_headers(driver_token))
        completed = client.post(f"/drivers/complete-ride/{ride_id}", headers=_headers(driver_token))
        assert completed.status_code == 200, completed.text
        response = client.post(f"/rides/{ride_id}/cancel", headers=_headers(rider_token), json={})
    _assert_invalid_transition(response, ride_id=ride_id, from_status="completed", to_status="cancelled")


def test_cancelled_to_accepted_rejected():
    _, driver_token = _create_user_token(UserRole.DRIVER, availability="available")
    db = SessionLocal()
    try:
        cancelled = Ride(customer_name="Cancelled", status=RideStatus.CANCELLED.value, distance=1.0)
        db.add(cancelled)
        db.commit()
        ride_id = cancelled.id
    finally:
        db.close()
    with TestClient(app) as client:
        _go_online(client, driver_token)
        response = client.post(f"/drivers/accept-ride/{ride_id}", headers=_headers(driver_token))
    assert response.status_code == 409, response.text
    detail = response.json()["detail"]
    assert detail.get("error") == "invalid_state_transition" or detail.get("reason")


def test_cancelled_to_completed_rejected():
    _, driver_token = _create_user_token(UserRole.DRIVER, availability="available")
    db = SessionLocal()
    try:
        cancelled = Ride(
            customer_name="Cancelled",
            status=RideStatus.CANCELLED.value,
            driver_id=1,
            distance=1.0,
        )
        db.add(cancelled)
        db.commit()
        ride_id = cancelled.id
    finally:
        db.close()
    with TestClient(app) as client:
        response = client.post(f"/drivers/complete-ride/{ride_id}", headers=_headers(driver_token))
    assert response.status_code == 409, response.text
    detail = response.json()["detail"]
    if isinstance(detail, dict) and detail.get("error") == "invalid_state_transition":
        _assert_invalid_transition(
            response,
            ride_id=ride_id,
            from_status="cancelled",
            to_status="completed",
        )
    else:
        assert "not found" in str(detail).lower() or "assigned" in str(detail).lower()


def test_valid_accept_records_audit_event():
    _, rider_token = _create_user_token(UserRole.CUSTOMER)
    driver_id, driver_token = _create_user_token(UserRole.DRIVER, availability="available")
    with TestClient(app) as client:
        ride_id = _create_requested_ride(client, rider_token)
        _go_online(client, driver_token)
        response = client.post(f"/drivers/accept-ride/{ride_id}", headers=_headers(driver_token))
        assert response.status_code == 200, response.text
    db = SessionLocal()
    try:
        events = (
            db.query(Event)
            .filter(Event.entity_type == "ride", Event.entity_id == ride_id, Event.event_type == "ride.accepted")
            .all()
        )
        assert len(events) >= 1
        assert events[0].actor_id == driver_id
    finally:
        db.close()
