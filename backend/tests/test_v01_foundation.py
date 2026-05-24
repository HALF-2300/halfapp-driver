"""v0.1 foundation — pricing ledger + map provider metadata (no paid routing APIs)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models.ride import Ride
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.lifecycle import DriverStatus, RideStatus
from services.map_route_foundation import (
    V01_ROUTE_PROVIDER,
    V01_TRAFFIC_PROVIDER,
    external_routing_enabled,
)
from services.pricing_service import (
    DEFAULT_PLATFORM_SERVICE_FEE_CENTS,
    compute_financials,
    compute_ride_financials_from_trip,
)
from services.ride_pricing import PricingLockedError, finalize_ride_pricing


def _driver_token(db) -> str:
    uid = uuid.uuid4().hex[:10]
    u = create_user(
        db,
        f"v01_driver_{uid}@example.com",
        "V01 Driver",
        "pw12345",
        UserRole.DRIVER,
        f"V01{uid}",
        driver_approval_status="approved",
    )
    u.availability = DriverStatus.AVAILABLE.value
    db.commit()
    return create_access_token(sub=u.email, role=u.role.value)


def _seed_ride(db, *, distance_km: float = 4.0) -> int:
    ride = Ride(
        customer_name="Pricing Rider",
        status="requested",
        pickup_location="P",
        destination="D",
        distance=distance_km,
        duration=12,
    )
    db.add(ride)
    db.commit()
    db.refresh(ride)
    return ride.id


def _complete_lifecycle(client, headers, ride_id: int, body: dict | None = None):
    client.post(f"/drivers/accept-ride/{ride_id}", headers=headers)
    client.post(f"/drivers/arrive-pickup/{ride_id}", headers=headers)
    client.post(f"/drivers/start-ride/{ride_id}", headers=headers)
    kwargs = {"json": body} if body else {}
    return client.post(f"/drivers/complete-ride/{ride_id}", headers=headers, **kwargs)


def test_normal_ride_pricing_split():
    """Spec scenario 1 — fixed shareable $25.00, service fee $1.50."""
    b = compute_financials(
        driver_shareable_ride_fare_cents=2500,
        platform_service_fee_cents=150,
    )
    assert b.platform_commission_cents == 500
    assert b.driver_ride_payout_cents == 2000
    assert b.platform_revenue_cents == 650
    assert b.customer_total_cents == 2650


def test_short_ride_includes_default_service_fee():
    b = compute_financials(driver_shareable_ride_fare_cents=1000, platform_service_fee_cents=150)
    assert b.platform_commission_cents == 200
    assert b.driver_ride_payout_cents == 800
    assert b.platform_revenue_cents == 350
    assert b.platform_service_fee_cents == DEFAULT_PLATFORM_SERVICE_FEE_CENTS == 150


def test_tip_not_commissioned():
    b = compute_financials(driver_shareable_ride_fare_cents=2500, tip_cents=500)
    assert b.driver_total_payout_cents == 2500
    assert b.platform_commission_cents == 500


def test_pass_through_fees_not_commissioned():
    b = compute_financials(
        driver_shareable_ride_fare_cents=2500,
        city_fee_cents=200,
        airport_fee_cents=300,
        toll_cents=100,
        accessibility_fee_cents=50,
    )
    assert b.platform_commission_cents == 500
    assert b.driver_ride_payout_cents + b.platform_commission_cents == 2500
    assert b.customer_total_cents == 2500 + 150 + 200 + 300 + 100 + 50


def test_pricing_survives_refresh_via_my_rides():
    db = SessionLocal()
    try:
        token = _driver_token(db)
        ride_id = _seed_ride(db, distance_km=4.0)
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {token}"}
    with TestClient(app) as client:
        _complete_lifecycle(client, headers, ride_id, {"tip_cents": 200})
        listed = client.get("/drivers/my-rides", headers=headers)
        assert listed.status_code == 200
        row = next(r for r in listed.json() if r["id"] == ride_id)
        assert row["status"] == "completed"
        assert row["pricing"]["financial_locked"] is True
        assert row["pricing"]["driver_total_payout_cents"] >= row["pricing"]["driver_ride_payout_cents"]
        assert row["pricing"]["tip_cents"] == 200


def test_completed_ride_locks_financial_fields():
    db = SessionLocal()
    try:
        token = _driver_token(db)
        ride_id = _seed_ride(db, distance_km=1.0)
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {token}"}
    with TestClient(app) as client:
        _complete_lifecycle(client, headers, ride_id)
        locked = client.post(
            f"/drivers/complete-ride/{ride_id}",
            headers=headers,
            json={"tip_cents": 9999},
        )
        assert locked.status_code == 409
        assert "locked" in locked.json()["detail"].lower()

    db = SessionLocal()
    try:
        with pytest.raises(PricingLockedError):
            finalize_ride_pricing(db, ride_id=ride_id, distance_km=1.0, tip_cents=1, lock=True)
    finally:
        db.close()


def test_map_foundation_defaults_on_accept():
    db = SessionLocal()
    try:
        token = _driver_token(db)
        ride_id = _seed_ride(db)
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {token}"}
    with TestClient(app) as client:
        accepted = client.post(f"/drivers/accept-ride/{ride_id}", headers=headers)
        assert accepted.status_code == 200
        ride = accepted.json()["ride"]
        assert ride["route_provider"] in (
            V01_ROUTE_PROVIDER,
            "current_or_osrm",
            "osrm_self_hosted",
            "haversine_fallback",
        )
        assert ride["traffic_provider"] == V01_TRAFFIC_PROVIDER
        assert ride["traffic_aware"] is False
        assert ride["google_maps_fallback_enabled"] is False
        assert ride["mapbox_traffic_enabled"] is False
        assert ride["route_calculated_at"] is not None


def test_external_routing_disabled_by_default():
    ride = Ride(customer_name="Map", status="requested")
    assert external_routing_enabled(ride) is False


def test_driver_app_does_not_reference_paid_map_apis():
    root = Path(__file__).resolve().parents[2] / "driver-app" / "src"
    forbidden = (
        "api.mapbox.com",
        "mapbox://",
        "maps.googleapis.com/maps/api",
        "google.maps",
    )
    hits = []
    for path in root.rglob("*"):
        if path.suffix not in {".js", ".jsx", ".ts", ".tsx"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for needle in forbidden:
            if needle in text:
                hits.append(f"{path.relative_to(root)}: {needle}")
    assert hits == []


def test_alembic_head_includes_v01_foundation():
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    from database import engine

    cfg = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
    expected_head = ScriptDirectory.from_config(cfg).get_current_head()

    with engine.connect() as conn:
        version = conn.exec_driver_sql("SELECT version_num FROM alembic_version").scalar()
    assert version == expected_head
