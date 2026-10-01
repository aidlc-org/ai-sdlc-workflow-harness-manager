"""Stdio MCP server for pipeline memory search (JSON-RPC minimal + optional SDK).

Implements a small subset of the MCP surface so agents can call tools without
requiring the ``mcp`` package. If ``mcp`` is installed, prefer it when available.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from pipeline_memory.index import get_backend
from pipeline_memory.resolve import (
    feature_dir,
    index_db_path,
    load_config,
    resolve_memory_root,
    artifact_dir_name,
    artifact_root,
)


TOOLS = [
    {
        "name": "memory_search",
        "description": "Full-text search over pipeline feature artifacts in the memory bank.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 8},
                "slug": {"type": "string"},
                "kind": {
                    "type": "string",
                    "description": "request|decision|handoff|architecture|plan|signoff|state|test|other",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "memory_get",
        "description": "Read one artifact file by relative path under the memory root, or slug+rel.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path relative to memory root"},
                "slug": {"type": "string"},
                "rel": {"type": "string", "description": "Path relative to feature slug dir"},
            },
        },
    },
    {
        "name": "memory_list_slugs",
        "description": "List feature slugs under the configured artifact root.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "memory_list_files",
        "description": "List files under a feature slug.",
        "inputSchema": {
            "type": "object",
            "properties": {"slug": {"type": "string"}},
            "required": ["slug"],
        },
    },
    {
        "name": "memory_why",
        "description": "Find decision/request/handoff/architecture snippets that explain a change.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "slug": {"type": "string"},
                "limit": {"type": "integer", "default": 8},
            },
            "required": ["question"],
        },
    },
]


class MemoryContext:
    def __init__(self, project: Path, root_override: str | None = None):
        self.project = Path(project).expanduser().resolve()
        self.cfg = load_config(self.project)
        if root_override:
            self.mem_root = Path(root_override).expanduser().resolve()
        else:
            self.mem_root = resolve_memory_root(self.project, self.cfg)
        self.db = index_db_path(self.project, self.cfg)
        if self.mem_root is None:
            # Fall back to local features index
            self.db = self.project / ".pipeline" / "state" / "memory-index.sqlite"
            self.scan_root = self.project / artifact_dir_name(self.cfg)
        else:
            self.scan_root = self.mem_root

    def ensure_index(self) -> None:
        if self.db.is_file():
            return
        if self.scan_root and Path(self.scan_root).is_dir():
            get_backend("fts5").rebuild(self.db, Path(self.scan_root))


def _hit_dict(h: Any) -> dict[str, Any]:
    return {
        "path": h.path,
        "slug": h.slug,
        "kind": h.kind,
        "title": h.title,
        "excerpt": h.excerpt,
        "score": h.score,
        "project_id": h.project_id,
    }


def call_tool(ctx: MemoryContext, name: str, arguments: dict[str, Any]) -> Any:
    ctx.ensure_index()
    backend = get_backend("fts5")
    mem = ctx.cfg.get("memory") if isinstance(ctx.cfg.get("memory"), dict) else {}
    pid = str(mem.get("project_id") or "").strip() or None

    if name == "memory_search":
        hits = backend.search(
            ctx.db,
            str(arguments.get("query") or ""),
            limit=int(arguments.get("limit") or 8),
            slug=(str(arguments["slug"]) if arguments.get("slug") else None),
            kind=(str(arguments["kind"]) if arguments.get("kind") else None),
            project_id=pid,
        )
        return [_hit_dict(h) for h in hits]

    if name == "memory_why":
        q = str(arguments.get("question") or "")
        limit = int(arguments.get("limit") or 8)
        slug = str(arguments["slug"]) if arguments.get("slug") else None
        collected: list[dict[str, Any]] = []
        seen: set[str] = set()
        for kind in ("decision", "request", "handoff", "architecture", "plan"):
            for h in backend.search(ctx.db, q, limit=limit, slug=slug, kind=kind, project_id=pid):
                key = f"{h.path}:{h.title}"
                if key in seen:
                    continue
                seen.add(key)
                collected.append(_hit_dict(h))
        collected.sort(key=lambda row: row["score"], reverse=True)
        return collected[:limit]

    if name == "memory_get":
        path_arg = arguments.get("path")
        if path_arg:
            base = ctx.mem_root or ctx.project
            target = (Path(base) / str(path_arg)).resolve()
        elif arguments.get("slug") and arguments.get("rel"):
            target = feature_dir(ctx.project, str(arguments["slug"]), ctx.cfg) / str(arguments["rel"])
            target = target.resolve()
        else:
            return {"error": "provide path or slug+rel"}
        # Containment check
        base = (ctx.mem_root or artifact_root(ctx.project, ctx.cfg)).resolve()
        try:
            target.relative_to(base)
        except ValueError:
            try:
                target.relative_to(ctx.project)
            except ValueError:
                return {"error": "path outside memory/project root"}
        if not target.is_file():
            return {"error": f"not found: {target}"}
        text = target.read_text(encoding="utf-8", errors="replace")
        if len(text) > 100_000:
            text = text[:100_000] + "\n…[truncated]"
        return {"path": str(target), "content": text}

    if name == "memory_list_slugs":
        root = artifact_root(ctx.project, ctx.cfg) / artifact_dir_name(ctx.cfg)
        if not root.is_dir():
            return []
        return sorted(p.name for p in root.iterdir() if p.is_dir() and not p.name.startswith("."))

    if name == "memory_list_files":
        slug = str(arguments.get("slug") or "").strip()
        if not slug:
            return {"error": "slug required"}
        base = feature_dir(ctx.project, slug, ctx.cfg)
        if not base.is_dir():
            return []
        files = []
        for path in base.rglob("*"):
            if path.is_file():
                files.append(path.relative_to(base).as_posix())
        return sorted(files)

    return {"error": f"unknown tool: {name}"}


def _result_text(payload: Any) -> dict[str, Any]:
    text = payload if isinstance(payload, str) else json.dumps(payload, indent=2)
    return {"content": [{"type": "text", "text": text}]}


def run_stdio(project: Path, root_override: str | None = None) -> int:
    """Minimal MCP-over-stdio loop (initialize, tools/list, tools/call)."""
    ctx = MemoryContext(project, root_override=root_override)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(req, dict):
            continue
        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params") if isinstance(req.get("params"), dict) else {}

        def reply(result: Any = None, error: dict[str, Any] | None = None) -> None:
            if req_id is None and error is None:
                return  # notification
            msg: dict[str, Any] = {"jsonrpc": "2.0", "id": req_id}
            if error is not None:
                msg["error"] = error
            else:
                msg["result"] = result
            sys.stdout.write(json.dumps(msg) + "\n")
            sys.stdout.flush()

        if method == "initialize":
            reply(
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "pipeline-memory", "version": "1.0.0"},
                }
            )
        elif method == "notifications/initialized":
            continue
        elif method == "tools/list":
            reply({"tools": TOOLS})
        elif method == "tools/call":
            name = str(params.get("name") or "")
            arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
            try:
                payload = call_tool(ctx, name, arguments)
                reply(_result_text(payload))
            except Exception as exc:  # noqa: BLE001 — surface to client
                reply(_result_text({"error": str(exc)}))
        elif method == "ping":
            reply({})
        else:
            if req_id is not None:
                reply(error={"code": -32601, "message": f"Method not found: {method}"})
    return 0


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="pipeline-memory-mcp")
    parser.add_argument("--project", default=".")
    parser.add_argument("--root", default="")
    args = parser.parse_args(argv)
    project = Path(args.project).expanduser().resolve()
    return run_stdio(project, root_override=args.root or None)


if __name__ == "__main__":
    raise SystemExit(main())
