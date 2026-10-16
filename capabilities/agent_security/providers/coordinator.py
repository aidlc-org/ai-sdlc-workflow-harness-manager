"""Inline provider coordinator: deadlines, isolation, decision merge."""

from __future__ import annotations

import time
from typing import Any

from ..models import (
    SEVERITY_RANK,
    Decision,
    DecisionAction,
    Finding,
    SecurityEvent,
    Severity,
    merge_actions,
)
from .registry import load_providers

PROVIDER_COORDINATOR = "coordinator"


def evaluate_event(
    event: SecurityEvent,
    cfg: dict[str, Any],
    *,
    guardrail_denied: bool = False,
) -> Decision:
    """Run enabled inline providers and merge with existing guardrail result.

    Existing guardrail denials can never be weakened. Provider failures default
    to fail-open unless fail_mode is ``closed``.
    """
    started = time.perf_counter()
    mode = str(cfg.get("mode") or "audit").lower()
    timeout_ms = float(cfg.get("inline_timeout_ms") or 100)
    fail_mode = str(cfg.get("fail_mode") or "open").lower()
    block_cfg = cfg.get("block") if isinstance(cfg.get("block"), dict) else {}
    min_sev = _severity(str(block_cfg.get("minimum_severity") or "high"))
    min_conf = float(block_cfg.get("minimum_confidence") or 0.9)

    findings: list[Finding] = []
    actions: list[DecisionAction] = []
    errors: list[str] = []
    timed_out = False

    if not cfg.get("enabled"):
        decision = Decision(
            action=DecisionAction.ALLOW,
            reason="agent_security disabled",
            provider=PROVIDER_COORDINATOR,
            latency_ms=(time.perf_counter() - started) * 1000.0,
        )
        return _apply_guardrail(decision, guardrail_denied)

    providers = load_providers(cfg, inline_only=True)
    deadline = started + (timeout_ms / 1000.0)

    for provider in providers:
        if time.perf_counter() >= deadline:
            timed_out = True
            errors.append("inline deadline exceeded")
            break
        try:
            caps = provider.capabilities() if hasattr(provider, "capabilities") else None
            if caps is not None and not getattr(caps, "synchronous", True):
                continue
            result = provider.evaluate(event) if hasattr(provider, "evaluate") else None
        except Exception as exc:  # noqa: BLE001 - isolate provider faults
            errors.append(f"{getattr(provider, 'name', lambda: 'provider')()}: {type(exc).__name__}")
            continue
        if result is None:
            continue
        actions.append(result.action)
        findings.extend(result.findings)

    recommended = merge_actions(*actions) if actions else DecisionAction.ALLOW
    if timed_out and fail_mode == "closed" and recommended == DecisionAction.ALLOW:
        recommended = DecisionAction.BLOCK
        errors.append("fail_closed_on_timeout")

    effective = _mode_effective(mode, recommended, findings, min_sev, min_conf)
    reason = _reason(effective, findings, errors, timed_out)
    decision = Decision(
        action=effective,
        reason=reason,
        provider=PROVIDER_COORDINATOR,
        findings=tuple(findings),
        latency_ms=(time.perf_counter() - started) * 1000.0,
        timed_out=timed_out,
        error="; ".join(errors) if errors else None,
    )
    return _apply_guardrail(decision, guardrail_denied)


def _apply_guardrail(decision: Decision, guardrail_denied: bool) -> Decision:
    if not guardrail_denied:
        return decision
    # Guardrail deny always wins; keep findings for the ledger.
    return Decision(
        action=DecisionAction.BLOCK,
        reason="existing guardrail denied the action",
        provider=decision.provider,
        findings=decision.findings,
        latency_ms=decision.latency_ms,
        timed_out=decision.timed_out,
        error=decision.error,
    )


def _mode_effective(
    mode: str,
    recommended: DecisionAction,
    findings: list[Finding],
    min_sev: Severity,
    min_conf: float,
) -> DecisionAction:
    if mode == "audit":
        return DecisionAction.ALLOW
    if mode == "warn":
        if recommended in {DecisionAction.WARN, DecisionAction.BLOCK}:
            return DecisionAction.WARN
        return DecisionAction.ALLOW
    # block mode
    if recommended == DecisionAction.BLOCK and _meets_block_threshold(findings, min_sev, min_conf):
        return DecisionAction.BLOCK
    if recommended == DecisionAction.WARN:
        return DecisionAction.WARN
    if recommended == DecisionAction.BLOCK:
        # Below threshold → warn instead of silent allow
        return DecisionAction.WARN
    return DecisionAction.ALLOW


def _meets_block_threshold(findings: list[Finding], min_sev: Severity, min_conf: float) -> bool:
    for finding in findings:
        if finding.recommended_action != DecisionAction.BLOCK:
            continue
        if SEVERITY_RANK[finding.severity] < SEVERITY_RANK[min_sev]:
            continue
        if finding.confidence < min_conf:
            continue
        return True
    return False


def _severity(name: str) -> Severity:
    try:
        return Severity(name.lower())
    except ValueError:
        return Severity.HIGH


def _reason(
    effective: DecisionAction,
    findings: list[Finding],
    errors: list[str],
    timed_out: bool,
) -> str:
    if findings:
        top = max(findings, key=lambda f: (SEVERITY_RANK[f.severity], f.confidence))
        base = top.reason
    elif timed_out:
        base = "inline provider deadline exceeded"
    elif errors:
        base = "provider error"
    else:
        base = "allow"
    if effective == DecisionAction.ALLOW:
        return base if base == "allow" else f"audit/allow: {base}"
    if effective == DecisionAction.WARN:
        return f"warning: {base}"
    return f"blocked: {base}"
