"""Frame extraction, static/frozen detection, and first-last similarity."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np

from . import config


def extract_sample_frames(
    file_path: str | Path,
    count: int | None = None,
) -> list[np.ndarray]:
    """Return *count* evenly-spaced BGR frames from the video.

    Raises ``ValueError`` if the file cannot be opened or contains no frames.
    """
    count = count or config.STATIC_SAMPLE_COUNT
    cap = cv2.VideoCapture(str(file_path))
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {file_path}")

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total < 1:
        cap.release()
        raise ValueError(f"Video has 0 frames: {file_path}")

    indices = np.linspace(0, total - 1, min(count, total), dtype=int)
    frames: list[np.ndarray] = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ok, frame = cap.read()
        if ok:
            frames.append(frame)

    cap.release()
    if not frames:
        raise ValueError(f"Could not read any frames from: {file_path}")
    return frames


def _ssim_gray(a: np.ndarray, b: np.ndarray) -> float:
    """Compute mean SSIM between two BGR images (resized to match)."""
    g1 = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY).astype(np.float64)
    g2 = cv2.cvtColor(b, cv2.COLOR_BGR2GRAY).astype(np.float64)
    if g1.shape != g2.shape:
        g2 = cv2.resize(g2, (g1.shape[1], g1.shape[0]))

    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2

    mu1 = cv2.GaussianBlur(g1, (11, 11), 1.5)
    mu2 = cv2.GaussianBlur(g2, (11, 11), 1.5)
    mu1_sq = mu1 * mu1
    mu2_sq = mu2 * mu2
    mu1_mu2 = mu1 * mu2

    sigma1_sq = cv2.GaussianBlur(g1 * g1, (11, 11), 1.5) - mu1_sq
    sigma2_sq = cv2.GaussianBlur(g2 * g2, (11, 11), 1.5) - mu2_sq
    sigma12 = cv2.GaussianBlur(g1 * g2, (11, 11), 1.5) - mu1_mu2

    num = (2 * mu1_mu2 + c1) * (2 * sigma12 + c2)
    den = (mu1_sq + mu2_sq + c1) * (sigma1_sq + sigma2_sq + c2)

    ssim_map = num / den
    return float(np.mean(ssim_map))


def detect_static_or_frozen_video(
    file_path: str | Path,
) -> dict[str, Any]:
    """Check whether the video is essentially a still image.

    Returns a dict with:
        is_static (bool)
        mean_ssim (float)
        pair_ssims (list[float])
    """
    frames = extract_sample_frames(file_path)
    if len(frames) < 2:
        return {"is_static": True, "mean_ssim": 1.0, "pair_ssims": []}

    pair_ssims: list[float] = []
    for i in range(len(frames) - 1):
        pair_ssims.append(_ssim_gray(frames[i], frames[i + 1]))

    mean_ssim = float(np.mean(pair_ssims))
    return {
        "is_static": mean_ssim >= config.STATIC_SSIM_THRESHOLD,
        "mean_ssim": round(mean_ssim, 6),
        "pair_ssims": [round(s, 6) for s in pair_ssims],
    }


def measure_first_last_frame_similarity(
    file_path: str | Path,
) -> dict[str, Any]:
    """Compare the first and last frame of the video via SSIM.

    Returns a dict with:
        ssim       (float)
        decision   ('ok' | 'warn' | 'reject')
    """
    cap = cv2.VideoCapture(str(file_path))
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {file_path}")

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total < 2:
        cap.release()
        return {"ssim": 1.0, "decision": "ok"}

    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    ok1, first = cap.read()
    cap.set(cv2.CAP_PROP_POS_FRAMES, total - 1)
    ok2, last = cap.read()
    cap.release()

    if not ok1 or not ok2:
        raise ValueError("Could not read first/last frames")

    ssim = _ssim_gray(first, last)

    if ssim < config.FIRST_LAST_REJECT_SSIM:
        decision = "reject"
    elif ssim < config.FIRST_LAST_WARN_SSIM:
        decision = "warn"
    else:
        decision = "ok"

    return {"ssim": round(ssim, 6), "decision": decision}
