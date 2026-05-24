"""OSRM runtime claim gating via proof evidence file."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from services import osrm_runtime_truth as truth


def _valid_evidence() -> dict:
    return {
        "slice": "HALFAPP_OSRM_RUNTIME_PROOF_PORTLAND_01",
        "verdict": "GO",
        "osrm_runtime_claim": "proved_portland_v0_1",
        "health_check": {"code": "Ok", "distance_meters": 1000, "duration_seconds": 60},
        "proof_routes": [
            {
                "label": "a",
                "route_provider": "osrm_self_hosted",
                "used_fallback": False,
            },
            {
                "label": "b",
                "route_provider": "osrm_self_hosted",
                "used_fallback": False,
            },
            {
                "label": "c",
                "route_provider": "osrm_self_hosted",
                "used_fallback": False,
            },
        ],
    }


def test_default_claim_without_evidence(monkeypatch, tmp_path: Path):
    missing = tmp_path / "missing.json"
    monkeypatch.setenv(truth._EVIDENCE_ENV, str(missing))
    assert truth.osrm_runtime_claim() == "not_proved"
    assert truth.production_routing_claim() == "not_proved"


def test_claim_advances_with_valid_evidence(monkeypatch, tmp_path: Path):
    path = tmp_path / "osrm_portland_proof.json"
    path.write_text(json.dumps(_valid_evidence()), encoding="utf-8")
    monkeypatch.setenv(truth._EVIDENCE_ENV, str(path))
    assert truth.osrm_runtime_claim() == "proved_portland_v0_1"


def test_invalid_evidence_does_not_advance_claim(monkeypatch, tmp_path: Path):
    path = tmp_path / "bad.json"
    bad = _valid_evidence()
    bad["proof_routes"][0]["used_fallback"] = True
    path.write_text(json.dumps(bad), encoding="utf-8")
    monkeypatch.setenv(truth._EVIDENCE_ENV, str(path))
    assert truth.osrm_runtime_claim() == "not_proved"
