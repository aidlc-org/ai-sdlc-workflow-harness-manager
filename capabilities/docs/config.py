"""Load and validate .pipeline/docs-modules.yaml."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pipeline_docs.const import CONFIG_REL

_ID = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")


class DocsConfigError(RuntimeError):
    def __init__(self, message: str, *, recovery: str = "") -> None:
        super().__init__(message)
        self.recovery = recovery


@dataclass
class ModuleSpec:
    id: str
    name: str
    path: str
    tech: list[str] = field(default_factory=list)
    enabled: bool = True

    @property
    def rel_path(self) -> str:
        return self.path.replace("\\", "/").strip().strip("/")


def config_path(project: Path) -> Path:
    return project / CONFIG_REL


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    """Minimal YAML subset for docs-modules (no PyYAML dependency)."""
    try:
        import json

        stripped = text.strip()
        if stripped.startswith("{"):
            data = json.loads(stripped)
            if isinstance(data, dict):
                return data
    except (json.JSONDecodeError, TypeError):
        pass

    modules: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    in_modules = False
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if line.strip() == "modules:":
            in_modules = True
            continue
        if line.strip() == "modules: []":
            in_modules = True
            continue
        if not in_modules:
            continue
        if line.lstrip().startswith("- "):
            if current:
                modules.append(current)
            current = {}
            rest = line.lstrip()[2:].strip()
            if rest and ":" in rest:
                key, _, val = rest.partition(":")
                current[key.strip()] = _scalar(val.strip())
            continue
        if current is None:
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            current[key] = _scalar(val)
    if current:
        modules.append(current)
    return {"modules": modules}


def _scalar(raw: str) -> Any:
    if not raw:
        return ""
    if raw in ("[]",):
        return []
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if not inner:
            return []
        return [part.strip().strip("'\"") for part in inner.split(",") if part.strip()]
    if raw.lower() in ("true", "yes"):
        return True
    if raw.lower() in ("false", "no"):
        return False
    if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
        return raw[1:-1]
    return raw


def load_modules(project: Path, *, config: Path | None = None) -> list[ModuleSpec]:
    path = config or config_path(project)
    if not path.is_file():
        raise DocsConfigError(
            f"missing module inventory: {CONFIG_REL}",
            recovery="pipeline-kit docs init-modules",
        )
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DocsConfigError(f"could not read {path}: {exc}") from exc
    data = _parse_simple_yaml(text)
    raw_list = data.get("modules")
    if raw_list is None:
        raise DocsConfigError("docs-modules.yaml needs a top-level modules: list")
    if not isinstance(raw_list, list):
        raise DocsConfigError("modules must be a list")
    out: list[ModuleSpec] = []
    seen: set[str] = set()
    root = project.resolve()
    for item in raw_list:
        if not isinstance(item, dict):
            raise DocsConfigError("each module must be a mapping")
        mid = str(item.get("id") or "").strip()
        name = str(item.get("name") or mid).strip()
        mpath = str(item.get("path") or "").strip()
        if not mid or not _ID.match(mid):
            raise DocsConfigError(
                f"invalid module id {mid!r} (use lowercase letter, then [a-z0-9_-])"
            )
        if mid in seen:
            raise DocsConfigError(f"duplicate module id: {mid}")
        seen.add(mid)
        if not mpath:
            raise DocsConfigError(f"module {mid}: path is required")
        rel = mpath.replace("\\", "/").strip().strip("/")
        target = (project / rel).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise DocsConfigError(f"module {mid}: path escapes project root") from exc
        if not target.exists():
            raise DocsConfigError(
                f"module {mid}: path does not exist: {rel}",
                recovery="Fix path in docs-modules.yaml",
            )
        tech = item.get("tech") or []
        if isinstance(tech, str):
            tech = [tech]
        if not isinstance(tech, list):
            raise DocsConfigError(f"module {mid}: tech must be a list")
        enabled = item.get("enabled", True)
        if not isinstance(enabled, bool):
            enabled = str(enabled).lower() in ("true", "yes", "1")
        out.append(
            ModuleSpec(
                id=mid,
                name=name,
                path=rel,
                tech=[str(t) for t in tech],
                enabled=bool(enabled),
            )
        )
    return out


def enabled_modules(project: Path, *, config: Path | None = None) -> list[ModuleSpec]:
    return [m for m in load_modules(project, config=config) if m.enabled]
