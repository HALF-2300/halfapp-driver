"""CLI entry point — run the gate on an MP4 and print the JSON report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .report import build_candidate_quality_report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="CandidateQualityReportV1 — video verification gate",
    )
    parser.add_argument("video", type=Path, help="Path to the MP4 candidate")
    parser.add_argument(
        "--pretty", action="store_true", default=True,
        help="Pretty-print the JSON output (default: yes)",
    )
    parser.add_argument(
        "--compact", action="store_true",
        help="Compact JSON (one line)",
    )
    args = parser.parse_args(argv)

    report = build_candidate_quality_report(args.video)

    indent = None if args.compact else 2
    print(json.dumps(report, indent=indent))

    if report["finalDecision"] == "REJECTED":
        sys.exit(1)
    elif report["finalDecision"] == "WARN_REVIEW_REQUIRED":
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
