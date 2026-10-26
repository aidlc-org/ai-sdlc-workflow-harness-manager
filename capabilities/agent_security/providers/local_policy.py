"""Built-in deterministic local policy provider (inline)."""

from __future__ import annotations

import math
import re
import time
from typing import Any

from ..models import (
    Decision,
    DecisionAction,
    Evidence,
    Finding,
    ProviderCapabilities,
    SecurityEvent,
    Severity,
)

PROVIDER_NAME = "local-policy"

# Path patterns that commonly hold credentials.
SECRET_PATH = re.compile(
    r"(?:^|/|\\)\.env(?:\.|$)|credentials\.json|\.pem$|\.p12$|id_rsa$|id_ed25519$|\.netrc$|"
    r"secrets?\.(ya?ml|json|toml)$|aws/credentials|\.kube/config",
    re.I,
)

# Shell: destructive or curl|sh style.
DESTROY = re.compile(
    r"(rm\s+-rf\s+(?:/|~|\$HOME)(?:\s|$|/))|(\bmkfs\.)|(\bdd\s+if=)",
    re.I,
)
PIPE_SHELL = re.compile(r"(curl|wget|fetch)\b[^|&;\n]*\|\s*(ba)?sh\b", re.I)
FORCE_PUSH = re.compile(r"\bgit\s+push\s+.*--force\b|\bgit\s+push\s+-f\b", re.I)
REMOTE = re.compile(r"\b(ssh\s+|scp\s+|rsync\s+.*:)", re.I)
NET = re.compile(r"\b(curl|wget|nc|ncat|npx\s+--yes)\b", re.I)
LOCAL_NET = re.compile(r"(127\.0\.0\.1|localhost|\[::1\])", re.I)
EXFIL_HINT = re.compile(
    r"\b(curl|wget|nc|ncat)\b[\s\S]{0,120}\b(\.env|id_rsa|credentials|secret|token|password)\b"
    r"|\b(\.env|id_rsa|credentials)\b[\s\S]{0,80}\b(curl|wget|nc|ncat)\b"
    r"|\b(curl|wget|nc|ncat)\b[\s\S]{0,80}<\s*\.?/?\.?env\b"
    r"|\b(cat|type|Get-Content)\b[\s\S]{0,80}\b(\.env|id_rsa)\b[\s\S]{0,40}\|\s*(curl|wget|nc)",
    re.I,
)

# Content patterns — match structure only; findings never store the matched value.
SECRET_BODY = re.compile(
    r"(?i)(api[_-]?key|secret_key|private_key|password|token)\s*[:=]\s*['\"][^'\"]{8,}"
    r"|BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY"
    r"|sk[_-]live[_-]|ghp_[A-Za-z0-9]{20,}"
    r"|xox[baprs]-[A-Za-z0-9-]{10,}"
)

# MCP tools that look like upload/exfil.
MCP_RISKY = re.compile(
    r"(upload|exfil|send_file|post_secret|webhook|pastebin|raw_http)",
    re.I,
)

# High-entropy token-ish strings (contextual — only when keys look secret-related).
SECRET_KEY_NAME = re.compile(r"(password|secret|token|api[_-]?key|credential|auth)", re.I)


class LocalPolicyProvider:
    def name(self) -> str:
        return PROVIDER_NAME

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            name=PROVIDER_NAME,
            sources=("cursor", "copilot-cli", "claude", "unknown"),
            event_types=("pre_shell", "pre_mcp", "pre_read", "pre_write"),
            synchronous=True,
            block_capable=True,
            max_latency_ms=50,
        )

    def health(self) -> list[dict[str, Any]]:
        return [
            {
                "kind": "provider_health",
                "provider": PROVIDER_NAME,
                "state": "ok",
                "source": None,
                "reason": "local-policy ready",
            }
        ]

    def evaluate(self, event: SecurityEvent) -> Decision | None:
        started = time.perf_counter()
        findings: list[Finding] = []
        findings.extend(self._shell_rules(event))
        findings.extend(self._path_rules(event))
        findings.extend(self._mcp_rules(event))
        findings.extend(self._write_rules(event))
        findings.extend(self._entropy_rules(event))
        latency = (time.perf_counter() - started) * 1000.0
        if not findings:
            return Decision(
                action=DecisionAction.ALLOW,
                reason="local-policy: no match",
                provider=PROVIDER_NAME,
                latency_ms=latency,
            )
        action = DecisionAction.ALLOW
        for finding in findings:
            if finding.recommended_action == DecisionAction.BLOCK:
                action = DecisionAction.BLOCK
            elif finding.recommended_action == DecisionAction.WARN and action != DecisionAction.BLOCK:
                action = DecisionAction.WARN
        top = max(findings, key=lambda f: (f.severity.value, f.confidence))
        return Decision(
            action=action,
            reason=top.reason,
            provider=PROVIDER_NAME,
            findings=tuple(findings),
            latency_ms=latency,
        )

    def collect(self, state_dir: Any, sources: tuple[str, ...] | list[str]) -> dict[str, Any]:
        return {"provider": PROVIDER_NAME, "new_events": 0, "note": "local-policy is inline-only"}

    def _finding(
        self,
        event: SecurityEvent,
        *,
        rule_id: str,
        category: str,
        technique: str,
        severity: Severity,
        confidence: float,
        action: DecisionAction,
        reason: str,
        field: str,
        detail: str,
    ) -> Finding:
        return Finding(
            finding_id=Finding.new_id(),
            provider=PROVIDER_NAME,
            rule_id=rule_id,
            category=category,
            technique=technique,
            severity=severity,
            confidence=confidence,
            recommended_action=action,
            reason=reason,
            evidence=(Evidence(rule_id=rule_id, field=field, detail=detail),),
            source=event.source,
            session_id=event.session_id,
            event_type=event.event_type,
        )

    def _shell_rules(self, event: SecurityEvent) -> list[Finding]:
        if event.event_type not in {"pre_shell", "shell"} and event.operation not in {"shell", "bash"}:
            if not event.command:
                return []
        cmd = event.command or ""
        if not cmd.strip():
            return []
        out: list[Finding] = []
        if DESTROY.search(cmd) or PIPE_SHELL.search(cmd):
            out.append(
                self._finding(
                    event,
                    rule_id="shell.destructive",
                    category="dangerous_command",
                    technique="T1059",
                    severity=Severity.CRITICAL,
                    confidence=0.99,
                    action=DecisionAction.BLOCK,
                    reason="Destructive or curl|sh style command detected",
                    field="command",
                    detail="matched destructive/pipe-shell pattern",
                )
            )
        if EXFIL_HINT.search(cmd):
            out.append(
                self._finding(
                    event,
                    rule_id="shell.credential_exfil",
                    category="credential_exfiltration",
                    technique="T1048",
                    severity=Severity.CRITICAL,
                    confidence=0.95,
                    action=DecisionAction.BLOCK,
                    reason="Command appears to transmit credential material off-host",
                    field="command",
                    detail="matched exfil pattern",
                )
            )
        if FORCE_PUSH.search(cmd):
            out.append(
                self._finding(
                    event,
                    rule_id="shell.force_push",
                    category="destructive_vcs",
                    technique="T1485",
                    severity=Severity.HIGH,
                    confidence=0.85,
                    action=DecisionAction.WARN,
                    reason="Force-push to remote detected",
                    field="command",
                    detail="git push --force",
                )
            )
        if REMOTE.search(cmd):
            out.append(
                self._finding(
                    event,
                    rule_id="shell.remote_transfer",
                    category="remote_access",
                    technique="T1021",
                    severity=Severity.HIGH,
                    confidence=0.9,
                    action=DecisionAction.BLOCK,
                    reason="Remote ssh/scp/rsync command detected",
                    field="command",
                    detail="matched remote transfer pattern",
                )
            )
        if NET.search(cmd) and not LOCAL_NET.search(cmd):
            out.append(
                self._finding(
                    event,
                    rule_id="shell.outbound_network",
                    category="outbound_network",
                    technique="T1071",
                    severity=Severity.MEDIUM,
                    confidence=0.8,
                    action=DecisionAction.WARN,
                    reason="Non-localhost network command detected",
                    field="command",
                    detail="matched outbound network tool",
                )
            )
        return out

    def _path_rules(self, event: SecurityEvent) -> list[Finding]:
        target = event.target or ""
        if not target:
            return []
        out: list[Finding] = []
        if SECRET_PATH.search(target.replace("\\", "/")):
            category = (
                "credential_file_access"
                if event.event_type in {"pre_read", "read"}
                else "credential_file_write"
            )
            out.append(
                self._finding(
                    event,
                    rule_id="path.credential",
                    category=category,
                    technique="T1552",
                    severity=Severity.CRITICAL,
                    confidence=0.97,
                    action=DecisionAction.BLOCK,
                    reason="Protected credential path referenced",
                    field="target",
                    detail="matched credential path pattern",
                )
            )
        return out

    def _mcp_rules(self, event: SecurityEvent) -> list[Finding]:
        if event.event_type not in {"pre_mcp", "mcp"} and event.operation not in {"mcp"}:
            return []
        name = event.tool_name or ""
        out: list[Finding] = []
        if MCP_RISKY.search(name):
            out.append(
                self._finding(
                    event,
                    rule_id="mcp.risky_tool",
                    category="unapproved_mcp_tool",
                    technique="T1105",
                    severity=Severity.HIGH,
                    confidence=0.9,
                    action=DecisionAction.BLOCK,
                    reason="MCP tool name matches upload/exfil pattern",
                    field="tool_name",
                    detail="matched risky MCP name pattern",
                )
            )
        # Sensitive path keys on MCP args
        sensitive_keys = {"path", "file", "file_path", "filepath", "target"}
        if sensitive_keys.intersection(event.argument_keys) and event.event_type in {"pre_mcp", "mcp"}:
            # Only warn — path value is not available by design
            out.append(
                self._finding(
                    event,
                    rule_id="mcp.path_argument",
                    category="mcp_scope_violation",
                    technique="T1083",
                    severity=Severity.MEDIUM,
                    confidence=0.6,
                    action=DecisionAction.WARN,
                    reason="MCP tool received a path-like argument key",
                    field="argument_keys",
                    detail="path-related argument key present",
                )
            )
        return out

    def _write_rules(self, event: SecurityEvent) -> list[Finding]:
        if event.event_type not in {"pre_write", "write"} and event.operation not in {"write", "edit"}:
            return []
        out: list[Finding] = []
        # content_present alone cannot prove a secret; path rules handle credential files.
        # When content is present we emit a low-confidence note only if target looks secret-ish.
        target = (event.target or "").lower()
        if event.content_present and SECRET_KEY_NAME.search(target):
            out.append(
                self._finding(
                    event,
                    rule_id="write.secret_named_file",
                    category="secret_write",
                    technique="T1552",
                    severity=Severity.HIGH,
                    confidence=0.7,
                    action=DecisionAction.WARN,
                    reason="Write to a secret-named file with content present",
                    field="target",
                    detail="secret-like filename with body",
                )
            )
        return out

    def _entropy_rules(self, event: SecurityEvent) -> list[Finding]:
        """Argument-key based entropy gate — values are never inspected here."""
        # Without values we can only flag suspicious key names on outbound tools.
        if not event.command and event.event_type not in {"pre_shell", "shell"}:
            return []
        keys = event.argument_keys
        if not keys:
            return []
        suspicious = [k for k in keys if SECRET_KEY_NAME.search(k)]
        if not suspicious:
            return []
        if event.command and NET.search(event.command):
            return [
                self._finding(
                    event,
                    rule_id="shell.secret_keys_with_network",
                    category="credential_exfiltration",
                    technique="T1048",
                    severity=Severity.HIGH,
                    confidence=0.75,
                    action=DecisionAction.WARN,
                    reason="Network command carries secret-like argument keys",
                    field="argument_keys",
                    detail="secret-like keys with network tool",
                )
            ]
        return []


def shannon_entropy(text: str) -> float:
    """Public helper for tests; production path does not store matched values."""
    if not text:
        return 0.0
    freq: dict[str, int] = {}
    for ch in text:
        freq[ch] = freq.get(ch, 0) + 1
    length = len(text)
    return -sum((n / length) * math.log2(n / length) for n in freq.values())
