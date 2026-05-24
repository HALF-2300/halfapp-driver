"""
Generate the current OpenAPI path snapshot. Compare to checked-in snapshot.

If different, fail with a diff. To update intentionally:

    pytest tests/test_openapi_surface_does_not_drift.py --update-snapshot
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

SNAPSHOT = Path(__file__).parent / "snapshots" / "openapi_paths.json"

DOSSIER_PATHS = (
    "/supply/heartbeat",
    "/demand/request",
    "/trip/complete",
)


def _production_openapi_paths(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    monkeypatch.delenv("HALFAPP_DOSSIER_SPINE_ENABLED", raising=False)
    import main

    importlib.reload(main)
    return sorted(main.app.openapi()["paths"].keys())


def test_openapi_snapshot_matches(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest):
    current_paths = _production_openapi_paths(monkeypatch)

    if request.config.getoption("--update-snapshot"):
        SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT.write_text(json.dumps(current_paths, indent=2) + "\n", encoding="utf-8")
        pytest.skip("Snapshot updated via --update-snapshot")

    if not SNAPSHOT.exists():
        SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT.write_text(json.dumps(current_paths, indent=2) + "\n", encoding="utf-8")
        pytest.skip("Snapshot created on first run.")

    expected_paths = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert current_paths == expected_paths, (
        "OpenAPI path set drifted. Run: "
        "pytest tests/test_openapi_surface_does_not_drift.py --update-snapshot"
    )

    for dossier_path in DOSSIER_PATHS:
        assert dossier_path not in current_paths
