"""GO/NO_GO tests for dossier dispatch + double-entry ledger slice."""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from database import SessionLocal, engine
from main import app  # noqa: F401


def _heartbeat(client: TestClient, driver_id: str, lat: float = 45.501, lng: float = -122.681):
    return client.post(
        "/supply/heartbeat",
        json={
            "driver_id": driver_id,
            "latitude": lat,
            "longitude": lng,
            "velocity_mps": 8.0,
            "vehicle_type": "standard",
        },
    )


def test_supply_heartbeat_persists_active_driver():
    driver_id = f"driver_{uuid.uuid4().hex[:8]}"
    with TestClient(app) as client:
        response = _heartbeat(client, driver_id)
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "HEARTBEAT_ACCEPTED"

    db = SessionLocal()
    try:
        row = db.execute(
            text("SELECT status, latitude, longitude FROM active_drivers WHERE id = :id"),
            {"id": driver_id},
        ).one()
        assert row[0] == "AVAILABLE"
        assert row[1] is not None
        assert row[2] is not None
    finally:
        db.close()


def test_demand_request_matches_nearest_available_driver():
    # Isolated coordinates so other tests' active_drivers do not win the match.
    driver_near = f"driver_near_{uuid.uuid4().hex[:6]}"
    driver_far = f"driver_far_{uuid.uuid4().hex[:6]}"
    rider_id = f"rider_{uuid.uuid4().hex[:6]}"
    key = f"idem_{uuid.uuid4().hex}"
    pickup_lat, pickup_lng = 64.842, -147.720

    with TestClient(app) as client:
        assert _heartbeat(client, driver_near, 64.841, -147.721).status_code == 200
        assert _heartbeat(client, driver_far, 64.950, -147.500).status_code == 200

        response = client.post(
            "/demand/request",
            json={
                "rider_id": rider_id,
                "pickup_latitude": pickup_lat,
                "pickup_longitude": pickup_lng,
                "vehicle_type": "standard",
                "idempotency_key": key,
            },
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "DRIVER_EN_ROUTE"
        assert body["current_state"] == "DRIVER_EN_ROUTE"
        assert body["driver_id"] == driver_near
        assert "CANCEL" in body["allowed_actions"]
        trip_id = body["trip_id"]

    db = SessionLocal()
    try:
        dispatched = db.execute(
            text("SELECT status, assigned_trip_id FROM active_drivers WHERE id = :id"),
            {"id": driver_near},
        ).one()
        assert dispatched[0] == "DISPATCHED"
        assert dispatched[1] == trip_id

        events = db.execute(
            text(
                """
                SELECT to_state, trigger_event
                FROM trip_lifecycle_events
                WHERE trip_id = :trip_id
                ORDER BY id ASC
                """
            ),
            {"trip_id": trip_id},
        ).fetchall()
        assert [row[0] for row in events] == ["MATCHING", "DRIVER_EN_ROUTE"]
    finally:
        db.close()


def test_demand_request_returns_no_drivers_without_rollback_of_intent():
    rider_id = f"rider_{uuid.uuid4().hex[:6]}"
    key = f"idem_{uuid.uuid4().hex}"

    with TestClient(app) as client:
        response = client.post(
            "/demand/request",
            json={
                "rider_id": rider_id,
                "pickup_latitude": 40.0,
                "pickup_longitude": -74.0,
                "vehicle_type": "standard",
                "idempotency_key": key,
            },
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "NO_DRIVERS_AVAILABLE"
        assert body["current_state"] == "MATCHING"
        trip_id = body["trip_id"]

    db = SessionLocal()
    try:
        count = db.execute(
            text("SELECT COUNT(*) FROM trip_lifecycle_events WHERE trip_id = :trip_id"),
            {"trip_id": trip_id},
        ).scalar()
        assert count == 1
    finally:
        db.close()


def test_trip_complete_writes_balanced_ledger_and_completes_fsm():
    driver_id = f"driver_{uuid.uuid4().hex[:8]}"
    rider_id = f"rider_{uuid.uuid4().hex[:8]}"
    demand_key = f"demand_{uuid.uuid4().hex}"
    complete_key = f"complete_{uuid.uuid4().hex}"

    with TestClient(app) as client:
        assert _heartbeat(client, driver_id).status_code == 200
        demand = client.post(
            "/demand/request",
            json={
                "rider_id": rider_id,
                "pickup_latitude": 45.502,
                "pickup_longitude": -122.680,
                "vehicle_type": "standard",
                "idempotency_key": demand_key,
            },
        )
        assert demand.status_code == 200, demand.text
        trip_id = demand.json()["trip_id"]

        complete = client.post(
            "/trip/complete",
            json={
                "trip_id": trip_id,
                "idempotency_key": complete_key,
                "fare_cents": 5000,
                "driver_share_cents": 4000,
                "processing_fee_cents": 50,
                "platform_share_cents": 950,
            },
        )
        assert complete.status_code == 200, complete.text
        assert complete.json()["current_state"] == "TRIP_COMPLETED"

    db = SessionLocal()
    try:
        debits, credits = db.execute(
            text(
                """
                SELECT
                    COALESCE(SUM(CASE WHEN direction = 'DEBIT' THEN amount_cents ELSE 0 END), 0),
                    COALESCE(SUM(CASE WHEN direction = 'CREDIT' THEN amount_cents ELSE 0 END), 0)
                FROM ledger_entries le
                JOIN ledger_transactions lt ON lt.id = le.transaction_id
                WHERE lt.reference_key = :reference_key
                """
            ),
            {"reference_key": complete_key},
        ).one()
        assert debits == credits == 5000

        driver_available = db.execute(
            text("SELECT status FROM active_drivers WHERE id = :id"),
            {"id": driver_id},
        ).scalar()
        assert driver_available == "AVAILABLE"
    finally:
        db.close()


def test_trip_complete_rejects_unbalanced_split():
    driver_id = f"driver_{uuid.uuid4().hex[:8]}"
    with TestClient(app) as client:
        assert _heartbeat(client, driver_id).status_code == 200
        demand = client.post(
            "/demand/request",
            json={
                "rider_id": "rider_x",
                "pickup_latitude": 45.502,
                "pickup_longitude": -122.680,
                "vehicle_type": "standard",
                "idempotency_key": f"demand_{uuid.uuid4().hex}",
            },
        )
        trip_id = demand.json()["trip_id"]
        bad = client.post(
            "/trip/complete",
            json={
                "trip_id": trip_id,
                "idempotency_key": f"bad_{uuid.uuid4().hex}",
                "fare_cents": 5000,
                "driver_share_cents": 4000,
                "processing_fee_cents": 50,
                "platform_share_cents": 900,
            },
        )
        assert bad.status_code == 422


def test_ledger_entries_and_trip_events_are_append_only():
    driver_id = f"driver_{uuid.uuid4().hex[:8]}"
    complete_key = f"complete_{uuid.uuid4().hex}"

    with TestClient(app) as client:
        assert _heartbeat(client, driver_id, 21.306, -157.858).status_code == 200
        demand = client.post(
            "/demand/request",
            json={
                "rider_id": "rider_append",
                "pickup_latitude": 21.307,
                "pickup_longitude": -157.857,
                "vehicle_type": "standard",
                "idempotency_key": f"demand_{uuid.uuid4().hex}",
            },
        )
        assert demand.status_code == 200, demand.text
        trip_id = demand.json()["trip_id"]
        complete = client.post(
            "/trip/complete",
            json={
                "trip_id": trip_id,
                "idempotency_key": complete_key,
                "fare_cents": 1000,
                "driver_share_cents": 800,
                "processing_fee_cents": 10,
                "platform_share_cents": 190,
            },
        )
        assert complete.status_code == 200, complete.text

    db = SessionLocal()
    try:
        event_id = db.execute(
            text("SELECT id FROM trip_lifecycle_events WHERE trip_id = :trip_id LIMIT 1"),
            {"trip_id": trip_id},
        ).scalar()
        entry_id = db.execute(
            text(
                """
                SELECT le.id FROM ledger_entries le
                JOIN ledger_transactions lt ON lt.id = le.transaction_id
                WHERE lt.reference_key = :reference_key
                LIMIT 1
                """
            ),
            {"reference_key": complete_key},
        ).scalar()
        assert entry_id is not None
    finally:
        db.close()

    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.exec_driver_sql(
                "UPDATE trip_lifecycle_events SET to_state = 'MUTATED' WHERE id = ?",
                (event_id,),
            )

    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.exec_driver_sql("DELETE FROM ledger_entries WHERE id = ?", (entry_id,))


def test_alembic_head_includes_dossier_foundation():
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from pathlib import Path

    cfg = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
    expected_head = ScriptDirectory.from_config(cfg).get_current_head()

    with engine.connect() as conn:
        version = conn.exec_driver_sql("SELECT version_num FROM alembic_version").scalar()
    assert version == expected_head
