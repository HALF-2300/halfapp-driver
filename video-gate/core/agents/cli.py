"""CLI for Agent 2 — The Motion Auditor.

Usage::

    python -m core.agents.agent2 clip.mp4
    python -m core.agents.agent2 clip.mp4 --compact
    python -m core.agents.agent2 clip.mp4 --quiet

Exit codes (same as the inter-agent protocol):
    0  PASS   — temporally stable, cleared for Agent 7
    1  REJECT — broken, Agent 7 is blocked, feedback sent to Agent 1
    2  WARN   — marginal, Agent 7 may proceed with caution
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .agent2 import audit


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="agent2",
        description="Agent 2 — The Motion Auditor.  Intercepts MP4 clips and "
                     "blocks broken ones before they reach Agent 7 (Upscaler).",
    )
    parser.add_argument(
        "video", type=Path,
        help="Path to the MP4 candidate to audit",
    )
    parser.add_argument(
        "--compact", action="store_true",
        help="Emit single-line JSON instead of pretty-printed",
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true",
        help="Suppress log output (only emit the JSON verdict)",
    )
    args = parser.parse_args(argv)

    level = logging.WARNING if args.quiet else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s | %(name)s | %(message)s",
    )

    verdict = audit(args.video)

    indent = None if args.compact else 2
    print(json.dumps(verdict.to_dict(), indent=indent))
    sys.exit(verdict.exit_code)
