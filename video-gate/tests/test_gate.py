"""Acceptance tests for CandidateQualityReportV1."""

from __future__ import annotations

from pathlib import Path

from gate.report import (
    DECISION_APPROVED,
    DECISION_REJECTED,
    DECISION_WARN,
    build_candidate_quality_report,
)

REQUIRED_FIELDS = {
    "schemaVersion",
    "candidateId",
    "artifactPath",
    "artifactSha256",
    "technicalFloor",
    "durationSeconds",
    "fps",
    "codec",
    "frameCount",
    "staticFrameCheck",
    "opticalFlowCheck",
    "firstLastSimilarityCheck",
    "warnings",
    "failures",
    "finalDecision",
}


def _assert_report_shape(report: dict) -> None:
    """Every report must carry all required fields and a valid SHA-256."""
    assert REQUIRED_FIELDS.issubset(report.keys()), (
        f"Missing fields: {REQUIRED_FIELDS - report.keys()}"
    )
    assert report["artifactSha256"] is not None
    assert isinstance(report["warnings"], list)
    assert isinstance(report["failures"], list)
    assert report["finalDecision"] in (
        DECISION_APPROVED, DECISION_WARN, DECISION_REJECTED,
    )


# ── acceptance tests ─────────────────────────────────────────────────


class TestValidMovingVideo:
    def test_approved_or_warn(self, moving_video: Path) -> None:
        r = build_candidate_quality_report(moving_video)
        _assert_report_shape(r)
        assert r["finalDecision"] in (DECISION_APPROVED, DECISION_WARN)

    def test_has_sha256(self, moving_video: Path) -> None:
        r = build_candidate_quality_report(moving_video)
        assert len(r["artifactSha256"]) == 64

    def test_technical_floor_passed(self, moving_video: Path) -> None:
        r = build_candidate_quality_report(moving_video)
        assert r["technicalFloor"]["passed"] is True

    def test_not_static(self, moving_video: Path) -> None:
        r = build_candidate_quality_report(moving_video)
        assert r["staticFrameCheck"]["is_static"] is False


class TestStaticFrozenVideo:
    def test_rejected(self, static_video: Path) -> None:
        r = build_candidate_quality_report(static_video)
        _assert_report_shape(r)
        assert r["finalDecision"] == DECISION_REJECTED

    def test_failure_reason(self, static_video: Path) -> None:
        r = build_candidate_quality_report(static_video)
        assert "static_or_frozen" in r["failures"]


class TestCorruptedVideo:
    def test_rejected(self, corrupted_video: Path) -> None:
        r = build_candidate_quality_report(corrupted_video)
        _assert_report_shape(r)
        assert r["finalDecision"] == DECISION_REJECTED

    def test_has_sha256(self, corrupted_video: Path) -> None:
        r = build_candidate_quality_report(corrupted_video)
        assert len(r["artifactSha256"]) == 64


class TestTooShortVideo:
    def test_rejected(self, too_short_video: Path) -> None:
        r = build_candidate_quality_report(too_short_video)
        _assert_report_shape(r)
        assert r["finalDecision"] == DECISION_REJECTED

    def test_failure_reason(self, too_short_video: Path) -> None:
        r = build_candidate_quality_report(too_short_video)
        assert any(
            f in r["failures"]
            for f in ("below_min_duration", "insufficient_frames")
        )


class TestOpticalFlowSpike:
    def test_warn_or_reject(self, flow_spike_video: Path) -> None:
        r = build_candidate_quality_report(flow_spike_video)
        _assert_report_shape(r)
        has_flow_signal = (
            "optical_flow_spike" in r["warnings"]
            or "optical_flow_unstable" in r["failures"]
        )
        assert has_flow_signal or r["finalDecision"] in (
            DECISION_WARN, DECISION_REJECTED,
        )


class TestNonexistentFile:
    def test_rejected(self) -> None:
        r = build_candidate_quality_report("nonexistent_file_xyz.mp4")
        _assert_report_shape(r)
        assert r["finalDecision"] == DECISION_REJECTED
