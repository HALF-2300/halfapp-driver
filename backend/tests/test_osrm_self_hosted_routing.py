"""Self-hosted OSRM routing proof — parsing, pricing handoff, fallback, no paid APIs."""

from __future__ import annotations

import json
import uuid
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models.ride import Ride
from models.ride_pricing import RidePricing
from services import routing_service
from services.osrm_self_hosted_provider import (
    PROVIDER_ID,
    build_route_url,
    parse_osrm_route_response,
)
from services.pricing_service import compute_ride_financials_from_trip


def _osrm_ok_payload(distance_m: float = 12500.0, duration_s: float = 900.0) -> dict:
    return {
        "code": "Ok",
        "routes": [{"distance": distance_m, "duration": duration_s}],
    }


def test_parse_osrm_route_response():
    parsed = parse_osrm_route_response(_osrm_ok_payload(10000, 600))
    assert parsed.route_provider == PROVIDER_ID
    assert parsed.distance_km == 10.0
    assert parsed.duration_minutes == 10
    assert parsed.distance_miles == pytest.approx(6.214, rel=0.01)


def test_build_route_url_uses_lon_lat_order():
    url = build_route_url((45.5898, -122.5951), (45.5152, -122.6784), base_url="http://localhost:5000")
    assert "/route/v1/driving/-122.5951,45.5898;-122.6784,45.5152" in url
    assert "google" not in url
    assert "mapbox" not in url


def test_successful_osrm_route_for_pricing_handoff(monkeypatch):
    monkeypatch.setenv("ROUTING_PROVIDER", "osrm_self_hosted")
    monkeypatch.setenv("ROUTING_FALLBACK_ENABLED", "true")
    routing_service.reset_routing_cache_for_tests()

    def fake_fetch(origin, destination, base_url=None, client=None):
        return parse_osrm_route_response(_osrm_ok_payload(15000, 1200))

    monkeypatch.setattr("services.osrm_self_hosted_provider.fetch_osrm_route", fake_fetch)

    est = routing_service.route((45.5898, -122.5951), (45.5152, -122.6784))
    assert est.route_provider == PROVIDER_ID
    assert est.traffic_provider == "none"
    assert est.traffic_aware is False
    assert est.route_confidence == "medium"
    assert est.used_fallback is False
    assert est.distance_km == 15.0
    assert est.duration_minutes == 20

    assert est.distance_miles == pytest.approx(est.distance_km * 0.621371, rel=0.01)

    financials = compute_ride_financials_from_trip(
        distance_km=est.distance_km,
        duration_minutes=est.duration_minutes,
    )
    assert financials.driver_shareable_ride_fare_cents > 0
    assert financials.platform_service_fee_cents == 150
    miles_from_km = est.distance_km * 0.621371
    assert est.distance_miles == pytest.approx(miles_from_km, rel=0.01)


def test_fallback_when_osrm_unavailable(monkeypatch):
    monkeypatch.setenv("ROUTING_PROVIDER", "osrm_self_hosted")
    monkeypatch.setenv("ROUTING_FALLBACK_ENABLED", "true")
    routing_service.reset_routing_cache_for_tests()

    def fail_fetch(*args, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr("services.osrm_self_hosted_provider.fetch_osrm_route", fail_fetch)

    est = routing_service.route((45.52, -122.68), (45.53, -122.67))
    assert est.route_provider == "haversine_fallback"
    assert est.route_confidence == "low"
    assert est.used_fallback is True
    assert est.traffic_aware is False


def test_no_google_mapbox_in_osrm_http_client(monkeypatch):
    monkeypatch.setenv("OSRM_BASE_URL", "http://127.0.0.1:5999")
    routing_service.reset_routing_cache_for_tests()

    captured: list[str] = []

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def get(self, url):
            captured.append(url)
            response = MagicMock()
            response.raise_for_status = MagicMock()
            response.json = MagicMock(return_value=_osrm_ok_payload())
            return response

        def close(self):
            pass

    monkeypatch.setattr("services.osrm_self_hosted_provider.httpx.Client", FakeClient)

    from services.osrm_self_hosted_provider import fetch_osrm_route

    fetch_osrm_route((45.5, -122.6), (45.51, -122.61))
    assert len(captured) == 1
    assert "127.0.0.1:5999" in captured[0]
    assert "google" not in captured[0].lower()
    assert "mapbox" not in captured[0].lower()


def test_ride_create_stores_route_metadata(monkeypatch):
    monkeypatch.setenv("ROUTING_PROVIDER", "osrm_self_hosted")
    routing_service.reset_routing_cache_for_tests()

    def fake_fetch(origin, destination, base_url=None, client=None):
        return parse_osrm_route_response(_osrm_ok_payload(8000, 480))

    monkeypatch.setattr("services.osrm_self_hosted_provider.fetch_osrm_route", fake_fetch)

    from models.user import UserRole
    from services.auth import create_access_token, create_user

    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:8]
        rider = create_user(
            db,
            f"osrm_rider_{uid}@example.com",
            "OSRM Rider",
            "pw12345",
            UserRole.CUSTOMER,
            None,
        )
        token = create_access_token(sub=rider.email, role=rider.role.value)
        db.commit()
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {token}"}
    with TestClient(app) as client:
        res = client.post(
            "/rides/",
            headers=headers,
            json={
                "pickup_latitude": 45.5898,
                "pickup_longitude": -122.5951,
                "dropoff_latitude": 45.5152,
                "dropoff_longitude": -122.6784,
                "pickup_location": "PDX",
                "dropoff_location": "Downtown Portland",
            },
        )
        assert res.status_code == 200
        ride = res.json()["ride"]
        assert ride["route_provider"] == PROVIDER_ID
        assert ride["traffic_provider"] == "none"
        assert ride["traffic_aware"] is False
        assert ride["route_confidence"] == "medium"
        assert ride["route_calculated_at"] is not None
        ride_id = ride["id"]

    db2 = SessionLocal()
    try:
        row = db2.query(Ride).filter(Ride.id == ride_id).first()
        pricing = db2.query(RidePricing).filter(RidePricing.ride_id == ride_id).first()
        assert row is not None
        assert row.route_provider == PROVIDER_ID
        assert pricing is not None
        assert pricing.driver_shareable_fare_cents > 0
    finally:
        db2.close()
