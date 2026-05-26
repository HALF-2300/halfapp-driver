"""Telemetry retention job — delete stale GPS points, keep recent window."""

from __future__ import annotations

import uuid
from datetime import timedelta

import models.driver_telemetry_point  # noqa: F401
import models.user  # noqa: F401
from database import SessionLocal
from jobs.telemetry_retention import run_telemetry_retention_once
from models.driver_telemetry_point import DriverTelemetryPoint
from models.user import UserRole
from services.auth import create_user
from services.datetime_utils import utc_now_naive


def _driver_id(db) -> int:
    stamp = uuid.uuid4().hex[:10]
    user = create_user(
        db,
        f"ret_drv_{stamp}@example.com",
        "Retention Driver",
        "TestPw1",
        UserRole.DRIVER,
        f"RET{stamp}",
        driver_approval_status="approved",
    )
    db.commit()
    return user.id


def test_telemetry_retention_deletes_old_points(monkeypatch):
    monkeypatch.setenv("HALFAPP_TELEMETRY_RETENTION_DAYS", "14")
    db = SessionLocal()
    try:
        driver_id = _driver_id(db)
        now = utc_now_naive()
        old_ts = now - timedelta(days=20)
        recent_ts = now - timedelta(days=3)
        db.add_all(
            [
                DriverTelemetryPoint(
                    driver_id=driver_id,
                    lat=45.52,
                    lng=-122.68,
                    speed_mps=2.0,
                    created_at=old_ts,
                ),
                DriverTelemetryPoint(
                    driver_id=driver_id,
                    lat=45.53,
                    lng=-122.67,
                    speed_mps=3.0,
                    created_at=recent_ts,
                ),
            ]
        )
        db.commit()
        deleted = run_telemetry_retention_once(db)
        assert deleted >= 1
        remaining = db.query(DriverTelemetryPoint).filter(
            DriverTelemetryPoint.driver_id == driver_id
        ).all()
        assert len(remaining) == 1
        assert remaining[0].created_at >= now - timedelta(days=14)
    finally:
        db.close()


def test_telemetry_retention_preserves_within_window(monkeypatch):
    monkeypatch.setenv("HALFAPP_TELEMETRY_RETENTION_DAYS", "14")
    db = SessionLocal()
    try:
        driver_id = _driver_id(db)
        now = utc_now_naive()
        recent_ts = now - timedelta(days=1)
        db.add(
            DriverTelemetryPoint(
                driver_id=driver_id,
                lat=45.52,
                lng=-122.68,
                speed_mps=2.0,
                created_at=recent_ts,
            )
        )
        db.commit()
        deleted = run_telemetry_retention_once(db)
        assert deleted == 0
        assert (
            db.query(DriverTelemetryPoint)
            .filter(DriverTelemetryPoint.driver_id == driver_id)
            .count()
            == 1
        )
    finally:
        db.close()
