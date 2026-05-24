"""Tests for the orchestrator logic.

ComfyUI is mocked (no GPU required).  The gate audit runs Agent 2
(Motion Auditor) for real against the synthetic fixtures from conftest.py.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from core.orchestrator import config
from core.orchestrator.loop import (
    calculate_retry_parameters,
    evaluate_and_promote,
    execute_gate_audit,
)
from core.orchestrator.manifest import ShotManifest


# ── execute_gate_audit (Agent 2 — Motion Auditor, no subprocess) ─────


class TestExecuteGateAudit:
    """The gate audit now routes through Agent 2 in-process."""

    def test_moving_video_approved(self, moving_video: Path) -> None:
        reports = execute_gate_audit([moving_video])
        assert len(reports) == 1
        assert reports[0]["finalDecision"] == "APPROVED_FOR_TIMELINE"
        assert len(reports[0]["artifactSha256"]) == 64

    def test_moving_video_has_agent2_verdict(self, moving_video: Path) -> None:
        reports = execute_gate_audit([moving_video])
        a2 = reports[0].get("agent2Verdict", {})
        assert a2.get("agent_name") == "motion_auditor"
        assert a2.get("agent_id") == 2

    def test_corrupted_video_rejected(self, corrupted_video: Path) -> None:
        reports = execute_gate_audit([corrupted_video])
        assert reports[0]["finalDecision"] == "REJECTED"
        assert reports[0]["blocksAgent7"] is True
        assert reports[0]["creditsSaved"] is True

    def test_batch_audit(self, moving_video: Path, corrupted_video: Path) -> None:
        reports = execute_gate_audit([moving_video, corrupted_video])
        assert len(reports) == 2
        assert reports[0]["finalDecision"] == "APPROVED_FOR_TIMELINE"
        assert reports[1]["finalDecision"] == "REJECTED"


# ── calculate_retry_parameters ───────────────────────────────────────


class TestCalculateRetryParameters:
    def test_flow_failure_lowers_cfg(self) -> None:
        failed = [
            {"failures": ["optical_flow_unstable"], "warnings": []},
        ]
        result = calculate_retry_parameters(failed, 6.0, 1.0)
        assert result["cfg_scale"] < 6.0
        assert result["cfg_scale"] >= config.CFG_FLOOR
        assert any("optical flow" in a for a in result["adjustments"])

    def test_static_failure_bumps_control(self) -> None:
        failed = [
            {"failures": ["static_or_frozen"], "warnings": []},
        ]
        result = calculate_retry_parameters(failed, 6.0, 1.0)
        assert result["control_strength"] > 1.0
        assert result["control_strength"] <= config.CONTROL_STRENGTH_CEILING

    def test_drift_failure_reduces_cfg(self) -> None:
        failed = [
            {"failures": ["first_last_drift_extreme"], "warnings": []},
        ]
        result = calculate_retry_parameters(failed, 6.0, 1.0)
        assert result["cfg_scale"] < 6.0

    def test_combined_failures(self) -> None:
        failed = [
            {"failures": ["optical_flow_unstable", "static_or_frozen"], "warnings": []},
        ]
        result = calculate_retry_parameters(failed, 6.0, 1.0)
        assert result["cfg_scale"] < 6.0
        assert result["control_strength"] > 1.0

    def test_no_targeted_correction(self) -> None:
        failed = [
            {"failures": ["probe_failure"], "warnings": []},
        ]
        result = calculate_retry_parameters(failed, 6.0, 1.0)
        assert result["cfg_scale"] == 6.0
        assert "new seeds" in result["adjustments"][0]

    def test_should_abandon_when_exhausted(self) -> None:
        failed = [
            {"failures": ["optical_flow_unstable", "static_or_frozen"], "warnings": []},
        ]
        result = calculate_retry_parameters(
            failed, config.CFG_FLOOR, config.CONTROL_STRENGTH_CEILING,
        )
        assert result["should_abandon"] is True

    def test_flow_warning_also_triggers(self) -> None:
        failed = [
            {"failures": [], "warnings": ["optical_flow_spike"]},
        ]
        result = calculate_retry_parameters(failed, 6.0, 1.0)
        assert result["cfg_scale"] < 6.0


# ── evaluate_and_promote ─────────────────────────────────────────────


class TestEvaluateAndPromote:
    def test_selects_approved_over_warn(self, tmp_path: Path) -> None:
        config.PROMOTED_DIR = tmp_path / "promoted"
        config.PROMOTED_DIR.mkdir()

        fake_file = tmp_path / "candidate_a.mp4"
        fake_file.write_bytes(b"\x00" * 100)

        manifest = ShotManifest("test_shot_001", prompt_text="test")
        reports = [
            {
                "finalDecision": "WARN_REVIEW_REQUIRED",
                "artifactSha256": "aaa",
                "artifactPath": str(fake_file),
                "failures": [],
                "warnings": ["optical_flow_spike"],
            },
            {
                "finalDecision": "APPROVED_FOR_TIMELINE",
                "artifactSha256": "bbb",
                "artifactPath": str(fake_file),
                "failures": [],
                "warnings": [],
            },
        ]
        winner = evaluate_and_promote(reports, manifest)
        assert winner is not None
        assert winner["artifactSha256"] == "bbb"
        assert manifest.status == "APPROVED"
        assert manifest.data["verifiedArtifact"]["gateDecision"] == "APPROVED_FOR_TIMELINE"

    def test_returns_none_if_all_rejected(self) -> None:
        manifest = ShotManifest("test_shot_002", prompt_text="test")
        reports = [
            {"finalDecision": "REJECTED", "artifactSha256": "ccc",
             "artifactPath": "/fake", "failures": ["static_or_frozen"], "warnings": []},
        ]
        winner = evaluate_and_promote(reports, manifest)
        assert winner is None
        assert manifest.status != "APPROVED"

    def test_accepts_warn_if_no_approved(self, tmp_path: Path) -> None:
        config.PROMOTED_DIR = tmp_path / "promoted"
        config.PROMOTED_DIR.mkdir()

        fake_file = tmp_path / "candidate_w.mp4"
        fake_file.write_bytes(b"\x00" * 100)

        manifest = ShotManifest("test_shot_003", prompt_text="test")
        reports = [
            {
                "finalDecision": "WARN_REVIEW_REQUIRED",
                "artifactSha256": "ddd",
                "artifactPath": str(fake_file),
                "failures": [],
                "warnings": ["first_last_drift"],
            },
        ]
        winner = evaluate_and_promote(reports, manifest)
        assert winner is not None
        assert manifest.data["verifiedArtifact"]["gateDecision"] == "WARN_REVIEW_REQUIRED"


# ── ShotManifest ─────────────────────────────────────────────────────


class TestShotManifest:
    def test_create_and_save(self, tmp_path: Path) -> None:
        config.MANIFEST_DIR = tmp_path
        m = ShotManifest("scn01_sh04", prompt_text="A robot walks left")
        m.set_status("IN_PROGRESS")
        m.increment_attempts()
        m.add_candidate({
            "round": 1,
            "seed": 12345,
            "cfgScale": 6.0,
            "controlStrength": 1.0,
            "gateResult": "REJECTED",
            "failureReasons": ["static_or_frozen"],
            "warnings": [],
            "artifactHash": "abc123",
        })
        path = m.save()
        assert path.exists()

        loaded = json.loads(path.read_text())
        assert loaded["shotId"] == "scn01_sh04"
        assert loaded["generationAttempts"] == 1
        assert len(loaded["candidates"]) == 1
        assert loaded["candidates"][0]["seed"] == 12345

    def test_round_trip_load(self, tmp_path: Path) -> None:
        config.MANIFEST_DIR = tmp_path
        m = ShotManifest("scn02_sh01", prompt_text="test")
        m.set_cfg_scale(4.5)
        m.set_control_strength(1.15)
        m.save()

        loaded = ShotManifest.load(m.path)
        assert loaded.cfg_scale == 4.5
        assert loaded.control_strength == 1.15
        assert loaded.shot_id == "scn02_sh01"

    def test_promote_sets_status(self, tmp_path: Path) -> None:
        config.MANIFEST_DIR = tmp_path
        m = ShotManifest("scn03_sh01", prompt_text="test")
        m.promote("sha256hex", "/output/final.mp4", "APPROVED_FOR_TIMELINE")
        assert m.status == "APPROVED"
        assert m.data["verifiedArtifact"]["artifactHash"] == "sha256hex"
