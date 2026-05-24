"""Street Intelligence Layer v0.1 — labels, proof gates, privacy, integration."""

from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient

import models.driver_telemetry_point  # noqa: F401
import models.proof_receipt  # noqa: F401
import models.route_quote  # noqa: F401
import models.sil_cell_aggregate  # noqa: F401
import models.user  # noqa: F401
from database import SessionLocal
from main import app
from models.driver_telemetry_point import DriverTelemetryPoint
from models.ride import Ride
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.datetime_utils import utc_now_naive
from services.lifecycle import RideStatus, to_storage_ride_status
from services.rate_limit import reset_rate_limits_for_tests
from services.routing_service import reset_routing_cache_for_tests
from services.sil_gates import assert_no_unqualified_live_traffic, proof_level_for_route
from services.sil_labels import BUSY_LAYER_LABEL, SLOW_LAYER_LABEL


def _driver_headers(db) -> dict[str, str]:
    stamp = uuid.uuid4().hex[:10]
    user = create_user(
        db,
        f"sil_drv_{stamp}@example.com",
        "SIL Driver",
        "TestPw1",
        UserRole.DRIVER,
        f"SIL{stamp}",
        driver_approval_status="approved",
    )
    user.availability = "available"
    user.last_latitude = 45.52
    user.last_longitude = -122.68
    db.commit()
    token = create_access_token(sub=user.email, role=user.role.value)
    return {"Authorization": f"Bearer {token}"}, user.id


@pytest.fixture(autouse=True)
def _sil_low_thresholds(monkeypatch):
    monkeypatch.setenv("SIL_MIN_FLEET_SAMPLES", "2")
    monkeypatch.setenv("SIL_MIN_DEMAND", "1")
    monkeypatch.setenv("SIL_MIN_UNIQUE_DRIVERS", "1")
    monkeypatch.setenv("ROUTING_PROVIDER", "haversine_fallback")
    reset_routing_cache_for_tests()


def test_truthfulness_labels_in_map_response():
    reset_rate_limits_for_tests()
    db = SessionLocal()
    try:
        headers, driver_id = _driver_headers(db)
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
    finally:
        db.close()

    with TestClient(app) as client:
        resp = client.get("/v1/sil/map?layers=busy,slow", headers=headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["disclaimer"]
        assert body["labels"]["busy"] == BUSY_LAYER_LABEL
        assert body["labels"]["slow"] == SLOW_LAYER_LABEL
        if body["cells"]:
            assert body["cells"][0]["labels"]["busy"] == BUSY_LAYER_LABEL
        text = resp.text
        assert "Not official demand" in text
        assert "Not official live traffic" in text
        assert "driver_id" not in text


def test_proof_gating_fallback_route_quote():
    reset_rate_limits_for_tests()
    db = SessionLocal()
    try:
        headers, _driver_id = _driver_headers(db)
    finally:
        db.close()

    with TestClient(app) as client:
        quote = client.post(
            "/v1/sil/route/quote",
            headers=headers,
            json={
                "from_lat": 45.52,
                "from_lng": -122.68,
                "to_lat": 45.53,
                "to_lng": -122.67,
            },
        )
        assert quote.status_code == 200, quote.text
        body = quote.json()
        assert body["route_method"] == "fallback_straight_line"
        assert body["proof_level"] != "A_ROAD_ACCURATE"
        assert "not road-accurate" in body["label"].lower()
        assert proof_level_for_route(
            route_method="fallback_straight_line", used_fallback=True
        ) == "B_APPROXIMATE"

        receipt = client.get(
            f"/v1/sil/proof/receipt/{body['proof_receipt_id']}",
            headers=headers,
        )
        assert receipt.status_code == 200
        assert receipt.json()["receipt_hash"]


def test_gate_g1_no_unqualified_live_traffic():
    with pytest.raises(ValueError):
        assert_no_unqualified_live_traffic("Heavy live traffic ahead")
    assert_no_unqualified_live_traffic(SLOW_LAYER_LABEL)


def test_privacy_map_payload():
    reset_rate_limits_for_tests()
    db = SessionLocal()
    try:
        headers, driver_id = _driver_headers(db)
        db.add(
            DriverTelemetryPoint(
                driver_id=driver_id,
                lat=45.52,
                lng=-122.68,
                speed_mps=2.0,
                created_at=utc_now_naive(),
            )
        )
        db.commit()
    finally:
        db.close()

    with TestClient(app) as client:
        resp = client.get("/v1/sil/map", headers=headers)
        assert resp.status_code == 200
        payload = resp.json()
        for cell in payload.get("cells", []):
            assert "demand_count" not in cell
            assert "fleet_samples" not in cell
            assert "driver_id" not in cell
