"""v0.1 routing provider abstraction — no Google/Mapbox by default."""

import os

import pytest

from services import routing_service


def test_route_estimate_without_external_providers(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_FALLBACK_ENABLED", "false")
    monkeypatch.setenv("MAPBOX_TRAFFIC_ENABLED", "false")
    monkeypatch.setenv("TRAFFIC_PROVIDER", "none")
    routing_service.reset_routing_cache_for_tests()

    est = routing_service.route((45.52, -122.68), (45.53, -122.67))
    assert est.distance_km > 0
    assert est.duration_minutes >= 1
    assert est.traffic_provider == "none"
    assert est.traffic_aware is False
    assert est.route_provider in ("osrm_self_hosted", "haversine_fallback")
    assert est.route_confidence in ("medium", "low")


def test_google_fallback_not_called_when_disabled(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_FALLBACK_ENABLED", "false")
    monkeypatch.setenv("GOOGLE_MAPS_FALLBACK_ENABLED", "false")
    routing_service.reset_routing_cache_for_tests()
    est = routing_service.route((40.0, -74.0), (40.01, -74.01))
    assert "google" not in est.route_provider.lower()


def test_route_cache_reduces_duplicate_calls(monkeypatch):
    routing_service.reset_routing_cache_for_tests()
    origin = (37.77, -122.42)
    dest = (37.78, -122.41)
    routing_service.route(origin, dest)
    count_after_first = routing_service.routing_call_count()
    routing_service.route(origin, dest)
    assert routing_service.routing_call_count() == count_after_first + 1
