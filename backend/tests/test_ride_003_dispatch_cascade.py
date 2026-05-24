"""RIDE-003: dispatch timeout cascade and ride_dispatch_log."""
from __future__ import annotations

import uuid
from datetime import timedelta

import pytest

from fastapi.testclient import TestClient

from database import SessionLocal
import models.ride_dispatch_log  # noqa: F401
from main import app
from models.ride import Ride
from models.ride_dispatch_log import RideDispatchLog
from models.user import User, UserRole
from services.driver_status_service import set_driver_offline, set_driver_online
from services.auth import create_access_token, create_user
from services.datetime_utils import utc_now_naive
from services.ride_dispatch_cascade import (
    MAX_DISPATCH_ATTEMPTS,
    process_dispatch_timeouts,
    refresh_open_dispatch_offers,
    start_dispatch_for_ride,
)

pytestmark = pytest.mark.sequential_dispatch


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _driver(db, prefix: str) -> tuple[str, int]:
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
    db.commit()
    return create_access_token(sub=user.email, role=user.role.value), user.id


def _rider(db) -> str:
    uid = uuid.uuid4().hex[:8]
    user = create_user(db, f"rider_{uid}@example.com", "Rider", "pw12345", UserRole.CUSTOMER)
    db.commit()
    return create_access_token(sub=user.email, role=user.role.value)


def _go_online(client: TestClient, token: str, *, lat: float = 45.52, lng: float = -122.68) -> None:
    client.patch(
        "/drivers/me/status",
        headers=_headers(token),
        json={"online": True, "lat": lat, "lng": lng},
    )
    client.put("/drivers/presence", headers=_headers(token), json={"state": "available"})


def _isolate_dispatch_pool(db, *keep_driver_ids: int) -> None:
    """Keep only listed drivers dispatch-eligible (shared pytest DB)."""
    keep = set(keep_driver_ids)
    for driver in db.query(User).filter(User.role == UserRole.DRIVER).all():
        if driver.id in keep:
            continue
        set_driver_offline(db, driver)
    db.commit()


def _create_ride(client: TestClient, rider_token: str) -> int:
    response = client.post(
        "/rides/",
        headers=_headers(rider_token),
        json={
            "pickup_location": "A",
            "dropoff_location": "B",
            "pickup_latitude": 45.501,
            "pickup_longitude": -122.681,
            "dropoff_latitude": 45.551,
            "dropoff_longitude": -122.611,
            "distance_km": 2.0,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["ride"]["id"]


def test_no_response_times_out_and_offers_next_driver():
    db = SessionLocal()
    try:
        d1_token, d1_id = _driver(db, "dispatch_a")
        d2_token, d2_id = _driver(db, "dispatch_b")
        rider_token = _rider(db)
        _isolate_dispatch_pool(db, d1_id, d2_id)
    finally:
        db.close()

    with TestClient(app) as client:
        _go_online(client, d1_token, lat=45.501, lng=-122.681)
        ride_id = _create_ride(client, rider_token)

        available_d1 = client.get("/drivers/available-rides", headers=_headers(d1_token))
        assert any(r["id"] == ride_id for r in available_d1.json()), available_d1.text

        db = SessionLocal()
        try:
            ride = db.query(Ride).filter(Ride.id == ride_id).one()
            ride.dispatch_expires_at = utc_now_naive() - timedelta(seconds=1)
            db.commit()
            process_dispatch_timeouts(db, now=utc_now_naive())
            db.commit()
        finally:
            db.close()

        _go_online(client, d2_token, lat=45.502, lng=-122.682)
        available_d1_after = client.get("/drivers/available-rides", headers=_headers(d1_token))
        available_d2 = client.get("/drivers/available-rides", headers=_headers(d2_token))
        assert not any(r["id"] == ride_id for r in available_d1_after.json())
        assert any(r["id"] == ride_id for r in available_d2.json())

        db = SessionLocal()
        try:
            logs = db.query(RideDispatchLog).filter(RideDispatchLog.ride_id == ride_id).all()
            assert any(log.driver_id == d1_id and log.result == "timeout" for log in logs)
            assert any(log.driver_id == d2_id and log.result == "sent" for log in logs)
        finally:
            db.close()


def test_three_failed_attempts_sets_no_drivers_available():
    db = SessionLocal()
    try:
        pairs = [_driver(db, f"cascade_{i}") for i in range(3)]
        tokens = [p[0] for p in pairs]
        keep_ids = [p[1] for p in pairs]
        rider_token = _rider(db)
        _isolate_dispatch_pool(db, *keep_ids)
        ride = Ride(
            customer_name="Cascade",
            status="requested",
            pickup_location="P",
            destination="D",
            distance=1.0,
        )
        db.add(ride)
        db.commit()
        ride_id = ride.id
    finally:
        db.close()

    with TestClient(app) as client:
        for token in tokens:
            _go_online(client, token)
        client.get("/drivers/available-rides", headers=_headers(tokens[0]))
        db = SessionLocal()
        try:
            for _ in range(MAX_DISPATCH_ATTEMPTS):
                ride = db.query(Ride).filter(Ride.id == ride_id).one()
                if ride.status != "requested":
                    break
                ride.dispatch_expires_at = utc_now_naive() - timedelta(seconds=1)
                db.commit()
                process_dispatch_timeouts(db, now=utc_now_naive())
                db.commit()
            ride = db.query(Ride).filter(Ride.id == ride_id).one()
            assert ride.status == "cancelled"
            assert ride.lifecycle_reason == "no_drivers_available"
            assert db.query(RideDispatchLog).filter(RideDispatchLog.ride_id == ride_id).count() >= MAX_DISPATCH_ATTEMPTS
        finally:
            db.close()


def test_accept_before_timeout_clears_dispatch_offer():
    db = SessionLocal()
    try:
        driver_token, driver_id = _driver(db, "accept_before")
        rider_token = _rider(db)
        _isolate_dispatch_pool(db, driver_id)
    finally:
        db.close()

    with TestClient(app) as client:
        _go_online(client, driver_token)
        ride_id = _create_ride(client, rider_token)
        accept = client.post(f"/drivers/accept-ride/{ride_id}", headers=_headers(driver_token))
        assert accept.status_code == 200, accept.text
        db = SessionLocal()
        try:
            ride = db.query(Ride).filter(Ride.id == ride_id).one()
            assert ride.dispatch_driver_id is None
            assert ride.dispatch_expires_at is None
            assert ride.status == "accepted"
        finally:
            db.close()


def test_decline_does_not_assign_driver():
    db = SessionLocal()
    try:
        d1_token, d1_id = _driver(db, "decline_a")
        d2_token, d2_id = _driver(db, "decline_b")
        rider_token = _rider(db)
        _isolate_dispatch_pool(db, d1_id, d2_id)
    finally:
        db.close()

    with TestClient(app) as client:
        _go_online(client, d1_token, lat=45.501, lng=-122.681)
        _go_online(client, d2_token, lat=45.502, lng=-122.682)
        ride_id = _create_ride(client, rider_token)
        client.get("/drivers/available-rides", headers=_headers(d1_token))
        decline = client.post(f"/drivers/decline-dispatch/{ride_id}", headers=_headers(d1_token))
        assert decline.status_code == 200, decline.text
        db = SessionLocal()
        try:
            ride = db.query(Ride).filter(Ride.id == ride_id).one()
            assert ride.driver_id is None
            assert ride.dispatch_driver_id == d2_id
            logs = db.query(RideDispatchLog).filter(RideDispatchLog.ride_id == ride_id).all()
            assert any(log.driver_id == d1_id and log.result == "declined" for log in logs)
        finally:
            db.close()


def test_accept_before_timeout_processor_does_not_offer_second_driver():
    db = SessionLocal()
    try:
        d1_token, d1_id = _driver(db, "accept_first")
        d2_token, d2_id = _driver(db, "accept_second")
        rider_token = _rider(db)
        _isolate_dispatch_pool(db, d1_id, d2_id)
    finally:
        db.close()

    with TestClient(app) as client:
        _go_online(client, d1_token, lat=45.501, lng=-122.681)
        _go_online(client, d2_token, lat=45.502, lng=-122.682)
        ride_id = _create_ride(client, rider_token)
        accept = client.post(f"/drivers/accept-ride/{ride_id}", headers=_headers(d1_token))
        assert accept.status_code == 200, accept.text

        db = SessionLocal()
        try:
            ride = db.query(Ride).filter(Ride.id == ride_id).one()
            ride.dispatch_expires_at = utc_now_naive() - timedelta(seconds=1)
            db.commit()
            process_dispatch_timeouts(db, now=utc_now_naive())
            db.commit()
            ride = db.query(Ride).filter(Ride.id == ride_id).one()
            assert ride.status == "accepted"
            assert ride.driver_id == d1_id
            logs = db.query(RideDispatchLog).filter(RideDispatchLog.ride_id == ride_id).all()
            assert not any(log.driver_id == d2_id and log.result == "sent" for log in logs)
        finally:
            db.close()


def test_non_candidate_decline_returns_409():
    db = SessionLocal()
    try:
        d1_token, d1_id = _driver(db, "decline_owner")
        d2_token, d2_id = _driver(db, "decline_stranger")
        rider_token = _rider(db)
        _isolate_dispatch_pool(db, d1_id, d2_id)
    finally:
        db.close()

    with TestClient(app) as client:
        _go_online(client, d1_token, lat=45.501, lng=-122.681)
        _go_online(client, d2_token, lat=45.502, lng=-122.682)
        ride_id = _create_ride(client, rider_token)
        client.get("/drivers/available-rides", headers=_headers(d1_token))
        decline = client.post(f"/drivers/decline-dispatch/{ride_id}", headers=_headers(d2_token))
        assert decline.status_code == 409, decline.text

        db = SessionLocal()
        try:
            ride = db.query(Ride).filter(Ride.id == ride_id).one()
            assert ride.driver_id is None
            assert ride.status == "requested"
        finally:
            db.close()


def test_busy_driver_skipped_ineligible_logged():
    db = SessionLocal()
    try:
        online_token, online_id = _driver(db, "online_busy_test")
        busy_token, busy_id = _driver(db, "busy_skip")
        _isolate_dispatch_pool(db, online_id, busy_id)
        active = Ride(
            customer_name="Busy block",
            status="accepted",
            driver_id=busy_id,
            distance=1.0,
        )
        pool = Ride(
            customer_name="Pool",
            status="requested",
            pickup_location="P",
            destination="D",
            pickup_latitude=45.501,
            pickup_longitude=-122.681,
            distance=1.0,
        )
        db.add_all([active, pool])
        db.commit()
        ride_id = pool.id
    finally:
        db.close()

    with TestClient(app) as client:
        _go_online(client, online_token, lat=45.501, lng=-122.681)
        _go_online(client, busy_token, lat=45.502, lng=-122.682)
        db = SessionLocal()
        try:
            set_driver_online(
                db,
                db.query(User).filter(User.id == online_id).one(),
                lat=45.501,
                lng=-122.681,
            )
            db.commit()
            start_dispatch_for_ride(db, ride_id)
            db.commit()
            logs = db.query(RideDispatchLog).filter(RideDispatchLog.ride_id == ride_id).all()
            assert any(
                log.driver_id == busy_id and log.result == "skipped_ineligible" and log.reason == "driver_busy"
                for log in logs
            )
            ride = db.query(Ride).filter(Ride.id == ride_id).one()
            assert ride.dispatch_driver_id == online_id
            busy_accept = client.post(
                f"/drivers/accept-ride/{ride_id}",
                headers=_headers(busy_token),
            )
            assert busy_accept.status_code == 409, busy_accept.text
            assert busy_accept.json()["detail"]["reason"] == "driver_already_on_active_ride"
        finally:
            db.close()


def test_offline_driver_skipped_ineligible_logged():
    db = SessionLocal()
    try:
        online_token, online_id = _driver(db, "online_only")
        offline_token, offline_id = _driver(db, "offline_skip")
        _isolate_dispatch_pool(db, online_id, offline_id)
        ride = Ride(
            customer_name="Skip",
            status="requested",
            pickup_location="P",
            destination="D",
            pickup_latitude=45.501,
            pickup_longitude=-122.681,
            distance=1.0,
        )
        db.add(ride)
        db.commit()
        ride_id = ride.id
    finally:
        db.close()

    with TestClient(app) as client:
        _go_online(client, online_token, lat=45.501, lng=-122.681)
        client.put("/drivers/presence", headers=_headers(offline_token), json={"state": "offline"})
        db = SessionLocal()
        try:
            set_driver_online(db, db.query(User).filter(User.id == online_id).one(), lat=45.501, lng=-122.681)
            db.commit()
            start_dispatch_for_ride(db, ride_id)
            db.commit()
            logs = db.query(RideDispatchLog).filter(RideDispatchLog.ride_id == ride_id).all()
            assert any(
                log.driver_id == offline_id and log.result == "skipped_ineligible" for log in logs
            )
            ride = db.query(Ride).filter(Ride.id == ride_id).one()
            assert ride.dispatch_driver_id is not None
            assert ride.dispatch_driver_id != offline_id
            assert any(log.driver_id == ride.dispatch_driver_id and log.result == "sent" for log in logs)
        finally:
            db.close()
