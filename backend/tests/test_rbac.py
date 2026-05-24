import uuid

from fastapi.testclient import TestClient

import services.rbac as rbac
from database import SessionLocal, get_db
from main import app
from models.ride import Ride
from models.user import UserRole
from services.auth import create_access_token, create_user


def _token_for(role: UserRole) -> str:
    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:10]
        license_no = f"RBAC{uid}" if role == UserRole.DRIVER else None
        kwargs = {}
        if role == UserRole.DRIVER:
            kwargs["driver_approval_status"] = "approved"
        user = create_user(
            db,
            f"rbac_{role.value}_{uid}@example.com",
            f"RBAC {role.value}",
            "pw12345",
            role,
            license_no,
            **kwargs,
        )
        return create_access_token(user=user)
    finally:
        db.close()


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_driver_lane_rejects_rider_and_admin_tokens():
    driver_token = _token_for(UserRole.DRIVER)
    rider_token = _token_for(UserRole.CUSTOMER)
    admin_token = _token_for(UserRole.ADMIN)

    with TestClient(app) as client:
        allowed = client.get("/drivers/available-rides", headers=_headers(driver_token))
        rider_blocked = client.get("/drivers/available-rides", headers=_headers(rider_token))
        admin_blocked = client.get("/drivers/available-rides", headers=_headers(admin_token))

    assert allowed.status_code == 200, allowed.text
    assert rider_blocked.status_code == 403, rider_blocked.text
    assert admin_blocked.status_code == 403, admin_blocked.text


def test_rider_lane_rejects_driver_and_admin_tokens():
    rider_token = _token_for(UserRole.CUSTOMER)
    driver_token = _token_for(UserRole.DRIVER)
    admin_token = _token_for(UserRole.ADMIN)
    payload = {
        "pickup_location": "Origin",
        "dropoff_location": "Dest",
        "pickup_latitude": 45.501,
        "pickup_longitude": -122.681,
        "dropoff_latitude": 45.551,
        "dropoff_longitude": -122.611,
        "distance_km": 3.5,
    }

    with TestClient(app) as client:
        allowed = client.post("/rides/", headers=_headers(rider_token), json=payload)
        driver_blocked = client.post("/rides/", headers=_headers(driver_token), json=payload)
        admin_blocked = client.post("/rides/", headers=_headers(admin_token), json=payload)

    assert allowed.status_code == 200, allowed.text
    assert driver_blocked.status_code == 403, driver_blocked.text
    assert admin_blocked.status_code == 403, admin_blocked.text


def test_admin_lane_rejects_marketplace_participant_tokens():
    admin_token = _token_for(UserRole.ADMIN)
    driver_token = _token_for(UserRole.DRIVER)
    rider_token = _token_for(UserRole.CUSTOMER)

    with TestClient(app) as client:
        allowed = client.get("/internal/system-health", headers=_headers(admin_token))
        driver_blocked = client.get("/internal/system-health", headers=_headers(driver_token))
        rider_blocked = client.get("/internal/system-health", headers=_headers(rider_token))

    assert allowed.status_code == 200, allowed.text
    assert driver_blocked.status_code == 403, driver_blocked.text
    assert rider_blocked.status_code == 403, rider_blocked.text


def test_auth_boundary_returns_401_for_missing_or_invalid_tokens():
    from services.auth_errors import AUTH_ERROR_INVALID_TOKEN, AUTH_ERROR_UNAUTHENTICATED

    with TestClient(app) as client:
        missing = client.get("/drivers/my-rides")
        malformed = client.get("/drivers/my-rides", headers={"Authorization": "Bearer not-a-real-token"})

    assert missing.status_code == 401
    assert missing.json()["detail"]["error"] == AUTH_ERROR_UNAUTHENTICATED
    assert malformed.status_code == 401
    assert malformed.json()["detail"]["error"] == AUTH_ERROR_INVALID_TOKEN


def test_cross_lane_request_stops_before_business_database_dependencies(monkeypatch):
    rider_token = _token_for(UserRole.CUSTOMER)

    def fail_session_local():
        raise AssertionError("RBAC must reject rider token before opening a DB session")

    def fail_get_db():
        raise AssertionError("Route DB dependency should not execute for forbidden lane")
        yield

    monkeypatch.setattr(rbac, "SessionLocal", fail_session_local)
    app.dependency_overrides[get_db] = fail_get_db
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/drivers/available-rides", headers=_headers(rider_token))
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 403, response.text


def test_token_role_mismatch_is_forbidden():
    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:10]
        ride = Ride(customer_name="RBAC mismatch rider", status="requested", distance=1.0)
        user = create_user(
            db,
            f"rbac_mismatch_{uid}@example.com",
            "RBAC Mismatch",
            "pw12345",
            UserRole.CUSTOMER,
            None,
        )
        db.add(ride)
        db.commit()
        forged_lane_token = create_access_token(sub=user.email, role=UserRole.DRIVER.value)
        ride_id = ride.id
    finally:
        db.close()

    with TestClient(app) as client:
        response = client.post(f"/drivers/accept-ride/{ride_id}", headers=_headers(forged_lane_token))

    assert response.status_code == 403, response.text
