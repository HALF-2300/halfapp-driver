"""
Deprecated: use ``alembic upgrade head`` (P0-G1).

Kept as a thin wrapper for runbooks that still reference this script.
"""

from __future__ import annotations

import os
import subprocess
import sys

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> None:
    url = os.environ.get("DATABASE_URL", "")
    if not url.startswith("postgresql"):
        raise SystemExit("DATABASE_URL must be postgresql+psycopg2://...")
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_ROOT,
        env=os.environ.copy(),
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(result.returncode)
    print("alembic_upgrade_head_ok")


if __name__ == "__main__":
    main()
