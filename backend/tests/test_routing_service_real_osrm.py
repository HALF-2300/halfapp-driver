"""OSRM runtime integration — skipped unless OSRM_RUNTIME_URL or OSRM_BASE_URL is reachable."""

from __future__ import annotations

import os

import httpx
import pytest

from services.routing_service import reset_routing_cache_for_tests, route

OSRM_BASE = os.environ.get("OSRM_RUNTIME_URL") or os.environ.get("OSRM_BASE_URL", "").strip()

pytestmark = pytest.mark.skipif(
    not OSRM_BASE,
    reason="Set OSRM_RUNTIME_URL or OSRM_BASE_URL to run real OSRM routing tests.",
)


def _osrm_up() -> bool:
    try:
        from services.osrm_self_hosted_provider import build_route_url

        url = build_route_url((45.5152, -122.6784), (45.5887, -122.5968), base_url=OSRM_BASE)
        resp = httpx.get(url, timeout=5.0)
        return resp.status_code == 200 and resp.json().get("code") == "Ok"
    except Exception:
        return False


@pytest.fixture(autouse=True)
def _routing_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OSRM_BASE_URL", OSRM_BASE.rstrip("/"))
    monkeypatch.setenv("ROUTING_PROVIDER", "osrm_self_hosted")
    monkeypatch.setenv("ROUTING_FALLBACK_ENABLED", "true")
    reset_routing_cache_for_tests()
    yield
    reset_routing_cache_for_tests()


@pytest.mark.skipif(not _osrm_up(), reason="OSRM not reachable at configured base URL")
def test_routing_service_real_osrm_no_fallback():
    est = route((45.5152, -122.6784), (45.5887, -122.5968))
    assert est.route_provider == "osrm_self_hosted"
    assert est.used_fallback is False
    assert est.distance_km > 0
    assert est.duration_minutes > 0
