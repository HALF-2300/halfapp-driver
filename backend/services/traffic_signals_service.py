"""
Free official traffic signals (ODOT TripCheck, WSDOT Traveler Information).

Failure-safe: never raises to callers; returns empty signals on error or missing credentials.
Not route-level live traffic — incidents/flow warnings only (traffic_aware stays false).
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional
from xml.etree import ElementTree

import httpx

from services.datetime_utils import utc_now_naive
from services.traffic_region import TrafficRegion, traffic_region_for_point, traffic_region_for_route

logger = logging.getLogger(__name__)

TRAFFIC_SIGNALS_ENABLED = os.getenv("TRAFFIC_SIGNALS_ENABLED", "false").lower() == "true"
ODOT_TRIPCHECK_SUBSCRIPTION_KEY = os.getenv("ODOT_TRIPCHECK_SUBSCRIPTION_KEY", "").strip()
ODOT_TRIPCHECK_INCIDENTS_URL = os.getenv(
    "ODOT_TRIPCHECK_INCIDENTS_URL",
    "https://apiportal.odot.state.or.us/tripcheck-api-v1-0/incidents",
).strip()
WSDOT_ACCESS_CODE = os.getenv("WSDOT_ACCESS_CODE", "").strip()
WSDOT_ALERTS_URL = os.getenv(
    "WSDOT_ALERTS_URL",
    "https://www.wsdot.wa.gov/Traffic/api/HighwayAlerts/HighwayAlertsREST.svc/GetAlertsAsJson",
).strip()
WSDOT_TRAFFIC_FLOW_URL = os.getenv(
    "WSDOT_TRAFFIC_FLOW_URL",
    "https://www.wsdot.wa.gov/Traffic/api/TrafficFlow/TrafficFlowREST.svc/GetTrafficFlowsAsJson",
).strip()

_SIGNAL_CACHE: dict[str, tuple[datetime, list["TrafficSignal"]]] = {}
_ODOT_TTL = timedelta(seconds=30)
_WSDOT_TTL = timedelta(seconds=90)
_HTTP_TIMEOUT = 8.0

INCIDENT_BUFFER_KM = 8.0
MAX_ETA_BUFFER_MINUTES = 10
MINUTES_PER_NEARBY_INCIDENT = 2


@dataclass(frozen=True)
class TrafficSignal:
    id: str
    provider: TrafficRegion
    kind: str  # incident | flow | alert
    title: str
    latitude: float
    longitude: float
    severity: str = "medium"
    description: str = ""
    raw_category: str = ""


@dataclass
class TrafficSignalsResult:
    provider: TrafficRegion
    signals: list[TrafficSignal] = field(default_factory=list)
    traffic_signal_aware: bool = False
    route_confidence: str = "low"
    eta_buffer_minutes: int = 0
    fetch_status: str = "skipped"  # ok | unavailable | skipped | error
    warning: Optional[str] = None


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    from math import asin, cos, radians, sin, sqrt

    r = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return r * 2 * asin(sqrt(a))


def _cache_get(key: str, ttl: timedelta) -> Optional[list[TrafficSignal]]:
    row = _SIGNAL_CACHE.get(key)
    if not row:
        return None
    if row[0] < utc_now_naive() - ttl:
        return None
    return row[1]


def _cache_set(key: str, signals: list[TrafficSignal]) -> None:
    _SIGNAL_CACHE[key] = (utc_now_naive(), signals)


def reset_traffic_cache_for_tests() -> None:
    _SIGNAL_CACHE.clear()


def _parse_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_wsdot_alert(item: dict[str, Any]) -> Optional[TrafficSignal]:
    lat = _parse_float(item.get("Latitude") or item.get("StartLatitude"))
    lng = _parse_float(item.get("Longitude") or item.get("StartLongitude"))
    if lat is None or lng is None:
        return None
    alert_id = item.get("AlertID") or item.get("EventId")
    title = (
        str(item.get("HeadlineDescription") or item.get("EventCategory") or "Highway alert")
        .strip()[:120]
    )
    desc = str(item.get("ExtendedDescription") or item.get("Description") or "").strip()[:500]
    return TrafficSignal(
        id=f"wsdot-{alert_id}",
        provider="wsdot",
        kind="incident",
        title=title or "Traffic alert",
        latitude=lat,
        longitude=lng,
        severity="medium",
        description=desc,
        raw_category=str(item.get("EventCategory") or ""),
    )


def _normalize_wsdot_flow(item: dict[str, Any]) -> Optional[TrafficSignal]:
    lat = _parse_float(item.get("Latitude"))
    lng = _parse_float(item.get("Longitude"))
    if lat is None or lng is None:
        return None
    flow_id = item.get("FlowDataID") or item.get("FlowStationLocation", {}).get("Description", "flow")
    reading = str(item.get("FlowReadingValue") or item.get("Reading") or "Unknown")
    heavy = reading in ("Heavy", "StopAndGo", "Moderate")
    return TrafficSignal(
        id=f"wsdot-flow-{flow_id}",
        provider="wsdot",
        kind="flow",
        title=f"Flow: {reading}",
        latitude=lat,
        longitude=lng,
        severity="high" if reading == "StopAndGo" else ("medium" if heavy else "low"),
        description=f"WSDOT traffic flow status: {reading}",
        raw_category=reading,
    )


def _parse_odot_incidents_payload(payload: Any) -> list[TrafficSignal]:
    signals: list[TrafficSignal] = []
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        items = (
            payload.get("incidents")
            or payload.get("Incidents")
            or payload.get("items")
            or [payload]
        )
    else:
        return signals

    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        lat = _parse_float(
            item.get("latitude")
            or item.get("Latitude")
            or item.get("lat")
            or (item.get("location") or {}).get("latitude")
        )
        lng = _parse_float(
            item.get("longitude")
            or item.get("Longitude")
            or item.get("lng")
            or (item.get("location") or {}).get("longitude")
        )
        if lat is None or lng is None:
            continue
        inc_id = item.get("id") or item.get("IncidentID") or idx
        title = str(
            item.get("summary")
            or item.get("Summary")
            or item.get("description")
            or item.get("Description")
            or "ODOT incident"
        )[:120]
        signals.append(
            TrafficSignal(
                id=f"odot-{inc_id}",
                provider="odot_tripcheck",
                kind="incident",
                title=title,
                latitude=lat,
                longitude=lng,
                severity="medium",
                description=title,
                raw_category=str(item.get("type") or item.get("Type") or ""),
            )
        )
    return signals


def _parse_odot_xml(text: str) -> list[TrafficSignal]:
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError:
        return []
    signals: list[TrafficSignal] = []
    for node in root.iter():
        tag = node.tag.split("}")[-1] if "}" in node.tag else node.tag
        if tag.lower() not in ("incident", "item", "event"):
            continue
        lat_el = node.find(".//{*}Latitude") or node.find(".//{*}latitude")
        lng_el = node.find(".//{*}Longitude") or node.find(".//{*}longitude")
        if lat_el is None or lng_el is None or not lat_el.text or not lng_el.text:
            continue
        lat = _parse_float(lat_el.text)
        lng = _parse_float(lng_el.text)
        if lat is None or lng is None:
            continue
        title_el = (
            node.find(".//{*}Summary")
            or node.find(".//{*}Description")
            or node.find(".//{*}summary")
        )
        title = (title_el.text or "ODOT incident").strip()[:120]
        inc_id = node.get("id") or len(signals)
        signals.append(
            TrafficSignal(
                id=f"odot-xml-{inc_id}",
                provider="odot_tripcheck",
                kind="incident",
                title=title,
                latitude=lat,
                longitude=lng,
                severity="medium",
                description=title,
            )
        )
    return signals


def fetch_odot_signals() -> list[TrafficSignal]:
    if not ODOT_TRIPCHECK_SUBSCRIPTION_KEY:
        return []
    cached = _cache_get("odot", _ODOT_TTL)
    if cached is not None:
        return cached

    headers = {"Ocp-Apim-Subscription-Key": ODOT_TRIPCHECK_SUBSCRIPTION_KEY}
    try:
        with httpx.Client(timeout=_HTTP_TIMEOUT) as client:
            resp = client.get(ODOT_TRIPCHECK_INCIDENTS_URL, headers=headers)
            resp.raise_for_status()
            content_type = (resp.headers.get("content-type") or "").lower()
            if "json" in content_type:
                signals = _parse_odot_incidents_payload(resp.json())
            else:
                text = resp.text
                try:
                    signals = _parse_odot_incidents_payload(json.loads(text))
                except json.JSONDecodeError:
                    signals = _parse_odot_xml(text)
    except Exception as exc:
        logger.warning("ODOT TripCheck fetch failed: %s", exc)
        return []

    _cache_set("odot", signals)
    return signals


def fetch_wsdot_signals() -> list[TrafficSignal]:
    if not WSDOT_ACCESS_CODE:
        return []
    cached = _cache_get("wsdot", _WSDOT_TTL)
    if cached is not None:
        return cached

    signals: list[TrafficSignal] = []
    try:
        with httpx.Client(timeout=_HTTP_TIMEOUT) as client:
            alerts_resp = client.get(
                WSDOT_ALERTS_URL,
                params={"AccessCode": WSDOT_ACCESS_CODE},
            )
            alerts_resp.raise_for_status()
            alerts_body = alerts_resp.json()
            alert_items = alerts_body if isinstance(alerts_body, list) else alerts_body.get("Alerts", [])
            for item in alert_items:
                if isinstance(item, dict):
                    sig = _normalize_wsdot_alert(item)
                    if sig:
                        signals.append(sig)

            try:
                flow_resp = client.get(
                    WSDOT_TRAFFIC_FLOW_URL,
                    params={"AccessCode": WSDOT_ACCESS_CODE},
                )
                if flow_resp.is_success:
                    flow_body = flow_resp.json()
                    flow_items = flow_body if isinstance(flow_body, list) else []
                    for item in flow_items:
                        if isinstance(item, dict):
                            sig = _normalize_wsdot_flow(item)
                            if sig and sig.severity in ("medium", "high"):
                                signals.append(sig)
            except Exception as flow_exc:
                logger.debug("WSDOT traffic flow fetch skipped: %s", flow_exc)
    except Exception as exc:
        logger.warning("WSDOT traveler info fetch failed: %s", exc)
        return []

    _cache_set("wsdot", signals)
    return signals


def fetch_signals_for_provider(provider: TrafficRegion) -> list[TrafficSignal]:
    if provider == "odot_tripcheck":
        return fetch_odot_signals()
    if provider == "wsdot":
        return fetch_wsdot_signals()
    return []


def filter_signals_near_route(
    signals: list[TrafficSignal],
    origin: tuple[float, float],
    destination: tuple[float, float],
    *,
    buffer_km: float = INCIDENT_BUFFER_KM,
) -> list[TrafficSignal]:
    if not signals:
        return []
    mid_lat = (origin[0] + destination[0]) / 2
    mid_lng = (origin[1] + destination[1]) / 2
    nearby: list[TrafficSignal] = []
    for sig in signals:
        d_origin = _haversine_km(origin[0], origin[1], sig.latitude, sig.longitude)
        d_dest = _haversine_km(destination[0], destination[1], sig.latitude, sig.longitude)
        d_mid = _haversine_km(mid_lat, mid_lng, sig.latitude, sig.longitude)
        if min(d_origin, d_dest, d_mid) <= buffer_km:
            nearby.append(sig)
    return nearby


def filter_signals_in_bbox(
    signals: list[TrafficSignal],
    *,
    min_lat: float,
    max_lat: float,
    min_lng: float,
    max_lng: float,
) -> list[TrafficSignal]:
    return [
        s
        for s in signals
        if min_lat <= s.latitude <= max_lat and min_lng <= s.longitude <= max_lng
    ]


def compute_eta_buffer_minutes(nearby_count: int) -> int:
    if nearby_count <= 0:
        return 0
    return min(MAX_ETA_BUFFER_MINUTES, nearby_count * MINUTES_PER_NEARBY_INCIDENT)


def resolve_traffic_signals_for_route(
    origin: tuple[float, float],
    destination: tuple[float, float],
    *,
    enabled: Optional[bool] = None,
) -> TrafficSignalsResult:
    """
    Load regional official signals and compute optional ETA buffer.
    Never raises; safe for ride booking paths.
    """
    if enabled is None:
        enabled = TRAFFIC_SIGNALS_ENABLED

    provider = traffic_region_for_route(origin, destination)
    if not enabled or provider == "none":
        return TrafficSignalsResult(provider="none", fetch_status="skipped")

    if provider == "odot_tripcheck" and not ODOT_TRIPCHECK_SUBSCRIPTION_KEY:
        return TrafficSignalsResult(
            provider=provider,
            fetch_status="unavailable",
            route_confidence="low",
            warning="ODOT TripCheck API key not configured",
        )
    if provider == "wsdot" and not WSDOT_ACCESS_CODE:
        return TrafficSignalsResult(
            provider=provider,
            fetch_status="unavailable",
            route_confidence="low",
            warning="WSDOT access code not configured",
        )

    all_signals = fetch_signals_for_provider(provider)
    nearby = filter_signals_near_route(all_signals, origin, destination)
    buffer = compute_eta_buffer_minutes(len(nearby))
    signal_aware = len(nearby) > 0
    confidence = "medium" if signal_aware or len(all_signals) > 0 else "low"

    return TrafficSignalsResult(
        provider=provider,
        signals=nearby,
        traffic_signal_aware=signal_aware,
        route_confidence=confidence,
        eta_buffer_minutes=buffer,
        fetch_status="ok" if all_signals else "unavailable",
        warning=None
        if all_signals
        else "No traffic signals returned from official feed",
    )


def resolve_traffic_signals_for_bbox(
    *,
    min_lat: float,
    max_lat: float,
    min_lng: float,
    max_lng: float,
    enabled: Optional[bool] = None,
) -> TrafficSignalsResult:
    if enabled is None:
        enabled = TRAFFIC_SIGNALS_ENABLED

    center_lat = (min_lat + max_lat) / 2
    center_lng = (min_lng + max_lng) / 2
    provider = traffic_region_for_point(center_lat, center_lng)
    if not enabled or provider == "none":
        return TrafficSignalsResult(provider="none", fetch_status="skipped")

    all_signals = fetch_signals_for_provider(provider)
    in_view = filter_signals_in_bbox(
        all_signals, min_lat=min_lat, max_lat=max_lat, min_lng=min_lng, max_lng=max_lng
    )
    return TrafficSignalsResult(
        provider=provider,
        signals=in_view[:50],
        traffic_signal_aware=len(in_view) > 0,
        route_confidence="medium" if in_view else "low",
        fetch_status="ok" if all_signals else "unavailable",
    )


def signal_to_dict(sig: TrafficSignal) -> dict[str, Any]:
    return {
        "id": sig.id,
        "provider": sig.provider,
        "kind": sig.kind,
        "title": sig.title,
        "latitude": sig.latitude,
        "longitude": sig.longitude,
        "severity": sig.severity,
        "description": sig.description,
        "category": sig.raw_category,
    }
