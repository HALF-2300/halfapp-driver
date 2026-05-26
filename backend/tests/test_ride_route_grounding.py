"""OSRM route grounding for ride AI dispatch — stamps osrm_self_hosted when OSRM responds."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from main import app
from models.ride import Ride
from services.osrm_self_hosted_provider import PROVIDER_ID
from services.map_route_foundation import (
    confidence_score,
    route_provider_used_fallback,
    route_source_label,
)
from services.ride_route_grounding import ground_ride_route
from services.datetime_utils import utc_now_naive
from services.routing_service import RouteEstimate, reset_routing_cache_for_tests


@pytest.fixture(autouse=True)
def _reset_routing_cache():
    reset_routing_cache_for_tests()
    yield
    reset_routing_cache_for_tests()


def test_route_source_label_osrm():
    assert route_source_label("osrm_self_hosted", used_fallback=False) == "osrm_v5"
    assert route_source_label("osrm_self_hosted", used_fallback=True) is None


def test_route_provider_used_fallback():
    assert route_provider_used_fallback("haversine_fallback") is True
    assert route_provider_used_fallback("osrm_self_hosted") is False


def test_confidence_score_skips_fallback():
    assert confidence_score("medium", used_fallback=True) is None
    assert confidence_score("medium", used_fallback=False) == 0.91


@patch("services.ride_route_grounding.route")
def test_ground_ride_route_applies_osrm_estimate(mock_route):
    mock_route.return_value = RouteEstimate(
        distance_km=12.4,
        duration_minutes=18,
        route_provider=PROVIDER_ID,
        traffic_provider="none",
        traffic_aware=False,
        traffic_signal_aware=False,
        route_confidence="medium",
        route_calculated_at=utc_now_naive(),
        used_fallback=False,
    )
    ride = Ride(
        customer_name="Test",
        pickup_latitude=45.5152,
        pickup_longitude=-122.6784,
        dropoff_latitude=45.5887,
        dropoff_longitude=-122.5968,
    )
    estimate = ground_ride_route(ride)
    assert estimate is not None
    assert ride.route_provider == PROVIDER_ID
    assert ride.distance == 12.4
    assert ride.duration == 18
    assert ride.route_calculated_at is not None


@patch("services.ride_route_grounding.route")
def test_simulation_ride_view_includes_osrm_grounding_fields(mock_route, monkeypatch):
    monkeypatch.setenv("HALFAPP_ENABLE_RIDE_SIMULATION", "1")
    monkeypatch.setenv("ALLOW_TEST_USER_SEED", "1")
    mock_route.return_value = RouteEstimate(
        distance_km=11.2,
        duration_minutes=16,
        route_provider=PROVIDER_ID,
        traffic_provider="none",
        traffic_aware=False,
        traffic_signal_aware=False,
        route_confidence="medium",
        route_calculated_at=utc_now_naive(),
        used_fallback=False,
    )
    reset_routing_cache_for_tests()

    with TestClient(app) as client:
        driver = client.post(
            "/internal/test-users",
            json={
                "email": "osrmground@example.com",
                "password": "TestDriver1!",
                "name": "OSRM Driver",
                "role": "driver",
                "license_no": "OSRM001",
                "driver_approval_status": "approved",
            },
        )
        assert driver.status_code == 200
        login = client.post(
            "/auth/login",
            json={"email": "osrmground@example.com", "password": "TestDriver1!"},
        )
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        sim = client.post(
            "/drivers/simulate-ride",
            headers=headers,
            json={"customer_name": "Sim Rider"},
        )
        assert sim.status_code == 200, sim.text
        ride = sim.json()["ride"]
        assert ride["route_provider"] == PROVIDER_ID
        assert ride["route_source"] == "osrm_v5"
        assert ride["route_used_fallback"] is False
        assert ride["route_provider_confidence"] == 0.91
        assert ride["route_calculated_at"] is not None
        assert ride["distance_km"] == pytest.approx(11.2, rel=0.01)
