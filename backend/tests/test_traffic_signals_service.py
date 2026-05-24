"""Free official traffic signals — region, failure-safety, no paid providers."""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from services import routing_service
from services.traffic_region import traffic_region_for_point
from services.traffic_signals_service import (
    TrafficSignal,
    compute_eta_buffer_minutes,
    fetch_odot_signals,
    fetch_wsdot_signals,
    filter_signals_near_route,
    reset_traffic_cache_for_tests,
    resolve_traffic_signals_for_route,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    reset_traffic_cache_for_tests()
    routing_service.reset_routing_cache_for_tests()
    yield
    reset_traffic_cache_for_tests()
    routing_service.reset_routing_cache_for_tests()


def test_portland_region_is_odot():
    assert traffic_region_for_point(45.523, -122.676) == "odot_tripcheck"


def test_vancouver_wa_region_is_wsdot():
    assert traffic_region_for_point(45.638, -122.673) == "wsdot"


def test_montreal_has_no_regional_provider():
    assert traffic_region_for_point(45.501, -73.567) == "none"


def test_resolve_signals_skipped_when_disabled():
    result = resolve_traffic_signals_for_route(
        (45.52, -122.68),
        (45.55, -122.61),
        enabled=False,
    )
    assert result.provider == "none"
    assert result.fetch_status == "skipped"
    assert result.traffic_signal_aware is False
    assert result.signals == []


def test_resolve_signals_unavailable_without_api_key(monkeypatch):
    import services.traffic_signals_service as tss

    monkeypatch.setattr(tss, "TRAFFIC_SIGNALS_ENABLED", True)
    monkeypatch.setattr(tss, "ODOT_TRIPCHECK_SUBSCRIPTION_KEY", "")
    result = tss.resolve_traffic_signals_for_route(
        (45.52, -122.68),
        (45.55, -122.61),
        enabled=True,
    )
    assert result.provider == "odot_tripcheck"
    assert result.fetch_status == "unavailable"
    assert result.traffic_signal_aware is False


def test_filter_near_route():
    origin = (45.52, -122.68)
    dest = (45.55, -122.61)
    signals = [
        TrafficSignal(
            id="near",
            provider="odot_tripcheck",
            kind="incident",
            title="Crash",
            latitude=45.53,
            longitude=-122.65,
        ),
        TrafficSignal(
            id="far",
            provider="odot_tripcheck",
            kind="incident",
            title="Far",
            latitude=44.0,
            longitude=-121.0,
        ),
    ]
    nearby = filter_signals_near_route(signals, origin, dest)
    assert len(nearby) == 1
    assert nearby[0].id == "near"


def test_eta_buffer_caps_at_ten():
    assert compute_eta_buffer_minutes(0) == 0
    assert compute_eta_buffer_minutes(2) == 4
    assert compute_eta_buffer_minutes(10) == 10


def test_fetch_wsdot_parses_json(monkeypatch):
    import services.traffic_signals_service as tss

    monkeypatch.setattr(tss, "WSDOT_ACCESS_CODE", "test-code")
    sample = [
        {
            "AlertID": 1,
            "Latitude": 45.63,
            "Longitude": -122.67,
            "HeadlineDescription": "Collision",
            "EventCategory": "Collision",
        }
    ]

    class FakeResponse:
        def __init__(self, body):
            self._body = body

        def raise_for_status(self):
            return None

        def json(self):
            return self._body

        @property
        def is_success(self):
            return True

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url, params=None):
            if "TrafficFlow" in url:
                return FakeResponse([])
            return FakeResponse(sample)

    with patch("services.traffic_signals_service.httpx.Client", FakeClient):
        signals = tss.fetch_wsdot_signals()
    assert len(signals) >= 1
    assert signals[0].provider == "wsdot"


def test_fetch_odot_failure_returns_empty(monkeypatch):
    import services.traffic_signals_service as tss

    monkeypatch.setattr(tss, "ODOT_TRIPCHECK_SUBSCRIPTION_KEY", "bad-key")

    def boom(*args, **kwargs):
        raise ConnectionError("network down")

    with patch("services.traffic_signals_service.httpx.Client", side_effect=boom):
        assert tss.fetch_odot_signals() == []


def test_routing_stays_not_traffic_aware_with_signals(monkeypatch):
    monkeypatch.setattr(routing_service.traffic_signals_service, "TRAFFIC_SIGNALS_ENABLED", True)
    signals = [
        TrafficSignal(
            id="n1",
            provider="odot_tripcheck",
            kind="incident",
            title="Slow",
            latitude=45.525,
            longitude=-122.670,
        )
    ]

    routing_service.reset_routing_cache_for_tests()
    with patch(
        "services.traffic_signals_service.resolve_traffic_signals_for_route",
        return_value=type(
            "R",
            (),
            {
                "provider": "odot_tripcheck",
                "signals": signals,
                "traffic_signal_aware": True,
                "route_confidence": "medium",
                "eta_buffer_minutes": 2,
                "fetch_status": "ok",
                "warning": None,
            },
        )(),
    ):
        est = routing_service.route((45.52, -122.68), (45.53, -122.67))
    assert est.traffic_aware is False
    assert est.traffic_signal_aware is True
    assert est.traffic_provider == "odot_tripcheck"
    assert est.duration_minutes >= 1


def test_traffic_signals_api_returns_without_crashing():
    import uuid
    from fastapi.testclient import TestClient

    from database import SessionLocal
    from main import app
    from models.user import UserRole
    from services.auth import create_access_token, create_user

    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:8]
        u = create_user(
            db,
            f"traffic_{uid}@example.com",
            "Traffic Driver",
            "pw12345",
            UserRole.DRIVER,
            f"T{uid}",
            driver_approval_status="approved",
        )
        db.commit()
        token = create_access_token(sub=u.email, role=u.role.value)
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {token}"}
    with TestClient(app) as client:
        resp = client.get(
            "/drivers/traffic-signals",
            headers=headers,
            params={
                "origin_lat": 45.52,
                "origin_lng": -122.68,
                "destination_lat": 45.55,
                "destination_lng": -122.61,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["traffic_aware"] is False
        assert "disclaimer" in body
