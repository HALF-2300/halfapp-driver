"""Assemble a CandidateQualityReportV1 from all sub-checks."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from . import config
from .hash import generate_artifact_hash
from .probe import ProbeError, run_ffprobe_audit
from .frames import detect_static_or_frozen_video, measure_first_last_frame_similarity
from .flow import assess_optical_flow_stability

DECISION_APPROVED = "APPROVED_FOR_TIMELINE"
DECISION_WARN = "WARN_REVIEW_REQUIRED"
DECISION_REJECTED = "REJECTED"


def build_candidate_quality_report(file_path: str | Path) -> dict[str, Any]:
    """Top-level entry: produce a complete CandidateQualityReportV1 dict."""

    fp = Path(file_path).resolve()
    candidate_id = str(uuid.uuid4())
    warnings: list[str] = []
    failures: list[str] = []

    # --- artifact hash (always written, even on early rejection) ---
    try:
        sha256 = generate_artifact_hash(fp)
    except OSError as exc:
        return _rejected_early(
            fp, candidate_id, f"Cannot read file for hashing: {exc}"
        )

    # --- ffprobe technical audit ---
    try:
        probe = run_ffprobe_audit(fp)
    except ProbeError as exc:
        return _rejected_report(
            fp, candidate_id, sha256,
            failure=f"ffprobe failed: {exc}",
        )

    duration = probe["duration_seconds"]
    fps = probe["fps"]
    codec = probe["codec"]
    frame_count = probe["frame_count"]

    technical_floor: dict[str, Any] = {
        "passed": True,
        "details": [],
    }

    if duration is None or duration < config.MIN_DURATION_SECONDS:
        technical_floor["passed"] = False
        technical_floor["details"].append(
            f"Duration {duration}s below minimum {config.MIN_DURATION_SECONDS}s"
        )
        failures.append("below_min_duration")

    if fps is None or not (config.MIN_FPS <= fps <= config.MAX_FPS):
        technical_floor["passed"] = False
        technical_floor["details"].append(f"FPS {fps} outside [{config.MIN_FPS}, {config.MAX_FPS}]")
        failures.append("invalid_fps")

    if codec is None:
        technical_floor["passed"] = False
        technical_floor["details"].append("Missing codec")
        failures.append("missing_codec")

    if frame_count is None or frame_count < config.MIN_FRAME_COUNT:
        technical_floor["passed"] = False
        technical_floor["details"].append(
            f"Frame count {frame_count} below minimum {config.MIN_FRAME_COUNT}"
        )
        failures.append("insufficient_frames")

    if not technical_floor["passed"]:
        return _build(
            fp, candidate_id, sha256,
            technical_floor=technical_floor,
            duration=duration, fps=fps, codec=codec, frame_count=frame_count,
            static_check=None, flow_check=None, similarity_check=None,
            warnings=warnings, failures=failures,
            decision=DECISION_REJECTED,
        )

    # --- visual checks (only if technical floor passed) ---
    try:
        static_check = detect_static_or_frozen_video(fp)
    except Exception as exc:
        static_check = {"is_static": None, "mean_ssim": None, "pair_ssims": [], "error": str(exc)}
        failures.append("static_check_error")

    if static_check.get("is_static"):
        failures.append("static_or_frozen")

    try:
        flow_check = assess_optical_flow_stability(fp)
    except Exception as exc:
        flow_check = {"decision": "error", "error": str(exc)}
        warnings.append("flow_check_error")

    if flow_check.get("decision") == "reject":
        failures.append("optical_flow_unstable")
    elif flow_check.get("decision") == "warn":
        warnings.append("optical_flow_spike")

    try:
        similarity_check = measure_first_last_frame_similarity(fp)
    except Exception as exc:
        similarity_check = {"ssim": None, "decision": "error", "error": str(exc)}
        warnings.append("similarity_check_error")

    if similarity_check.get("decision") == "reject":
        failures.append("first_last_drift_extreme")
    elif similarity_check.get("decision") == "warn":
        warnings.append("first_last_drift")

    # --- final decision ---
    if failures:
        decision = DECISION_REJECTED
    elif warnings:
        decision = DECISION_WARN
    else:
        decision = DECISION_APPROVED

    return _build(
        fp, candidate_id, sha256,
        technical_floor=technical_floor,
        duration=duration, fps=fps, codec=codec, frame_count=frame_count,
        static_check=static_check, flow_check=flow_check,
        similarity_check=similarity_check,
        warnings=warnings, failures=failures,
        decision=decision,
    )


# ── helpers ──────────────────────────────────────────────────────────

def _build(
    fp: Path,
    candidate_id: str,
    sha256: str,
    *,
    technical_floor: dict | None,
    duration: float | None,
    fps: float | None,
    codec: str | None,
    frame_count: int | None,
    static_check: dict | None,
    flow_check: dict | None,
    similarity_check: dict | None,
    warnings: list[str],
    failures: list[str],
    decision: str,
) -> dict[str, Any]:
    return {
        "schemaVersion": config.SCHEMA_VERSION,
        "candidateId": candidate_id,
        "artifactPath": str(fp),
        "artifactSha256": sha256,
        "technicalFloor": technical_floor,
        "durationSeconds": duration,
        "fps": fps,
        "codec": codec,
        "frameCount": frame_count,
        "staticFrameCheck": static_check,
        "opticalFlowCheck": flow_check,
        "firstLastSimilarityCheck": similarity_check,
        "warnings": warnings,
        "failures": failures,
        "finalDecision": decision,
    }


def _rejected_early(fp: Path, cid: str, reason: str) -> dict[str, Any]:
    """Report for files we cannot even hash."""
    return _build(
        fp, cid, sha256="UNAVAILABLE",
        technical_floor={"passed": False, "details": [reason]},
        duration=None, fps=None, codec=None, frame_count=None,
        static_check=None, flow_check=None, similarity_check=None,
        warnings=[], failures=["unreadable"],
        decision=DECISION_REJECTED,
    )


def _rejected_report(
    fp: Path, cid: str, sha256: str, *, failure: str,
) -> dict[str, Any]:
    return _build(
        fp, cid, sha256,
        technical_floor={"passed": False, "details": [failure]},
        duration=None, fps=None, codec=None, frame_count=None,
        static_check=None, flow_check=None, similarity_check=None,
        warnings=[], failures=["probe_failure"],
        decision=DECISION_REJECTED,
    )
