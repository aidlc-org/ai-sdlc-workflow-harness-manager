"""CLI handlers for pipeline-kit docs …"""

from __future__ import annotations

import sys
from pathlib import Path

from pipeline_docs.config import DocsConfigError, config_path, enabled_modules, load_modules
from pipeline_docs.const import CONFIG_REL, DEFAULT_WORKERS, MODULES_TEMPLATE
from pipeline_docs.extract import extract_modules
from pipeline_docs.index_agents import link_agents, write_index
from pipeline_docs.layout_wiki import (
    ensure_wiki_skeleton,
    module_graph_path,
    system_graph_path,
    wiki_root,
)
from pipeline_plugins.graphify import GraphifyError, merge_graphs, graphify_status


def cmd_init_modules(project: Path) -> int:
    cfg = config_path(project)
    cfg.parent.mkdir(parents=True, exist_ok=True)
    if not cfg.is_file():
        cfg.write_text(MODULES_TEMPLATE, encoding="utf-8")
        print(f"wrote {CONFIG_REL}")
    else:
        print(f"exists {CONFIG_REL}")
    actions = ensure_wiki_skeleton(project)
    for action in actions:
        print(action)
    print(f"wiki: {wiki_root(project).relative_to(project)}")
    print("Next: edit modules in docs-modules.yaml, then pipeline-kit docs extract-modules")
    return 0


def cmd_extract_modules(
    project: Path,
    *,
    workers: int = DEFAULT_WORKERS,
    module: str | None = None,
    force: bool = False,
    config: Path | None = None,
) -> int:
    try:
        manifest = extract_modules(
            project,
            workers=workers,
            module_id=module,
            force=force,
            config=config,
        )
    except DocsConfigError as exc:
        print(str(exc), file=sys.stderr)
        if exc.recovery:
            print(exc.recovery, file=sys.stderr)
        return 64
    except GraphifyError as exc:
        print(str(exc), file=sys.stderr)
        if getattr(exc, "recovery", ""):
            print(exc.recovery, file=sys.stderr)
        return 1
    print(f"run: {manifest.get('run_id')}")
    print(f"ok: {manifest.get('ok')}  failed: {manifest.get('failed')}")
    for row in manifest.get("modules") or []:
        status = row.get("status")
        mid = row.get("id")
        if status == "ok":
            print(f"  {mid}: ok → {row.get('graph')}")
        else:
            print(f"  {mid}: FAILED — {row.get('error')}", file=sys.stderr)
    try:
        write_index(project, config=config)
        print("updated wiki/codebase/INDEX.md")
    except DocsConfigError:
        pass
    return 1 if manifest.get("failed") else 0


def cmd_merge_modules(project: Path, *, config: Path | None = None) -> int:
    try:
        modules = enabled_modules(project, config=config)
    except DocsConfigError as exc:
        print(str(exc), file=sys.stderr)
        if exc.recovery:
            print(exc.recovery, file=sys.stderr)
        return 64
    inputs = []
    for mod in modules:
        path = module_graph_path(project, mod.id)
        if path.is_file():
            inputs.append(path)
    if len(inputs) < 2:
        print(
            "merge needs at least two module graphs. Run docs extract-modules first.",
            file=sys.stderr,
        )
        return 1
    out = system_graph_path(project)
    try:
        path = merge_graphs(project, inputs, out=out)
    except GraphifyError as exc:
        print(str(exc), file=sys.stderr)
        print(exc.recovery, file=sys.stderr)
        return 1
    print(f"merged {len(inputs)} graphs → {path.relative_to(project)}")
    return 0


def cmd_status(project: Path, *, config: Path | None = None) -> int:
    cli = graphify_status()
    print(f"graphify: {cli['state']}")
    if cli.get("version"):
        print(f"version: {cli['version']}")
    cfg = config or config_path(project)
    print(f"{CONFIG_REL}: {'present' if cfg.is_file() else 'absent'}")
    print(f"wiki/codebase: {'present' if wiki_root(project).is_dir() else 'absent'}")
    try:
        modules = load_modules(project, config=config)
    except DocsConfigError as exc:
        print(str(exc))
        if exc.recovery:
            print(exc.recovery)
        return 0 if not cfg.is_file() else 64
    enabled = [m for m in modules if m.enabled]
    print(f"modules: {len(modules)} ({len(enabled)} enabled)")
    for mod in modules:
        flag = "on" if mod.enabled else "off"
        graph = "graph" if module_graph_path(project, mod.id).is_file() else "no-graph"
        print(f"  [{flag}] {mod.id}  {mod.rel_path}  {graph}")
    sys_g = system_graph_path(project)
    print(f"system graph: {'present' if sys_g.is_file() else 'absent'}")
    return 0


def cmd_link_index(project: Path, *, config: Path | None = None) -> int:
    try:
        path = write_index(project, config=config)
    except DocsConfigError as exc:
        print(str(exc), file=sys.stderr)
        if exc.recovery:
            print(exc.recovery, file=sys.stderr)
        return 64
    print(f"wrote {path.relative_to(project)}")
    return 0


def cmd_link_agents(
    project: Path,
    *,
    dry_run: bool = False,
    config: Path | None = None,
) -> int:
    try:
        section, wrote = link_agents(project, dry_run=dry_run, config=config)
    except DocsConfigError as exc:
        print(str(exc), file=sys.stderr)
        if exc.recovery:
            print(exc.recovery, file=sys.stderr)
        return 64
    if dry_run:
        print(section)
        return 0
    print("updated AGENTS.md" if wrote else "AGENTS.md unchanged")
    return 0
