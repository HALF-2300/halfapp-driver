"""Inter-agent message protocol.

Defines the structured verdict and feedback types that agents exchange.
Every agent reads MP4 data in, emits an AgentVerdict out.  The verdict
carries enough context for any downstream agent to act without parsing
free-form text.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import IntEnum
from typing import Any


class ExitCode(IntEnum):
    """Process-level exit codes shared across all pipeline agents."""
    PASS = 0
    REJECT = 1
    WARN = 2


@dataclass(frozen=True)
class RetryGuidance:
    """Concrete parameter adjustments Agent 2 sends back to Agent 1.

    ``direction`` is always "lower" or "higher".  ``amount`` is the
    absolute delta to apply (e.g. 1.5 means subtract 1.5 from CFG).
    """
    parameter: str
    direction: str
    amount: float
    reason: str


@dataclass
class AgentVerdict:
    """Canonical output of any pipeline agent.

    Serialises cleanly to JSON for IPC (stdout piping between agents).
    """
    agent_name: str
    agent_id: int
    verdict: str                            # "PASS", "REJECT", "WARN"
    exit_code: int
    artifact_path: str
    artifact_sha256: str

    analysis: dict[str, Any] = field(default_factory=dict)
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    feedback_to_agent1: str | None = None
    retry_guidance: list[RetryGuidance] = field(default_factory=list)

    blocks_agent7: bool = False
    credits_saved: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["retry_guidance"] = [asdict(g) for g in self.retry_guidance]
        return d
