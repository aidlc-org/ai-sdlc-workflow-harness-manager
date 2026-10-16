"""Normalize host hook payloads into SecurityEvent (no secret values retained)."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from .models import SecurityEvent

NEST_KEYS = ("tool_input", "input", "updated_input", "toolArgs", "tool_args", "file", "mcp")


def detect_source(payload: dict[str, Any] | None = None) -> str:
    """Best-effort host source label for findings and decisions."""
    env = (
        os.environ.get("PIPELINE_HOOK_FORMAT")
        or os.environ.get("CHORUS_HOOK_FORMAT")
        or os.environ.get("COPILOT_CLI")
        or ""
    ).strip().lower()
    if env in {"cursor", "claude", "copilot", "copilot-cli"}:
        return "copilot-cli" if env in {"copilot", "copilot-cli"} else env
    if payload:
        if payload.get("cursor_version") or payload.get("composerId"):
            return "cursor"
        if payload.get("copilot_session_id") or payload.get("sessionId"):
            return "copilot-cli"
    return "unknown"


def normalize_hook_payload(
    payload: dict[str, Any],
    *,
    event_type: str,
    operation: str,
    source: str | None = None,
) -> SecurityEvent:
    nested = _nested(payload)
    tool_name = _first_str(payload, ("tool_name", "toolName", "tool", "name", "mcp_tool")) or ""
    if not tool_name:
        for inner in nested:
            tool_name = _first_str(inner, ("tool_name", "toolName", "name", "tool")) or tool_name
            if tool_name:
                break

    target = _first_str(payload, ("path", "file_path", "filePath", "target_file"))
    if not target:
        for inner in nested:
            target = _first_str(inner, ("path", "file_path", "filePath", "target_file"))
            if target:
                break

    command = _first_str(payload, ("command", "cmd", "shell"))
    if not command:
        for inner in nested:
            command = _first_str(inner, ("command", "cmd", "shell"))
            if command:
                break

    argument_keys = _argument_keys(payload, nested)
    content_present = _content_present(payload, nested)
    session_id = _first_str(
        payload,
        ("session_id", "sessionId", "conversation_id", "composerId", "thread_id"),
    )

    return SecurityEvent(
        source=source or detect_source(payload),
        event_type=event_type,
        operation=operation,
        tool_name=tool_name or operation,
        target=target.replace("\\", "/") if target else None,
        command=command,
        argument_keys=tuple(sorted(argument_keys)),
        content_present=content_present,
        session_id=session_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _nested(payload: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
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


def _first_str(data: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _argument_keys(payload: dict[str, Any], nested: list[dict[str, Any]]) -> set[str]:
    keys: set[str] = set()
    for source in (payload, *nested):
        for key, value in source.items():
            if key in NEST_KEYS or key in {
                "tool_name",
                "toolName",
                "permission",
                "hook_event_name",
            }:
                continue
            if isinstance(value, (str, int, float, bool, list, dict)) or value is None:
                keys.add(str(key))
    return keys


def _content_present(payload: dict[str, Any], nested: list[dict[str, Any]]) -> bool:
    content_keys = (
        "contents",
        "new_string",
        "newString",
        "content",
        "file_text",
        "new_str",
        "prompt",
        "text",
    )
    for source in (payload, *nested):
        for key in content_keys:
            value = source.get(key)
            if isinstance(value, str) and value.strip():
                return True
    return False
