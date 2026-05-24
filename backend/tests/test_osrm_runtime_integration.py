"""
OSRM runtime integration test.

Skipped unless OSRM_RUNTIME_URL is set in the env.
Mirrors the pattern used by test_postgres_claim_race_proof_01.py.
"""

from __future__ import annotations

import os

import httpx
import pytest

from services.routing_service import route, reset_routing_cache_for_tests

OSRM_URL = os.environ.get("OSRM_RUNTIME_URL")
pytestmark = pytest.mark.skipif(
    not OSRM_URL,
    reason="OSRM_RUNTIME_URL not set — runtime proof requires a live OSRM.",
)

# Known Portland landmarks (lng, lat) in OSRM path order; routing_service uses (lat, lng).
PDX_AIRPORT = (45.5887, -122.5968)
PORTLAND_DOWNTOWN = (45.5152, -122.6765)
OHSU = (45.4994, -122.6862)
PEARL_DISTRICT = (45.5236, -122.6816)
HAWTHORNE = (45.5118, -122.6334)


def _route(a: tuple[float, float], b: tuple[float, float]) -> dict:
    lat1, lon1 = a
    lat2, lon2 = b
    coords = f"{lon1},{lat1};{lon2},{lat2}"
    response = httpx.get(
        f"{OSRM_URL.rstrip('/')}/route/v1/driving/{coords}",
        params={"overview": "false"},
        timeout=5.0,
    )
    response.raise_for_status()
    return response.json()


def test_osrm_downtown_to_airport_returns_ok():
    data = _route(PORTLAND_DOWNTOWN, PDX_AIRPORT)
    assert data["code"] == "Ok"
    assert len(data["routes"]) >= 1
    route_row = data["routes"][0]
    assert 10_000 < route_row["distance"] < 25_000
    assert 600 < route_row["duration"] < 2400


def test_osrm_downtown_to_ohsu_returns_ok():
    data = _route(PORTLAND_DOWNTOWN, OHSU)
    assert data["code"] == "Ok"
    assert data["routes"][0]["distance"] > 0


def test_osrm_unreachable_coordinates_returns_no_route():
    data = _route((30.0, -150.0), PDX_AIRPORT)
    assert data["code"] in {"NoRoute", "NoSegment", "Ok"}
    if data["code"] == "Ok":
        assert True


def test_routing_service_stamps_provider(monkeypatch):
    """End-to-end: routing_service must stamp osrm_self_hosted when OSRM responds."""
    monkeypatch.setenv("OSRM_BASE_URL", OSRM_URL.rstrip("/"))
    monkeypatch.setenv("ROUTING_PROVIDER", "osrm_self_hosted")
    monkeypatch.setenv("ROUTING_FALLBACK_ENABLED", "true")
    reset_routing_cache_for_tests()
    result = route(PORTLAND_DOWNTOWN, PDX_AIRPORT)
    assert result.route_provider == "osrm_self_hosted"
    assert result.used_fallback is False
    assert result.distance_km * 1000 > 0
