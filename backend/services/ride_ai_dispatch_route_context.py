"""Mirror of driver-app routeContext.js for runtime proof and server-side validation."""
from __future__ import annotations

from typing import Any, Optional

from services.map_route_foundation import (
    confidence_score,
    route_provider_used_fallback,
    route_source_label,
)

ROUTE_ADVISORY_LABEL = "[ADVISORY · AI ESTIMATE · NOT LIVE TRAFFIC]"


def _normalize_ride(ride: dict[str, Any]) -> dict[str, Any]:
    distance_km = ride.get("distance_km", ride.get("distance"))
    duration_minutes = ride.get("duration_minutes", ride.get("duration"))
    out = dict(ride)
    out["distance_km"] = float(distance_km) if distance_km is not None else None
    out["duration_minutes"] = int(duration_minutes) if duration_minutes is not None else None
    return out


def build_route_context_for_prompt(ride: dict[str, Any]) -> dict[str, Any]:
    """Align with driver-app ``routeContextFromRide`` + ``formatRouteContextForPrompt``."""
    if not ride:
        return {
            "provider": "none",
            "live": False,
            "advisory_label": ROUTE_ADVISORY_LABEL,
            "live_traffic": False,
        }

    normalized = _normalize_ride(ride)
    provider_raw = str(normalized.get("route_provider") or "").lower()
    used_fallback = normalized.get("route_used_fallback") is True or "haversine" in provider_raw
    osrm_grounded = "osrm" in provider_raw and not used_fallback
    has_evidence = normalized.get("route_calculated_at") is not None and (
        normalized.get("distance_km") is not None or normalized.get("duration_minutes") is not None
    )
    live = bool(osrm_grounded and has_evidence)

    provider = normalized.get("route_provider")
    used_fb = (
        normalized.get("route_used_fallback")
        if normalized.get("route_used_fallback") is not None
        else route_provider_used_fallback(provider)
    )

    distance_km = normalized.get("distance_km")
    duration_minutes = normalized.get("duration_minutes")
    distance_meters = (
        round(float(distance_km) * 1000) if distance_km is not None and float(distance_km) >= 0 else None
    )
    duration_seconds = (
        round(int(duration_minutes) * 60) if duration_minutes is not None and int(duration_minutes) > 0 else None
    )

    route_source = normalized.get("route_source") or route_source_label(provider, used_fallback=bool(used_fb))
    confidence = normalized.get("route_provider_confidence") or confidence_score(
        normalized.get("route_confidence"), used_fallback=bool(used_fb)
    )
    if confidence is None and live:
        confidence = 0.91

    return {
        "provider": "osrm" if osrm_grounded else "none",
        "live": live,
        "live_traffic": live,
        "advisory_label": "" if live else ROUTE_ADVISORY_LABEL,
        "route_source": route_source,
        "route_calculated_at": normalized.get("route_calculated_at"),
        "route_provider_confidence": confidence,
        "distance_km": distance_km,
        "distance_meters": distance_meters,
        "duration_minutes": duration_minutes,
        "duration_seconds": duration_seconds,
        "route_used_fallback": used_fallback,
        "evidence": (
            f"OSRM road-network route ({provider_raw})"
            if live
            else (
                f"Route metadata ({provider_raw or 'unknown'}; not OSRM-grounded)"
                if has_evidence
                else None
            )
        ),
        "instruction": (
            "Summarize only the grounded route context above. Do not invent traffic incidents."
            if live
            else "No live traffic source. Provide general advisory only; never claim live traffic conditions."
        ),
    }
