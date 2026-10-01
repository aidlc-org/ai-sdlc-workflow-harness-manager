#!/usr/bin/env python3
"""Shared stdin/stdout JSON helpers for Cursor, Claude Code, and Chorus."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any


def load_config() -> dict[str, Any]:
    """Project `.pipeline/config.json`, else `~/.pipeline/config.json`. Missing means defaults."""
    repo = Path(__file__).resolve().parents[2]
    candidates = (
        repo / ".pipeline" / "config.json",
        Path.home() / ".pipeline" / "config.json",
    )
    for path in candidates:
        try:
            if not path.is_file():
                continue
            with path.open(encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            return data
    return {}


def artifact_dir_name(cfg: dict[str, Any] | None = None) -> str:
    cfg = cfg if cfg is not None else load_config()
    product = cfg.get("product") if isinstance(cfg.get("product"), dict) else {}
    value = product.get("artifact_dir") if isinstance(product, dict) else None
    if not isinstance(value, str) or not value.strip():
        return "features"
    return value.strip().strip("/\\").replace("\\", "/") or "features"


def memory_root_from_config(cfg: dict[str, Any] | None = None, repo: Path | None = None) -> Path | None:
    """Absolute memory root when enabled, else None."""
    cfg = cfg if cfg is not None else load_config()
    mem = cfg.get("memory") if isinstance(cfg.get("memory"), dict) else {}
    if not isinstance(mem, dict) or mem.get("enabled") is not True:
        return None
    raw = mem.get("root")
    if not isinstance(raw, str) or not raw.strip():
        return None
    path = Path(raw.strip()).expanduser()
    base = repo or Path(__file__).resolve().parents[2]
    if not path.is_absolute():
        path = base / path
    return path.resolve()


def artifact_zone_roots(cfg: dict[str, Any] | None = None, repo: Path | None = None) -> list[Path]:
    """Directories that count as the artifact write zone."""
    cfg = cfg if cfg is not None else load_config()
    repo = (repo or Path(__file__).resolve().parents[2]).resolve()
    name = artifact_dir_name(cfg)
    roots: list[Path] = []
    mem = memory_root_from_config(cfg, repo)
    if mem is not None:
        layout = str(mem_cfg_layout(cfg))
        pid = mem_cfg_project_id(cfg)
        if layout == "namespaced" and pid:
            roots.append((mem / "projects" / pid / name).resolve())
        else:
            roots.append((mem / name).resolve())
        # Also allow bare memory root + features for flat writes
        roots.append((mem / name).resolve())
    roots.append((repo / name).resolve())
    # de-dupe
    seen: set[str] = set()
    out: list[Path] = []
    for r in roots:
        key = str(r).lower()
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def mem_cfg_layout(cfg: dict[str, Any]) -> str:
    mem = cfg.get("memory") if isinstance(cfg.get("memory"), dict) else {}
    layout = mem.get("layout") if isinstance(mem, dict) else None
    if isinstance(layout, str) and layout.strip().lower() in {"flat", "namespaced"}:
        return layout.strip().lower()
    pid = mem_cfg_project_id(cfg)
    return "namespaced" if pid else "flat"


def mem_cfg_project_id(cfg: dict[str, Any]) -> str | None:
    mem = cfg.get("memory") if isinstance(cfg.get("memory"), dict) else {}
    if not isinstance(mem, dict):
        return None
    pid = mem.get("project_id")
    if pid is None:
        return None
    text = str(pid).strip()
    return text or None


def is_artifact_path(path: str, cfg: dict[str, Any] | None = None, repo: Path | None = None) -> bool:
    """True if path (relative or absolute) is under a configured artifact zone."""
    if not path:
        return False
    cfg = cfg if cfg is not None else load_config()
    repo = (repo or Path(__file__).resolve().parents[2]).resolve()
    name = artifact_dir_name(cfg)
    norm = path.replace("\\", "/")
    # Relative product-style path
    if norm.startswith(f"{name}/") or f"/{name}/" in f"/{norm}":
        # If memory is enabled, still allow local features/ for transition
        return True
    # Absolute path under memory root / feature zone
    try:
        target = Path(path)
        if not target.is_absolute():
            target = (repo / path).resolve()
        else:
            target = target.resolve()
    except (OSError, RuntimeError):
        return norm.startswith(f"{name}/")
    for zone in artifact_zone_roots(cfg, repo):
        try:
            target.relative_to(zone)
            return True
        except ValueError:
            continue
    return False


def load_payload() -> dict[str, Any]:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def portal_owns_gate() -> bool:
    """Skip when an external HITL portal already owns the session."""
    if os.environ.get("PIPELINE_HOOK_SKIP") == "1":
        return True
    return bool(os.environ.get("CHORUS_TASK_ID") and os.environ.get("CHORUS_PORTAL"))


def hook_format() -> str:
    """`cursor` or `claude` forces one shape. Anything else means emit both."""
    raw = os.environ.get("PIPELINE_HOOK_FORMAT") or os.environ.get("CHORUS_HOOK_FORMAT") or ""
    return raw.strip().lower()


def _write(out: dict[str, Any]) -> int:
    json.dump(out, sys.stdout)
    sys.stdout.write("\n")
    return 0


def emit_permission(allow: bool, reason: str, extra: dict[str, Any] | None = None) -> int:
    """Allow/deny in a shape every supported harness understands.

    Cursor reads `permission`, Claude Code reads `hookSpecificOutput`, and
    Copilot reads a top-level `permissionDecision`. The three key sets do not
    collide, so emitting all of them lets one hook serve every host with no
    environment variable -- which no harness sets portably on Windows anyway.
    Set `PIPELINE_HOOK_FORMAT` to `cursor`, `claude`, or `copilot` to force one.
    """
    fmt = hook_format()
    reason = reason or ("allow" if allow else "deny")
    extra = dict(extra or {})
    event = extra.pop("claude_event", "PreToolUse")
    decision = "allow" if allow else "deny"
    claude = {
        "hookSpecificOutput": {
            "hookEventName": event,
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }
    cursor = {"permission": decision, "user_message": reason, "agent_message": reason}
    # Copilot reads these at the top level; Cursor and Claude ignore them.
    copilot = {"permissionDecision": decision, "permissionDecisionReason": reason}
    if fmt == "claude":
        return _write(claude)
    if fmt == "cursor":
        return _write({**cursor, **extra})
    if fmt == "copilot":
        return _write(copilot)
    return _write({**cursor, **extra, **copilot, **claude})

def emit_followup(message: str) -> int:
    json.dump({"followup_message": message}, sys.stdout)
    sys.stdout.write("\n")
    return 0


def subagent_type(payload: dict[str, Any]) -> str:
    for key in ("subagent_type", "subagentType", "agent_type", "agentType", "type"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    nested = payload.get("subagent")
    if isinstance(nested, dict):
        return subagent_type(nested)
    return ""


def prompt_text(payload: dict[str, Any]) -> str:
    for key in ("prompt", "task", "description", "user_prompt"):
        val = payload.get(key)
        if isinstance(val, str):
            return val
    return ""


def emit_context(message: str, event: str = "PostToolUse") -> int:
    """Inject a reminder. Both shapes, for the same reason as `emit_permission`."""
    if not message:
        return _write({})
    fmt = hook_format()
    cursor = {"additional_context": message}
    claude = {"hookSpecificOutput": {"hookEventName": event, "additionalContext": message}}
    if fmt == "claude":
        return _write(claude)
    if fmt == "cursor":
        return _write(cursor)
    return _write({**cursor, **claude})

# Copilot puts tool arguments in `toolArgs`; Cursor and Claude use `tool_input`.
NEST_KEYS = ("tool_input", "input", "updated_input", "toolArgs", "tool_args", "file")


def _nested(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Candidate argument objects, accepting a JSON-string `toolArgs`.

    Copilot's docs type `toolArgs` as an object in the hooks reference and as a
    JSON string in the CLI tutorial, so both are handled.
    """
    found = []
    for key in NEST_KEYS:
        value = payload.get(key)
        if isinstance(value, str) and value.lstrip()[:1] == "{":
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                continue
        if isinstance(value, dict):
            found.append(value)
    return found


def tool_path(payload: dict[str, Any]) -> str:
    for key in ("path", "file_path", "filePath"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val.replace(chr(92), "/")
    for inner in _nested(payload):
        found = tool_path(inner)
        if found:
            return found
    return ""

def tool_mcp_name(payload: dict[str, Any]) -> str:
    """Best-effort MCP tool name from Cursor/Claude hook payloads."""
    for key in ("tool_name", "toolName", "tool", "name", "mcp_tool", "mcpTool"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    nested = payload.get("tool_input") or payload.get("input") or payload.get("mcp") or {}
    if isinstance(nested, dict):
        found = tool_mcp_name(nested)
        if found:
            return found
    return ""


def tool_mcp_server(payload: dict[str, Any]) -> str:
    for key in ("server", "server_name", "serverName", "namespace", "mcp_server"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    nested = payload.get("mcp") if isinstance(payload.get("mcp"), dict) else {}
    if nested:
        return tool_mcp_server(nested)
    return ""


def tool_command(payload: dict[str, Any]) -> str:
    for key in ("command", "cmd", "shell"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val
    for inner in _nested(payload):
        found = tool_command(inner)
        if found:
            return found
    return ""


def tool_contents(payload: dict[str, Any]) -> str:
    for key in ("contents", "new_string", "newString", "content", "file_text", "new_str"):
        val = payload.get(key)
        if isinstance(val, str):
            return val
    for inner in _nested(payload):
        found = tool_contents(inner)
        if found:
            return found
    return ""

ARTIFACT_ROOT = Path(__file__).resolve().parents[2] / "features"
SLUG_TOKEN = re.compile(r"FEATURE_SLUG:\s*([a-z0-9][a-z0-9-]*(?:/[a-z0-9][a-z0-9-]*)?)", re.I)
DECLARED_DEPS_LINE = re.compile(r"(?mi)^\*\*new_dependencies:\*\*\s*(.+)$")


def normalize_package(name: str) -> str:
    """Lowercase and fold `_` to `-` so npm and PyPI spellings compare equal."""
    return name.strip().strip("\"'`").lower().replace("_", "-")


def feature_slug(payload: dict[str, Any] | None = None) -> str:
    """`FEATURE_SLUG` env first; a spawn payload may also carry the token in its prompt."""
    env = os.environ.get("FEATURE_SLUG", "").strip()
    if env:
        return env
    if payload:
        match = SLUG_TOKEN.search(prompt_text(payload))
        if match:
            return match.group(1)
    return ""


def feature_base(slug: str, cfg: dict[str, Any] | None = None, repo: Path | None = None) -> Path:
    """Absolute feature slug directory (local features/ or linked memory root)."""
    repo = (repo or Path(__file__).resolve().parents[2]).resolve()
    cfg = cfg if cfg is not None else load_config()
    safe = (slug or "").strip().strip("/\\")
    if not safe:
        return artifact_zone_roots(cfg, repo)[0] if artifact_zone_roots(cfg, repo) else repo / "features"
    # Prefer memory-aware zones; fall back to local features/{slug}
    for zone in artifact_zone_roots(cfg, repo):
        candidate = zone / safe
        if candidate.is_dir():
            return candidate
    name = artifact_dir_name(cfg)
    mem = memory_root_from_config(cfg, repo)
    if mem is not None:
        layout = mem_cfg_layout(cfg)
        pid = mem_cfg_project_id(cfg)
        if layout == "namespaced" and pid:
            return (mem / "projects" / pid / name / safe).resolve()
        return (mem / name / safe).resolve()
    return (repo / name / safe).resolve()


def _deps_from_state(path: Path) -> set[str]:
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return set()
    context = data.get("context") if isinstance(data, dict) else None
    rows = context.get("new_dependencies") if isinstance(context, dict) else None
    if not isinstance(rows, list):
        return set()
    found = set()
    for row in rows:
        name = row.get("name") if isinstance(row, dict) else row
        if isinstance(name, str) and name.strip():
            found.add(normalize_package(name))
    return found


def _deps_from_handoff(path: Path) -> set[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return set()
    found = set()
    for match in DECLARED_DEPS_LINE.finditer(text):
        for part in match.group(1).split(","):
            if part.strip():
                found.add(normalize_package(part))
    return found


def declared_dependencies(slug: str) -> set[str]:
    """Packages the Architect declared for this slug, plus any `ALLOW_DEPENDENCY` override.

    Union of the state JSON and the HANDOFF line, so a half-filled artifact still
    unblocks. Unfilled template placeholders and `none` are dropped. Never raises.
    """
    names = {
        normalize_package(v)
        for v in (os.environ.get("ALLOW_DEPENDENCY") or "").split(",")
        if v.strip()
    }
    seen = []
    if slug:
        seen.append(slug)
        parent = slug.split("/", 1)[0]
        if parent and parent != slug:
            seen.append(parent)
    cfg = load_config()
    repo = Path(__file__).resolve().parents[2]
    for candidate in seen:
        base = feature_base(candidate, cfg, repo)
        # Also check local features/ during memory transition
        local = repo / artifact_dir_name(cfg) / candidate
        for root in (base, local):
            names |= _deps_from_state(root / "state" / "architect-agent.json")
            names |= _deps_from_handoff(root / "HANDOFF-architect.md")
    return {n for n in names if n and n != "none" and "{" not in n}
