"""wiki/codebase skeleton and path helpers."""

from __future__ import annotations

from pathlib import Path

from pipeline_docs.config import ModuleSpec
from pipeline_docs.const import (
    GRAPH_DIRNAME,
    GRAPH_JSON,
    INDEX_HEADER,
    MODULES_DIR,
    RUNS_DIR,
    SYSTEM_DIR,
    WIKI_README,
    WIKI_ROOT,
)


def wiki_root(project: Path) -> Path:
    return project / WIKI_ROOT


def module_dir(project: Path, module_id: str) -> Path:
    return wiki_root(project) / MODULES_DIR / module_id


def module_graph_path(project: Path, module_id: str) -> Path:
    return module_dir(project, module_id) / GRAPH_DIRNAME / GRAPH_JSON


def module_readme_path(project: Path, module_id: str) -> Path:
    return module_dir(project, module_id) / "README.md"


def module_security_path(project: Path, module_id: str) -> Path:
    return module_dir(project, module_id) / "security.md"


def system_dir(project: Path) -> Path:
    return wiki_root(project) / SYSTEM_DIR


def system_graph_path(project: Path) -> Path:
    return system_dir(project) / GRAPH_DIRNAME / GRAPH_JSON


def runs_dir(project: Path) -> Path:
    return wiki_root(project) / RUNS_DIR


def index_path(project: Path) -> Path:
    return wiki_root(project) / "INDEX.md"


def ensure_wiki_skeleton(project: Path) -> list[str]:
    """Create wiki/codebase layout. Idempotent."""
    actions: list[str] = []
    root = wiki_root(project)
    for rel in (MODULES_DIR, SYSTEM_DIR, RUNS_DIR, f"{SYSTEM_DIR}/{GRAPH_DIRNAME}"):
        path = root / rel
        if not path.is_dir():
            path.mkdir(parents=True, exist_ok=True)
            actions.append(f"mkdir {path.relative_to(project)}")
    readme = root / "README.md"
    if not readme.is_file():
        readme.write_text(WIKI_README, encoding="utf-8")
        actions.append("wrote wiki/codebase/README.md")
    idx = index_path(project)
    if not idx.is_file():
        idx.write_text(INDEX_HEADER + "| _(none yet)_ | | | | | |\n", encoding="utf-8")
        actions.append("wrote wiki/codebase/INDEX.md")
    gitignore = root / ".gitignore"
    if not gitignore.is_file():
        gitignore.write_text(
            "# Optional: ignore large graphs; regenerate with docs extract-modules\n"
            "# **/graph/graph.json\n",
            encoding="utf-8",
        )
        actions.append("wrote wiki/codebase/.gitignore")
    return actions


def ensure_module_dirs(project: Path, module: ModuleSpec) -> Path:
    dest = module_dir(project, module.id) / GRAPH_DIRNAME
    dest.mkdir(parents=True, exist_ok=True)
    return dest
