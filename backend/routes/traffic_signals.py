"""Driver-facing free official traffic signals (ODOT / WSDOT) — failure-safe."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from services.rbac import AuthPrincipal, require_role
from models.user import UserRole
from services.traffic_signals_service import (
    TRAFFIC_SIGNALS_ENABLED,
    resolve_traffic_signals_for_bbox,
    resolve_traffic_signals_for_route,
    signal_to_dict,
)

router = APIRouter(prefix="/drivers", tags=["drivers", "traffic"])
DRIVER_ACCESS = require_role("driver")


class TrafficSignalView(BaseModel):
    id: str
    provider: str
    kind: str
    title: str
    latitude: float
    longitude: float
    severity: str = "medium"
    description: str = ""
    category: str = ""


class TrafficSignalsResponse(BaseModel):
    provider: str
    traffic_aware: bool = Field(
        False,
        description="Always false in v0.1 — no route-level live traffic timing",
    )
    traffic_signal_aware: bool
    route_confidence: str
    fetch_status: str
    signals: list[TrafficSignalView] = Field(default_factory=list)
    eta_buffer_minutes: int = 0
    disclaimer: str = (
        "Official ODOT/WSDOT incident and flow signals only — not Google-level street traffic"
    )
    warning: Optional[str] = None


def _to_response(result) -> TrafficSignalsResponse:
    return TrafficSignalsResponse(
        provider=result.provider,
        traffic_signal_aware=result.traffic_signal_aware,
        route_confidence=result.route_confidence,
        fetch_status=result.fetch_status,
        signals=[TrafficSignalView(**signal_to_dict(s)) for s in result.signals],
        eta_buffer_minutes=result.eta_buffer_minutes,
        warning=result.warning,
    )


@router.get("/traffic-signals", response_model=TrafficSignalsResponse)
def get_traffic_signals(
    _principal: AuthPrincipal = Depends(DRIVER_ACCESS),
    min_lat: Optional[float] = Query(None, ge=-90, le=90),
    max_lat: Optional[float] = Query(None, ge=-90, le=90),
    min_lng: Optional[float] = Query(None, ge=-180, le=180),
    max_lng: Optional[float] = Query(None, ge=-180, le=180),
    origin_lat: Optional[float] = Query(None, ge=-90, le=90),
    origin_lng: Optional[float] = Query(None, ge=-180, le=180),
    destination_lat: Optional[float] = Query(None, ge=-90, le=90),
    destination_lng: Optional[float] = Query(None, ge=-180, le=180),
):
    """
    Optional map overlay data from free official feeds.
    Never blocks booking — returns empty signals on failure or when disabled.
    """
    try:
        if (
            origin_lat is not None
            and origin_lng is not None
            and destination_lat is not None
            and destination_lng is not None
        ):
            result = resolve_traffic_signals_for_route(
                (origin_lat, origin_lng),
                (destination_lat, destination_lng),
                enabled=TRAFFIC_SIGNALS_ENABLED,
            )
            return _to_response(result)

        if (
            min_lat is not None
            and max_lat is not None
            and min_lng is not None
            and max_lng is not None
        ):
            result = resolve_traffic_signals_for_bbox(
                min_lat=min(min_lat, max_lat),
                max_lat=max(min_lat, max_lat),
                min_lng=min(min_lng, max_lng),
                max_lng=max(min_lng, max_lng),
                enabled=TRAFFIC_SIGNALS_ENABLED,
            )
            return _to_response(result)

        return TrafficSignalsResponse(
            provider="none",
            traffic_signal_aware=False,
            route_confidence="low",
            fetch_status="skipped",
            warning="Provide origin/destination or bounding box query params",
        )
    except Exception:
        return TrafficSignalsResponse(
            provider="none",
            traffic_signal_aware=False,
            route_confidence="low",
            fetch_status="error",
            warning="Traffic signals temporarily unavailable",
        )
