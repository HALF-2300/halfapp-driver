"""City Reality Layer v0.1 — honesty, traceability, privacy."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

import models.city_event  # noqa: F401
import models.crl_cell_explanation  # noqa: F401
import models.crl_cell_snapshot  # noqa: F401
import models.crl_time_pattern  # noqa: F401
import models.driver_telemetry_point  # noqa: F401
import models.user  # noqa: F401
import models.zone_catalog  # noqa: F401
from database import SessionLocal
from main import app
from models.ride import Ride
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.crl_labels import FORBIDDEN_CERTAINTY_WORDS, NOT_ENOUGH_DATA_LABEL
from services.datetime_utils import utc_now_naive
from services.lifecycle import RideStatus, to_storage_ride_status
from services.rate_limit import reset_rate_limits_for_tests


def _driver_headers(db) -> dict[str, str]:
    stamp = uuid.uuid4().hex[:10]
    user = create_user(
        db,
        f"crl_drv_{stamp}@example.com",
        "CRL Driver",
        "TestPw1",
        UserRole.DRIVER,
        f"CRL{stamp}",
        driver_approval_status="approved",
    )
    user.availability = "available"
    user.last_latitude = 45.52
    user.last_longitude = -122.68
    db.commit()
    token = create_access_token(sub=user.email, role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


def _admin_headers(db) -> dict[str, str]:
    stamp = uuid.uuid4().hex[:10]
    user = create_user(
        db,
        f"crl_adm_{stamp}@example.com",
        "CRL Admin",
        "TestPw1",
        UserRole.ADMIN,
        f"ADM{stamp}",
    )
    db.commit()
    token = create_access_token(sub=user.email, role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _crl_low_thresholds(monkeypatch):
    monkeypatch.setenv("SIL_MIN_DEMAND", "1")
    monkeypatch.setenv("SIL_MIN_UNIQUE_DRIVERS", "1")
    monkeypatch.setenv("SIL_MIN_FLEET_SAMPLES", "1")


def test_crl_map_labels_honesty_and_privacy():
    reset_rate_limits_for_tests()
    db = SessionLocal()
    try:
        headers = _driver_headers(db)
        now = utc_now_naive()
        for i in range(6):
            db.add(
                Ride(
                    customer_name=f"R{i}",
                    status=to_storage_ride_status(RideStatus.REQUESTED),
                    pickup_latitude=45.521 + i * 0.0002,
                    pickup_longitude=-122.681,
                    pickup_location="A",
                    destination="B",
                    created_at=now,
                )
            )
        db.commit()
    finally:
        db.close()

    with TestClient(app) as client:
        resp = client.get("/v1/crl/map", headers=headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "Not a guarantee" in body["disclaimer"]
        assert NOT_ENOUGH_DATA_LABEL in body.get("not_enough_data_label", "")
        text = resp.text.lower()
        for word in FORBIDDEN_CERTAINTY_WORDS:
            assert word not in text
        assert "driver_id" not in resp.text
        if body.get("cells"):
            cell = body["cells"][0]
            assert "label" in cell
            assert "likely" in cell["label"].lower() or "possible" in cell["label"].lower()
            assert "signals_used" not in cell
            assert "demand_count" not in cell


def test_crl_explain_traceability():
    reset_rate_limits_for_tests()
    db = SessionLocal()
    try:
        headers = _driver_headers(db)
        db.add(
            Ride(
                customer_name="Trace",
                status=to_storage_ride_status(RideStatus.REQUESTED),
                pickup_latitude=45.521,
                pickup_longitude=-122.681,
                pickup_location="A",
                destination="B",
                created_at=utc_now_naive(),
            )
        )
        db.commit()
    finally:
        db.close()

    with TestClient(app) as client:
        map_resp = client.get("/v1/crl/map", headers=headers)
        assert map_resp.status_code == 200
        cells = map_resp.json().get("cells") or []
        if not cells:
            pytest.skip("no gated cells in fixture")
        h3 = cells[0]["h3"]
        expl = client.get(f"/v1/crl/explain?h3={h3}", headers=headers)
        assert expl.status_code == 200, expl.text
        data = expl.json()
        assert "signals_used" in data
        assert isinstance(data["signals_used"], dict)
        assert data["signals_used"]
        assert "primary_cause" in data


def test_admin_create_event_and_overview():
    reset_rate_limits_for_tests()
    db = SessionLocal()
    try:
        admin = _admin_headers(db)
    finally:
        db.close()

    with TestClient(app) as client:
        start = utc_now_naive()
        end = start.replace(hour=min(start.hour + 2, 23))
        created = client.post(
            "/admin/crl/events",
            headers=admin,
            json={
                "name": "Test Concert",
                "event_type": "concert",
                "start_ts": start.isoformat(),
                "end_ts": end.isoformat(),
                "center_lat": 45.523,
                "center_lng": -122.676,
                "radius_m": 2000,
            },
        )
        assert created.status_code == 200, created.text
        overview = client.get("/admin/crl/overview", headers=admin)
        assert overview.status_code == 200
        assert "cause_breakdown" in overview.json()
        assert "Not externally verified" in overview.json()["disclaimer"]
