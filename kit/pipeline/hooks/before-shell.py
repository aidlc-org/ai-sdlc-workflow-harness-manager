#!/usr/bin/env python3
"""beforeShellExecution: block high-risk autonomous actions (VCS, exfil, deps, destroy)."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import (
    portal_owns_gate,
    declared_dependencies,
    emit_permission,
    feature_slug,
    load_payload,
    normalize_package,
    tool_command,
)

PIPE_SHELL = re.compile(r"(curl|wget|fetch)\b[^|&;\n]*\|\s*(ba)?sh\b", re.I)
DESTROY = re.compile(
    r"(rm\s+-rf\s+(/|~|\$HOME)\b)|(\bmkfs\.)|(\bdd\s+if=)",
    re.I,
)
VCS = re.compile(
    r"\b(git\s+commit|git\s+push|git\s+push\s+--force|npm\s+publish|twine\s+upload)\b",
    re.I,
)
DEPS = re.compile(
    r"\b(npm\s+i(nstall)?|pnpm\s+add|yarn\s+add|pip(\d)?\s+install|uv\s+add)\b",
    re.I,
)
REMOTE = re.compile(r"\b(ssh\s+|scp\s+|rsync\s+.*:)", re.I)
NET = re.compile(r"\b(curl|wget|nc|ncat|npx\s+--yes)\b", re.I)
LOCAL_NET = re.compile(r"(127\.0\.0\.1|localhost|\[::1\])", re.I)
INSTALL_VERB = re.compile(
    r"\b(?:npm\s+i(?:nstall)?|pnpm\s+add|yarn\s+add|pip\d?\s+install|uv\s+add)\b",
    re.I,
)
VERSION_SPEC = re.compile(r"(==|>=|<=|~=|!=|>|<).*$")
ARG_TAKES_VALUE = {"-r", "--requirement", "-c", "--constraint", "-e", "--editable", "--prefix", "--target"}


def _package_name(token: str) -> str:
    """Bare package name from one install argument, or "" when it is not a package."""
    token = VERSION_SPEC.sub("", token.strip().strip("\"'"))
    if token.startswith("@"):
        at = token.find("@", 1)
        token = token[:at] if at > 0 else token
    elif "@" in token:
        token = token.split("@", 1)[0]
    if not token or token.startswith(("$", ".", "/", "~")) or "://" in token:
        return ""
    if "/" in token and not token.startswith("@"):
        return ""
    if token.endswith((".txt", ".toml", ".cfg", ".whl", ".gz", ".zip", ".json")):
        return ""
    return token


def install_packages(cmd: str) -> list[str]:
    """Packages an install command would add. Empty means a manifest restore."""
    names: list[str] = []
    for segment in re.split(r"&&|\|\||;|\|", cmd):
        match = INSTALL_VERB.search(segment)
        if not match:
            continue
        skip_next = False
        for token in segment[match.end():].split():
            if skip_next:
                skip_next = False
                continue
            if token.startswith("-"):
                skip_next = token in ARG_TAKES_VALUE
                continue
            name = _package_name(token)
            if name and name not in names:
                names.append(name)
    return names


def main() -> int:
    extra = {"claude_event": "PreToolUse"}
    if portal_owns_gate() or os.environ.get("PIPELINE_ALLOW_ALL") == "1":
        return emit_permission(True, "allow", extra)

    payload = load_payload()
    cmd = tool_command(payload)
    if not cmd.strip():
        return emit_permission(True, "allow", extra)

    if DESTROY.search(cmd) or PIPE_SHELL.search(cmd):
        return emit_permission(
            False,
            "Blocked destructive or curl|sh command. Autonomous agents must not wipe disks or pipe remote scripts to a shell.",
            extra,
        )
    if os.environ.get("PIPELINE_ALLOW_GIT") != "1" and VCS.search(cmd):
        return emit_permission(
            False,
            "Blocked commit/push/publish. Set PIPELINE_ALLOW_GIT=1 only when the user asked to ship.",
            extra,
        )
    if os.environ.get("PIPELINE_ALLOW_DEPS") != "1" and DEPS.search(cmd):
        # No package argument means "restore what the manifest already pins" — nothing new.
        wanted = install_packages(cmd)
        slug = feature_slug(payload)
        declared = declared_dependencies(slug)
        missing = [name for name in wanted if normalize_package(name) not in declared]
        if missing and (slug or declared):
            return emit_permission(
                False,
                "Blocked undeclared dependency: %s. Architect must declare it in "
                "features/%s/state/architect-agent.json context.new_dependencies "
                "(name + why_nothing_existing_works) and mirror it in HANDOFF-architect.md. "
                "Otherwise use the native or already-installed alternative. See minimalism-policy.md."
                % (", ".join(missing), slug or "{slug}"),
                extra,
            )
        if missing:
            return emit_permission(
                False,
                "Blocked new dependency install. Reuse existing libraries or set PIPELINE_ALLOW_DEPS=1 after a spec/security note.",
                extra,
            )
    if REMOTE.search(cmd):
        return emit_permission(
            False,
            "Blocked ssh/scp/rsync to a remote host from the agent session.",
            extra,
        )
    if os.environ.get("PIPELINE_ALLOW_NET") != "1" and NET.search(cmd) and not LOCAL_NET.search(cmd):
        return emit_permission(
            False,
            "Blocked non-localhost network command (possible exfil). Use 127.0.0.1 or set PIPELINE_ALLOW_NET=1.",
            extra,
        )
    return emit_permission(True, "allow", extra)


if __name__ == "__main__":
    raise SystemExit(main())
