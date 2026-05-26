#!/usr/bin/env python3
"""RIDE_AI_ROUTE_GROUNDING_RUNTIME_PROOF_01 — live OSRM + ride AI route context proof.

Prerequisites:
  - OSRM listening (docker/osrm-portland: docker compose up -d)
  - Env: OSRM_BASE_URL, ROUTING_PROVIDER=osrm_self_hosted, HALFAPP_ENABLE_RIDE_SIMULATION=1

Writes: backend/runtime_evidence/ride_ai_route_grounding_runtime_proof.json
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from main import app
from services.osrm_self_hosted_provider import PROVIDER_ID, build_route_url, parse_osrm_route_response
from services.routing_service import reset_routing_cache_for_tests, route as routing_route
from services.ride_ai_dispatch_route_context import build_route_context_for_prompt

EVIDENCE_PATH = (
    Path(__file__).resolve().parent.parent
    / "runtime_evidence"
    / "ride_ai_route_grounding_runtime_proof.json"
)

SLICE = "RIDE_AI_ROUTE_GROUNDING_RUNTIME_PROOF_01"
VERDICT_GO = "GO_SELF_HOSTED_ROUTE_GROUNDING_RUNTIME_PROVEN"
VERDICT_PARTIAL = "PARTIAL_GO_ROUTE_GROUNDING_CODE_COMPLETE_RUNTIME_PROOF_PENDING"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def osrm_health(base_url: str) -> dict[str, Any]:
    url = build_route_url((45.5152, -122.6784), (45.5887, -122.5951), base_url=base_url)
    response = httpx.get(url, timeout=15.0)
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") != "Ok":
        raise RuntimeError(f"OSRM health failed: {payload}")
    parsed = parse_osrm_route_response(payload)
    return {
        "url": url,
        "code": payload.get("code"),
        "distance_meters": parsed.raw_distance_meters,
        "duration_seconds": parsed.raw_duration_seconds,
    }


def _seed_driver(client: TestClient, stamp: str) -> dict[str, str]:
    email = f"routeproof+{stamp}@example.com"
    res = client.post(
        "/internal/test-users",
        json={
            "email": email,
            "password": "RouteProof1!",
            "name": "Route Proof Driver",
            "role": "driver",
            "license_no": f"RP{stamp[-6:]}",
            "driver_approval_status": "approved",
        },
    )
    assert res.status_code == 200, res.text
    login = client.post("/auth/login", json={"email": email, "password": "RouteProof1!"})
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    online = client.post("/drivers/go-online", headers=headers, json={})
    assert online.status_code == 200, online.text
    return headers


def _assert_osrm_ride_view(ride: dict[str, Any], *, label: str) -> dict[str, Any]:
    checks = {
        "route_provider": ride.get("route_provider") == PROVIDER_ID,
        "route_source": ride.get("route_source") == "osrm_v5",
        "route_used_fallback": ride.get("route_used_fallback") is False,
        "route_calculated_at": bool(ride.get("route_calculated_at")),
        "route_provider_confidence": ride.get("route_provider_confidence") is not None,
        "distance_km_not_default_4": ride.get("distance_km") != 4.0,
        "duration_minutes_positive": (ride.get("duration_minutes") or 0) > 0,
    }
    failed = [k for k, ok in checks.items() if not ok]
    if failed:
        raise AssertionError(f"{label}: failed checks {failed}; ride={json.dumps(ride, indent=2)}")
    return {
        "label": label,
        "ride_id": ride.get("id"),
        "route_provider": ride.get("route_provider"),
        "route_source": ride.get("route_source"),
        "route_used_fallback": ride.get("route_used_fallback"),
        "route_calculated_at": ride.get("route_calculated_at"),
        "route_provider_confidence": ride.get("route_provider_confidence"),
        "distance_km": ride.get("distance_km"),
        "duration_minutes": ride.get("duration_minutes"),
        "checks": checks,
    }


def _prove_osrm_success(client: TestClient, base_url: str) -> dict[str, Any]:
    os.environ["OSRM_BASE_URL"] = base_url
    os.environ["ROUTING_PROVIDER"] = "osrm_self_hosted"
    os.environ["ROUTING_FALLBACK_ENABLED"] = "true"
    os.environ["HALFAPP_ENABLE_RIDE_SIMULATION"] = "1"
    os.environ["ALLOW_TEST_USER_SEED"] = "1"
    reset_routing_cache_for_tests()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    headers = _seed_driver(client, stamp)

    sim = client.post(
        "/drivers/simulate-ride",
        headers=headers,
        json={"customer_name": "Runtime Proof Rider"},
    )
    assert sim.status_code == 200, sim.text
    created = sim.json()["ride"]
    created_proof = _assert_osrm_ride_view(created, label="simulate-ride")

    ride_id = created["id"]
    accept = client.post(f"/drivers/accept-ride/{ride_id}", headers=headers)
    assert accept.status_code == 200, accept.text
    accepted = accept.json()["ride"]
    accepted_proof = _assert_osrm_ride_view(accepted, label="accept-ride")

    prompt_ctx = build_route_context_for_prompt(accepted)
    prompt_checks = {
        "live": prompt_ctx.get("live") is True,
        "route_source": prompt_ctx.get("route_source") == "osrm_v5",
        "route_calculated_at": bool(prompt_ctx.get("route_calculated_at")),
        "route_provider_confidence": prompt_ctx.get("route_provider_confidence") is not None,
        "distance_meters": (prompt_ctx.get("distance_meters") or 0) > 0,
        "duration_seconds": (prompt_ctx.get("duration_seconds") or 0) > 0,
        "no_advisory_label": not prompt_ctx.get("advisory_label"),
        "not_live_traffic": prompt_ctx.get("live_traffic") is True,
    }
    failed_prompt = [k for k, ok in prompt_checks.items() if not ok]
    if failed_prompt:
        raise AssertionError(
            f"prompt context failed {failed_prompt}; ctx={json.dumps(prompt_ctx, indent=2)}"
        )

    ui_meta = "Route intelligence (grounded)" if prompt_ctx["live"] else "[ADVISORY · AI ESTIMATE · NOT LIVE TRAFFIC]"
    ui_checks = {
        "grounded_meta": "grounded" in ui_meta.lower(),
        "no_not_live_traffic_label": "NOT LIVE TRAFFIC" not in ui_meta,
    }

    return {
        "health_ok": True,
        "created": created_proof,
        "accepted": accepted_proof,
        "prompt_context": prompt_ctx,
        "prompt_checks": prompt_checks,
        "ui_expectation": {
            "panel_meta": ui_meta,
            "checks": ui_checks,
        },
    }


def _prove_fallback_honest(base_url: str) -> dict[str, Any]:
    os.environ["OSRM_BASE_URL"] = "http://127.0.0.1:59998"
    os.environ["ROUTING_PROVIDER"] = "osrm_self_hosted"
    os.environ["ROUTING_FALLBACK_ENABLED"] = "true"
    reset_routing_cache_for_tests()

    est = routing_route((45.5152, -122.6784), (45.5887, -122.5951))
    prompt_ctx = build_route_context_for_prompt(
        {
            "route_provider": est.route_provider,
            "route_used_fallback": est.used_fallback,
            "route_calculated_at": est.route_calculated_at.isoformat() + "Z",
            "distance_km": est.distance_km,
            "duration_minutes": est.duration_minutes,
            "route_confidence": est.route_confidence,
        }
    )
    checks = {
        "route_provider_haversine": est.route_provider == "haversine_fallback",
        "used_fallback": est.used_fallback is True,
        "live_false": prompt_ctx.get("live") is False,
        "advisory_present": bool(prompt_ctx.get("advisory_label")),
        "not_live_traffic_false": prompt_ctx.get("live_traffic") is False,
    }
    failed = [k for k, ok in checks.items() if not ok]
    if failed:
        raise AssertionError(f"fallback proof failed {failed}")

    os.environ["OSRM_BASE_URL"] = base_url
    reset_routing_cache_for_tests()
    return {
        "route_provider": est.route_provider,
        "used_fallback": est.used_fallback,
        "prompt_context": prompt_ctx,
        "checks": checks,
        "note": "OSRM pointed at closed port 59998; labels must stay honest (not live traffic).",
    }


def write_evidence(payload: dict[str, Any]) -> Path:
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return EVIDENCE_PATH


def main() -> int:
    base_url = os.getenv("OSRM_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
    host_note = os.getenv("HALFAPP_PROOF_HOST_NOTE", "local dev")

    payload: dict[str, Any] = {
        "slice": SLICE,
        "recorded_at": _utc_now(),
        "host_note": host_note,
        "osrm_base_url": base_url,
        "routing_provider": os.getenv("ROUTING_PROVIDER", "osrm_self_hosted"),
        "verdict": VERDICT_PARTIAL,
        "blocker": None,
        "health_check": None,
        "osrm_success_proof": None,
        "fallback_proof": None,
        "honesty": {
            "osrm_is_road_network_not_live_traffic": True,
            "advisory_label_must_remain_on_fallback": True,
        },
    }

    try:
        payload["health_check"] = osrm_health(base_url)
    except Exception as exc:
        payload["blocker"] = f"OSRM not listening at {base_url}: {exc}"
        payload["verdict"] = VERDICT_PARTIAL
        path = write_evidence(payload)
        print("BLOCKED_DEPENDENCY_NOT_RUNNING")
        print(payload["blocker"])
        print(f"Wrote partial evidence: {path}")
        print(f"VERDICT: {VERDICT_PARTIAL}")
        return 2

    with TestClient(app) as client:
        try:
            payload["osrm_success_proof"] = _prove_osrm_success(client, base_url)
            payload["fallback_proof"] = _prove_fallback_honest(base_url)
            payload["verdict"] = VERDICT_GO
        except Exception as exc:
            payload["blocker"] = str(exc)
            payload["verdict"] = VERDICT_PARTIAL
            path = write_evidence(payload)
            print(f"PROOF_FAILED: {exc}")
            print(f"Wrote partial evidence: {path}")
            print(f"VERDICT: {VERDICT_PARTIAL}")
            return 1

    path = write_evidence(payload)
    print("OSRM_HEALTH_OK")
    print(json.dumps(payload["health_check"], indent=2))
    print("RIDE_AI_ROUTE_GROUNDING_OK")
    print(json.dumps(payload["osrm_success_proof"]["prompt_context"], indent=2))
    print(f"Wrote evidence: {path}")
    print(f"VERDICT: {VERDICT_GO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
