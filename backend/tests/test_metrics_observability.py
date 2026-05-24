from datetime import timedelta
import uuid

from fastapi.testclient import TestClient

from database import SessionLocal  # noqa: F401
import models.metrics  # noqa: F401
import models.ride  # noqa: F401
import models.user  # noqa: F401
import routes.notifications  # noqa: F401
from main import app
from models.metrics import Metric, RideClaimAttempt, RideVisibility
from models.ride import Ride
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.datetime_utils import utc_now_naive
from services.lifecycle import DriverStatus


def _driver_token(db) -> str:
    uid = uuid.uuid4().hex[:10]
    user = create_user(
        db,
        f"metrics_driver_{uid}@example.com",
        "Metrics Driver",
        "pw12345",
        UserRole.DRIVER,
        f"MDL{uid}",
        driver_approval_status="approved",
    )
    user.availability = DriverStatus.AVAILABLE.value
    db.commit()
    return create_access_token(sub=user.email, role=user.role.value)


def _admin_token(db) -> str:
    uid = uuid.uuid4().hex[:10]
    user = create_user(
        db,
        f"metrics_admin_{uid}@example.com",
        "Metrics Admin",
        "pw12345",
        UserRole.ADMIN,
        None,
    )
    return create_access_token(sub=user.email, role=user.role.value)


def test_available_rides_records_visibility_and_count_metric():
    db = SessionLocal()
    try:
        token = _driver_token(db)
        rides = [
            Ride(customer_name="Visible A", status="requested", distance=1.0),
            Ride(customer_name="Visible B", status="requested", distance=2.0),
        ]
        db.add_all(rides)
        db.commit()
        ride_ids = {ride.id for ride in rides}
    finally:
        db.close()

    with TestClient(app) as client:
        response = client.get("/drivers/available-rides", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200, response.text
    returned_ids = {ride["id"] for ride in response.json()}
    assert ride_ids.issubset(returned_ids)

    db = SessionLocal()
    try:
        visibility = db.query(RideVisibility).filter(RideVisibility.ride_id.in_(ride_ids)).all()
        assert len(visibility) == 2
        assert all(row.ordering_rank > 0 for row in visibility)

        count_metric = (
            db.query(Metric)
            .filter(Metric.metric_name == "rides_visible_count")
            .order_by(Metric.id.desc())
            .first()
        )
        assert count_metric is not None
        assert count_metric.value >= 2
    finally:
        db.close()


def test_claim_metrics_health_and_driver_performance():
    db = SessionLocal()
    try:
        first_token = _driver_token(db)
        second_token = _driver_token(db)
        admin_token = _admin_token(db)
        ride = Ride(
            customer_name="Measured Race",
            status="requested",
            distance=2.0,
            created_at=utc_now_naive() - timedelta(seconds=30),
        )
        db.add(ride)
        db.commit()
        db.refresh(ride)
        ride_id = ride.id
    finally:
        db.close()

    first_headers = {"Authorization": f"Bearer {first_token}"}
    second_headers = {"Authorization": f"Bearer {second_token}"}

    with TestClient(app) as client:
        first_claim = client.post(f"/drivers/accept-ride/{ride_id}", headers=first_headers)
        assert first_claim.status_code == 200, first_claim.text

        second_claim = client.post(f"/drivers/accept-ride/{ride_id}", headers=second_headers)
        assert second_claim.status_code == 409, second_claim.text

        arrived = client.post(f"/drivers/arrive-pickup/{ride_id}", headers=first_headers)
        assert arrived.status_code == 200, arrived.text
        started = client.post(f"/drivers/start-ride/{ride_id}", headers=first_headers)
        assert started.status_code == 200, started.text
        completed = client.post(f"/drivers/complete-ride/{ride_id}", headers=first_headers)
        assert completed.status_code == 200, completed.text

        performance = client.get("/drivers/performance", headers=first_headers)
        assert performance.status_code == 200, performance.text
        assert performance.json()["avg_accept_time"] >= 30

        second_performance = client.get("/drivers/performance", headers=second_headers)
        assert second_performance.status_code == 200, second_performance.text
        assert second_performance.json()["conflict_losses"] == 1

        health = client.get("/internal/system-health", headers={"Authorization": f"Bearer {admin_token}"})
        assert health.status_code == 200, health.text
        assert health.json()["average_match_time_seconds"] >= 0
        assert health.json()["conflict_rate"] > 0

    db = SessionLocal()
    try:
        attempts = db.query(RideClaimAttempt).filter(RideClaimAttempt.ride_id == ride_id).all()
        assert {attempt.outcome for attempt in attempts} == {"won", "conflict"}

        metric_names = {
            row[0]
            for row in db.query(Metric.metric_name).filter(Metric.ride_id == ride_id).distinct().all()
        }
        assert "time_to_accept" in metric_names
        assert "requested_to_accepted_latency" in metric_names
        assert "accepted_to_pickup_arrival_latency" in metric_names
        assert "pickup_to_completion_duration" in metric_names
        assert "claim_conflict" in metric_names
    finally:
        db.close()
