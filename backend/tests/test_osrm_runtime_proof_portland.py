"""Live Portland OSRM runtime proof — skipped unless OSRM is up and env gate is set."""

from __future__ import annotations

import os

import httpx
import pytest

from services.osrm_self_hosted_provider import build_route_url
from services.routing_service import route, reset_routing_cache_for_tests

PDX = (45.5898, -122.5951)
DOWNTOWN = (45.5152, -122.6784)


def _osrm_live() -> bool:
    if os.getenv("HALFAPP_OSRM_RUNTIME_PROOF", "").lower() not in ("1", "true", "yes"):
        return False
    base = os.getenv("OSRM_BASE_URL", "http://127.0.0.1:5000")
    url = build_route_url(PDX, DOWNTOWN, base_url=base)
    try:
        response = httpx.get(url, timeout=5.0)
        payload = response.json()
        return response.status_code == 200 and payload.get("code") == "Ok"
    except Exception:
        return False


@pytest.mark.skipif(not _osrm_live(), reason="Set HALFAPP_OSRM_RUNTIME_PROOF=1 with OSRM on :5000")
def test_portland_route_uses_osrm_without_fallback(monkeypatch):
    monkeypatch.setenv("ROUTING_PROVIDER", "osrm_self_hosted")
    monkeypatch.setenv("ROUTING_FALLBACK_ENABLED", "false")
    monkeypatch.setenv("OSRM_BASE_URL", os.getenv("OSRM_BASE_URL", "http://127.0.0.1:5000"))
    reset_routing_cache_for_tests()
    est = route(PDX, DOWNTOWN)
    assert est.route_provider == "osrm_self_hosted"
    assert est.used_fallback is False
    assert est.distance_km > 0
    assert est.duration_minutes > 0
