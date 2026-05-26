#!/usr/bin/env python3
"""P0 deployment sanity — ports, CORS, env template (HALFAPP_DRIVER_STABLE_CAR_P0_01)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "backend"
FAILURES: list[str] = []


def ok(msg: str) -> None:
    print(f"  OK  {msg}")


def fail(msg: str) -> None:
    FAILURES.append(msg)
    print(f"  FAIL {msg}")


def check_env_example() -> None:
    env_ex = BACKEND / ".env.example"
    if not env_ex.is_file():
        fail(".env.example missing")
        return
    text = env_ex.read_text(encoding="utf-8")
    for needle in (
        "CORS_ORIGINS",
        "3022",
        "3023",
        "3024",
        "OSRM_BASE_URL",
        "ROUTING_FALLBACK_ENABLED",
        "HALFAPP_OPEN_BOARD_DISPATCH",
    ):
        if needle in text:
            ok(f".env.example contains {needle}")
        else:
            fail(f".env.example missing {needle}")


def check_vite_ports() -> None:
    specs = [
        (REPO / "driver-app" / "vite.config.js", "3022"),
        (REPO / "rider-app" / "vite.config.js", "3023"),
        (REPO / "ops-app" / "vite.config.js", "3024"),
    ]
    for path, port in specs:
        if not path.is_file():
            fail(f"{path.relative_to(REPO)} missing")
            continue
        body = path.read_text(encoding="utf-8")
        if f"port: {port}" in body or f"port:{port}" in body.replace(" ", ""):
            ok(f"{path.parent.name} vite port {port}")
        else:
            fail(f"{path.parent.name} vite.config.js expected port {port}")


def check_runbook() -> None:
    runbook = REPO / "docs" / "OWNER_INTERNAL_TEST_RUNBOOK_01.md"
    if not runbook.is_file():
        fail("OWNER_INTERNAL_TEST_RUNBOOK_01.md missing")
        return
    text = runbook.read_text(encoding="utf-8")
    for port in ("8000", "3022", "3023", "3024"):
        if port in text:
            ok(f"runbook documents port {port}")
        else:
            fail(f"runbook missing port {port}")


def check_cors_resolver() -> None:
    sys.path.insert(0, str(BACKEND))
    try:
        from production_guards import get_cors_origins_for_environment

        origins = get_cors_origins_for_environment(
            "development",
            "http://127.0.0.1:3022,http://127.0.0.1:3023,http://127.0.0.1:3024",
        )
        joined = " ".join(origins)
        for port in ("3022", "3023", "3024"):
            if f":{port}" in joined:
                ok(f"dev CORS includes :{port}")
            else:
                fail(f"dev CORS missing :{port} (got {origins!r})")
    except Exception as exc:
        fail(f"CORS resolver import: {exc}")
    finally:
        if str(BACKEND) in sys.path:
            sys.path.remove(str(BACKEND))


def main() -> int:
    print("HALFAPP_DRIVER_STABLE_CAR_P0_01 — deployment sanity")
    check_env_example()
    check_vite_ports()
    check_runbook()
    check_cors_resolver()
    if FAILURES:
        print(f"\n{len(FAILURES)} failure(s)")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("\nDEPLOYMENT SANITY PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
