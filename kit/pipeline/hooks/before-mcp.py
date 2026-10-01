#!/usr/bin/env python3
"""beforeMCPExecution: allow MCP reads; deny remote mutations unless opted in."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import portal_owns_gate, emit_permission, load_payload, tool_mcp_name, tool_mcp_server

ALLOW_EXACT = {
    "mcp_auth",
    "atlassianuserinfo",
    "search",
    "fetch",
    # pipeline-memory MCP tools (read-only)
    "memory_search",
    "memory_get",
    "memory_list_slugs",
    "memory_list_files",
    "memory_why",
}

# CamelCase (getJiraIssue) and snake (list_pull_requests) both count as reads.
READ_PREFIX = re.compile(r"^(get|search|list|lookup|fetch|read)(_|[A-Z]|$)", re.I)

MUTATE = re.compile(
    r"(^|_)(create|edit|update|delete|transition|merge|fork|push)(_|$)|"
    r"^create|^edit|^update|^delete|^transition|^merge|"
    r"push_files|issue_write|sub_issue_write|pull_request_review_write|"
    r"addcomment|addworklog|addteamwork|createissuelink|"
    r"request_copilot_review|run_secret_scanning",
    re.I,
)


def main() -> int:
    extra = {"claude_event": "PreToolUse"}
    if portal_owns_gate() or os.environ.get("PIPELINE_ALLOW_ALL") == "1":
        return emit_permission(True, "allow", extra)

    payload = load_payload()
    name = tool_mcp_name(payload)
    server = tool_mcp_server(payload)
    key = name.strip().lower().replace("-", "_")
    label = f"{server}/{name}" if server else (name or "unknown MCP tool")

    if os.environ.get("PIPELINE_ALLOW_MCP") == "1":
        return emit_permission(True, f"MCP allowed via PIPELINE_ALLOW_MCP=1 ({label})", extra)

    if not key:
        return emit_permission(
            False,
            "Blocked MCP call with no tool name. Set PIPELINE_ALLOW_MCP=1 only if you asked for a remote write.",
            extra,
        )

    if MUTATE.search(key):
        return emit_permission(
            False,
            f"Blocked mutating MCP tool ({label}). "
            "Reads and search stay allowed. Set PIPELINE_ALLOW_MCP=1 only when the user asked to create/update remote data.",
            extra,
        )

    if key in ALLOW_EXACT or READ_PREFIX.match(key):
        return emit_permission(True, f"MCP read allowed ({label})", extra)

    return emit_permission(
        False,
        f"Blocked unknown MCP tool ({label}). "
        "Treat as a write until it is classified. Set PIPELINE_ALLOW_MCP=1 if the user asked for this call.",
        extra,
    )


if __name__ == "__main__":
    raise SystemExit(main())
