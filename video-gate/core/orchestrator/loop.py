"""Local Draft Orchestrator — autonomous generation→audit→retry loop.

Public API (the four deliverables):
    request_draft_batch      — fire N parallel Wan2.1 generations
    execute_gate_audit       — run Agent 2 (Motion Auditor) on each candidate
    evaluate_and_promote     — pick the best APPROVED candidate
    calculate_retry_parameters — self-correct CFG / control strength

Top-level entry:
    run_shot_loop            — autonomous loop that ties everything together

Agent architecture
──────────────────
Agent 2 (Motion Auditor) sits between generation and upscaling as a
blocking gate.  If Agent 2 returns Exit Code 1, the clip is killed before
it ever reaches Agent 7 (Upscaler), saving expensive upscale credits.
Agent 2's feedback is relayed back to Agent 1 for re-roll guidance.
"""

from __future__ import annotations

import json
import logging
import random
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from . import config
from .comfyui import ComfyUIError, generate_single, health_check
from .manifest import ShotManifest
from ..agents.agent2 import audit as agent2_audit, audit_batch as agent2_audit_batch
from ..agents.protocol import AgentVerdict, ExitCode

log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# 1. request_draft_batch
# ═══════════════════════════════════════════════════════════════════════

def request_draft_batch(
    prompt: str,
    control_video: str | None = None,
    count: int = config.DEFAULT_BATCH_SIZE,
    *,
    cfg_scale: float = config.DEFAULT_CFG_SCALE,
    control_strength: float = config.DEFAULT_CONTROL_STRENGTH,
    seeds: list[int] | None = None,
) -> list[dict[str, Any]]:
    """Trigger *count* concurrent Wan2.1 generations via ComfyUI.

    Returns a list of dicts, one per generation attempt:
        {
          "seed": int,
          "cfg_scale": float,
          "control_strength": float,
          "paths": [Path, ...],   # downloaded output files
          "error": str | None,
        }
    """
    if seeds is None:
        seeds = [random.randint(0, 2**32 - 1) for _ in range(count)]

    results: list[dict[str, Any]] = []

    def _run(seed: int) -> dict[str, Any]:
        try:
            paths, _hist = generate_single(
                prompt,
                seed=seed,
                cfg_scale=cfg_scale,
                control_strength=control_strength,
                control_video_path=control_video,
            )
            return {
                "seed": seed,
                "cfg_scale": cfg_scale,
                "control_strength": control_strength,
                "paths": paths,
                "error": None,
            }
        except ComfyUIError as exc:
            log.error("Generation failed (seed=%d): %s", seed, exc)
            return {
                "seed": seed,
                "cfg_scale": cfg_scale,
                "control_strength": control_strength,
                "paths": [],
                "error": str(exc),
            }

    with ThreadPoolExecutor(max_workers=count) as pool:
        futures = {pool.submit(_run, s): s for s in seeds}
        for future in as_completed(futures):
            results.append(future.result())

    return results


# ═══════════════════════════════════════════════════════════════════════
# 2. execute_gate_audit  (Agent 2 — The Motion Auditor)
# ═══════════════════════════════════════════════════════════════════════

def execute_gate_audit(batch_paths: list[Path]) -> list[dict[str, Any]]:
    """Route every candidate through Agent 2 (Motion Auditor).

    Agent 2 is the **blocking gate** for Agent 7 (Upscaler).
    If Agent 2 returns exit_code 1, the clip is killed here — Agent 7
    never sees it, and no upscale credits are spent.

    Returns legacy-compatible dicts so the rest of the orchestrator
    doesn't need to change its interface.
    """
    verdicts = agent2_audit_batch(batch_paths)
    reports: list[dict[str, Any]] = []
    for v in verdicts:
        report = _verdict_to_report(v)
        if v.exit_code == ExitCode.REJECT:
            log.info(
                "Agent 2 BLOCKED %s before Agent 7 — credits saved. "
                "Feedback to Agent 1: %s",
                Path(v.artifact_path).name,
                v.feedback_to_agent1,
            )
        reports.append(report)
    return reports


def _verdict_to_report(verdict: AgentVerdict) -> dict[str, Any]:
    """Translate an AgentVerdict into the legacy report format.

    The orchestrator loop and evaluate_and_promote still speak the
    CandidateQualityReportV1 dict format.  This bridge lets Agent 2
    slot in without rewriting every consumer at once.
    """
    decision_map = {
        "PASS": "APPROVED_FOR_TIMELINE",
        "WARN": "WARN_REVIEW_REQUIRED",
        "REJECT": "REJECTED",
    }
    return {
        "schemaVersion": "1.0.0",
        "candidateId": f"agent2-{verdict.artifact_sha256[:12]}",
        "artifactPath": verdict.artifact_path,
        "artifactSha256": verdict.artifact_sha256,
        "technicalFloor": {"passed": verdict.verdict != "REJECT", "details": []},
        "durationSeconds": verdict.analysis.get("probe", {}).get("duration_seconds"),
        "fps": verdict.analysis.get("probe", {}).get("fps"),
        "codec": verdict.analysis.get("probe", {}).get("codec"),
        "frameCount": verdict.analysis.get("probe", {}).get("frame_count"),
        "staticFrameCheck": None,
        "opticalFlowCheck": verdict.analysis.get("opticalFlow"),
        "firstLastSimilarityCheck": verdict.analysis.get("firstLastSimilarity"),
        "warnings": verdict.warnings,
        "failures": verdict.failures,
        "finalDecision": decision_map.get(verdict.verdict, "REJECTED"),
        # Agent 2 additions — downstream consumers can inspect these
        "agent2Verdict": verdict.to_dict(),
        "blocksAgent7": verdict.blocks_agent7,
        "creditsSaved": verdict.credits_saved,
    }


# ═══════════════════════════════════════════════════════════════════════
# 3. evaluate_and_promote
# ═══════════════════════════════════════════════════════════════════════

def evaluate_and_promote(
    audit_results: list[dict[str, Any]],
    manifest: ShotManifest,
) -> dict[str, Any] | None:
    """Select the first APPROVED candidate and promote it.

    Priority: APPROVED_FOR_TIMELINE > WARN_REVIEW_REQUIRED.
    Returns the winning report, or None if no candidate qualifies.
    """
    approved = [r for r in audit_results if r["finalDecision"] == "APPROVED_FOR_TIMELINE"]
    warned = [r for r in audit_results if r["finalDecision"] == "WARN_REVIEW_REQUIRED"]

    winner = (approved or warned or [None])[0]
    if winner is None:
        return None

    src = Path(winner["artifactPath"])
    dest = config.PROMOTED_DIR / src.name
    if src.exists():
        shutil.copy2(src, dest)

    manifest.promote(
        artifact_hash=winner["artifactSha256"],
        artifact_path=str(dest),
        gate_decision=winner["finalDecision"],
    )
    manifest.save()
    log.info(
        "PROMOTED %s → %s (decision=%s, sha=%s)",
        src.name, dest, winner["finalDecision"], winner["artifactSha256"][:16],
    )
    return winner


# ═══════════════════════════════════════════════════════════════════════
# 4. calculate_retry_parameters
# ═══════════════════════════════════════════════════════════════════════

def calculate_retry_parameters(
    failed_reports: list[dict[str, Any]],
    current_cfg: float,
    current_control_strength: float,
) -> dict[str, Any]:
    """Inspect failure reasons and compute adjusted generation parameters.

    When Agent 2's structured ``retry_guidance`` is available in the
    report, those concrete deltas take priority over the heuristic
    fallbacks.  This lets Agent 2 directly tell Agent 1 *exactly*
    how to re-roll.

    Returns:
        {
          "cfg_scale": float,
          "control_strength": float,
          "adjustments": ["description of each change"],
          "should_abandon": bool,
        }
    """
    adjustments: list[str] = []
    new_cfg = current_cfg
    new_cs = current_control_strength

    # Try Agent 2's structured guidance first
    agent2_guided = _apply_agent2_guidance(
        failed_reports, new_cfg, new_cs, adjustments,
    )
    if agent2_guided is not None:
        new_cfg, new_cs = agent2_guided
    else:
        # Fallback: heuristic analysis of failure/warning tags
        all_failures: list[str] = []
        all_warnings: list[str] = []
        for r in failed_reports:
            all_failures.extend(r.get("failures", []))
            all_warnings.extend(r.get("warnings", []))

        if "optical_flow_unstable" in all_failures or "optical_flow_spike" in all_warnings:
            reduction = config.CFG_REDUCTION_ON_FLOW_FAIL
            new_cfg = max(new_cfg - reduction, config.CFG_FLOOR)
            adjustments.append(
                f"CFG {current_cfg:.1f} → {new_cfg:.1f} (optical flow failure)"
            )

        if "static_or_frozen" in all_failures:
            bump = config.CONTROL_STRENGTH_BUMP_ON_STATIC
            new_cs = min(new_cs + bump, config.CONTROL_STRENGTH_CEILING)
            adjustments.append(
                f"Control strength {current_control_strength:.2f} → {new_cs:.2f} "
                f"(static/frozen content)"
            )

        if "first_last_drift_extreme" in all_failures or "first_last_drift" in all_warnings:
            reduction = config.CFG_REDUCTION_ON_DRIFT
            new_cfg = max(new_cfg - reduction, config.CFG_FLOOR)
            adjustments.append(
                f"CFG → {new_cfg:.1f} (first/last frame drift)"
            )

    should_abandon = (new_cfg <= config.CFG_FLOOR and new_cs >= config.CONTROL_STRENGTH_CEILING)

    if not adjustments:
        adjustments.append("No targeted correction available; retrying with new seeds")

    return {
        "cfg_scale": round(new_cfg, 2),
        "control_strength": round(new_cs, 2),
        "adjustments": adjustments,
        "should_abandon": should_abandon,
    }


def _apply_agent2_guidance(
    reports: list[dict[str, Any]],
    cfg: float,
    cs: float,
    adjustments: list[str],
) -> tuple[float, float] | None:
    """Extract and apply Agent 2's structured RetryGuidance if present.

    Returns (new_cfg, new_cs) or None if no guidance was found.
    """
    all_guidance: list[dict] = []
    for r in reports:
        a2 = r.get("agent2Verdict", {})
        all_guidance.extend(a2.get("retry_guidance", []))

    if not all_guidance:
        return None

    new_cfg = cfg
    new_cs = cs

    for g in all_guidance:
        param = g.get("parameter", "")
        amount = g.get("amount", 0.0)
        direction = g.get("direction", "lower")
        reason = g.get("reason", "Agent 2 guidance")

        if param == "cfg_scale":
            if direction == "lower":
                new_cfg = max(new_cfg - amount, config.CFG_FLOOR)
            else:
                new_cfg = new_cfg + amount
            adjustments.append(f"CFG {cfg:.1f} → {new_cfg:.1f} ({reason})")

        elif param == "control_strength":
            if direction == "higher":
                new_cs = min(new_cs + amount, config.CONTROL_STRENGTH_CEILING)
            else:
                new_cs = max(new_cs - amount, 0.0)
            adjustments.append(f"Control {cs:.2f} → {new_cs:.2f} ({reason})")

    return new_cfg, new_cs


# ═══════════════════════════════════════════════════════════════════════
# Autonomous loop
# ═══════════════════════════════════════════════════════════════════════

def run_shot_loop(
    shot_id: str,
    prompt: str,
    control_video: str | None = None,
    *,
    batch_size: int = config.DEFAULT_BATCH_SIZE,
    max_rounds: int = config.MAX_RETRY_ROUNDS,
) -> ShotManifest:
    """Run the full autonomous generation→audit→promote/retry loop.

    Returns the final ShotManifest (always saved to disk).
    """
    manifest = ShotManifest(
        shot_id=shot_id,
        prompt_text=prompt,
        control_video_path=control_video,
    )
    manifest.set_status("IN_PROGRESS")
    manifest.save()

    cfg = config.DEFAULT_CFG_SCALE
    cs = config.DEFAULT_CONTROL_STRENGTH
    total_candidates = 0

    if not health_check():
        log.error("ComfyUI is not reachable at %s", config.COMFYUI_BASE_URL)
        manifest.set_status("FAILED_MAX_RETRIES")
        manifest.save()
        return manifest

    for round_num in range(1, max_rounds + 1):
        log.info(
            "═══ Round %d/%d for %s (CFG=%.1f, CS=%.2f) ═══",
            round_num, max_rounds, shot_id, cfg, cs,
        )
        manifest.increment_attempts()

        # 1. Generate batch
        batch_results = request_draft_batch(
            prompt,
            control_video=control_video,
            count=batch_size,
            cfg_scale=cfg,
            control_strength=cs,
        )

        # Collect all output files
        candidate_files: list[Path] = []
        for br in batch_results:
            if br["error"]:
                log.warning("Skipping failed generation (seed=%d)", br["seed"])
                continue
            for p in br["paths"]:
                candidate_files.append(Path(p))

        if not candidate_files:
            log.error("All generations in round %d failed", round_num)
            continue

        # 2. Agent 2 intercepts — motion audit (blocking gate for Agent 7)
        reports = execute_gate_audit(candidate_files)

        # Record every candidate in the manifest
        for br, report in zip(batch_results, reports):
            manifest.add_candidate({
                "round": round_num,
                "seed": br["seed"],
                "cfgScale": br["cfg_scale"],
                "controlStrength": br["control_strength"],
                "gateResult": report["finalDecision"],
                "failureReasons": report.get("failures", []),
                "warnings": report.get("warnings", []),
                "artifactHash": report.get("artifactSha256", "UNAVAILABLE"),
                "artifactPath": report.get("artifactPath", ""),
                "gateReportSnapshot": report,
            })

        total_candidates += len(reports)

        # 3. Promote?
        winner = evaluate_and_promote(reports, manifest)
        if winner is not None:
            log.info("Shot %s APPROVED after %d rounds", shot_id, round_num)
            return manifest

        # 4. Agent 2 → Agent 1 feedback loop: self-correct from rejection data
        rejected = [r for r in reports if r["finalDecision"] == "REJECTED"]
        retry = calculate_retry_parameters(rejected, cfg, cs)
        cfg = retry["cfg_scale"]
        cs = retry["control_strength"]
        manifest.set_cfg_scale(cfg)
        manifest.set_control_strength(cs)
        manifest.save()

        for adj in retry["adjustments"]:
            log.info("Self-correction: %s", adj)

        if retry["should_abandon"]:
            log.warning("Parameters exhausted for %s — abandoning", shot_id)
            break

        if total_candidates >= config.MAX_TOTAL_CANDIDATES:
            log.warning("Candidate cap (%d) reached for %s", total_candidates, shot_id)
            break

    manifest.set_status("FAILED_MAX_RETRIES")
    manifest.save()
    log.info("Shot %s FAILED after %d rounds", shot_id, manifest.generation_attempts)
    return manifest
