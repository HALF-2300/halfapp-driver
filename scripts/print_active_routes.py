#!/usr/bin/env python3
"""Print sorted active FastAPI route paths from backend/main.py (read-only).

Run from repo root:

  py -3.11 scripts/print_active_routes.py

Or from backend/:

  py -3.11 ../scripts/print_active_routes.py
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from main import app  # noqa: E402


def main() -> None:
    paths = sorted(
        {getattr(r, "path", "") for r in app.routes if getattr(r, "path", "")}
    )
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
