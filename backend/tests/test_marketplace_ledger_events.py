import json
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import DBAPIError

from database import SessionLocal, engine
from main import app
from models.ledger import MarketplaceLedgerEvent
from models.ride import Ride
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.ledger import MarketplaceLedgerEventType, append_marketplace_event
from services.lifecycle import DriverStatus


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _user(db, role: UserRole, prefix: str) -> tuple[str, int]:
    uid = uuid.uuid4().hex[:10]
    kwargs = {}
    if role == UserRole.DRIVER:
        kwargs["driver_approval_status"] = "approved"
    user = create_user(
        db,
        f"{prefix}_{uid}@example.com",
        f"{prefix} User",
        "pw12345",
        role,
        f"{prefix.upper()}{uid}" if role == UserRole.DRIVER else None,
        **kwargs,
    )
    if role == UserRole.DRIVER:
        user.availability = DriverStatus.AVAILABLE.value
    db.commit()
    return create_access_token(sub=user.email, role=user.role.value), user.id


def _create_rider_ride(client: TestClient, rider_token: str, pickup: str = "Ledger Pickup") -> int:
    response = client.post(
        "/rides/",
        headers=_headers(rider_token),
        json={
            "pickup_location": pickup,
            "dropoff_location": "Ledger Dropoff",
            "pickup_latitude": 45.501,
            "pickup_longitude": -122.681,
            "dropoff_latitude": 45.551,
            "dropoff_longitude": -122.611,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["ride"]["id"]


def test_marketplace_ledger_events_are_append_only_idempotent_and_hash_chained():
    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:10]
        driver = create_user(
            db,
            f"event_driver_{uid}@example.com",
            "Event Driver",
            "pw12345",
            UserRole.DRIVER,
            f"EVENT{uid}",
            driver_approval_status="approved",
        )
        ride = Ride(customer_name="Event Rider", status="requested", distance=1.0)
        db.add(ride)
        db.flush()

        first = append_marketplace_event(
            db,
            event_type=MarketplaceLedgerEventType.RIDE_CREATED,
            entity_type="ride",
            entity_id=ride.id,
            ride_id=ride.id,
            actor_id=driver.id,
            idempotency_key=f"ride-created:{ride.id}",
            correlation_id=f"corr-{uid}",
            payload={"source": "test"},
        )
        duplicate = append_marketplace_event(
            db,
            event_type=MarketplaceLedgerEventType.RIDE_CREATED,
            entity_type="ride",
            entity_id=ride.id,
            ride_id=ride.id,
            actor_id=driver.id,
            idempotency_key=f"ride-created:{ride.id}",
            correlation_id=f"corr-{uid}",
            payload={"source": "test"},
        )
        second = append_marketplace_event(
            db,
            event_type=MarketplaceLedgerEventType.RIDE_CANCELLED,
            entity_type="ride",
            entity_id=ride.id,
            ride_id=ride.id,
            actor_id=driver.id,
            payload={"reason": "test"},
        )
        ride_id = ride.id
        first_id = first.id
        duplicate_id = duplicate.id
        second_id = second.id
        db.commit()
    finally:
        db.close()

    assert duplicate_id == first_id

    db = SessionLocal()
    try:
        rows = db.query(MarketplaceLedgerEvent).filter(MarketplaceLedgerEvent.ride_id == ride_id).all()
        assert len(rows) == 2
        assert rows[1].id == second_id
        assert rows[1].previous_event_hash == rows[0].event_hash
        assert json.loads(rows[0].payload_json) == {"source": "test"}
    finally:
        db.close()

    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.exec_driver_sql(
                "UPDATE marketplace_ledger_events SET payload_json = '{}' WHERE id = ?",
                (first_id,),
            )

    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.exec_driver_sql("DELETE FROM marketplace_ledger_events WHERE id = ?", (first_id,))


def test_ride_lifecycle_writes_marketplace_ledger_events():
    db = SessionLocal()
    try:
        rider_token, _ = _user(db, UserRole.CUSTOMER, "ledger_rider")
        driver_token, driver_id = _user(db, UserRole.DRIVER, "ledger_driver")
    finally:
        db.close()

    with TestClient(app) as client:
        ride_id = _create_rider_ride(client, rider_token)

        visible = client.get("/drivers/available-rides", headers=_headers(driver_token))
        assert visible.status_code == 200, visible.text
        visible_ride = next(item for item in visible.json() if item["id"] == ride_id)
        assert visible_ride["visibility_correlation_id"]

        assert client.post(f"/drivers/accept-ride/{ride_id}", headers=_headers(driver_token)).status_code == 200
        assert client.post(f"/drivers/arrive-pickup/{ride_id}", headers=_headers(driver_token)).status_code == 200
        assert client.post(f"/drivers/start-ride/{ride_id}", headers=_headers(driver_token)).status_code == 200
        complete = client.post(f"/drivers/complete-ride/{ride_id}", headers=_headers(driver_token))
        assert complete.status_code == 200, complete.text

    db = SessionLocal()
    try:
        rows = (
            db.query(MarketplaceLedgerEvent)
            .filter(MarketplaceLedgerEvent.ride_id == ride_id)
            .order_by(MarketplaceLedgerEvent.id.asc())
            .all()
        )
        event_types = [row.event_type for row in rows]
        assert event_types[0] == MarketplaceLedgerEventType.RIDE_CREATED.value
        assert set(event_types) >= {
            MarketplaceLedgerEventType.DISPATCH_RIDE_VISIBLE.value,
            MarketplaceLedgerEventType.DISPATCH_CLAIM_ATTEMPTED.value,
            MarketplaceLedgerEventType.DISPATCH_CLAIM_WON.value,
            MarketplaceLedgerEventType.RIDE_ACCEPTED.value,
            MarketplaceLedgerEventType.RIDE_ARRIVED_PICKUP.value,
            MarketplaceLedgerEventType.RIDE_STARTED.value,
            MarketplaceLedgerEventType.RIDE_COMPLETED.value,
            MarketplaceLedgerEventType.EARNING_CALCULATED.value,
        }
        visible_event = next(
            row for row in rows if row.event_type == MarketplaceLedgerEventType.DISPATCH_RIDE_VISIBLE.value
        )
        assert visible_event.driver_id == driver_id
        assert visible_event.correlation_id == visible_ride["visibility_correlation_id"]
    finally:
        db.close()


def test_hide_and_cancel_write_marketplace_ledger_events():
    db = SessionLocal()
    try:
        rider_token, _ = _user(db, UserRole.CUSTOMER, "hide_rider")
        driver_token, _ = _user(db, UserRole.DRIVER, "hide_driver")
    finally:
        db.close()

    with TestClient(app) as client:
        hidden_ride_id = _create_rider_ride(client, rider_token, pickup="Hide Pickup")
        assert client.get("/drivers/available-rides", headers=_headers(driver_token)).status_code == 200
        hidden = client.post(
            f"/drivers/rides/{hidden_ride_id}/hide",
            headers=_headers(driver_token),
            json={"reason": "not_today"},
        )
        assert hidden.status_code == 200, hidden.text

        cancelled_ride_id = _create_rider_ride(client, rider_token, pickup="Cancel Pickup")
        cancelled = client.post(
            f"/rides/{cancelled_ride_id}/cancel",
            headers=_headers(rider_token),
            json={"reason": "changed_mind"},
        )
        assert cancelled.status_code == 200, cancelled.text

    db = SessionLocal()
    try:
        hidden_events = {
            row.event_type
            for row in db.query(MarketplaceLedgerEvent).filter(MarketplaceLedgerEvent.ride_id == hidden_ride_id)
        }
        cancelled_events = {
            row.event_type
            for row in db.query(MarketplaceLedgerEvent).filter(MarketplaceLedgerEvent.ride_id == cancelled_ride_id)
        }
        assert MarketplaceLedgerEventType.RIDE_HIDDEN.value in hidden_events
        assert MarketplaceLedgerEventType.RIDE_CANCELLED.value in cancelled_events
    finally:
        db.close()
