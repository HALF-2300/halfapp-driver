#!/usr/bin/env python3
"""Owner runbook API verification — HALFAPP_DRIVER_STABLE_CAR_P0_01."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]

TESTS = [
    "tests/test_stable_car_p0_01.py",
    "tests/test_ride_flow_ui_proof.py",
    "tests/test_rider_auth.py",
    "tests/test_rider_ride_stream.py",
    "tests/test_ops_phase4.py",
    "tests/test_active_ride_recovery.py",
    "tests/test_driver_ride_idempotency_slice03.py",
    "tests/test_ride_claim_lock_concurrency.py",
    "tests/test_ride_pool_sse.py",
]


def main() -> int:
    cmd = [sys.executable, "-m", "pytest", "-q", *TESTS]
    print("HALFAPP_DRIVER_STABLE_CAR_P0_01 — runbook API verify")
    print(" ".join(cmd))
    result = subprocess.run(cmd, cwd=BACKEND)
    if result.returncode == 0:
        print("RUNBOOK API PASS")
    else:
        print("RUNBOOK API FAIL", file=sys.stderr)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
