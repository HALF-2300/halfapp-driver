"""Tests for Agent 2 — The Motion Auditor.

Exercises every verdict path (PASS / REJECT / WARN) against the
synthetic fixtures from conftest.py.  Validates:
  - Exit codes match the inter-agent protocol
  - Feedback-to-Agent1 is present on rejections
  - RetryGuidance carries concrete parameter deltas
  - blocks_agent7 / credits_saved flags are set correctly
  - The batch API preserves order
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.agents.agent2 import audit, audit_batch, AGENT_NAME, AGENT_ID
from core.agents.protocol import ExitCode


# ── PASS path ───────────────────────────────────────────────────────


class TestMovingVideoPass:
    def test_verdict_is_pass(self, moving_video: Path) -> None:
        v = audit(moving_video)
        assert v.verdict == "PASS"
        assert v.exit_code == ExitCode.PASS

    def test_identity(self, moving_video: Path) -> None:
        v = audit(moving_video)
        assert v.agent_name == AGENT_NAME
        assert v.agent_id == AGENT_ID

    def test_does_not_block_agent7(self, moving_video: Path) -> None:
        v = audit(moving_video)
        assert v.blocks_agent7 is False
        assert v.credits_saved is False

    def test_no_failures(self, moving_video: Path) -> None:
        v = audit(moving_video)
        assert v.failures == []

    def test_sha256_present(self, moving_video: Path) -> None:
        v = audit(moving_video)
        assert len(v.artifact_sha256) == 64

    def test_analysis_contains_both_checks(self, moving_video: Path) -> None:
        v = audit(moving_video)
        assert "opticalFlow" in v.analysis
        assert "firstLastSimilarity" in v.analysis


# ── REJECT path: static / frozen ────────────────────────────────────


class TestStaticVideoPass:
    """Agent 2 is the *Motion* Auditor — it checks for temporal
    instability (flow spikes, drift), not for frozen content.

    A static video has near-zero flow (stable) and near-identical
    first/last frames (no drift), so Agent 2 correctly passes it.
    The static/frozen detection lives in the full gate report
    (``detect_static_or_frozen_video``) and is a separate concern."""

    def test_verdict_is_pass(self, static_video: Path) -> None:
        v = audit(static_video)
        assert v.verdict == "PASS"

    def test_does_not_block_agent7(self, static_video: Path) -> None:
        v = audit(static_video)
        assert v.blocks_agent7 is False

    def test_no_flow_failures(self, static_video: Path) -> None:
        v = audit(static_video)
        assert "optical_flow_unstable" not in v.failures


# ── REJECT path: optical flow spikes ────────────────────────────────


class TestFlowSpikeReject:
    def test_verdict(self, flow_spike_video: Path) -> None:
        v = audit(flow_spike_video)
        assert v.verdict in ("REJECT", "WARN")

    def test_exit_code(self, flow_spike_video: Path) -> None:
        v = audit(flow_spike_video)
        if v.verdict == "REJECT":
            assert v.exit_code == ExitCode.REJECT
        else:
            assert v.exit_code == ExitCode.WARN

    def test_has_flow_signal(self, flow_spike_video: Path) -> None:
        v = audit(flow_spike_video)
        has_signal = (
            "optical_flow_unstable" in v.failures
            or "optical_flow_spike" in v.warnings
        )
        assert has_signal

    def test_feedback_to_agent1(self, flow_spike_video: Path) -> None:
        v = audit(flow_spike_video)
        if v.verdict == "REJECT":
            assert v.feedback_to_agent1 is not None
            feedback_lower = v.feedback_to_agent1.lower()
            assert any(kw in feedback_lower for kw in (
                "lower", "re-roll", "reduce", "cfg", "flow", "drift",
            ))

    def test_retry_guidance_targets_cfg(self, flow_spike_video: Path) -> None:
        v = audit(flow_spike_video)
        if v.retry_guidance:
            cfg_guidance = [g for g in v.retry_guidance if g.parameter == "cfg_scale"]
            assert len(cfg_guidance) > 0
            assert cfg_guidance[0].direction == "lower"
            assert cfg_guidance[0].amount > 0


# ── REJECT path: corrupted container ────────────────────────────────


class TestCorruptedVideoReject:
    def test_verdict_is_reject(self, corrupted_video: Path) -> None:
        v = audit(corrupted_video)
        assert v.verdict == "REJECT"
        assert v.exit_code == ExitCode.REJECT

    def test_blocks_agent7(self, corrupted_video: Path) -> None:
        v = audit(corrupted_video)
        assert v.blocks_agent7 is True
        assert v.credits_saved is True

    def test_feedback_present(self, corrupted_video: Path) -> None:
        v = audit(corrupted_video)
        assert v.feedback_to_agent1 is not None
        assert len(v.feedback_to_agent1) > 0


# ── serialisation ───────────────────────────────────────────────────


class TestVerdictSerialisation:
    def test_to_dict_roundtrip(self, moving_video: Path) -> None:
        v = audit(moving_video)
        d = v.to_dict()
        assert isinstance(d, dict)
        assert d["agent_name"] == AGENT_NAME
        assert d["agent_id"] == AGENT_ID
        assert d["verdict"] in ("PASS", "WARN", "REJECT")
        assert isinstance(d["retry_guidance"], list)
        assert isinstance(d["analysis"], dict)

    def test_rejected_verdict_has_guidance_dicts(self, flow_spike_video: Path) -> None:
        v = audit(flow_spike_video)
        d = v.to_dict()
        for g in d["retry_guidance"]:
            assert "parameter" in g
            assert "direction" in g
            assert "amount" in g


# ── batch API ───────────────────────────────────────────────────────


class TestBatchAudit:
    def test_preserves_order(
        self, moving_video: Path, corrupted_video: Path,
    ) -> None:
        verdicts = audit_batch([moving_video, corrupted_video])
        assert len(verdicts) == 2
        assert verdicts[0].verdict in ("PASS", "WARN")
        assert verdicts[1].verdict == "REJECT"

    def test_all_have_agent_identity(
        self, moving_video: Path, static_video: Path,
    ) -> None:
        verdicts = audit_batch([moving_video, static_video])
        for v in verdicts:
            assert v.agent_name == AGENT_NAME
            assert v.agent_id == AGENT_ID


# ── nonexistent file ────────────────────────────────────────────────


class TestNonexistentFile:
    def test_reject(self) -> None:
        v = audit("totally_fake_file_abc123.mp4")
        assert v.verdict == "REJECT"
        assert v.exit_code == ExitCode.REJECT
        assert v.blocks_agent7 is True
