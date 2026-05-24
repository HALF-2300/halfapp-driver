#!/usr/bin/env python3
"""Portland OSRM runtime proof (HALFAPP_OSRM_RUNTIME_PROOF_PORTLAND_01).

Prerequisite: ``python scripts/verify_osrm_health.py`` must exit 0 first.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.osrm_self_hosted_provider import build_route_url, parse_osrm_route_response
from services.osrm_runtime_truth import PROVED_OSRM_RUNTIME_CLAIM, evidence_path
from services.routing_service import route, reset_routing_cache_for_tests

PDX = (45.5898, -122.5951)
DOWNTOWN = (45.5152, -122.6784)
BEAVERTON = (45.4871, -122.8037)
GRESHAM = (45.5001, -122.4302)
VANCOUVER_WA_TEST = (45.6387, -122.6615)

PROOF_ROUTES = [
    ("PDX Airport -> Downtown Portland", PDX, DOWNTOWN),
    ("Downtown Portland -> Beaverton", DOWNTOWN, BEAVERTON),
    ("Downtown Portland -> Gresham", DOWNTOWN, GRESHAM),
]

OPTIONAL_TEST_ROUTES = [
    ("Portland -> Vancouver WA (test only)", DOWNTOWN, VANCOUVER_WA_TEST),
]


def _health_check(base_url: str) -> dict:
    url = build_route_url(PDX, DOWNTOWN, base_url=base_url)
    response = httpx.get(url, timeout=10.0)
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") != "Ok":
        raise RuntimeError(f"OSRM health check failed: {payload}")
    parsed = parse_osrm_route_response(payload)
    return {
        "url": url,
        "code": payload.get("code"),
        "distance_meters": parsed.raw_distance_meters,
        "duration_seconds": parsed.raw_duration_seconds,
    }


def _print_route(label: str, origin: tuple[float, float], dest: tuple[float, float]) -> dict:
    est = route(origin, dest)
    print(f"=== {label} ===")
    print(f"  route_provider:      {est.route_provider}")
    print(f"  route_confidence:    {est.route_confidence}")
    print(f"  used_fallback:       {est.used_fallback}")
    print(f"  distance_km:         {est.distance_km}")
    print(f"  distance_miles:      {est.distance_miles}")
    print(f"  duration_minutes:    {est.duration_minutes}")
    print(f"  traffic_provider:    {est.traffic_provider}")
    print(f"  traffic_aware:       {est.traffic_aware}")
    print(f"  route_calculated_at: {est.route_calculated_at.isoformat()}")
    print()
    return {
        "label": label,
        "origin": {"lat": origin[0], "lng": origin[1]},
        "destination": {"lat": dest[0], "lng": dest[1]},
        "route_provider": est.route_provider,
        "used_fallback": est.used_fallback,
        "distance_km": est.distance_km,
        "duration_minutes": est.duration_minutes,
        "traffic_provider": est.traffic_provider,
        "traffic_aware": est.traffic_aware,
    }


def _prove_snapshot_row() -> dict:
    from database import SessionLocal
    from models.ride import Ride
    from services.route_snapshots import list_route_snapshots_for_ride
    from services.routing_service import RouteEstimate
    from services.route_snapshots import create_route_snapshot

    db = SessionLocal()
    try:
        ride = Ride(customer_name="OSRM Proof", status="requested", distance=0.0, duration=0)
        db.add(ride)
        db.flush()
        est = route(PDX, DOWNTOWN)
        if est.used_fallback:
            raise RuntimeError("Cannot persist snapshot proof: routing used fallback")
        row = create_route_snapshot(
            db,
            ride=ride,
            route_result=RouteEstimate(
                distance_km=est.distance_km,
                duration_minutes=est.duration_minutes,
                distance_miles=est.distance_miles,
                route_provider=est.route_provider,
                traffic_provider=est.traffic_provider,
                traffic_aware=est.traffic_aware,
                traffic_signal_aware=est.traffic_signal_aware,
                route_confidence=est.route_confidence,
                route_calculated_at=est.route_calculated_at,
                used_fallback=est.used_fallback,
            ),
            snapshot_role="diagnostic",
        )
        db.commit()
        snapshots = list_route_snapshots_for_ride(db, ride_id=ride.id)
        return {
            "ride_id": ride.id,
            "snapshot_id": row.id,
            "snapshot_role": row.snapshot_role,
            "route_provider": row.route_provider,
            "used_fallback": bool(row.used_fallback),
            "distance_meters": row.distance_meters,
            "duration_seconds": row.duration_seconds,
            "snapshot_count": len(snapshots),
        }
    finally:
        db.close()


def _prove_fallback_honest(base_url: str) -> dict:
    """With fallback enabled, unreachable OSRM must still return haversine_fallback."""
    os.environ["ROUTING_FALLBACK_ENABLED"] = "true"
    os.environ["OSRM_BASE_URL"] = "http://127.0.0.1:59998"
    reset_routing_cache_for_tests()
    est = route(PDX, DOWNTOWN)
    os.environ["OSRM_BASE_URL"] = base_url
    reset_routing_cache_for_tests()
    return {
        "route_provider": est.route_provider,
        "used_fallback": est.used_fallback,
        "note": "OSRM pointed at closed port 59998 with ROUTING_FALLBACK_ENABLED=true",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Portland OSRM runtime proof")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Set ROUTING_FALLBACK_ENABLED=false for proof legs (fail if OSRM down)",
    )
    parser.add_argument(
        "--skip-health",
        action="store_true",
        help="Skip direct health check (not recommended)",
    )
    parser.add_argument(
        "--write-evidence",
        action="store_true",
        help="Write runtime evidence JSON on full GO (enables osrm_runtime_claim)",
    )
    parser.add_argument(
        "--snapshot-proof",
        action="store_true",
        help="Persist one diagnostic route_snapshot row via OSRM",
    )
    parser.add_argument(
        "--skip-fallback-proof",
        action="store_true",
        help="Skip fallback honesty leg",
    )
    args = parser.parse_args()

    base_url = os.getenv("OSRM_BASE_URL", "http://127.0.0.1:5000")
    os.environ.setdefault("ROUTING_PROVIDER", "osrm_self_hosted")
    os.environ["OSRM_BASE_URL"] = base_url
    if args.strict:
        os.environ["ROUTING_FALLBACK_ENABLED"] = "false"
    else:
        os.environ.setdefault("ROUTING_FALLBACK_ENABLED", "true")

    reset_routing_cache_for_tests()

    print(f"ROUTING_PROVIDER={os.getenv('ROUTING_PROVIDER')}")
    print(f"OSRM_BASE_URL={base_url}")
    print(f"ROUTING_FALLBACK_ENABLED={os.getenv('ROUTING_FALLBACK_ENABLED')}")
    print()

    health: dict | None = None
    if not args.skip_health:
        try:
            health = _health_check(base_url)
            print("OSRM_HEALTH_OK")
            print(json.dumps(health, indent=2))
            print()
        except Exception as exc:
            print("BLOCKED_DEPENDENCY_NOT_RUNNING")
            print(f"error: {exc}")
            print("Run: python scripts/verify_osrm_health.py")
            return 2

    proof_rows: list[dict] = []
    all_ok = True
    for label, origin, dest in PROOF_ROUTES:
        row = _print_route(label, origin, dest)
        proof_rows.append(row)
        if row["route_provider"] != "osrm_self_hosted" or row["used_fallback"] is not False:
            all_ok = False

    if os.getenv("PROOF_INCLUDE_VANCOUVER_WA", "").lower() in ("1", "true", "yes"):
        print("--- optional cross-border test (not launch scope) ---")
        for label, origin, dest in OPTIONAL_TEST_ROUTES:
            _print_route(label, origin, dest)

    snapshot_proof: dict | None = None
    if args.snapshot_proof and all_ok:
        try:
            os.environ["OSRM_BASE_URL"] = base_url
            os.environ["ROUTING_FALLBACK_ENABLED"] = "false"
            reset_routing_cache_for_tests()
            snapshot_proof = _prove_snapshot_row()
            print("SNAPSHOT_PROOF_OK")
            print(json.dumps(snapshot_proof, indent=2))
            print()
        except Exception as exc:
            print(f"SNAPSHOT_PROOF_FAILED: {exc}")
            all_ok = False

    fallback_proof: dict | None = None
    if not args.skip_fallback_proof:
        try:
            fallback_proof = _prove_fallback_honest(base_url)
            print("FALLBACK_PROOF_OK")
            print(json.dumps(fallback_proof, indent=2))
            print()
            if fallback_proof["route_provider"] != "haversine_fallback" or not fallback_proof["used_fallback"]:
                print("FALLBACK_PROOF_INVALID")
                all_ok = False
        except Exception as exc:
            print(f"FALLBACK_PROOF_FAILED: {exc}")
            all_ok = False

    if not all_ok:
        print("VERDICT: NO_GO — not all Portland proof legs used osrm_self_hosted without fallback")
        return 1

    print("VERDICT: GO — Portland OSRM runtime proof legs passed")

    if args.write_evidence and health is not None:
        out = evidence_path()
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "slice": "HALFAPP_OSRM_RUNTIME_PROOF_PORTLAND_01",
            "verdict": "GO",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "host_note": os.getenv("HALFAPP_PROOF_HOST_NOTE", ""),
            "osrm_base_url": base_url,
            "routing_provider": os.getenv("ROUTING_PROVIDER"),
            "routing_fallback_enabled_for_proof": os.getenv("ROUTING_FALLBACK_ENABLED"),
            "osrm_runtime_claim": PROVED_OSRM_RUNTIME_CLAIM,
            "health_check": health,
            "proof_routes": proof_rows,
            "snapshot_proof": snapshot_proof,
            "fallback_proof": fallback_proof,
        }
        out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote evidence: {out}")
        print("osrm_runtime_claim may advance from not_proved when API reads this file.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
