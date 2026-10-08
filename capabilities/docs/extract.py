"""Parallel module graph extract into wiki/codebase."""

from __future__ import annotations

import json
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from pipeline_docs.config import ModuleSpec, enabled_modules
from pipeline_docs.const import DEFAULT_WORKERS
from pipeline_docs.layout_wiki import (
    ensure_module_dirs,
    ensure_wiki_skeleton,
    module_graph_path,
    runs_dir,
)
from pipeline_plugins.graphify import GraphifyError, extract_graph_at

RunFn = Callable[..., Any]


def _utc_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def extract_one(
    project: Path,
    module: ModuleSpec,
    *,
    force: bool = False,
    runner: RunFn | None = None,
) -> dict[str, Any]:
    ensure_module_dirs(project, module)
    dest = module_graph_path(project, module.id)
    try:
        path = extract_graph_at(
            project,
            path=module.rel_path,
            force=force,
            dest=dest,
            runner=runner,
        )
        return {
            "id": module.id,
            "path": module.rel_path,
            "status": "ok",
            "graph": str(path.relative_to(project)).replace("\\", "/"),
            "error": None,
        }
    except GraphifyError as exc:
        return {
            "id": module.id,
            "path": module.rel_path,
            "status": "failed",
            "graph": None,
            "error": str(exc),
            "recovery": getattr(exc, "recovery", ""),
        }
    except Exception as exc:  # noqa: BLE001 — surface unexpected extract errors
        return {
            "id": module.id,
            "path": module.rel_path,
            "status": "failed",
            "graph": None,
            "error": f"{exc}\n{traceback.format_exc(limit=3)}",
        }


def extract_modules(
    project: Path,
    *,
    workers: int = DEFAULT_WORKERS,
    module_id: str | None = None,
    force: bool = False,
    runner: RunFn | None = None,
    config: Path | None = None,
) -> dict[str, Any]:
    ensure_wiki_skeleton(project)
    modules = enabled_modules(project, config=config)
    if module_id:
        modules = [m for m in modules if m.id == module_id]
        if not modules:
            raise GraphifyError(
                f"module not found or disabled: {module_id}",
                recovery="Check .pipeline/docs-modules.yaml",
            )
    if not modules:
        return {
            "run_id": _utc_run_id(),
            "modules": [],
            "ok": 0,
            "failed": 0,
            "message": "no enabled modules",
        }
    workers = max(1, min(workers, len(modules)))
    results: list[dict[str, Any]] = []
    run_id = _utc_run_id()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(extract_one, project, mod, force=force, runner=runner): mod
            for mod in modules
        }
        for fut in as_completed(futures):
            results.append(fut.result())
    results.sort(key=lambda row: row["id"])
    ok = sum(1 for row in results if row["status"] == "ok")
    failed = len(results) - ok
    manifest = {
        "run_id": run_id,
        "kind": "extract-modules",
        "workers": workers,
        "ok": ok,
        "failed": failed,
        "modules": results,
    }
    out_dir = runs_dir(project) / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest
