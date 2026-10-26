"""Canonical models for agent security: sessions, inline events, findings, decisions.

Only redacted metadata is kept. Prompt text, tool argument values, secrets, and
tool results must never appear in persisted records.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any
from uuid import uuid4

SCHEMA_VERSION = 1


class DecisionAction(str, Enum):
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


SEVERITY_RANK = {
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}

ACTION_RANK = {
    DecisionAction.ALLOW: 1,
    DecisionAction.WARN: 2,
    DecisionAction.BLOCK: 3,
}


@dataclass(frozen=True)
class CanonicalToolCall:
    name: str
    tool_type: str
    server: str | None
    status: str | None
    argument_keys: tuple[str, ...]


@dataclass(frozen=True)
class CanonicalSessionEvent:
    provider: str
    source: str
    session_id: str
    event_id: str
    timestamp: str
    user_messages: int
    assistant_messages: int
    tool_calls: tuple[CanonicalToolCall, ...]
    schema_version: int = SCHEMA_VERSION

    def to_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["kind"] = "session_event"
        return record


@dataclass(frozen=True)
class SecurityEvent:
    """Normalized pre-action event from a host hook payload."""

    source: str
    event_type: str
    operation: str
    tool_name: str
    target: str | None
    command: str | None
    argument_keys: tuple[str, ...]
    content_present: bool
    session_id: str | None = None
    timestamp: str | None = None
    schema_version: int = SCHEMA_VERSION

    def to_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["kind"] = "security_event"
        return record


@dataclass(frozen=True)
class Evidence:
    """Bounded, redacted references — never secret values."""

    rule_id: str
    field: str
    detail: str


@dataclass(frozen=True)
class Finding:
    finding_id: str
    provider: str
    rule_id: str
    category: str
    technique: str
    severity: Severity
    confidence: float
    recommended_action: DecisionAction
    reason: str
    evidence: tuple[Evidence, ...] = ()
    source: str | None = None
    session_id: str | None = None
    event_type: str | None = None
    latency_ms: float | None = None
    schema_version: int = SCHEMA_VERSION

    @staticmethod
    def new_id() -> str:
        return str(uuid4())

    def to_record(
        self,
        *,
        effective_action: DecisionAction | None = None,
        mode: str | None = None,
    ) -> dict[str, Any]:
        record = asdict(self)
        record["kind"] = "security_finding"
        record["severity"] = self.severity.value
        record["recommended_action"] = self.recommended_action.value
        if effective_action is not None:
            record["effective_action"] = effective_action.value
        if mode is not None:
            record["mode"] = mode
        record["evidence"] = [asdict(item) for item in self.evidence]
        return record


@dataclass(frozen=True)
class Decision:
    action: DecisionAction
    reason: str
    provider: str
    findings: tuple[Finding, ...] = ()
    latency_ms: float = 0.0
    timed_out: bool = False
    error: str | None = None

    def to_record(self, *, mode: str | None = None) -> dict[str, Any]:
        return {
            "kind": "security_decision",
            "action": self.action.value,
            "reason": self.reason,
            "provider": self.provider,
            "latency_ms": self.latency_ms,
            "timed_out": self.timed_out,
            "error": self.error,
            "mode": mode,
            "finding_ids": [f.finding_id for f in self.findings],
            "schema_version": SCHEMA_VERSION,
        }


@dataclass(frozen=True)
class ProviderCapabilities:
    name: str
    sources: tuple[str, ...]
    event_types: tuple[str, ...]
    synchronous: bool
    block_capable: bool
    max_latency_ms: int
    api_version: int = 1


@dataclass
class ProviderHealth:
    provider: str
    state: str
    reason: str
    source: str | None = None
    observed_at: str | None = None

    def to_record(self) -> dict[str, Any]:
        return {
            "kind": "provider_health",
            "provider": self.provider,
            "state": self.state,
            "source": self.source,
            "reason": self.reason,
            "observed_at": self.observed_at,
            "schema_version": SCHEMA_VERSION,
        }


def merge_actions(*actions: DecisionAction) -> DecisionAction:
    """Most restrictive wins: block > warn > allow."""
    best = DecisionAction.ALLOW
    for action in actions:
        if ACTION_RANK[action] > ACTION_RANK[best]:
            best = action
    return best
