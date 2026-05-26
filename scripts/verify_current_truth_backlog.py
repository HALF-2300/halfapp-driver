#!/usr/bin/env python3
"""Read-only doc sync checks for HALFAPP_TRUTH_SYNC_BACKLOG_RECONCILIATION_01."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    path = ROOT / rel
    if not path.is_file():
        raise FileNotFoundError(rel)
    return path.read_text(encoding="utf-8")


def _require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise AssertionError(f"Missing {label}: {needle!r}")


def main() -> int:
    backlog = _read("docs/BACKLOG.md")
    truth = _read("docs/CURRENT_TRUTH.md")

    # BACKLOG must not read like greenfield P0 rebuild
    for closed in (
        "AUTH-001",
        "RIDE-001",
        "RIDE-002",
        "RIDE-003",
        "HALFAPP_PRODUCTION_SECRET_KEY_GUARD_01",
        "HALFAPP_ENGINEERING_INTELLIGENCE_SAFE_SHELL_01",
        "Do not reopen without rescope",
        "DONE_PROVEN",
        "Next executable work queue",
    ):
        _require(backlog, closed, f"BACKLOG.md/{closed}")

    _require(backlog, "STALE_OR_SUPERSEDED", "BACKLOG.md/superseded ticket 6.1")
    _require(backlog, "OSRM runtime proof", "BACKLOG.md/P0 OSRM")

    # CURRENT_TRUTH forbidden / status boundaries
    for needle in (
        "Current state table",
        "Do not reopen without rescope",
        "HALFAPP_PRODUCTION_SECRET_KEY_GUARD_01",
        "HALFAPP_ENGINEERING_INTELLIGENCE_SAFE_SHELL_01",
        "OSRM runtime",
        "NO_GO",
        "PARALLEL_NOT_WIRED",
        "LOCAL_CONTEXT_ONLY",
        "NOT IMPLEMENTED",
        "383 passed, 9 skipped",
        "HALFAPP_COMPREHENSIVE_PROGRAM_REPORT_03",
    ):
        _require(truth, needle, f"CURRENT_TRUTH.md/{needle}")

    _require(truth, "No payment processing", "CURRENT_TRUTH.md/payment boundary")

    print("verify_current_truth_backlog: OK")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, FileNotFoundError) as exc:
        print(f"verify_current_truth_backlog: FAIL — {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
