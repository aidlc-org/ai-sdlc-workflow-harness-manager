#!/usr/bin/env python3
"""preToolUse Write/StrReplace: secrets, junk dirs, analysis-agent isolation, secret-looking content."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import (
    portal_owns_gate,
    emit_permission,
    load_config,
    load_payload,
    subagent_type,
    tool_contents,
    tool_path,
)

_PRODUCT = load_config().get("product")
_PRODUCT = _PRODUCT if isinstance(_PRODUCT, dict) else {}
_ARTIFACT = _PRODUCT.get("artifact_dir")
_AGENTS = _PRODUCT.get("readonly_agents")

# Analysis agents may write artifacts only; every other tree is product source.
ARTIFACT_DIR = (_ARTIFACT if isinstance(_ARTIFACT, str) and _ARTIFACT.strip() else "features").strip("/") + "/"
RESTRICTED = (
    {str(name).lower() for name in _AGENTS}
    if isinstance(_AGENTS, list) and _AGENTS
    else {"product-manager-agent", "ui-designer-agent", "ba-agent", "ba-critic-agent", "telemetry-agent"}
)

SECRET_PATH = re.compile(
    r"(?:^|/)\.env(?:\.|$)|credentials\.json|\.pem$|\.p12$|id_rsa$|id_ed25519$|\.netrc$",
    re.I,
)
JUNK = re.compile(r"(?:^|/)(node_modules|\.git|dist|build|coverage)(?:/|$)", re.I)
# Character classes keep the vendor prefixes from matching this file itself.
SECRET_BODY = re.compile(
    r"(?i)(api[_-]?key|secret_key|private_key|password|token)\s*[:=]\s*['\"][^'\"]{8,}"
    r"|BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY"
    r"|sk[_-]live[_-]|gh[p][_][A-Za-z0-9]{20,}"
    r"|console\.(log|debug|info|warn)\([^)]{0,200}\b(email|password|ssn|authorization)\b"
    r"|\b(gtag|fbq|mixpanel\.init|analytics\.load)\s*\("
)
UI_ARTIFACT_REF = re.compile(r"features/[a-z0-9][a-z0-9_-]*/ui/", re.I)
_REPO = Path(__file__).resolve().parents[2]


def _norm(path: str) -> str:
    return path.replace("\\", "/")


def _is_artifact(rel: str) -> bool:
    return rel.startswith(ARTIFACT_DIR) or f"/{ARTIFACT_DIR}" in rel


def _is_mockup_copy(rel: str, body: str) -> bool:
    """True when product-source write looks like features/{slug}/ui/ HTML."""
    if not rel or _is_artifact(rel):
        return False
    if UI_ARTIFACT_REF.search(body or ""):
        return True
    name = Path(rel).name.lower()
    lowered = (body or "").lower()
    skeleton = (
        "<!doctype html>" in lowered
        and "skip to content" in lowered
        and "--focus-ring" in lowered
    )
    if name.endswith((".html", ".htm", ".css")) and skeleton:
        return True
    if name.endswith((".html", ".htm", ".css")) and name not in {"index.html", "index.htm"}:
        root = _REPO / "features"
        if root.is_dir() and (any(root.glob(f"*/ui/{name}")) or any(root.glob(f"*/*/ui/{name}"))):
            return True
    return False


def main() -> int:
    extra = {"claude_event": "PreToolUse"}
    if portal_owns_gate():
        return emit_permission(True, "external portal owns this session", extra)

    payload = load_payload()
    rel = _norm(tool_path(payload))
    body = tool_contents(payload)
    kind = subagent_type(payload).lower()

    if rel and SECRET_PATH.search(rel):
        return emit_permission(False, f"Blocked write to secret/credential path: {rel}", extra)
    if rel and JUNK.search(rel):
        return emit_permission(False, f"Blocked write into generated or VCS dir: {rel}", extra)
    if body and SECRET_BODY.search(body):
        return emit_permission(
            False,
            "Blocked write: payload looks like a hardcoded secret. Use env vars / secret stores.",
            extra,
        )
    if _is_mockup_copy(rel, body):
        return emit_permission(
            False,
            f"Blocked copy of pipeline UI mockups into product source ({rel}). "
            f"Keep mockups under {ARTIFACT_DIR}{{slug}}/ui/; implement production UI in the app stack.",
            extra,
        )
    if kind in RESTRICTED and rel and not _is_artifact(rel):
        return emit_permission(
            False,
            f"{kind} may not edit product source ({rel}). Write only under {ARTIFACT_DIR}{{slug}}/.",
            extra,
        )
    return emit_permission(True, "allow", extra)


if __name__ == "__main__":
    raise SystemExit(main())
