"""Public entry used by hooks and CLI to evaluate one action."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import load_agent_security_config, state_dir_for
from .ledger import append_decision, append_findings, project_to_observability
from .models import Decision, DecisionAction, SecurityEvent
from .normalize import normalize_hook_payload
from .providers.coordinator import evaluate_event


def evaluate_payload(
    payload: dict[str, Any],
    *,
    event_type: str,
    operation: str,
    project: Path | None = None,
    guardrail_denied: bool = False,
    persist: bool = True,
    cfg: dict[str, Any] | None = None,
) -> Decision:
    """Normalize payload, run inline providers, optionally persist findings."""
    project = Path(project) if project is not None else Path.cwd()
    cfg = cfg if cfg is not None else load_agent_security_config(project)
    event = normalize_hook_payload(payload, event_type=event_type, operation=operation)
    decision = evaluate_event(event, cfg, guardrail_denied=guardrail_denied)
    if persist and cfg.get("enabled"):
        _persist(project, cfg, decision)
    return decision


def evaluate_security_event(
    event: SecurityEvent,
    *,
    project: Path | None = None,
    guardrail_denied: bool = False,
    persist: bool = True,
    cfg: dict[str, Any] | None = None,
) -> Decision:
    project = Path(project) if project is not None else Path.cwd()
    cfg = cfg if cfg is not None else load_agent_security_config(project)
    decision = evaluate_event(event, cfg, guardrail_denied=guardrail_denied)
    if persist and cfg.get("enabled"):
        _persist(project, cfg, decision)
    return decision


def decision_allows(decision: Decision) -> bool:
    return decision.action != DecisionAction.BLOCK


def decision_message(decision: Decision) -> str:
    return decision.reason or decision.action.value


def _persist(project: Path, cfg: dict[str, Any], decision: Decision) -> None:
    state = state_dir_for(project, cfg)
    mode = str(cfg.get("mode") or "audit")
    if decision.findings:
        append_findings(
            state,
            decision.findings,
            effective_action=decision.action,
            mode=mode,
        )
    append_decision(state, decision, mode=mode)
    if cfg.get("export_observability_projection", True):
        project_to_observability(
            project,
            findings=decision.findings,
            decision=decision,
            mode=mode,
        )
