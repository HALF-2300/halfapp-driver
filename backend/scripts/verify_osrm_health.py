#!/usr/bin/env python3
"""Direct OSRM health check (step 3 of docs/RUNTIME_PROOF_PROCEDURE.md)."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx

from services.osrm_self_hosted_provider import build_route_url, parse_osrm_route_response

# PDX -> Downtown Portland (same leg as proof script)
_ORIGIN = (45.5898, -122.5951)
_DEST = (45.5152, -122.6784)


def main() -> int:
    base_url = os.getenv("OSRM_BASE_URL", "http://127.0.0.1:5000")
    url = build_route_url(_ORIGIN, _DEST, base_url=base_url)
    print(f"OSRM_BASE_URL={base_url}")
    print(f"GET {url}")
    try:
        response = httpx.get(url, timeout=10.0)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        print("BLOCKED_DEPENDENCY_NOT_RUNNING")
        print(f"error: {exc}")
        return 2

    if payload.get("code") != "Ok":
        print("BLOCKED_DEPENDENCY_NOT_RUNNING")
        print(json.dumps(payload, indent=2))
        return 2

    parsed = parse_osrm_route_response(payload)
    if parsed.raw_distance_meters <= 0 or parsed.raw_duration_seconds <= 0:
        print("BLOCKED_DEPENDENCY_NOT_RUNNING")
        print("error: OSRM returned zero distance or duration")
        return 2

    print("OSRM_HEALTH_OK")
    print(
        json.dumps(
            {
                "code": payload.get("code"),
                "distance_meters": parsed.raw_distance_meters,
                "duration_seconds": parsed.raw_duration_seconds,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
