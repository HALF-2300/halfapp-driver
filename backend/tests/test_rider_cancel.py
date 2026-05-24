"""
Rider-side cancel — allowed states, forbidden states, ownership, and
driver-side visibility per docs/RIDE_LIFECYCLE_CONTRACT.md.
"""

import uuid

from database import SessionLocal  # noqa: F401
import models.user  # noqa: F401
import models.ride  # noqa: F401
import routes.notifications  # noqa: F401

from fastapi.testclient import TestClient
from main import app
from models.ride import Ride
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.lifecycle import DriverStatus, RideStatus


def _customer(db):
    uid = uuid.uuid4().hex[:10]
    u = create_user(db, f"rider_{uid}@example.com", "Rider", "pw12345", UserRole.CUSTOMER, None)
    return u, create_access_token(sub=u.email, role=u.role.value)


def _driver(db):
    uid = uuid.uuid4().hex[:10]
    u = create_user(
        db,
        f"drv_{uid}@example.com",
        "Drv",
        "pw12345",
        UserRole.DRIVER,
        f"DLC{uid}",
        driver_approval_status="approved",
    )
    u.availability = DriverStatus.AVAILABLE.value
    db.commit()
    return u, create_access_token(sub=u.email, role=u.role.value)


def _create_ride(client, customer_token: str) -> dict:
    r = client.post(
        "/rides/",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={
            "pickup_location": "Origin",
            "dropoff_location": "Dest",
            "pickup_latitude": 45.501,
            "pickup_longitude": -122.681,
            "dropoff_latitude": 45.551,
            "dropoff_longitude": -122.611,
            "distance_km": 3.5,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ride"]["pickup_latitude"] == 45.501
    assert body["ride"]["dropoff_longitude"] == -122.611
    return body


def test_rider_create_and_cancel_from_requested():
    db = SessionLocal()
    try:
        _, customer_token = _customer(db)
    finally:
        db.close()

    with TestClient(app) as client:
        created = _create_ride(client, customer_token)
        rid = created["ride"]["id"]
        assert created["ride"]["status"] == "requested"

        r = client.post(
            f"/rides/{rid}/cancel",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={"reason": "changed my mind"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ride"]["status"] == "cancelled"
        assert body["ride"]["cancelled_at"] is not None
        assert body["ride"]["lifecycle_reason"] == "changed my mind"


def test_rider_create_requires_coordinates():
    db = SessionLocal()
    try:
        _, customer_token = _customer(db)
    finally:
        db.close()

    with TestClient(app) as client:
        r = client.post(
            "/rides/",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={"pickup_location": "Origin", "destination": "Dest", "distance_km": 3.5},
        )
        assert r.status_code == 422


def test_rider_cancel_after_driver_accept_preserves_driver_visibility():
    db = SessionLocal()
    try:
        _, customer_token = _customer(db)
        _, driver_token = _driver(db)
    finally:
        db.close()

    with TestClient(app) as client:
        created = _create_ride(client, customer_token)
        rid = created["ride"]["id"]

        r = client.post(
            f"/drivers/accept-ride/{rid}",
            headers={"Authorization": f"Bearer {driver_token}"},
        )
        assert r.status_code == 200

        r = client.post(
            f"/rides/{rid}/cancel",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={},
        )
        assert r.status_code == 200
        cancelled = r.json()["ride"]
        assert cancelled["status"] == "cancelled"

        r = client.get("/drivers/my-rides", headers={"Authorization": f"Bearer {driver_token}"})
        assert r.status_code == 200
        statuses = {ride["id"]: ride["status"] for ride in r.json()}
        assert statuses.get(rid) == "cancelled"

        r = client.get(
            "/drivers/available-rides", headers={"Authorization": f"Bearer {driver_token}"}
        )
        assert r.status_code == 200
        ids = [ride["id"] for ride in r.json()]
        assert rid not in ids


def test_rider_can_cancel_in_progress_before_completed():
    db = SessionLocal()
    try:
        _, customer_token = _customer(db)
        _, driver_token = _driver(db)
    finally:
        db.close()

    with TestClient(app) as client:
        created = _create_ride(client, customer_token)
        rid = created["ride"]["id"]

        client.post(
            f"/drivers/accept-ride/{rid}", headers={"Authorization": f"Bearer {driver_token}"}
        )
        client.post(
            f"/drivers/arrive-pickup/{rid}", headers={"Authorization": f"Bearer {driver_token}"}
        )
        client.post(
            f"/drivers/start-ride/{rid}", headers={"Authorization": f"Bearer {driver_token}"}
        )

        r = client.post(
            f"/rides/{rid}/cancel",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={},
        )
        assert r.status_code == 200
        assert r.json()["ride"]["status"] == RideStatus.CANCELLED.value


def test_rider_cannot_cancel_someone_elses_ride():
    db = SessionLocal()
    try:
        _, customer_a_token = _customer(db)
        _, customer_b_token = _customer(db)
    finally:
        db.close()

    with TestClient(app) as client:
        created = _create_ride(client, customer_a_token)
        rid = created["ride"]["id"]

        r = client.post(
            f"/rides/{rid}/cancel",
            headers={"Authorization": f"Bearer {customer_b_token}"},
            json={},
        )
        assert r.status_code == 403


def test_driver_cannot_complete_a_cancelled_ride():
    db = SessionLocal()
    try:
        _, customer_token = _customer(db)
        _, driver_token = _driver(db)
    finally:
        db.close()

    with TestClient(app) as client:
        created = _create_ride(client, customer_token)
        rid = created["ride"]["id"]
        client.post(
            f"/drivers/accept-ride/{rid}", headers={"Authorization": f"Bearer {driver_token}"}
        )
        client.post(
            f"/rides/{rid}/cancel",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={},
        )

        for endpoint in (
            f"/drivers/arrive-pickup/{rid}",
            f"/drivers/start-ride/{rid}",
            f"/drivers/complete-ride/{rid}",
            f"/drivers/decline-ride/{rid}",
        ):
            r = client.post(endpoint, headers={"Authorization": f"Bearer {driver_token}"})
            assert r.status_code == 409, f"{endpoint} unexpectedly returned {r.status_code}"


def test_openapi_exposes_rider_paths_and_schemas():
    spec = app.openapi()
    paths = spec.get("paths", {})
    assert "/rides/" in paths
    assert "/rides/{ride_id}/cancel" in paths
    names = spec.get("components", {}).get("schemas", {})
    assert "RiderRideCreate" in names
    assert "RiderRideResponse" in names
    assert "RiderCancelBody" in names
