"""Driver read-only ride audit endpoint (HALFAPP_DRIVER_AUDIT_READ_UI_01)."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models.ledger import MarketplaceLedgerEvent
from models.settlement_entry import ENTRY_TYPE_DRIVER_PAYOUT
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.ledger import MarketplaceLedgerEventType
from services.lifecycle import DriverStatus
from services.ride_settlement import generate_settlement_entries


def _driver_token(db, prefix: str = "audit") -> str:
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


def _rider_token(db, prefix: str = "audit_r") -> str:
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


def _complete_ride_flow(client: TestClient, rider_token: str, driver_token: str) -> int:
    created = client.post(
        "/rides/",
        headers={"Authorization": f"Bearer {rider_token}"},
        json={
            "pickup_location": "Audit Pickup",
            "dropoff_location": "Audit Dropoff",
            "pickup_latitude": 45.501,
            "pickup_longitude": -122.681,
            "dropoff_latitude": 45.551,
            "dropoff_longitude": -122.611,
            "distance_km": 3.0,
        },
    )
    assert created.status_code == 200, created.text
    ride_id = created.json()["ride"]["id"]
    headers = {"Authorization": f"Bearer {driver_token}"}
    client.put("/drivers/presence", headers=headers, json={"state": "available"})
    client.post(f"/drivers/accept-ride/{ride_id}", headers=headers)
    client.post(f"/drivers/arrive-pickup/{ride_id}", headers=headers)
    client.post(f"/drivers/start-ride/{ride_id}", headers=headers)
    done = client.post(
        f"/drivers/complete-ride/{ride_id}",
        headers=headers,
        json={"tip_cents": 300, "toll_cents": 100},
    )
    assert done.status_code == 200, done.text
    return ride_id


def test_driver_can_read_audit_for_completed_ride():
    db = SessionLocal()
    try:
        rider_token = _rider_token(db)
        driver_token = _driver_token(db)
    finally:
        db.close()

    with TestClient(app) as client:
        ride_id = _complete_ride_flow(client, rider_token, driver_token)
        headers = {"Authorization": f"Bearer {driver_token}"}
        res = client.get(f"/drivers/rides/{ride_id}/audit", headers=headers)
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["ride_id"] == ride_id
        assert body["status"] == "completed"
        assert body["financial_locked"] is True
        assert body["copy"]["payment_execution"] == "not_implemented"
        label = body["copy"]["driver_payment_label"].lower()
        assert "obligation" in label
        assert "does not mean payout" in label
        assert body["pricing"]["platform_service_fee_cents"] == 150
        assert body["pricing"]["tip_cents"] == 300
        assert any(e["entry_type"] == ENTRY_TYPE_DRIVER_PAYOUT for e in body["settlement_entries"])
        event_types = {e["event_type"] for e in body["ledger_events"]}
        assert MarketplaceLedgerEventType.RIDE_COMPLETED.value in event_types
        assert MarketplaceLedgerEventType.EARNING_CALCULATED.value in event_types
        assert body["route_truth"]["osrm_runtime_claim"] == "not_proved"
        assert body["lifecycle"]["completed_at"] is not None
        assert len(body["lifecycle_events"]) >= 1
        assert any(e["event_type"] == "ride.completed" for e in body["lifecycle_events"])


def test_driver_cannot_read_another_drivers_ride_audit():
    db = SessionLocal()
    try:
        rider_token = _rider_token(db, "audit2_r")
        driver_a = _driver_token(db, "audit2_a")
        driver_b = _driver_token(db, "audit2_b")
    finally:
        db.close()

    with TestClient(app) as client:
        ride_id = _complete_ride_flow(client, rider_token, driver_a)
        blocked = client.get(
            f"/drivers/rides/{ride_id}/audit",
            headers={"Authorization": f"Bearer {driver_b}"},
        )
        assert blocked.status_code == 403


def test_audit_endpoint_is_read_only():
    db = SessionLocal()
    try:
        rider_token = _rider_token(db, "audit3_r")
        driver_token = _driver_token(db, "audit3_d")
    finally:
        db.close()

    with TestClient(app) as client:
        ride_id = _complete_ride_flow(client, rider_token, driver_token)
        headers = {"Authorization": f"Bearer {driver_token}"}
        before = client.get(f"/drivers/rides/{ride_id}/audit", headers=headers).json()
        count_before = len(before["settlement_entries"])
        ledger_before = len(before["ledger_events"])
        db2 = SessionLocal()
        try:
            generate_settlement_entries(db2, ride_id=ride_id)
        finally:
            db2.close()
        after = client.get(f"/drivers/rides/{ride_id}/audit", headers=headers).json()
        assert len(after["settlement_entries"]) == count_before
        assert len(after["ledger_events"]) == ledger_before
