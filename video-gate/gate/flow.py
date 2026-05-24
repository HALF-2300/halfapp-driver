"""Optical-flow stability assessment using Farneback dense flow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np

from . import config
from .frames import extract_sample_frames


def assess_optical_flow_stability(
    file_path: str | Path,
) -> dict[str, Any]:
    """Measure dense optical-flow magnitude between sampled frame pairs.

    Returns:
        mean_magnitudes   list[float] — per-pair mean magnitude
        overall_mean      float
        stable_ratio      float       — fraction of pairs below warn threshold
        decision          'ok' | 'warn' | 'reject'
    """
    frames = extract_sample_frames(file_path)
    if len(frames) < 2:
        return {
            "mean_magnitudes": [],
            "overall_mean": 0.0,
            "stable_ratio": 1.0,
            "decision": "ok",
        }

    grays = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in frames]

    magnitudes: list[float] = []
    for i in range(len(grays) - 1):
        prev, nxt = grays[i], grays[i + 1]
        if prev.shape != nxt.shape:
            nxt = cv2.resize(nxt, (prev.shape[1], prev.shape[0]))
        flow = cv2.calcOpticalFlowFarneback(
            prev, nxt,
            None,   # type: ignore[arg-type]
            pyr_scale=0.5,
            levels=3,
            winsize=15,
            iterations=3,
            poly_n=5,
            poly_sigma=1.2,
            flags=0,
        )
        mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        magnitudes.append(float(np.mean(mag)))

    overall = float(np.mean(magnitudes)) if magnitudes else 0.0
    stable_count = sum(
        1 for m in magnitudes if m < config.FLOW_WARN_MEAN_MAGNITUDE
    )
    stable_ratio = stable_count / len(magnitudes) if magnitudes else 1.0

    if overall >= config.FLOW_REJECT_MEAN_MAGNITUDE:
        decision = "reject"
    elif stable_ratio < config.FLOW_STABLE_RATIO:
        decision = "warn"
    elif overall >= config.FLOW_WARN_MEAN_MAGNITUDE:
        decision = "warn"
    else:
        decision = "ok"

    return {
        "mean_magnitudes": [round(m, 4) for m in magnitudes],
        "overall_mean": round(overall, 4),
        "stable_ratio": round(stable_ratio, 4),
        "decision": decision,
    }
