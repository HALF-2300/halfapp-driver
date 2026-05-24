"""HALFAPP_ROUTE_SNAPSHOT_READ_UI_01 — driver route snapshot read API."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.lifecycle import DriverStatus
from services.route_snapshots_read import OSRM_RUNTIME_CLAIM, PRODUCTION_ROUTING_CLAIM
from services.routing_service import HAVERSINE_FALLBACK_PROVIDER


def _driver_token(db, prefix: str = "rsnap") -> str:
    uid = uuid.uuid4().hex[:8]
    user = create_user(
        db,
        f"{prefix}_{uid}@example.com",
        f"{prefix} Driver",
        "pw12345",
        UserRole.DRIVER,
        f"DL{uid}",
        driver_approval_status="approved",
    )
    user.availability = DriverStatus.AVAILABLE.value
    db.commit()
    return create_access_token(sub=user.email, role=user.role.value)


def _rider_token(db, prefix: str = "rsnap_r") -> str:
    uid = uuid.uuid4().hex[:8]
    user = create_user(
        db,
        f"{prefix}_{uid}@example.com",
        f"{prefix} Rider",
        "pw12345",
        UserRole.CUSTOMER,
    )
    db.commit()
    return create_access_token(sub=user.email, role=user.role.value)


def _accept_and_complete(client: TestClient, ride_id: int, driver_token: str) -> None:
    headers = {"Authorization": f"Bearer {driver_token}"}
    client.put("/drivers/presence", headers=headers, json={"state": "available"})
    client.post(f"/drivers/accept-ride/{ride_id}", headers=headers)
    client.post(f"/drivers/arrive-pickup/{ride_id}", headers=headers)
    client.post(f"/drivers/start-ride/{ride_id}", headers=headers)
    client.post(f"/drivers/complete-ride/{ride_id}", headers=headers)


def test_driver_reads_route_snapshots_for_own_completed_ride():
    db = SessionLocal()
    try:
        rider_token = _rider_token(db)
        driver_token = _driver_token(db)
    finally:
        db.close()

    with TestClient(app) as client:
        created = client.post(
            "/rides/",
            headers={"Authorization": f"Bearer {rider_token}"},
            json={
                "pickup_location": "Snap Pickup",
                "dropoff_location": "Snap Dropoff",
                "pickup_latitude": 45.501,
                "pickup_longitude": -122.681,
                "dropoff_latitude": 45.551,
                "dropoff_longitude": -122.611,
            },
        )
        assert created.status_code == 200, created.text
        ride_id = created.json()["ride"]["id"]
        headers = {"Authorization": f"Bearer {driver_token}"}
        _accept_and_complete(client, ride_id, driver_token)

        res = client.get(f"/drivers/rides/{ride_id}/route-snapshots", headers=headers)
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["ride_id"] == ride_id
        assert body["route_truth"]["osrm_runtime_claim"] == OSRM_RUNTIME_CLAIM
        assert body["route_truth"]["production_routing_claim"] == PRODUCTION_ROUTING_CLAIM
        assert "used_fallback" in body["route_truth"]
        assert body["copy"]["osrm_status"] == "OSRM runtime not proved"
        assert len(body["snapshots"]) >= 1
        snap = body["snapshots"][0]
        assert snap["id"] is not None
        assert snap["snapshot_role"] in {"quote", "complete", "accept", "refresh", "diagnostic"}
        assert snap["distance_meters"] >= 0
        assert snap["duration_seconds"] >= 0


def test_driver_cannot_read_another_drivers_route_snapshots():
    db = SessionLocal()
    try:
        rider_token = _rider_token(db, "rsnap2_r")
        driver_a = _driver_token(db, "rsnap2_a")
        driver_b = _driver_token(db, "rsnap2_b")
    finally:
        db.close()

    with TestClient(app) as client:
        created = client.post(
            "/rides/",
            headers={"Authorization": f"Bearer {rider_token}"},
            json={
                "pickup_location": "Iso Pickup",
                "dropoff_location": "Iso Dropoff",
                "pickup_latitude": 45.501,
                "pickup_longitude": -122.681,
                "dropoff_latitude": 45.551,
                "dropoff_longitude": -122.611,
            },
        )
        ride_id = created.json()["ride"]["id"]
        _accept_and_complete(client, ride_id, driver_a)
        blocked = client.get(
            f"/drivers/rides/{ride_id}/route-snapshots",
            headers={"Authorization": f"Bearer {driver_b}"},
        )
        assert blocked.status_code == 403


def test_fallback_status_returned_honestly():
    db = SessionLocal()
    try:
        rider_token = _rider_token(db, "rsnap3_r")
        driver_token = _driver_token(db, "rsnap3_d")
    finally:
        db.close()

    with TestClient(app) as client:
        created = client.post(
            "/rides/",
            headers={"Authorization": f"Bearer {rider_token}"},
            json={
                "pickup_location": "Fallback Pickup",
                "dropoff_location": "Fallback Dropoff",
                "pickup_latitude": 45.501,
                "pickup_longitude": -122.681,
                "dropoff_latitude": 45.551,
                "dropoff_longitude": -122.611,
            },
        )
        ride_id = created.json()["ride"]["id"]
        headers = {"Authorization": f"Bearer {driver_token}"}
        client.put("/drivers/presence", headers=headers, json={"state": "available"})
        client.get("/drivers/available-rides", headers=headers)
        body = client.get(f"/drivers/rides/{ride_id}/route-snapshots", headers=headers).json()
        assert body["route_truth"]["used_fallback"] is True
        assert body["route_truth"]["current_provider"] == HAVERSINE_FALLBACK_PROVIDER
        assert body["copy"]["routing_label"] == "Straight-line estimate"
        assert body["copy"]["estimate_note"]


def test_route_snapshots_endpoint_is_read_only_get():
    with TestClient(app) as client:
        assert client.post("/drivers/rides/1/route-snapshots").status_code == 405
        assert client.put("/drivers/rides/1/route-snapshots").status_code == 405
