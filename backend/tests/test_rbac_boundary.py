from fastapi.testclient import TestClient

from database import get_db
from main import app
from models.user import UserRole
from services.auth import create_access_token


def _sentinel_db():
    raise AssertionError("RBAC boundary allowed a database dependency to run")
    yield


def test_rider_token_cannot_enter_driver_lane_before_db():
    app.dependency_overrides[get_db] = _sentinel_db
    try:
        token = create_access_token(sub="rider-token@example.com", role=UserRole.CUSTOMER.value)
        with TestClient(app) as client:
            response = client.post(
                "/drivers/accept-ride/1",
                headers={"Authorization": f"Bearer {token}"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"]["error"] == "forbidden"
    assert "driver" in response.json()["detail"]["message"].lower()


def test_driver_token_cannot_enter_rider_lane_before_db():
    app.dependency_overrides[get_db] = _sentinel_db
    try:
        token = create_access_token(sub="driver-token@example.com", role=UserRole.DRIVER.value)
        with TestClient(app) as client:
            response = client.post(
                "/rides/",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "pickup_location": "Origin",
                    "dropoff_location": "Destination",
                    "pickup_latitude": 45.501,
                    "pickup_longitude": -122.681,
                    "dropoff_latitude": 45.551,
                    "dropoff_longitude": -122.611,
                    "distance_km": 3.5,
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"]["error"] == "forbidden"
    assert "rider" in response.json()["detail"]["message"].lower()
