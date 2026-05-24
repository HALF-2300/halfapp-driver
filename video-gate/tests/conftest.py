"""Pytest fixtures — generate synthetic MP4 test videos on the fly."""

from __future__ import annotations

import subprocess
from pathlib import Path

import cv2
import numpy as np
import pytest

FIXTURES = Path(__file__).parent / "fixtures"
FIXTURES.mkdir(exist_ok=True)

WIDTH, HEIGHT, FPS = 320, 240, 24


def _write_mp4(path: Path, frames: list[np.ndarray], fps: int = FPS) -> Path:
    """Write a list of BGR frames to an MP4 via OpenCV."""
    fourcc = cv2.VideoWriter.fourcc(*"mp4v")
    out = cv2.VideoWriter(str(path), fourcc, fps, (WIDTH, HEIGHT))
    for f in frames:
        out.write(f)
    out.release()

    # Re-encode with ffmpeg so ffprobe reports nb_read_frames reliably
    tmp = path.with_suffix(".tmp.mp4")
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(path), "-c:v", "libx264",
         "-pix_fmt", "yuv420p", "-an", str(tmp)],
        capture_output=True,
    )
    if tmp.exists():
        tmp.replace(path)
    return path


@pytest.fixture(scope="session")
def moving_video() -> Path:
    """3-second video with a moving white rectangle on a dark background."""
    path = FIXTURES / "moving.mp4"
    if path.exists():
        return path
    total = FPS * 3
    frames = []
    for i in range(total):
        f = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        x = int((i / total) * (WIDTH - 60))
        cv2.rectangle(f, (x, 80), (x + 60, 160), (255, 255, 255), -1)
        frames.append(f)
    return _write_mp4(path, frames)


@pytest.fixture(scope="session")
def static_video() -> Path:
    """2-second video where every frame is identical (frozen)."""
    path = FIXTURES / "static.mp4"
    if path.exists():
        return path
    frame = np.full((HEIGHT, WIDTH, 3), 128, dtype=np.uint8)
    cv2.putText(frame, "STATIC", (80, 140),
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
    return _write_mp4(path, [frame] * (FPS * 2))


@pytest.fixture(scope="session")
def too_short_video() -> Path:
    """Video with only 2 frames (~0.08 s at 24fps) — below minimum duration."""
    path = FIXTURES / "tooshort.mp4"
    if path.exists():
        return path
    frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    return _write_mp4(path, [frame, frame])


@pytest.fixture(scope="session")
def corrupted_video() -> Path:
    """A file that exists but contains garbage bytes."""
    path = FIXTURES / "corrupted.mp4"
    if path.exists():
        return path
    path.write_bytes(b"\x00\x00\x00\x1cftypisom" + b"\xff" * 512)
    return path


@pytest.fixture(scope="session")
def flow_spike_video() -> Path:
    """Horizontal bars that jump 100px every other frame — huge flow spikes."""
    path = FIXTURES / "flow_spike.mp4"
    if path.exists():
        return path
    total = FPS * 3
    frames = []
    for i in range(total):
        f = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        offset = 0 if i % 2 == 0 else 100
        for y in range(HEIGHT):
            if ((y + offset) // 20) % 2 == 0:
                f[y, :] = (255, 255, 255)
        frames.append(f)
    return _write_mp4(path, frames)
