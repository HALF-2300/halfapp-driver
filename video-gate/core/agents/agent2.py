"""Agent 2 — The Motion Auditor.

The uncompromising critic of the pipeline.  Agent 2 does not care about
the prompt or the story; it only cares about the MP4 data.

Responsibilities
────────────────
1. **Intercept** — grab every clip the moment it leaves generation.
2. **Analyse**  — run optical-flow stability *and* first-/last-frame
   similarity.  These are the two reality checks that catch temporal
   artefacts no prompt hack can fix.
3. **Vote**     — emit a structured ``AgentVerdict``.
   • Exit 0  → clip is temporally stable, cleared for Agent 7 (Upscaler).
   • Exit 1  → clip is broken.  Sends concrete retry guidance back to
     Agent 1 ("Rejected. Flow spike at frame 48. Re-roll with lower
     guidance.") and **kills** the pipeline before Agent 7 can spend
     credits on upscaling garbage.
   • Exit 2  → clip is marginal.  Agent 7 *may* proceed but the warning
     is forwarded so downstream QA knows.

Credit Protection
─────────────────
By sitting between generation (Agent 1) and upscaling (Agent 7),
Agent 2 is the cheapest possible place to reject a bad clip.  Every
rejection here saves the full cost of an upscale pass.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from gate.flow import assess_optical_flow_stability
from gate.frames import measure_first_last_frame_similarity
from gate.hash import generate_artifact_hash
from gate.probe import run_ffprobe_audit, ProbeError
from gate import config as gate_config

from .protocol import AgentVerdict, ExitCode, RetryGuidance

log = logging.getLogger(__name__)

AGENT_NAME = "motion_auditor"
AGENT_ID = 2


# ── core audit ──────────────────────────────────────────────────────


def audit(file_path: str | Path) -> AgentVerdict:
    """Run the full Motion Auditor pipeline on a single MP4.

    This is the primary public API.  Call it from the orchestrator,
    from the CLI, or from tests — the return value is always a
    self-contained ``AgentVerdict``.
    """
    fp = Path(file_path).resolve()
    log.info("[Agent 2] Intercepting %s", fp.name)

    sha256 = _safe_hash(fp)

    # Fast-fail: if we can't even probe the container, reject immediately.
    probe = _safe_probe(fp)
    if probe is None:
        return _reject(
            fp, sha256,
            failures=["container_unreadable"],
            feedback="Rejected. Container is unreadable — file may be truncated or corrupt.",
            guidance=[],
        )

    # ── the two core motion checks ──────────────────────────────────
    flow_result = _safe_flow(fp)
    similarity_result = _safe_similarity(fp)

    failures: list[str] = []
    warnings: list[str] = []
    guidance: list[RetryGuidance] = []

    _evaluate_flow(flow_result, failures, warnings, guidance)
    _evaluate_similarity(similarity_result, failures, warnings, guidance)

    analysis = {
        "opticalFlow": flow_result,
        "firstLastSimilarity": similarity_result,
        "probe": probe,
    }

    if failures:
        spike_frame = _find_spike_frame(flow_result)
        feedback = _build_rejection_feedback(failures, spike_frame)
        return _reject(fp, sha256, failures=failures, feedback=feedback,
                       guidance=guidance, warnings=warnings, analysis=analysis)

    if warnings:
        return _warn(fp, sha256, warnings=warnings, analysis=analysis)

    return _pass(fp, sha256, analysis=analysis)


# ── flow evaluation ─────────────────────────────────────────────────


def _evaluate_flow(
    flow: dict[str, Any],
    failures: list[str],
    warnings: list[str],
    guidance: list[RetryGuidance],
) -> None:
    if flow.get("error"):
        warnings.append("flow_check_error")
        return

    decision = flow.get("decision", "ok")
    if decision == "reject":
        failures.append("optical_flow_unstable")
        guidance.append(RetryGuidance(
            parameter="cfg_scale",
            direction="lower",
            amount=1.5,
            reason="Optical flow exceeds reject threshold — high CFG tears pixels.",
        ))
    elif decision == "warn":
        warnings.append("optical_flow_spike")
        guidance.append(RetryGuidance(
            parameter="cfg_scale",
            direction="lower",
            amount=0.75,
            reason="Optical flow spikes detected — moderate CFG reduction advised.",
        ))


def _evaluate_similarity(
    sim: dict[str, Any],
    failures: list[str],
    warnings: list[str],
    guidance: list[RetryGuidance],
) -> None:
    if sim.get("error"):
        warnings.append("similarity_check_error")
        return

    decision = sim.get("decision", "ok")
    if decision == "reject":
        failures.append("first_last_drift_extreme")
        guidance.append(RetryGuidance(
            parameter="cfg_scale",
            direction="lower",
            amount=0.5,
            reason="First-last frame SSIM below reject floor — extreme visual drift.",
        ))
    elif decision == "warn":
        warnings.append("first_last_drift")


# ── spike localisation ──────────────────────────────────────────────


def _find_spike_frame(flow: dict[str, Any]) -> int | None:
    """Return the pair index with the highest magnitude, if any."""
    magnitudes = flow.get("mean_magnitudes", [])
    if not magnitudes:
        return None
    peak = max(magnitudes)
    if peak < gate_config.FLOW_WARN_MEAN_MAGNITUDE:
        return None
    return magnitudes.index(peak)


# ── feedback construction ───────────────────────────────────────────


def _build_rejection_feedback(
    failures: list[str],
    spike_frame: int | None,
) -> str:
    parts: list[str] = ["Rejected."]

    if "optical_flow_unstable" in failures:
        if spike_frame is not None:
            parts.append(f"Flow spike at pair {spike_frame}.")
        else:
            parts.append("Optical flow exceeds stability threshold.")
        parts.append("Re-roll with lower guidance.")

    if "first_last_drift_extreme" in failures:
        parts.append("Extreme first-last frame drift.")
        parts.append("Reduce CFG to stabilise temporal coherence.")

    return " ".join(parts)


# ── safe wrappers (never let a sub-check crash the agent) ───────────


def _safe_hash(fp: Path) -> str:
    try:
        return generate_artifact_hash(fp)
    except OSError:
        return "UNAVAILABLE"


def _safe_probe(fp: Path) -> dict[str, Any] | None:
    try:
        return run_ffprobe_audit(fp)
    except ProbeError:
        return None


def _safe_flow(fp: Path) -> dict[str, Any]:
    try:
        return assess_optical_flow_stability(fp)
    except Exception as exc:
        log.warning("[Agent 2] Flow check error: %s", exc)
        return {"decision": "error", "error": str(exc), "mean_magnitudes": []}


def _safe_similarity(fp: Path) -> dict[str, Any]:
    try:
        return measure_first_last_frame_similarity(fp)
    except Exception as exc:
        log.warning("[Agent 2] Similarity check error: %s", exc)
        return {"ssim": None, "decision": "error", "error": str(exc)}


# ── verdict constructors ────────────────────────────────────────────


def _reject(
    fp: Path,
    sha256: str,
    *,
    failures: list[str],
    feedback: str,
    guidance: list[RetryGuidance],
    warnings: list[str] | None = None,
    analysis: dict[str, Any] | None = None,
) -> AgentVerdict:
    log.info("[Agent 2] REJECT %s — %s", fp.name, feedback)
    return AgentVerdict(
        agent_name=AGENT_NAME,
        agent_id=AGENT_ID,
        verdict="REJECT",
        exit_code=ExitCode.REJECT,
        artifact_path=str(fp),
        artifact_sha256=sha256,
        analysis=analysis or {},
        failures=failures,
        warnings=warnings or [],
        feedback_to_agent1=feedback,
        retry_guidance=guidance,
        blocks_agent7=True,
        credits_saved=True,
    )


def _warn(
    fp: Path,
    sha256: str,
    *,
    warnings: list[str],
    analysis: dict[str, Any] | None = None,
) -> AgentVerdict:
    log.info("[Agent 2] WARN %s — %s", fp.name, warnings)
    return AgentVerdict(
        agent_name=AGENT_NAME,
        agent_id=AGENT_ID,
        verdict="WARN",
        exit_code=ExitCode.WARN,
        artifact_path=str(fp),
        artifact_sha256=sha256,
        analysis=analysis or {},
        warnings=warnings,
        blocks_agent7=False,
        credits_saved=False,
    )


def _pass(
    fp: Path,
    sha256: str,
    *,
    analysis: dict[str, Any] | None = None,
) -> AgentVerdict:
    log.info("[Agent 2] PASS %s — cleared for Agent 7", fp.name)
    return AgentVerdict(
        agent_name=AGENT_NAME,
        agent_id=AGENT_ID,
        verdict="PASS",
        exit_code=ExitCode.PASS,
        artifact_path=str(fp),
        artifact_sha256=sha256,
        analysis=analysis or {},
        blocks_agent7=False,
        credits_saved=False,
    )


# ── batch API (for the orchestrator) ────────────────────────────────


def audit_batch(file_paths: list[Path]) -> list[AgentVerdict]:
    """Audit multiple candidates sequentially.

    Returns one AgentVerdict per path, in the same order.
    """
    return [audit(fp) for fp in file_paths]
