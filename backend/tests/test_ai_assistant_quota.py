"""Engineering assistant server-side quota."""

from __future__ import annotations

import pytest

from services.ai_assistant_quota import (
    AiAssistantQuotaExceeded,
    check_and_record_quota,
    reset_quota_for_tests,
)


def setup_function():
    reset_quota_for_tests()


def test_quota_min_interval():
    check_and_record_quota("driver-1")
    with pytest.raises(AiAssistantQuotaExceeded) as exc:
        check_and_record_quota("driver-1")
    assert exc.value.reason == "min_interval"


def test_quota_session_budget(monkeypatch):
    monkeypatch.setenv("ENGINEERING_ASSISTANT_MIN_INTERVAL_SECONDS", "0")
    monkeypatch.setenv("ENGINEERING_ASSISTANT_SESSION_BUDGET", "2")
    reset_quota_for_tests()
    import importlib
    import services.ai_assistant_quota as mod

    importlib.reload(mod)
    mod.check_and_record_quota("d")
    mod.check_and_record_quota("d")
    with pytest.raises(mod.AiAssistantQuotaExceeded) as exc:
        mod.check_and_record_quota("d")
    assert exc.value.reason == "session_budget_exceeded"
    importlib.reload(mod)
