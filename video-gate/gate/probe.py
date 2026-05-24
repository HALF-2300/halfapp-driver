"""FFprobe-based technical audit of an MP4 candidate."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


class ProbeError(Exception):
    """Raised when ffprobe cannot read the file or returns unexpected data."""


def run_ffprobe_audit(file_path: str | Path) -> dict[str, Any]:
    """Run ffprobe on *file_path* and return a normalised metadata dict.

    Returned keys:
        duration_seconds  (float)
        fps               (float)
        codec             (str)
        frame_count       (int)
        width             (int)
        height            (int)
        raw               (dict)   — full ffprobe JSON for debugging
    """
    fp = Path(file_path)
    if not fp.is_file():
        raise ProbeError(f"File not found: {fp}")

    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-count_frames",
        "-show_entries",
        "stream=codec_name,width,height,r_frame_rate,nb_read_frames,duration",
        "-show_entries",
        "format=duration",
        "-of", "json",
        str(fp),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except FileNotFoundError:
        raise ProbeError("ffprobe not found on PATH")
    except subprocess.TimeoutExpired:
        raise ProbeError("ffprobe timed out")

    if result.returncode != 0:
        raise ProbeError(
            f"ffprobe exited {result.returncode}: {result.stderr.strip()}"
        )

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ProbeError(f"ffprobe produced invalid JSON: {exc}")

    streams = data.get("streams", [])
    if not streams:
        raise ProbeError("No video stream found")

    s = streams[0]
    fmt = data.get("format", {})

    duration = _float(s.get("duration")) or _float(fmt.get("duration"))
    fps = _parse_rate(s.get("r_frame_rate"))
    frame_count = _int(s.get("nb_read_frames"))

    return {
        "duration_seconds": duration,
        "fps": fps,
        "codec": s.get("codec_name"),
        "frame_count": frame_count,
        "width": _int(s.get("width")),
        "height": _int(s.get("height")),
        "raw": data,
    }


def _float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _int(v: Any) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except (ValueError, TypeError):
        return None


def _parse_rate(rate_str: str | None) -> float | None:
    """Parse ffprobe's rational frame rate (e.g. '30/1', '24000/1001')."""
    if not rate_str:
        return None
    if "/" in rate_str:
        parts = rate_str.split("/")
        try:
            num, den = float(parts[0]), float(parts[1])
            return num / den if den else None
        except (ValueError, IndexError):
            return None
    return _float(rate_str)
