import uuid

from fastapi.testclient import TestClient

import services.rbac as rbac
from database import SessionLocal, get_db
from main import app
from models.ride import Ride
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.lifecycle import DriverStatus, RideStatus


def _create_user_token(role: UserRole, *, availability: DriverStatus | None = None):
    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:10]
        license_no = f"SM{uid}" if role == UserRole.DRIVER else None
        kwargs = {}
        if role == UserRole.DRIVER:
            kwargs["driver_approval_status"] = "approved"
        user = create_user(
            db,
            f"state_machine_{role.value}_{uid}@example.com",
            f"State Machine {role.value}",
            "pw12345",
            role,
            license_no,
            **kwargs,
        )
        if availability is not None:
            user.availability = availability.value
            db.commit()
            db.refresh(user)
        return user.id, create_access_token(sub=user.email, role=user.role.value)
    finally:
        db.close()


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


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


def _go_online(client: TestClient, driver_token: str) -> None:
    client.patch(
        "/drivers/me/status",
        headers=_headers(driver_token),
        json={"online": True, "lat": 45.52, "lng": -122.68},
    )
    client.put("/drivers/presence", headers=_headers(driver_token), json={"state": "available"})


def _create_requested_ride(client: TestClient, rider_token: str) -> int:
    response = client.post("/rides/", headers=_headers(rider_token), json=_ride_payload())
    assert response.status_code == 200, response.text
    ride = response.json()["ride"]
    assert ride["status"] == RideStatus.REQUESTED.value
    return ride["id"]


def test_rider_create_and_driver_state_machine_happy_path():
    _, rider_token = _create_user_token(UserRole.CUSTOMER)
    _, driver_token = _create_user_token(UserRole.DRIVER, availability=DriverStatus.AVAILABLE)

    with TestClient(app) as client:
        ride_id = _create_requested_ride(client, rider_token)

        online = client.patch(
            "/drivers/me/status",
            headers=_headers(driver_token),
            json={"online": True, "lat": 45.501, "lng": -122.681},
        )
        assert online.status_code == 200, online.text
        client.put("/drivers/presence", headers=_headers(driver_token), json={"state": "available"})

        accepted = client.post(f"/drivers/accept-ride/{ride_id}", headers=_headers(driver_token))
        assert accepted.status_code == 200, accepted.text
        assert accepted.json()["ride"]["status"] == RideStatus.ACCEPTED.value

        arrived = client.post(f"/drivers/arrive-pickup/{ride_id}", headers=_headers(driver_token))
        assert arrived.status_code == 200, arrived.text
        assert arrived.json()["ride"]["status"] == RideStatus.DRIVER_ARRIVED.value

        started = client.post(f"/drivers/start-ride/{ride_id}", headers=_headers(driver_token))
        assert started.status_code == 200, started.text
        assert started.json()["ride"]["status"] == RideStatus.IN_PROGRESS.value

        completed = client.post(f"/drivers/complete-ride/{ride_id}", headers=_headers(driver_token))
        assert completed.status_code == 200, completed.text
        assert completed.json()["ride"]["status"] == RideStatus.COMPLETED.value


def test_driver_can_accept_only_requested_and_available_driver_required():
    _, available_driver_token = _create_user_token(UserRole.DRIVER, availability=DriverStatus.AVAILABLE)
    _, offline_driver_token = _create_user_token(UserRole.DRIVER, availability=DriverStatus.OFFLINE)

    db = SessionLocal()
    try:
        requested = Ride(customer_name="Requested Rider", status=RideStatus.REQUESTED.value, distance=1.0)
        completed = Ride(customer_name="Completed Rider", status=RideStatus.COMPLETED.value, distance=1.0)
        db.add_all([requested, completed])
        db.commit()
        requested_id = requested.id
        completed_id = completed.id
    finally:
        db.close()

    with TestClient(app) as client:
        offline_claim = client.post(f"/drivers/accept-ride/{requested_id}", headers=_headers(offline_driver_token))
        completed_claim = client.post(f"/drivers/accept-ride/{completed_id}", headers=_headers(available_driver_token))

    assert offline_claim.status_code == 409, offline_claim.text
    assert offline_claim.json()["detail"]["reason"] == "presence_offline"
    assert completed_claim.status_code == 409, completed_claim.text


def test_completed_ride_cannot_be_cancelled_and_invalid_transition_returns_409():
    _, rider_token = _create_user_token(UserRole.CUSTOMER)
    _, driver_token = _create_user_token(UserRole.DRIVER, availability=DriverStatus.AVAILABLE)

    with TestClient(app) as client:
        ride_id = _create_requested_ride(client, rider_token)
        client.patch(
            "/drivers/me/status",
            headers=_headers(driver_token),
            json={"online": True, "lat": 45.501, "lng": -122.681},
        )
        client.put("/drivers/presence", headers=_headers(driver_token), json={"state": "available"})
        client.post(f"/drivers/accept-ride/{ride_id}", headers=_headers(driver_token))
        invalid_start = client.post(f"/drivers/start-ride/{ride_id}", headers=_headers(driver_token))
        client.post(f"/drivers/arrive-pickup/{ride_id}", headers=_headers(driver_token))
        client.post(f"/drivers/start-ride/{ride_id}", headers=_headers(driver_token))
        client.post(f"/drivers/complete-ride/{ride_id}", headers=_headers(driver_token))
        cancel_completed = client.post(f"/rides/{ride_id}/cancel", headers=_headers(rider_token), json={})

    assert invalid_start.status_code == 409, invalid_start.text
    assert invalid_start.json()["detail"]["error"] == "invalid_state_transition"
    assert cancel_completed.status_code == 409, cancel_completed.text
    assert cancel_completed.json()["detail"]["error"] == "invalid_state_transition"


def test_invalid_action_returns_422_for_canonical_action_endpoint():
    _, rider_token = _create_user_token(UserRole.CUSTOMER)

    with TestClient(app) as client:
        ride_id = _create_requested_ride(client, rider_token)
        response = client.post(
            f"/rides/{ride_id}/action",
            headers=_headers(rider_token),
            json={"action": "teleport"},
        )

    assert response.status_code == 422, response.text


def test_lanes_remain_segregated_for_ride_lifecycle_routes():
    _, rider_token = _create_user_token(UserRole.CUSTOMER)
    _, driver_token = _create_user_token(UserRole.DRIVER, availability=DriverStatus.AVAILABLE)
    _, admin_token = _create_user_token(UserRole.ADMIN)

    with TestClient(app) as client:
        ride_id = _create_requested_ride(client, rider_token)
        rider_accept = client.post(f"/drivers/accept-ride/{ride_id}", headers=_headers(rider_token))
        driver_create = client.post("/rides/", headers=_headers(driver_token), json=_ride_payload())
        admin_accept = client.post(f"/drivers/accept-ride/{ride_id}", headers=_headers(admin_token))
        admin_create = client.post("/rides/", headers=_headers(admin_token), json=_ride_payload())

    assert rider_accept.status_code == 403, rider_accept.text
    assert driver_create.status_code == 403, driver_create.text
    assert admin_accept.status_code == 403, admin_accept.text
    assert admin_create.status_code == 403, admin_create.text


def test_swapped_lane_rejection_still_happens_before_route_db_dependency(monkeypatch):
    _, rider_token = _create_user_token(UserRole.CUSTOMER)

    def fail_session_local():
        raise AssertionError("RBAC must reject rider token before opening a DB session")

    def fail_get_db():
        raise AssertionError("Route DB dependency should not execute for forbidden lane")
        yield

    monkeypatch.setattr(rbac, "SessionLocal", fail_session_local)
    app.dependency_overrides[get_db] = fail_get_db
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/drivers/accept-ride/1", headers=_headers(rider_token))
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 403, response.text


def test_openapi_exposes_canonical_contract_schemas():
    schemas = app.openapi().get("components", {}).get("schemas", {})

    assert "RideCreateRequest" in schemas
    assert "RideActionRequest" in schemas
    assert "RideDriverView" in schemas
    assert "RiderRideResponse" in schemas
    assert "DriverStatusResponse" in schemas
    assert "NotificationResponse" in schemas
