"""Rebuild wiki/codebase/INDEX.md and AGENTS.md marked section."""

from __future__ import annotations

from pathlib import Path

from pipeline_docs.config import ModuleSpec, enabled_modules, load_modules
from pipeline_docs.const import AGENTS_END, AGENTS_START, INDEX_HEADER
from pipeline_docs.layout_wiki import (
    ensure_wiki_skeleton,
    index_path,
    module_graph_path,
    module_readme_path,
    module_security_path,
    system_dir,
    system_graph_path,
    wiki_root,
)


def _yes(path: Path) -> str:
    return "yes" if path.is_file() else "—"


def build_index_markdown(project: Path, modules: list[ModuleSpec]) -> str:
    lines = [INDEX_HEADER.rstrip(), ""]
    if not modules:
        lines.append("| _(none)_ | | | | | |")
        lines.append("")
        return "\n".join(lines) + "\n"
    for mod in modules:
        graph = _yes(module_graph_path(project, mod.id))
        docs = _yes(module_readme_path(project, mod.id))
        sec = _yes(module_security_path(project, mod.id))
        lines.append(
            f"| `{mod.id}` | {mod.name} | `{mod.rel_path}` | {graph} | {docs} | {sec} |"
        )
    lines.append("")
    sys_readme = system_dir(project) / "README.md"
    if sys_readme.is_file() or system_graph_path(project).is_file():
        lines.extend(
            [
                "## System",
                "",
                f"- System docs: `wiki/codebase/system/` "
                f"(graph: {_yes(system_graph_path(project))})",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def write_index(project: Path, *, config: Path | None = None) -> Path:
    ensure_wiki_skeleton(project)
    modules = load_modules(project, config=config)
    path = index_path(project)
    path.write_text(build_index_markdown(project, modules), encoding="utf-8")
    return path


def build_agents_section(project: Path, modules: list[ModuleSpec]) -> str:
    lines = [
        AGENTS_START,
        "",
        "## Codebase modules (pipeline-kit)",
        "",
        "Agent-facing monorepo map. Prefer `wiki/codebase/INDEX.md`.",
        "",
        "| Module | Docs | Graph |",
        "|--------|------|-------|",
    ]
    for mod in modules:
        readme = f"wiki/codebase/modules/{mod.id}/README.md"
        graph = f"wiki/codebase/modules/{mod.id}/graph/graph.json"
        lines.append(f"| `{mod.id}` | `{readme}` | `{graph}` |")
    if (system_dir(project) / "README.md").is_file():
        lines.extend(
            [
                "",
                "- System architecture: `wiki/codebase/system/README.md`",
            ]
        )
    lines.extend(["", AGENTS_END, ""])
    return "\n".join(lines)


def link_agents(
    project: Path,
    *,
    dry_run: bool = False,
    config: Path | None = None,
) -> tuple[str, bool]:
    """Rewrite marked section in AGENTS.md. Returns (text, wrote)."""
    modules = enabled_modules(project, config=config)
    section = build_agents_section(project, modules)
    agents = project / "AGENTS.md"
    if dry_run:
        return section, False
    if agents.is_file():
        text = agents.read_text(encoding="utf-8")
        if AGENTS_START in text and AGENTS_END in text:
            before, _, rest = text.partition(AGENTS_START)
            _, _, after = rest.partition(AGENTS_END)
            new = before.rstrip() + "\n\n" + section + after.lstrip("\n")
        else:
            new = text.rstrip() + "\n\n" + section
        agents.write_text(new if new.endswith("\n") else new + "\n", encoding="utf-8")
    else:
        agents.write_text(section if section.endswith("\n") else section + "\n", encoding="utf-8")
    return section, True
