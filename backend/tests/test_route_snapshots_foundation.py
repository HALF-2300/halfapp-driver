"""Route snapshots foundation — durable route evidence, honest fallback labeling."""

from __future__ import annotations

import json
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from database import SessionLocal, engine
from main import app
from models.route_snapshot import RouteSnapshot
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.lifecycle import DriverStatus
from services.route_snapshots import (
    create_route_snapshot,
    list_route_snapshots_for_ride,
    sanitize_provenance,
    stable_hash,
    validate_snapshot_role,
)
from services.routing_service import HAVERSINE_FALLBACK_PROVIDER, RouteEstimate
from services.datetime_utils import utc_now_naive


def _driver_token(db, prefix: str = "snap") -> str:
    uid = uuid.uuid4().hex[:8]
    user = create_user(
        db,
        f"{prefix}_{uid}@example.com",
        f"{prefix.title()} Driver",
        "pw12345",
        UserRole.DRIVER,
        f"DL{uid}",
        driver_approval_status="approved",
    )
    user.availability = DriverStatus.AVAILABLE.value
    db.commit()
    return create_access_token(sub=user.email, role=user.role.value)


def _rider_token(db, prefix: str = "snap_rider") -> str:
    uid = uuid.uuid4().hex[:8]
    user = create_user(
        db,
        f"{prefix}_{uid}@example.com",
        f"{prefix.title()} Rider",
        "pw12345",
        UserRole.CUSTOMER,
        None,
    )
    db.commit()
    return create_access_token(sub=user.email, role=user.role.value)


def test_migration_creates_route_snapshots_table():
    inspector = inspect(engine)
    assert "route_snapshots" in inspector.get_table_names()
    columns = {col["name"] for col in inspector.get_columns("route_snapshots")}
    assert {
        "id",
        "ride_id",
        "snapshot_role",
        "route_provider",
        "used_fallback",
        "distance_meters",
        "duration_seconds",
        "geometry_polyline",
        "geometry_hash",
        "request_hash",
        "response_hash",
        "provenance_json",
        "pricing_id",
        "created_at",
    }.issubset(columns)


def test_validate_snapshot_role_rejects_unknown():
    with pytest.raises(ValueError, match="Unknown snapshot_role"):
        validate_snapshot_role("invalid")


def test_stable_hash_is_deterministic_for_same_payload():
    payload = {"route_provider": "haversine_fallback", "used_fallback": True, "distance_meters": 1200}
    assert stable_hash(payload) == stable_hash(dict(payload))


def test_sanitize_provenance_strips_secrets():
    cleaned = sanitize_provenance(
        {
            "api_key": "super-secret",
            "source": "test",
            "nested": {"authorization": "Bearer x", "ok": True},
            "url": "http://127.0.0.1:5000/route?token=abc",
        }
    )
    assert "api_key" not in cleaned
    assert cleaned["source"] == "test"
    assert "authorization" not in cleaned["nested"]
    assert cleaned["nested"]["ok"] is True
    assert cleaned["url"] == "<redacted>"


def test_create_route_snapshot_records_haversine_fallback_honestly():
    db = SessionLocal()
    try:
        from models.ride import Ride

        ride = Ride(
            customer_name="Snapshot Rider",
            status="requested",
            pickup_latitude=45.5,
            pickup_longitude=-122.6,
            dropoff_latitude=45.55,
            dropoff_longitude=-122.55,
        )
        db.add(ride)
        db.flush()
        estimate = RouteEstimate(
            distance_km=3.2,
            duration_minutes=8,
            route_provider=HAVERSINE_FALLBACK_PROVIDER,
            traffic_provider="none",
            traffic_aware=False,
            traffic_signal_aware=False,
            route_confidence="low",
            route_calculated_at=utc_now_naive(),
            used_fallback=True,
        )
        row = create_route_snapshot(
            db,
            ride=ride,
            route_result=estimate,
            snapshot_role="quote",
            provenance={"source": "unit_test"},
            origin=(45.5, -122.6),
            destination=(45.55, -122.55),
        )
        db.commit()
        assert row.route_provider == HAVERSINE_FALLBACK_PROVIDER
        assert row.used_fallback is True
        assert row.distance_meters == 3200
        assert row.duration_seconds == 480
        assert row.request_hash
        assert row.response_hash
        stored = json.loads(row.provenance_json or "{}")
        assert "api_key" not in stored
    finally:
        db.close()


def test_quote_creates_route_snapshot_on_rider_create():
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
                "pickup_location": "Quote Pickup",
                "dropoff_location": "Quote Dropoff",
                "pickup_latitude": 45.501,
                "pickup_longitude": -122.681,
                "dropoff_latitude": 45.551,
                "dropoff_longitude": -122.611,
            },
        )
        assert created.status_code == 200, created.text
        ride_id = created.json()["ride"]["id"]

        client.put(
            "/drivers/presence",
            headers={"Authorization": f"Bearer {driver_token}"},
            json={"state": "available"},
        )
        client.post("/drivers/heartbeat", headers={"Authorization": f"Bearer {driver_token}"})
        client.get("/drivers/available-rides", headers={"Authorization": f"Bearer {driver_token}"})

        snapshots = client.get(
            f"/drivers/rides/{ride_id}/route-snapshots",
            headers={"Authorization": f"Bearer {driver_token}"},
        )
        assert snapshots.status_code == 200, snapshots.text
        body = snapshots.json()
        assert body["ride_id"] == ride_id
        assert len(body["snapshots"]) >= 1
        quote = body["snapshots"][0]
        assert quote["snapshot_role"] == "quote"
        assert quote["route_provider"]
        assert "used_fallback" in quote
        assert quote["distance_meters"] >= 0
        assert quote["duration_seconds"] >= 0
        assert quote["pricing_id"] == ride_id
        assert quote["request_hash"]
        assert quote["response_hash"]
        assert "provenance_json" not in quote


def test_completion_creates_complete_snapshot():
    db = SessionLocal()
    try:
        rider_token = _rider_token(db, "complete_rider")
        driver_token = _driver_token(db, "complete_drv")
    finally:
        db.close()

    with TestClient(app) as client:
        created = client.post(
            "/rides/",
            headers={"Authorization": f"Bearer {rider_token}"},
            json={
                "pickup_location": "Complete Pickup",
                "dropoff_location": "Complete Dropoff",
                "pickup_latitude": 45.501,
                "pickup_longitude": -122.681,
                "dropoff_latitude": 45.551,
                "dropoff_longitude": -122.611,
            },
        )
        assert created.status_code == 200, created.text
        ride_id = created.json()["ride"]["id"]
        headers = {"Authorization": f"Bearer {driver_token}"}
        client.put("/drivers/presence", headers=headers, json={"state": "available"})
        client.post(f"/drivers/accept-ride/{ride_id}", headers=headers)
        client.post(f"/drivers/arrive-pickup/{ride_id}", headers=headers)
        client.post(f"/drivers/start-ride/{ride_id}", headers=headers)
        done = client.post(f"/drivers/complete-ride/{ride_id}", headers=headers)
        assert done.status_code == 200, done.text

        snapshots = client.get(f"/drivers/rides/{ride_id}/route-snapshots", headers=headers)
        assert snapshots.status_code == 200
        roles = [item["snapshot_role"] for item in snapshots.json()["snapshots"]]
        assert "quote" in roles
        assert "complete" in roles
        complete = next(item for item in snapshots.json()["snapshots"] if item["snapshot_role"] == "complete")
        assert complete["pricing_id"] == ride_id


def test_route_snapshots_endpoint_requires_auth():
    with TestClient(app) as client:
        response = client.get("/drivers/rides/1/route-snapshots")
        assert response.status_code == 401


def test_unrelated_driver_cannot_read_inaccessible_snapshots():
    db = SessionLocal()
    try:
        rider_token = _rider_token(db, "iso_rider")
        driver_a = _driver_token(db, "iso_a")
        driver_b = _driver_token(db, "iso_b")
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
        assert created.status_code == 200, created.text
        ride_id = created.json()["ride"]["id"]
        blocked = client.get(
            f"/drivers/rides/{ride_id}/route-snapshots",
            headers={"Authorization": f"Bearer {driver_b}"},
        )
        assert blocked.status_code == 403

        client.put(
            "/drivers/presence",
            headers={"Authorization": f"Bearer {driver_a}"},
            json={"state": "available"},
        )
        client.get(
            "/drivers/available-rides",
            headers={"Authorization": f"Bearer {driver_a}"},
        )
        allowed = client.get(
            f"/drivers/rides/{ride_id}/route-snapshots",
            headers={"Authorization": f"Bearer {driver_a}"},
        )
        assert allowed.status_code == 200


def test_list_route_snapshots_ordered():
    db = SessionLocal()
    try:
        from models.ride import Ride

        ride = Ride(customer_name="Order", status="requested", distance=1.0, duration=5)
        db.add(ride)
        db.flush()
        estimate = RouteEstimate(
            distance_km=1.0,
            duration_minutes=5,
            route_provider=HAVERSINE_FALLBACK_PROVIDER,
            traffic_provider="none",
            traffic_aware=False,
            traffic_signal_aware=False,
            route_confidence="low",
            route_calculated_at=utc_now_naive(),
            used_fallback=True,
        )
        create_route_snapshot(db, ride=ride, route_result=estimate, snapshot_role="quote")
        create_route_snapshot(db, ride=ride, route_result=None, snapshot_role="complete")
        db.commit()
        rows = list_route_snapshots_for_ride(db, ride_id=ride.id)
        assert [row.snapshot_role for row in rows] == ["quote", "complete"]
    finally:
        db.close()
