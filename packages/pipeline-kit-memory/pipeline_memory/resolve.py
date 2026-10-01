"""Thin wrappers around pipeline_kit.paths (or a local fallback)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _try_import_paths():
    try:
        from pipeline_kit import paths as p  # type: ignore

        return p
    except ImportError:
        pass
    # Source checkout: repo root on sys.path via install.py
    try:
        import paths as p  # type: ignore

        return p
    except ImportError:
        return None


_P = _try_import_paths()


def load_config(project: Path) -> dict[str, Any]:
    if _P is not None:
        return _P.load_pipeline_config(project)
    path = Path(project).resolve() / ".pipeline" / "config.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_config(project: Path, cfg: dict[str, Any]) -> None:
    path = Path(project).resolve() / ".pipeline" / "config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")


def _memory_section(cfg: dict[str, Any] | None) -> dict[str, Any]:
    raw = (cfg or {}).get("memory") if isinstance(cfg, dict) else {}
    return raw if isinstance(raw, dict) else {}


def _product_section(cfg: dict[str, Any] | None) -> dict[str, Any]:
    raw = (cfg or {}).get("product") if isinstance(cfg, dict) else {}
    return raw if isinstance(raw, dict) else {}


def artifact_dir_name(cfg: dict[str, Any] | None = None) -> str:
    if _P is not None:
        return _P.artifact_dir_name(cfg)
    product = _product_section(cfg)
    value = product.get("artifact_dir")
    if not isinstance(value, str) or not value.strip():
        return "features"
    return value.strip().strip("/\\").replace("\\", "/") or "features"


def memory_enabled(cfg: dict[str, Any] | None) -> bool:
    if _P is not None:
        return _P.memory_enabled(cfg)
    mem = _memory_section(cfg)
    return mem.get("enabled") is True and bool(str(mem.get("root") or "").strip())


def memory_project_id(cfg: dict[str, Any] | None = None) -> str | None:
    if _P is not None and hasattr(_P, "memory_project_id"):
        return _P.memory_project_id(cfg)
    mem = _memory_section(cfg)
    pid = mem.get("project_id")
    if pid is None:
        return None
    text = str(pid).strip()
    return text or None


def memory_layout(cfg: dict[str, Any] | None = None) -> str:
    if _P is not None and hasattr(_P, "memory_layout"):
        return _P.memory_layout(cfg)
    mem = _memory_section(cfg)
    layout = mem.get("layout")
    if isinstance(layout, str) and layout.strip().lower() in {"flat", "namespaced"}:
        return layout.strip().lower()
    return "namespaced" if memory_project_id(cfg) else "flat"


def resolve_memory_root(project: Path, cfg: dict[str, Any] | None = None) -> Path | None:
    if _P is not None:
        return _P.resolve_memory_root(project, cfg)
    project = Path(project).expanduser().resolve()
    if cfg is None:
        cfg = load_config(project)
    if not memory_enabled(cfg):
        return None
    raw = str(_memory_section(cfg).get("root") or "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = project / path
    return path.resolve()


def artifact_root(project: Path, cfg: dict[str, Any] | None = None) -> Path:
    if _P is not None:
        return _P.artifact_root(project, cfg)
    project = Path(project).expanduser().resolve()
    if cfg is None:
        cfg = load_config(project)
    mem_root = resolve_memory_root(project, cfg)
    if mem_root is None:
        return project
    layout = memory_layout(cfg)
    pid = memory_project_id(cfg)
    if layout == "namespaced" and pid:
        return (mem_root / "projects" / pid).resolve()
    return mem_root


def feature_dir(project: Path, slug: str, cfg: dict[str, Any] | None = None) -> Path:
    if _P is not None:
        return _P.feature_dir(project, slug, cfg)
    project = Path(project).expanduser().resolve()
    if cfg is None:
        cfg = load_config(project)
    safe = (slug or "").strip().strip("/\\")
    if not safe or ".." in safe.split("/") or ".." in safe.split("\\"):
        raise ValueError(f"invalid slug: {slug!r}")
    return (artifact_root(project, cfg) / artifact_dir_name(cfg) / safe).resolve()


def feature_rel(project: Path, slug: str, cfg: dict[str, Any] | None = None) -> str:
    if _P is not None and hasattr(_P, "feature_rel"):
        return _P.feature_rel(project, slug, cfg)
    project = Path(project).expanduser().resolve()
    if cfg is None:
        cfg = load_config(project)
    dest = feature_dir(project, slug, cfg)
    if memory_enabled(cfg):
        return str(dest)
    try:
        return dest.relative_to(project).as_posix()
    except ValueError:
        return str(dest)


def index_db_path(project: Path, cfg: dict[str, Any] | None = None) -> Path:
    if _P is not None:
        return _P.index_db_path(project, cfg)
    project = Path(project).expanduser().resolve()
    if cfg is None:
        cfg = load_config(project)
    mem = _memory_section(cfg)
    rel_path = ".memory/index.sqlite"
    index_cfg = mem.get("index")
    if isinstance(index_cfg, dict):
        candidate = index_cfg.get("path")
        if isinstance(candidate, str) and candidate.strip():
            rel_path = candidate.strip()
    base = resolve_memory_root(project, cfg) or project
    path = Path(rel_path).expanduser()
    if not path.is_absolute():
        path = base / path
    return path.resolve()
