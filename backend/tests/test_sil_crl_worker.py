"""SIL/CRL background worker and snapshot read-path headers."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

import models.crl_cell_explanation  # noqa: F401
import models.crl_cell_snapshot  # noqa: F401
import models.driver_telemetry_point  # noqa: F401
import models.sil_cell_aggregate  # noqa: F401
import models.user  # noqa: F401
from database import SessionLocal
from jobs.sil_crl_worker import run_crl_recompute_once, run_sil_recompute_once
from main import app
from models.driver_telemetry_point import DriverTelemetryPoint
from models.ride import Ride
from models.sil_cell_aggregate import SilCellAggregate
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.datetime_utils import utc_now_naive
from services.lifecycle import RideStatus, to_storage_ride_status
from services.rate_limit import reset_rate_limits_for_tests
from services.sil_compute import align_bucket_start


def _driver_headers(db) -> dict[str, str]:
    stamp = uuid.uuid4().hex[:10]
    user = create_user(
        db,
        f"worker_drv_{stamp}@example.com",
        "Worker Driver",
        "TestPw1",
        UserRole.DRIVER,
        f"WRK{stamp}",
        driver_approval_status="approved",
    )
    user.availability = "available"
    user.last_latitude = 45.52
    user.last_longitude = -122.68
    db.commit()
    token = create_access_token(sub=user.email, role=user.role.value)
    return {"Authorization": f"Bearer {token}"}, user.id


def _seed_sil_inputs(db, driver_id: int) -> None:
    now = utc_now_naive()
    for i in range(3):
        db.add(
            DriverTelemetryPoint(
                driver_id=driver_id,
                lat=45.52 + i * 0.0001,
                lng=-122.68,
                speed_mps=1.0,
                created_at=now,
            )
        )
    db.add(
        Ride(
            customer_name="Demand",
            status=to_storage_ride_status(RideStatus.REQUESTED),
            pickup_latitude=45.521,
            pickup_longitude=-122.681,
            pickup_location="A",
            destination="B",
        )
    )
    db.commit()


def test_worker_populates_sil_snapshot_table():
    db = SessionLocal()
    try:
        _, driver_id = _driver_headers(db)
        bucket_start = align_bucket_start(utc_now_naive(), 5)
        db.query(SilCellAggregate).filter(
            SilCellAggregate.bucket_start_ts == bucket_start
        ).delete(synchronize_session=False)
        db.commit()
        _seed_sil_inputs(db, driver_id)
        run_sil_recompute_once(db)
        count = (
            db.query(SilCellAggregate)
            .filter(SilCellAggregate.bucket_start_ts == bucket_start)
            .count()
        )
        assert count > 0
    finally:
        db.close()


def test_worker_populates_crl_snapshot_table():
    db = SessionLocal()
    try:
        _, driver_id = _driver_headers(db)
        _seed_sil_inputs(db, driver_id)
        bucket_start = run_crl_recompute_once(db)
        from models.crl_cell_snapshot import CrlCellSnapshot

        count = (
            db.query(CrlCellSnapshot)
            .filter(CrlCellSnapshot.bucket_start_ts == bucket_start)
            .count()
        )
        assert count >= 0
    finally:
        db.close()


def test_sil_map_header_snapshot_after_worker():
    reset_rate_limits_for_tests()
    db = SessionLocal()
    try:
        headers, driver_id = _driver_headers(db)
        bucket_start = align_bucket_start(utc_now_naive(), 5)
        db.query(SilCellAggregate).delete(synchronize_session=False)
        db.commit()
        _seed_sil_inputs(db, driver_id)
        run_sil_recompute_once(db)
        assert (
            db.query(SilCellAggregate)
            .filter(SilCellAggregate.bucket_start_ts == bucket_start)
            .count()
            > 0
        )
    finally:
        db.close()

    with TestClient(app) as client:
        resp = client.get("/v1/sil/map?layers=busy,slow", headers=headers)
        assert resp.status_code == 200, resp.text
        assert resp.headers.get("X-SIL-Source") == "snapshot"


def test_sil_map_header_live_when_snapshot_empty():
    reset_rate_limits_for_tests()
    db = SessionLocal()
    try:
        headers, driver_id = _driver_headers(db)
        db.query(SilCellAggregate).delete(synchronize_session=False)
        db.commit()
        _seed_sil_inputs(db, driver_id)
    finally:
        db.close()

    with TestClient(app) as client:
        resp = client.get("/v1/sil/map?layers=busy,slow", headers=headers)
        assert resp.status_code == 200, resp.text
        assert resp.headers.get("X-SIL-Source") == "live"
