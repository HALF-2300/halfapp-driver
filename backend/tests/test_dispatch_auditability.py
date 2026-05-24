import uuid

from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models.metrics import RideClaimAttempt, RideVisibility
from models.ride import Ride
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.lifecycle import DriverStatus, RideStatus


def _driver(db, prefix: str) -> tuple[str, int]:
    uid = uuid.uuid4().hex[:10]
    user = create_user(
        db,
        f"{prefix}_{uid}@example.com",
        f"{prefix} Driver",
        "pw12345",
        UserRole.DRIVER,
        f"{prefix.upper()}{uid}",
        driver_approval_status="approved",
    )
    user.availability = DriverStatus.AVAILABLE.value
    db.commit()
    return create_access_token(sub=user.email, role=user.role.value), user.id


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _go_online(client: TestClient, token: str) -> None:
    headers = _headers(token)
    status = client.patch(
        "/drivers/me/status",
        headers=headers,
        json={"online": True, "lat": 45.5, "lng": -122.6},
    )
    assert status.status_code == 200, status.text
    presence = client.put("/drivers/presence", headers=headers, json={"state": "available"})
    assert presence.status_code == 200, presence.text


def test_available_rides_return_dispatch_exposure_proof():
    db = SessionLocal()
    try:
        token, driver_id = _driver(db, "visibleproof")
        ride = Ride(
            customer_name="Audit Rider",
            status=RideStatus.REQUESTED.value,
            pickup_location="Audit Pickup",
            destination="Audit Dropoff",
            pickup_latitude=45.5,
            pickup_longitude=-122.6,
            distance=2.0,
        )
        db.add(ride)
        db.commit()
        ride_id = ride.id
    finally:
        db.close()

    with TestClient(app) as client:
        _go_online(client, token)
        response = client.get("/drivers/available-rides", headers=_headers(token))

    assert response.status_code == 200, response.text
    returned = next(item for item in response.json() if item["id"] == ride_id)
    assert returned["ride_visibility_id"] is not None
    assert returned["visibility_correlation_id"]
    assert returned["visibility_reason"] == "requested_unassigned_open_board"
    assert returned["dispatch_policy_id"] == "ranked_open_board_v1"
    assert returned["dispatch_policy_name"] == "Ranked Open Board v1"
    assert returned["ordered_by"] == ["ordering_score_desc", "created_at_asc", "ride_id_asc"]
    assert returned["why_this_rank"]

    db = SessionLocal()
    try:
        visibility = (
            db.query(RideVisibility)
            .filter(RideVisibility.ride_id == ride_id, RideVisibility.driver_id == driver_id)
            .one()
        )
        assert visibility.id == returned["ride_visibility_id"]
        assert visibility.correlation_id == returned["visibility_correlation_id"]
        assert visibility.metadata_json and "requested_unassigned_open_board" in visibility.metadata_json
    finally:
        db.close()


def test_claim_conflict_transparency_proves_winner_loser_and_409_reason():
    db = SessionLocal()
    try:
        first_token, first_driver_id = _driver(db, "winnerproof")
        second_token, second_driver_id = _driver(db, "loserproof")
        ride = Ride(customer_name="Race Audit Rider", status=RideStatus.REQUESTED.value, distance=2.0)
        db.add(ride)
        db.commit()
        ride_id = ride.id
    finally:
        db.close()

    with TestClient(app) as client:
        _go_online(client, first_token)
        _go_online(client, second_token)
        assert client.get("/drivers/available-rides", headers=_headers(first_token)).status_code == 200
        assert client.get("/drivers/available-rides", headers=_headers(second_token)).status_code == 200

        won = client.post(f"/drivers/accept-ride/{ride_id}", headers=_headers(first_token))
        assert won.status_code == 200, won.text

        lost = client.post(f"/drivers/accept-ride/{ride_id}", headers=_headers(second_token))
        assert lost.status_code == 409, lost.text
        conflict = lost.json()["detail"]
        assert conflict["detail"] == "Ride already claimed"
        assert conflict["claim_result"] == "lost"
        assert conflict["truth_status"] == "backend_conflict"
        assert conflict["reason"] == "ride_already_claimed"
        assert conflict["state_changed"] is False
        assert conflict["current_status"] == "accepted"
        assert conflict["assigned_driver_id"] == first_driver_id

        proof = client.get(f"/drivers/rides/{ride_id}/transparency", headers=_headers(second_token))

    assert proof.status_code == 200, proof.text
    body = proof.json()
    assert body["claim"]["last_claim_result"] == "lost"
    assert body["claim"]["claimed_by_driver_id"] == str(first_driver_id)
    assert "CLAIM_CONFLICT_PROOF" in body["truth_labels"]

    dispatch = body["dispatch_proof"]
    assert dispatch["claim_winner_driver_id"] == first_driver_id
    assert second_driver_id in dispatch["claim_lost_driver_ids"]
    assert dispatch["claim_conflict"]["http_status"] == 409
    assert dispatch["claim_conflict"]["reason"] == "ride_already_claimed"
    assert dispatch["claim_conflict"]["competing_driver_id"] == first_driver_id

    attempts = dispatch["claim_attempts"]
    assert {attempt["outcome"] for attempt in attempts} == {"won", "conflict"}
    losing_attempt = next(attempt for attempt in attempts if attempt["driver_id"] == second_driver_id)
    assert losing_attempt["http_status"] == 409
    assert losing_attempt["reason"] == "ride_already_claimed"
    assert losing_attempt["competing_driver_id"] == first_driver_id

    assert {entry["event_type"] for entry in dispatch["ledger_entries"]} >= {
        "claim_attempted",
        "claim_won",
        "claim_lost",
    }

    db = SessionLocal()
    try:
        db_attempts = db.query(RideClaimAttempt).filter(RideClaimAttempt.ride_id == ride_id).all()
        assert {attempt.outcome for attempt in db_attempts} == {"won", "conflict"}
    finally:
        db.close()
