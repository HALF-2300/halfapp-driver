"""Artifact SHA-256 hashing."""

import hashlib
from pathlib import Path

_CHUNK = 1 << 16  # 64 KiB


def generate_artifact_hash(file_path: str | Path) -> str:
    """Return lowercase hex SHA-256 of the file at *file_path*."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(_CHUNK)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()
