"""Honesty + privacy gates for Street Intelligence Layer (SIL)."""

from __future__ import annotations

import os
import re

from services.sil_labels import SLOW_LAYER_LABEL

MIN_UNIQUE_DRIVERS = int(os.getenv("SIL_MIN_UNIQUE_DRIVERS", "3"))
MIN_FLEET_SAMPLES = int(os.getenv("SIL_MIN_FLEET_SAMPLES", "20"))
MIN_DEMAND_COUNT = int(os.getenv("SIL_MIN_DEMAND", "5"))
MIN_CONFIDENCE_DEFAULT = float(os.getenv("SIL_MIN_CONF", "0.4"))

_FORBIDDEN_LIVE_TRAFFIC = re.compile(r"(?<!\bfleet-)\blive traffic\b", re.IGNORECASE)


def thresholds() -> dict[str, int | float]:
    return {
        "min_unique_drivers": MIN_UNIQUE_DRIVERS,
        "min_fleet_samples": MIN_FLEET_SAMPLES,
        "min_demand": MIN_DEMAND_COUNT,
        "min_confidence": MIN_CONFIDENCE_DEFAULT,
    }


def slow_layer_min_k_met(*, unique_drivers: int, fleet_samples: int) -> bool:
    return unique_drivers >= MIN_UNIQUE_DRIVERS and fleet_samples >= MIN_FLEET_SAMPLES


def busy_layer_min_k_met(*, demand_count: int) -> bool:
    return demand_count >= MIN_DEMAND_COUNT


def cell_passes_confidence(confidence: float, min_conf: float | None = None) -> bool:
    floor = MIN_CONFIDENCE_DEFAULT if min_conf is None else min_conf
    return confidence >= floor


def assert_no_unqualified_live_traffic(text: str) -> None:
    """Gate G1 — unqualified 'live traffic' is forbidden in SIL copy."""
    if _FORBIDDEN_LIVE_TRAFFIC.search(text) and SLOW_LAYER_LABEL not in text:
        raise ValueError("unqualified_live_traffic_claim")


def proof_level_for_route(*, route_method: str, used_fallback: bool) -> str:
    """Gate G2 — fallback cannot be road-accurate proof."""
    if used_fallback or route_method == "fallback_straight_line":
        return "B_APPROXIMATE"
    if route_method == "osrm_route":
        return "A_ROAD_ACCURATE"
    return "C_NONE"
