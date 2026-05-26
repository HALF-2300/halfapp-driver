"""In-memory per-principal quota for engineering assistant (advisory only)."""

from __future__ import annotations

import time
from collections import defaultdict

_MIN_INTERVAL_SECONDS = float(
    __import__("os").getenv("ENGINEERING_ASSISTANT_MIN_INTERVAL_SECONDS", "3")
)
_SESSION_BUDGET = int(__import__("os").getenv("ENGINEERING_ASSISTANT_SESSION_BUDGET", "48"))

_last_call_at: dict[str, float] = defaultdict(float)
_call_counts: dict[str, int] = defaultdict(int)


class AiAssistantQuotaExceeded(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def check_and_record_quota(principal_id: str) -> None:
    now = time.monotonic()
    if _call_counts[principal_id] >= _SESSION_BUDGET:
        raise AiAssistantQuotaExceeded("session_budget_exceeded")
    if now - _last_call_at[principal_id] < _MIN_INTERVAL_SECONDS:
        raise AiAssistantQuotaExceeded("min_interval")
    _last_call_at[principal_id] = now
    _call_counts[principal_id] += 1


def reset_quota_for_tests() -> None:
    _last_call_at.clear()
    _call_counts.clear()
