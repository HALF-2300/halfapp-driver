#!/usr/bin/env python3
"""HALFAPP_P0_G2 — OSRM runtime proof for Portland PDX pairs.

Exits 0 when OSRM responds with Ok and routing_service reports osrm_self_hosted
with used_fallback=false. Exits 2 when OSRM is down (honest blocker).

Env:
  OSRM_BASE_URL (default http://127.0.0.1:5000)
  ROUTING_PROVIDER (default osrm_self_hosted)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

# PDX pairs (lat, lon) — same corridor as smoke proofs
PDX_ROUTES = [
    ("Downtown -> PDX", (45.5152, -122.6784), (45.5887, -122.5968)),
    ("Pearl -> Hawthorne", (45.5236, -122.6816), (45.5118, -122.6334)),
    ("OHSU -> Downtown", (45.4994, -122.6862), (45.5152, -122.6765)),
]


def main() -> int:
    os.environ.setdefault("OSRM_BASE_URL", "http://127.0.0.1:5000")
    os.environ.setdefault("ROUTING_PROVIDER", "osrm_self_hosted")
    os.environ.setdefault("ROUTING_FALLBACK_ENABLED", "true")

    import httpx
    from services.osrm_self_hosted_provider import build_route_url, parse_osrm_route_response
    from services.routing_service import reset_routing_cache_for_tests, route

    base = os.environ["OSRM_BASE_URL"].rstrip("/")
    print(f"HALFAPP prove_osrm_runtime — OSRM_BASE_URL={base}")

    try:
        health_url = build_route_url((45.5152, -122.6784), (45.5887, -122.5968), base_url=base)
        resp = httpx.get(health_url, timeout=15.0)
        resp.raise_for_status()
        if resp.json().get("code") != "Ok":
            raise RuntimeError(resp.json())
    except Exception as exc:
        print(f"BLOCKED: OSRM not listening — {exc}")
        print("Start: cd docker/osrm-portland && docker compose up -d")
        return 2

    reset_routing_cache_for_tests()
    all_ok = True
    for label, origin, dest in PDX_ROUTES:
        est = route(origin, dest)
        ok = (
            est.route_provider == "osrm_self_hosted"
            and not est.used_fallback
        )
        status = "OK" if ok else "FAIL"
        print(
            f"  [{status}] {label}: provider={est.route_provider} "
            f"used_fallback={est.used_fallback} "
            f"distance_km={est.distance_km} duration_min={est.duration_minutes}"
        )
        if not ok:
            all_ok = False
        # Direct OSRM parse for evidence line
        url = build_route_url(origin, dest, base_url=base)
        raw = httpx.get(url, timeout=15.0).json()
        parsed = parse_osrm_route_response(raw)
        print(
            f"         osrm_raw: {parsed.raw_distance_meters}m "
            f"{parsed.raw_duration_seconds}s"
        )

    if not all_ok:
        print("NO_GO: routing_service did not return osrm_self_hosted without fallback")
        return 1

    print("GO: used_fallback=false provider=osrm_self_hosted (3 PDX routes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
