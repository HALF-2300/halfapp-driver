"""ShotManifestV1 — in-memory + on-disk tracking of the generation loop."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import config

_SCHEMA_VERSION = "1.0.0"


class ShotManifest:
    """Create, update, and persist a ShotManifestV1 to disk as JSON."""

    def __init__(
        self,
        shot_id: str,
        prompt_text: str = "",
        control_video_path: str | None = None,
    ) -> None:
        now = _now_iso()
        self._data: dict[str, Any] = {
            "schemaVersion": _SCHEMA_VERSION,
            "shotId": shot_id,
            "promptText": prompt_text,
            "controlVideoPath": control_video_path,
            "status": "AWAITING_MOTION_PASS",
            "generationAttempts": 0,
            "candidates": [],
            "currentCfgScale": config.DEFAULT_CFG_SCALE,
            "currentControlStrength": config.DEFAULT_CONTROL_STRENGTH,
            "verifiedArtifact": None,
            "createdAt": now,
            "updatedAt": now,
        }
        self._path = config.MANIFEST_DIR / f"{shot_id}.json"

    @property
    def data(self) -> dict[str, Any]:
        return self._data

    @property
    def path(self) -> Path:
        return self._path

    @property
    def shot_id(self) -> str:
        return self._data["shotId"]

    @property
    def status(self) -> str:
        return self._data["status"]

    @property
    def generation_attempts(self) -> int:
        return self._data["generationAttempts"]

    @property
    def cfg_scale(self) -> float:
        return self._data["currentCfgScale"]

    @property
    def control_strength(self) -> float:
        return self._data["currentControlStrength"]

    @property
    def candidates(self) -> list[dict]:
        return self._data["candidates"]

    def set_status(self, status: str) -> None:
        self._data["status"] = status
        self._touch()

    def increment_attempts(self) -> None:
        self._data["generationAttempts"] += 1
        self._touch()

    def add_candidate(self, candidate: dict) -> None:
        self._data["candidates"].append(candidate)
        self._touch()

    def set_cfg_scale(self, value: float) -> None:
        self._data["currentCfgScale"] = round(value, 2)
        self._touch()

    def set_control_strength(self, value: float) -> None:
        self._data["currentControlStrength"] = round(value, 2)
        self._touch()

    def promote(
        self,
        artifact_hash: str,
        artifact_path: str,
        gate_decision: str,
    ) -> None:
        self._data["verifiedArtifact"] = {
            "artifactHash": artifact_hash,
            "artifactPath": artifact_path,
            "promotedAt": _now_iso(),
            "gateDecision": gate_decision,
        }
        self._data["status"] = "APPROVED"
        self._touch()

    def save(self) -> Path:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._data, indent=2), encoding="utf-8",
        )
        return self._path

    @classmethod
    def load(cls, path: Path) -> ShotManifest:
        raw = json.loads(path.read_text(encoding="utf-8"))
        m = cls.__new__(cls)
        m._data = raw
        m._path = path
        return m

    def _touch(self) -> None:
        self._data["updatedAt"] = _now_iso()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
