"""CLI commands: link, unlink, status, doctor, index, search, mcp, import-local."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from pipeline_memory.index import get_backend
from pipeline_memory.layout import scaffold_memory_repo
from pipeline_memory.resolve import (
    artifact_dir_name,
    artifact_root,
    feature_dir,
    index_db_path,
    load_config,
    memory_enabled,
    resolve_memory_root,
    save_config,
)


def _print(msg: str) -> None:
    print(msg)


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)


def cmd_link(
    project: Path,
    root: str,
    *,
    project_id: str = "",
    layout: str = "",
    init: bool = True,
    enabled: bool = True,
) -> int:
    project = Path(project).expanduser().resolve()
    pack = project / ".pipeline"
    if not pack.is_dir():
        _err("no .pipeline — run pipeline-kit init first")
        return 1

    mem_root = Path(root).expanduser()
    if not mem_root.is_absolute():
        mem_root = (project / mem_root).resolve()
    else:
        mem_root = mem_root.resolve()

    if init:
        for line in scaffold_memory_repo(mem_root, git_init=True):
            _print(f"  {line}")

    cfg = load_config(project)
    pid = project_id.strip() or None
    chosen_layout = (layout or "").strip().lower()
    if chosen_layout not in {"flat", "namespaced"}:
        chosen_layout = "namespaced" if pid else "flat"

    cfg["memory"] = {
        "enabled": bool(enabled),
        "root": str(mem_root),
        "project_id": pid,
        "layout": chosen_layout,
        "git": {"auto_commit": False},
        "index": {"engine": "fts5", "path": ".memory/index.sqlite"},
        "mcp": {"name": "pipeline-memory", "allow_writes": False},
    }
    # Keep product.artifact_dir as relative name; root is controlled by memory.
    product = cfg.get("product")
    if not isinstance(product, dict):
        product = {}
        cfg["product"] = product
    product.setdefault("artifact_dir", "features/")

    save_config(project, cfg)
    link_meta = {
        "root": str(mem_root),
        "project_id": pid,
        "layout": chosen_layout,
        "linked_from": str(project),
    }
    (pack / "memory.link.json").write_text(json.dumps(link_meta, indent=2) + "\n", encoding="utf-8")

    sample = feature_dir(project, "example-slug", cfg)
    _print(f"memory linked: {mem_root}")
    _print(f"layout: {chosen_layout}" + (f" project_id={pid}" if pid else ""))
    _print(f"example feature path: {sample}")
    _print("next: pipeline-kit memory index")
    _print("MCP:  pipeline-kit memory mcp")
    return 0


def cmd_unlink(project: Path) -> int:
    project = Path(project).expanduser().resolve()
    cfg = load_config(project)
    if "memory" not in cfg and not (project / ".pipeline" / "memory.link.json").is_file():
        _print("memory was not linked")
        return 0
    mem = cfg.get("memory")
    if isinstance(mem, dict):
        mem["enabled"] = False
        cfg["memory"] = mem
    else:
        cfg.pop("memory", None)
    save_config(project, cfg)
    link = project / ".pipeline" / "memory.link.json"
    if link.is_file():
        link.unlink()
    _print("memory unlinked (config.enabled=false); external files left intact")
    return 0


def cmd_status(project: Path) -> int:
    project = Path(project).expanduser().resolve()
    cfg = load_config(project)
    mem = cfg.get("memory") if isinstance(cfg.get("memory"), dict) else {}
    enabled = memory_enabled(cfg)
    root = resolve_memory_root(project, cfg)
    payload = {
        "enabled": enabled,
        "root": str(root) if root else None,
        "layout": mem.get("layout"),
        "project_id": mem.get("project_id"),
        "artifact_root": str(artifact_root(project, cfg)),
        "artifact_dir": artifact_dir_name(cfg),
        "index": str(index_db_path(project, cfg)),
        "index_exists": index_db_path(project, cfg).is_file(),
    }
    _print(json.dumps(payload, indent=2))
    return 0


def cmd_doctor(project: Path) -> int:
    project = Path(project).expanduser().resolve()
    cfg = load_config(project)
    checks: list[tuple[str, bool, str]] = []
    pack_ok = (project / ".pipeline").is_dir()
    checks.append(("project pack", pack_ok, str(project / ".pipeline")))
    enabled = memory_enabled(cfg)
    checks.append(("memory.enabled", enabled, "set via memory link"))
    root = resolve_memory_root(project, cfg)
    if enabled:
        checks.append(("memory root exists", bool(root and root.is_dir()), str(root)))
        if root and root.is_dir():
            writable = True
            try:
                probe = root / ".memory" / ".write-probe"
                probe.parent.mkdir(parents=True, exist_ok=True)
                probe.write_text("ok", encoding="utf-8")
                probe.unlink(missing_ok=True)
            except OSError:
                writable = False
            checks.append(("memory root writable", writable, str(root)))
            checks.append(("git repo", (root / ".git").is_dir(), str(root / ".git")))
        idx = index_db_path(project, cfg)
        checks.append(("search index", idx.is_file(), str(idx)))
        try:
            sample = feature_dir(project, "doctor-sample", cfg)
            checks.append(("feature_dir resolves", True, str(sample)))
        except ValueError as exc:
            checks.append(("feature_dir resolves", False, str(exc)))
    else:
        checks.append(("default local features/", True, str(project / "features")))

    ok = True
    for label, passed, detail in checks:
        print(f"{'ok' if passed else 'missing'}  {label}: {detail}")
        ok = ok and passed
    return 0 if ok else 1


def cmd_index(project: Path, *, rebuild: bool = True, engine: str = "") -> int:
    project = Path(project).expanduser().resolve()
    cfg = load_config(project)
    root = resolve_memory_root(project, cfg)
    if root is None:
        # Index local features/ when memory not linked
        root = project / artifact_dir_name(cfg)
        if not root.is_dir():
            _err("nothing to index: link a memory root or create features/")
            return 1
        scan_root = root
        db = project / ".pipeline" / "state" / "memory-index.sqlite"
    else:
        scan_root = root
        db = index_db_path(project, cfg)

    mem = cfg.get("memory") if isinstance(cfg.get("memory"), dict) else {}
    index_cfg = mem.get("index") if isinstance(mem.get("index"), dict) else {}
    eng = (engine or index_cfg.get("engine") or "fts5") if isinstance(index_cfg, dict) else "fts5"
    backend = get_backend(str(eng))
    pid = mem.get("project_id") if isinstance(mem, dict) else None
    pid_s = str(pid).strip() if pid else None
    n = backend.rebuild(db, scan_root, project_id=pid_s)
    _print(f"indexed {n} chunks → {db}")
    return 0


def cmd_search(
    project: Path,
    query: str,
    *,
    limit: int = 10,
    slug: str = "",
    kind: str = "",
    as_json: bool = False,
) -> int:
    project = Path(project).expanduser().resolve()
    cfg = load_config(project)
    root = resolve_memory_root(project, cfg)
    if root is None:
        db = project / ".pipeline" / "state" / "memory-index.sqlite"
    else:
        db = index_db_path(project, cfg)
    if not db.is_file():
        _err("no index — run: pipeline-kit memory index")
        return 1
    backend = get_backend("fts5")
    mem = cfg.get("memory") if isinstance(cfg.get("memory"), dict) else {}
    pid = str(mem.get("project_id") or "").strip() or None
    hits = backend.search(
        db,
        query,
        limit=limit,
        slug=slug or None,
        kind=kind or None,
        project_id=pid,
    )
    if as_json:
        _print(
            json.dumps(
                [
                    {
                        "path": h.path,
                        "slug": h.slug,
                        "kind": h.kind,
                        "title": h.title,
                        "excerpt": h.excerpt,
                        "score": h.score,
                        "project_id": h.project_id,
                    }
                    for h in hits
                ],
                indent=2,
            )
        )
        return 0
    if not hits:
        _print("no hits")
        return 0
    for h in hits:
        _print(f"[{h.score:.4f}] {h.kind} {h.slug} {h.path}")
        _print(f"  {h.title}: {h.excerpt[:160]}")
    return 0


def cmd_import_local(project: Path, *, dry_run: bool = False) -> int:
    """Copy existing project features/ into the linked memory root once."""
    import shutil

    project = Path(project).expanduser().resolve()
    cfg = load_config(project)
    root = resolve_memory_root(project, cfg)
    if root is None:
        _err("memory not linked")
        return 1
    src = project / artifact_dir_name(cfg)
    if not src.is_dir():
        _err(f"no local {src}")
        return 1
    dest_root = artifact_root(project, cfg) / artifact_dir_name(cfg)
    if dry_run:
        _print(f"would copy {src} → {dest_root}")
        return 0
    dest_root.parent.mkdir(parents=True, exist_ok=True)
    if dest_root.exists():
        # merge copy
        for item in src.iterdir():
            target = dest_root / item.name
            if item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True)
            else:
                shutil.copy2(item, target)
    else:
        shutil.copytree(src, dest_root)
    _print(f"imported {src} → {dest_root}")
    return 0


def cmd_mcp(project: Path, *, root: str = "") -> int:
    """Run the memory MCP server on stdio (blocks)."""
    from pipeline_memory.mcp_server import run_stdio

    project = Path(project).expanduser().resolve()
    return run_stdio(project, root_override=root or None)


def cmd_memory_entrypoint(args: Any = None, **kwargs: Any) -> int:
    """Entry point for ``pipeline_kit.commands`` discovery and direct invocation.

    Accepts either an argparse Namespace (from a host CLI) or keyword arguments
    matching the subcommand handlers. Prefer ``pipeline-kit memory <cmd>``.
    """
    if args is not None and hasattr(args, "memory_command"):
        cmd = str(getattr(args, "memory_command") or "")
        project = Path(getattr(args, "project", ".") or ".").expanduser().resolve()
        if cmd == "link":
            return cmd_link(
                project,
                str(getattr(args, "root", "") or ""),
                project_id=str(getattr(args, "project_id", "") or ""),
                layout=str(getattr(args, "layout", "") or ""),
                init=bool(getattr(args, "init", True)),
            )
        if cmd == "unlink":
            return cmd_unlink(project)
        if cmd == "status":
            return cmd_status(project)
        if cmd == "doctor":
            return cmd_doctor(project)
        if cmd == "index":
            return cmd_index(project, engine=str(getattr(args, "engine", "") or ""))
        if cmd == "search":
            return cmd_search(
                project,
                str(getattr(args, "query", "") or ""),
                limit=int(getattr(args, "limit", 10) or 10),
                slug=str(getattr(args, "slug", "") or ""),
                kind=str(getattr(args, "kind", "") or ""),
                as_json=bool(getattr(args, "json", False)),
            )
        if cmd == "mcp":
            return cmd_mcp(project, root=str(getattr(args, "root", "") or ""))
        if cmd == "import-local":
            return cmd_import_local(project, dry_run=bool(getattr(args, "dry_run", False)))
        _err(f"unknown memory command: {cmd}")
        return 2

    # Keyword form: cmd_memory_entrypoint(command="status", project=path)
    command = str(kwargs.pop("command", kwargs.pop("memory_command", "")) or "")
    project = Path(kwargs.pop("project", ".") or ".").expanduser().resolve()
    dispatch = {
        "link": lambda: cmd_link(project, str(kwargs.get("root", "")), **{
            k: kwargs[k] for k in ("project_id", "layout", "init", "enabled") if k in kwargs
        }),
        "unlink": lambda: cmd_unlink(project),
        "status": lambda: cmd_status(project),
        "doctor": lambda: cmd_doctor(project),
        "index": lambda: cmd_index(project, engine=str(kwargs.get("engine", "") or "")),
        "search": lambda: cmd_search(
            project,
            str(kwargs.get("query", "")),
            limit=int(kwargs.get("limit", 10) or 10),
            slug=str(kwargs.get("slug", "") or ""),
            kind=str(kwargs.get("kind", "") or ""),
            as_json=bool(kwargs.get("as_json", kwargs.get("json", False))),
        ),
        "mcp": lambda: cmd_mcp(project, root=str(kwargs.get("root", "") or "")),
        "import-local": lambda: cmd_import_local(project, dry_run=bool(kwargs.get("dry_run", False))),
    }
    handler = dispatch.get(command)
    if handler is None:
        _err(f"unknown memory command: {command or '(empty)'}")
        return 2
    return handler()
