"""Fleet telemetry ingest + keyless traffic heatmap."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

import models.driver_telemetry_point  # noqa: F401
import models.user  # noqa: F401
from database import SessionLocal
from main import app
from models.driver_telemetry_point import DriverTelemetryPoint
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.datetime_utils import utc_now_naive
from services.rate_limit import reset_rate_limits_for_tests


def _driver_headers(db) -> tuple[dict[str, str], int]:
    stamp = uuid.uuid4().hex[:10]
    user = create_user(
        db,
        f"fleet_drv_{stamp}@example.com",
        "Fleet Driver",
        "TestPw1",
        UserRole.DRIVER,
        f"FLT{stamp}",
        driver_approval_status="approved",
    )
    db.commit()
    token = create_access_token(sub=user.email, role=user.role.value)
    return {"Authorization": f"Bearer {token}"}, user.id


def test_telemetry_ingest_and_traffic_heatmap():
    reset_rate_limits_for_tests()
    db = SessionLocal()
    try:
        headers, driver_id = _driver_headers(db)
        now = utc_now_naive()
        db.add_all(
            [
                DriverTelemetryPoint(
                    driver_id=driver_id,
                    lat=45.52,
                    lng=-122.68,
                    speed_mps=2.0,
                    created_at=now,
                ),
                DriverTelemetryPoint(
                    driver_id=driver_id,
                    lat=45.5205,
                    lng=-122.6805,
                    speed_mps=1.5,
                    created_at=now,
                ),
                DriverTelemetryPoint(
                    driver_id=driver_id,
                    lat=45.53,
                    lng=-122.67,
                    speed_mps=12.0,
                    created_at=now,
                ),
            ]
        )
        db.commit()
    finally:
        db.close()

    with TestClient(app) as client:
        post = client.post(
            "/drivers/me/telemetry",
            headers=headers,
            json={"lat": 45.521, "lng": -122.681, "speed_mps": 1.8},
        )
        assert post.status_code == 200, post.text
        assert post.json().get("ok") is True

        heat = client.get(
            "/drivers/me/traffic-heatmap?minutes=10&precision=0.002",
            headers=headers,
        )
        assert heat.status_code == 200, heat.text
        body = heat.json()
        assert "points" in body
        assert isinstance(body["points"], list)
        if body["points"]:
            assert len(body["points"][0]) == 3
