"""HALFAPP_DOSSIER_MOUNT_GATE_01 — dossier routes mount only when env is truthy."""

from __future__ import annotations

import importlib

import pytest


def _openapi_path_keys(monkeypatch: pytest.MonkeyPatch, dossier_env: str | None) -> list[str]:
    if dossier_env is None:
        monkeypatch.delenv("HALFAPP_DOSSIER_SPINE_ENABLED", raising=False)
    else:
        monkeypatch.setenv("HALFAPP_DOSSIER_SPINE_ENABLED", dossier_env)

    import main

    importlib.reload(main)
    return list(main.app.openapi().get("paths", {}).keys())


DOSSIER_ONLY_PATHS = (
    "/supply/heartbeat",
    "/demand/request",
    "/trip/complete",
)


def test_dossier_routes_not_mounted_by_default(monkeypatch: pytest.MonkeyPatch):
    paths = _openapi_path_keys(monkeypatch, None)
    for dossier_path in DOSSIER_ONLY_PATHS:
        assert dossier_path not in paths


def test_dossier_routes_mounted_when_enabled(monkeypatch: pytest.MonkeyPatch):
    paths = _openapi_path_keys(monkeypatch, "1")
    joined = "\n".join(paths)
    assert ("/supply" in joined) or ("/demand" in joined) or ("/trip" in joined)


@pytest.mark.parametrize("value", ["true", "yes", "on"])
def test_dossier_routes_mounted_for_truthy_variants(
    monkeypatch: pytest.MonkeyPatch, value: str
):
    paths = _openapi_path_keys(monkeypatch, value)
    joined = "\n".join(paths)
    assert "/supply/heartbeat" in joined
