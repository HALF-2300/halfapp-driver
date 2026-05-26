"""Telemetry retention configuration."""

from __future__ import annotations

import os

DEFAULT_TELEMETRY_RETENTION_DAYS = 14


def get_telemetry_retention_days() -> int:
    raw = os.getenv("HALFAPP_TELEMETRY_RETENTION_DAYS", str(DEFAULT_TELEMETRY_RETENTION_DAYS))
    try:
        days = int(raw)
    except ValueError:
        days = DEFAULT_TELEMETRY_RETENTION_DAYS
    return max(1, min(days, 365))
