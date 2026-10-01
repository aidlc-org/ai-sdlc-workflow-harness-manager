#!/usr/bin/env python3
"""preToolUse Write/StrReplace: secrets, junk dirs, analysis-agent isolation, secret-looking content."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import (
    portal_owns_gate,
    declared_dependencies,
    emit_permission,
    feature_slug,
    load_config,
    load_payload,
    normalize_package,
    subagent_type,
    tool_contents,
    tool_path,
    artifact_dir_name,
    is_artifact_path,
)

_PRODUCT = load_config().get("product")
_PRODUCT = _PRODUCT if isinstance(_PRODUCT, dict) else {}
_ARTIFACT = _PRODUCT.get("artifact_dir")
_AGENTS = _PRODUCT.get("readonly_agents")
_CFG = load_config()

# Analysis agents may write artifacts only; every other tree is product source.
ARTIFACT_DIR = (artifact_dir_name(_CFG) if _CFG else (
    _ARTIFACT if isinstance(_ARTIFACT, str) and _ARTIFACT.strip() else "features"
)).strip("/") + "/"
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
UI_ARTIFACT_REF = re.compile(
    r"(?:features|[A-Za-z]:[\\/][^\s\"']+)[\\/][a-z0-9][a-z0-9_-]*[\\/]ui[\\/]", re.I
)
_REPO = Path(__file__).resolve().parents[2]

_MINIMALISM = load_config().get("code_minimalism")
_MINIMALISM = _MINIMALISM if isinstance(_MINIMALISM, dict) else {}
_MANIFEST_NAMES = _MINIMALISM.get("manifest_files")
# Only the two formats this hook can parse without a third-party library.
MANIFESTS = (
    {str(name).lower() for name in _MANIFEST_NAMES}
    if isinstance(_MANIFEST_NAMES, list) and _MANIFEST_NAMES
    else {"package.json", "requirements.txt"}
)
DEPS_GATE_ON = _MINIMALISM.get("require_declared_dependencies", True) is not False
PKG_JSON_PAIR = re.compile(r'"([^"\s]+)"\s*:\s*"([~^><=*]|\d)[^"]*"')
REQ_LINE = re.compile(r"(?m)^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
PKG_JSON_BLOCKS = ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies")


def _packages_in(name: str, body: str) -> set[str]:
    """Package names a manifest body declares. Empty when the body cannot be read."""
    if not body:
        return set()
    if name == "package.json":
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            # An Edit sends a fragment, not a document; fall back to name/version pairs.
            return {normalize_package(m.group(1)) for m in PKG_JSON_PAIR.finditer(body)}
        found = set()
        if isinstance(data, dict):
            for block in PKG_JSON_BLOCKS:
                rows = data.get(block)
                if isinstance(rows, dict):
                    found |= {normalize_package(key) for key in rows}
        return found
    found = set()
    for line in body.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        match = REQ_LINE.match(line)
        if match:
            found.add(normalize_package(match.group(1)))
    return found


def _undeclared_manifest_deps(rel: str, body: str) -> list[str]:
    """Packages this write would add to a manifest without an Architect declaration."""
    name = Path(rel).name.lower()
    if name not in MANIFESTS:
        return []
    incoming = _packages_in(name, body)
    if not incoming:
        return []
    try:
        on_disk = _packages_in(name, (_REPO / rel).read_text(encoding="utf-8", errors="replace"))
    except OSError:
        on_disk = set()
    added = incoming - on_disk
    if not added:
        return []
    return sorted(added - declared_dependencies(feature_slug()))


def _norm(path: str) -> str:
    return path.replace("\\", "/")


def _is_artifact(rel: str) -> bool:
    return is_artifact_path(rel, _CFG, _REPO)


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
        from lib import artifact_zone_roots

        for zone in artifact_zone_roots(_CFG, _REPO):
            if zone.is_dir() and (
                any(zone.glob(f"*/ui/{name}")) or any(zone.glob(f"*/*/ui/{name}"))
            ):
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
    if DEPS_GATE_ON and rel and not _is_artifact(rel) and feature_slug():
        undeclared = _undeclared_manifest_deps(rel, body)
        if undeclared:
            return emit_permission(
                False,
                "Blocked undeclared dependency in %s: %s. Architect must declare it in "
                "features/%s/state/architect-agent.json context.new_dependencies "
                "(name + why_nothing_existing_works). See minimalism-policy.md."
                % (rel, ", ".join(undeclared), feature_slug()),
                extra,
            )
    return emit_permission(True, "allow", extra)


if __name__ == "__main__":
    raise SystemExit(main())
