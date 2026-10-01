"""Resolve feature artifact roots (local ``features/`` or external memory bank).

When ``memory.enabled`` is true and ``memory.root`` is set, feature artifacts
live under the linked memory repository instead of the product tree. Run state
under ``.pipeline/state/`` always stays in the product project.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_pipeline_config(project: Path) -> dict[str, Any]:
    """Load ``.pipeline/config.json`` for *project* (empty dict if missing)."""
    path = Path(project).expanduser().resolve() / ".pipeline" / "config.json"
    try:
        if not path.is_file():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def memory_section(cfg: dict[str, Any] | None) -> dict[str, Any]:
    raw = (cfg or {}).get("memory")
    return raw if isinstance(raw, dict) else {}


def product_section(cfg: dict[str, Any] | None) -> dict[str, Any]:
    raw = (cfg or {}).get("product")
    return raw if isinstance(raw, dict) else {}


def artifact_dir_name(cfg: dict[str, Any] | None = None) -> str:
    """Relative folder name under the artifact root (default ``features``)."""
    product = product_section(cfg)
    value = product.get("artifact_dir")
    if not isinstance(value, str) or not value.strip():
        return "features"
    return value.strip().strip("/\\").replace("\\", "/") or "features"


def memory_enabled(cfg: dict[str, Any] | None = None) -> bool:
    mem = memory_section(cfg)
    if mem.get("enabled") is not True:
        return False
    root = mem.get("root")
    return isinstance(root, str) and bool(root.strip())


def memory_project_id(cfg: dict[str, Any] | None = None) -> str | None:
    mem = memory_section(cfg)
    pid = mem.get("project_id")
    if pid is None:
        return None
    text = str(pid).strip()
    return text or None


def memory_layout(cfg: dict[str, Any] | None = None) -> str:
    mem = memory_section(cfg)
    layout = mem.get("layout")
    if isinstance(layout, str) and layout.strip().lower() in {"flat", "namespaced"}:
        return layout.strip().lower()
    return "namespaced" if memory_project_id(cfg) else "flat"


def resolve_memory_root(project: Path, cfg: dict[str, Any] | None = None) -> Path | None:
    """Absolute path to the linked memory repository, or None when disabled."""
    if cfg is None:
        cfg = load_pipeline_config(project)
    if not memory_enabled(cfg):
        return None
    raw = str(memory_section(cfg).get("root") or "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = Path(project).expanduser().resolve() / path
    return path.resolve()


def artifact_root(project: Path, cfg: dict[str, Any] | None = None) -> Path:
    """Directory that contains ``{artifact_dir}/{slug}/`` trees.

    With memory disabled this is the product *project*. With memory enabled it
    is the memory repo root (optionally under ``projects/{project_id}/``).
    """
    project = Path(project).expanduser().resolve()
    if cfg is None:
        cfg = load_pipeline_config(project)
    mem_root = resolve_memory_root(project, cfg)
    if mem_root is None:
        return project
    layout = memory_layout(cfg)
    pid = memory_project_id(cfg)
    if layout == "namespaced" and pid:
        return (mem_root / "projects" / pid).resolve()
    return mem_root


def feature_dir(project: Path, slug: str, cfg: dict[str, Any] | None = None) -> Path:
    """Absolute path for one feature slug's artifacts."""
    project = Path(project).expanduser().resolve()
    if cfg is None:
        cfg = load_pipeline_config(project)
    safe = (slug or "").strip().strip("/\\")
    if not safe or ".." in safe.split("/") or ".." in safe.split("\\"):
        raise ValueError(f"invalid slug: {slug!r}")
    root = artifact_root(project, cfg)
    return (root / artifact_dir_name(cfg) / safe).resolve()


def feature_rel(project: Path, slug: str, cfg: dict[str, Any] | None = None) -> str:
    """Path string for prompts: project-relative when local, absolute when external."""
    project = Path(project).expanduser().resolve()
    if cfg is None:
        cfg = load_pipeline_config(project)
    dest = feature_dir(project, slug, cfg)
    if memory_enabled(cfg):
        return str(dest)
    try:
        return dest.relative_to(project).as_posix()
    except ValueError:
        return str(dest)


def is_under_artifact_root(path: Path | str, project: Path, cfg: dict[str, Any] | None = None) -> bool:
    """True when *path* is under the configured artifact zone for this project."""
    project = Path(project).expanduser().resolve()
    if cfg is None:
        cfg = load_pipeline_config(project)
    target = Path(path)
    if not target.is_absolute():
        target = (project / target).resolve()
    else:
        target = target.resolve()
    root = artifact_root(project, cfg)
    name = artifact_dir_name(cfg)
    zone = (root / name).resolve()
    try:
        target.relative_to(zone)
        return True
    except ValueError:
        return False


def index_db_path(project: Path, cfg: dict[str, Any] | None = None) -> Path:
    """SQLite index path inside the memory root (or project when memory off)."""
    project = Path(project).expanduser().resolve()
    if cfg is None:
        cfg = load_pipeline_config(project)
    mem = memory_section(cfg)
    rel = mem.get("index", {})
    rel_path = ".memory/index.sqlite"
    if isinstance(rel, dict):
        candidate = rel.get("path")
        if isinstance(candidate, str) and candidate.strip():
            rel_path = candidate.strip()
    base = resolve_memory_root(project, cfg) or project
    path = Path(rel_path).expanduser()
    if not path.is_absolute():
        path = base / path
    return path.resolve()
