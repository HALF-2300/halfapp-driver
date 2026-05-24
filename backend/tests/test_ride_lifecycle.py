"""Lifecycle transitions — must match docs/RIDE_LIFECYCLE_CONTRACT.md and OpenAPI."""

from concurrent.futures import ThreadPoolExecutor
import uuid

from database import SessionLocal  # noqa: F401 — app startup runs migrations
import models.user  # noqa: F401
import models.ride  # noqa: F401
import routes.notifications  # noqa: F401

from main import app
from fastapi.testclient import TestClient
from models.ledger import MarketplaceLedgerEntry
from models.ride import Ride
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.lifecycle import DriverStatus, RideStatus


def _driver_token(db) -> str:
    uid = uuid.uuid4().hex[:10]
    u = create_user(
        db,
        f"lifecycle_driver_{uid}@example.com",
        "Life Driver",
        "pw12345",
        UserRole.DRIVER,
        f"DL{uid}",
        driver_approval_status="approved",
    )
    u.availability = DriverStatus.AVAILABLE.value
    db.commit()
    return create_access_token(sub=u.email, role=u.role.value)


def test_full_happy_path_accept_arrive_start_complete():
    db = SessionLocal()
    try:
        token = _driver_token(db)
        ride = Ride(
            customer_name="Rider A",
            status="requested",
            pickup_location="P1",
            destination="D1",
            distance=4.0,
            duration=12,
        )
        db.add(ride)
        db.commit()
        db.refresh(ride)
        rid = ride.id
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {token}"}
    with TestClient(app) as client:
        r = client.post(f"/drivers/accept-ride/{rid}", headers=headers)
        assert r.status_code == 200
        j = r.json()
        assert j["ride"]["status"] == "accepted"
        assert j["ride"]["accepted_at"] is not None

        r = client.post(f"/drivers/complete-ride/{rid}", headers=headers)
        assert r.status_code == 409

        r = client.post(f"/drivers/arrive-pickup/{rid}", headers=headers)
        assert r.status_code == 200
        assert r.json()["ride"]["status"] == RideStatus.DRIVER_ARRIVED.value

        r = client.post(f"/drivers/start-ride/{rid}", headers=headers)
        assert r.status_code == 200
        assert r.json()["ride"]["status"] == "in_progress"

        r = client.post(f"/drivers/complete-ride/{rid}", headers=headers)
        assert r.status_code == 200
        body = r.json()
        assert body["fare_earned"] > 0
        assert body["ride"]["status"] == "completed"
        assert body["ride"]["completed_at"] is not None


def test_decline_reopens_pool():
    db = SessionLocal()
    try:
        token = _driver_token(db)
        ride = Ride(customer_name="Rider B", status="requested", distance=1.0)
        db.add(ride)
        db.commit()
        db.refresh(ride)
        rid = ride.id
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {token}"}
    with TestClient(app) as client:
        client.post(f"/drivers/accept-ride/{rid}", headers=headers)
        r = client.post(f"/drivers/decline-ride/{rid}", headers=headers, json={"reason": "test reason"})
        assert r.status_code == 200
        assert r.json()["ride"]["status"] == "requested"
        assert r.json()["ride"]["lifecycle_reason"] == "test reason"

        r2 = client.get("/drivers/available-rides", headers=headers)
        assert r2.status_code == 200
        ids = [x["id"] for x in r2.json()]
        assert rid in ids


def test_open_board_first_claim_wins_with_conflict_for_loser():
    db = SessionLocal()
    try:
        first_token = _driver_token(db)
        second_token = _driver_token(db)
        ride = Ride(customer_name="Race Rider", status="requested", distance=2.0)
        db.add(ride)
        db.commit()
        db.refresh(ride)
        rid = ride.id
    finally:
        db.close()

    def claim(token: str):
        with TestClient(app) as client:
            return client.post(
                f"/drivers/accept-ride/{rid}",
                headers={"Authorization": f"Bearer {token}"},
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        first, second = list(executor.map(claim, [first_token, second_token]))

    responses = [first, second]
    winners = [response for response in responses if response.status_code == 200]
    losers = [response for response in responses if response.status_code == 409]
    assert len(winners) == 1, [response.text for response in responses]
    assert len(losers) == 1, [response.text for response in responses]
    assert winners[0].json()["ride"]["status"] == "accepted"
    conflict = losers[0].json()["detail"]
    assert conflict["detail"] == "Ride already claimed"
    assert conflict["claim_result"] == "lost"
    assert conflict["truth_status"] == "backend_conflict"

    db = SessionLocal()
    try:
        ledger_events = (
            db.query(MarketplaceLedgerEntry.event_type)
            .filter(MarketplaceLedgerEntry.ride_id == rid)
            .all()
        )
        assert [row[0] for row in ledger_events].count("claim_attempted") == 2
        assert [row[0] for row in ledger_events].count("claim_won") == 1
        assert [row[0] for row in ledger_events].count("claim_lost") == 1
    finally:
        db.close()

    with TestClient(app) as client:
        available = client.get(
            "/drivers/available-rides",
            headers={"Authorization": f"Bearer {second_token}"},
        )
    assert available.status_code == 200
    assert rid not in [item["id"] for item in available.json()]


def test_openapi_lists_ride_schemas():
    spec = app.openapi()
    names = spec.get("components", {}).get("schemas", {})
    assert "RideDriverView" in names
    assert "RideTransitionResponse" in names
    assert "CompleteRideResponse" in names


def test_decline_with_empty_json_body():
    db = SessionLocal()
    try:
        token = _driver_token(db)
        ride = Ride(customer_name="Rider C", status="requested", distance=1.0)
        db.add(ride)
        db.commit()
        db.refresh(ride)
        rid = ride.id
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {token}"}
    with TestClient(app) as client:
        client.post(f"/drivers/accept-ride/{rid}", headers=headers)
        r = client.post(f"/drivers/decline-ride/{rid}", headers=headers, json={})
        assert r.status_code == 200
        assert r.json()["ride"]["status"] == "requested"


def test_driver_only_simulation_ride_uses_backend_lifecycle():
    db = SessionLocal()
    try:
        token = _driver_token(db)
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {token}"}
    with TestClient(app) as client:
        created = client.post(
            "/drivers/simulate-ride",
            headers=headers,
            json={
                "customer_name": "Backend Simulation Rider",
                "pickup_location": "P2",
                "destination": "D2",
                "distance_km": 3.0,
                "duration_minutes": 9,
            },
        )
        assert created.status_code == 200, created.text
        ride = created.json()["ride"]
        assert ride["status"] == "requested"
        assert ride["lifecycle_reason"] == "simulation"
        assert 45.493064 <= ride["pickup_latitude"] <= 45.553064
        assert -122.706483 <= ride["pickup_longitude"] <= -122.646483
        assert 45.493064 <= ride["dropoff_latitude"] <= 45.553064
        assert -122.706483 <= ride["dropoff_longitude"] <= -122.646483
        rid = ride["id"]

        available = client.get("/drivers/available-rides", headers=headers)
        assert available.status_code == 200
        assert rid in [item["id"] for item in available.json()]

        accepted = client.post(f"/drivers/accept-ride/{rid}", headers=headers)
        assert accepted.status_code == 200
        assert accepted.json()["ride"]["status"] == "accepted"

        arrived = client.post(f"/drivers/arrive-pickup/{rid}", headers=headers)
        assert arrived.status_code == 200
        assert arrived.json()["ride"]["status"] == RideStatus.DRIVER_ARRIVED.value

        started = client.post(f"/drivers/start-ride/{rid}", headers=headers)
        assert started.status_code == 200
        assert started.json()["ride"]["status"] == "in_progress"

        completed = client.post(f"/drivers/complete-ride/{rid}", headers=headers)
        assert completed.status_code == 200
        assert completed.json()["ride"]["status"] == "completed"

        earnings = client.get("/drivers/earnings", headers=headers)
        assert earnings.status_code == 200
        assert earnings.json()["earnings_summary"]["total_rides_completed"] == 1


def test_simulation_ride_generates_coordinates_when_omitted():
    db = SessionLocal()
    try:
        token = _driver_token(db)
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {token}"}
    with TestClient(app) as client:
        generated = client.post(
            "/drivers/simulate-ride",
            headers=headers,
            json={
                "customer_name": "No Coordinates Rider",
                "pickup_location": "P3",
                "destination": "D3",
                "distance_km": 3.0,
                "duration_minutes": 9,
            },
        )
        assert generated.status_code == 200, generated.text
        ride = generated.json()["ride"]
        assert 45.493064 <= ride["pickup_latitude"] <= 45.553064
        assert -122.706483 <= ride["pickup_longitude"] <= -122.646483
        assert 45.493064 <= ride["dropoff_latitude"] <= 45.553064
        assert -122.706483 <= ride["dropoff_longitude"] <= -122.646483
