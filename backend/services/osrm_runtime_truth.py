"""OSRM runtime claim — only advances from ``not_proved`` when proof evidence exists."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_OSRM_RUNTIME_CLAIM = "not_proved"
DEFAULT_PRODUCTION_ROUTING_CLAIM = "not_proved"
PROVED_OSRM_RUNTIME_CLAIM = "proved_portland_v0_1"

_EVIDENCE_ENV = "HALFAPP_OSRM_RUNTIME_EVIDENCE_PATH"


def _default_evidence_path() -> Path:
    return Path(__file__).resolve().parent.parent / "runtime_evidence" / "osrm_portland_proof.json"


def evidence_path() -> Path:
    import os

    override = os.getenv(_EVIDENCE_ENV)
    if override:
        return Path(override)
    return _default_evidence_path()


def load_osrm_runtime_evidence() -> dict[str, Any] | None:
    path = evidence_path()
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _evidence_is_valid(payload: dict[str, Any]) -> bool:
    if payload.get("verdict") != "GO":
        return False
    if payload.get("slice") != "HALFAPP_OSRM_RUNTIME_PROOF_PORTLAND_01":
        return False
    routes = payload.get("proof_routes")
    if not isinstance(routes, list) or len(routes) < 3:
        return False
    for row in routes:
        if not isinstance(row, dict):
            return False
        if row.get("route_provider") != "osrm_self_hosted":
            return False
        if row.get("used_fallback") is not False:
            return False
    health = payload.get("health_check")
    if not isinstance(health, dict) or health.get("code") != "Ok":
        return False
    return True


def osrm_runtime_claim() -> str:
    payload = load_osrm_runtime_evidence()
    if payload and _evidence_is_valid(payload):
        return str(payload.get("osrm_runtime_claim") or PROVED_OSRM_RUNTIME_CLAIM)
    return DEFAULT_OSRM_RUNTIME_CLAIM


def production_routing_claim() -> str:
    """Production routing remains unproved until a separate launch/runtime lane says otherwise."""
    return DEFAULT_PRODUCTION_ROUTING_CLAIM
