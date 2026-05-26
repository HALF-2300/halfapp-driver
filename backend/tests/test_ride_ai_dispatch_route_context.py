"""Python mirror of driver-app routeContext for runtime proof."""
from __future__ import annotations

from services.ride_ai_dispatch_route_context import (
    ROUTE_ADVISORY_LABEL,
    build_route_context_for_prompt,
)


def test_osrm_grounded_context_is_live():
    ctx = build_route_context_for_prompt(
        {
            "route_provider": "osrm_self_hosted",
            "route_source": "osrm_v5",
            "route_used_fallback": False,
            "route_calculated_at": "2026-05-25T18:43:11Z",
            "route_provider_confidence": 0.91,
            "distance_km": 11.2,
            "duration_minutes": 16,
        }
    )
    assert ctx["live"] is True
    assert ctx["route_source"] == "osrm_v5"
    assert ctx["distance_meters"] == 11200
    assert ctx["duration_seconds"] == 960
    assert ctx["advisory_label"] == ""


def test_haversine_fallback_keeps_advisory():
    ctx = build_route_context_for_prompt(
        {
            "route_provider": "haversine_fallback",
            "route_used_fallback": True,
            "route_calculated_at": "2026-05-25T18:43:11Z",
            "distance_km": 4.0,
            "duration_minutes": 12,
        }
    )
    assert ctx["live"] is False
    assert ctx["advisory_label"] == ROUTE_ADVISORY_LABEL
    assert ctx["live_traffic"] is False
