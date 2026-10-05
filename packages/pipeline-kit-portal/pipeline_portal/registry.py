"""The fleet registry: ``{home}/.pipeline/portal/projects.json``.

One row per project the admin wants the portal to show. The registry lives
in the **user** pack location (``~/.pipeline`` by default, override with
``--home`` the same way ``pipeline-kit setup``/``memory``/``obs`` do) so one
portal instance can cover several checkouts. It is not a second source of
truth for any project's own config — only a list of paths plus a display
label and a team grouping.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REGISTRY_REL = Path("portal") / "projects.json"


class RegistryError(ValueError):
    """A registry row is malformed or the path is invalid."""


def registry_path(home: Path) -> Path:
    return Path(home).expanduser().resolve() / ".pipeline" / REGISTRY_REL


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalize_path(path: Path | str) -> str:
    return Path(path).expanduser().resolve().as_posix()


def load_registry(home: Path) -> list[dict[str, Any]]:
    path = registry_path(home)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    rows = data.get("projects") if isinstance(data, dict) else None
    return [row for row in rows if isinstance(row, dict) and row.get("path")] if isinstance(rows, list) else []


def save_registry(home: Path, rows: list[dict[str, Any]]) -> None:
    path = registry_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "projects": rows}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def add_project(
    home: Path,
    path: Path | str,
    *,
    team: str = "",
    label: str = "",
) -> dict[str, Any]:
    normalized = _normalize_path(path)
    rows = load_registry(home)
    for row in rows:
        if row.get("path") == normalized:
            row["team"] = team.strip() or row.get("team", "")
            row["label"] = label.strip() or row.get("label", "")
            row["updated_at"] = _utc_now()
            save_registry(home, rows)
            return row
    row = {
        "path": normalized,
        "team": team.strip(),
        "label": label.strip() or Path(normalized).name,
        "added_at": _utc_now(),
        "updated_at": _utc_now(),
    }
    rows.append(row)
    save_registry(home, rows)
    return row


def remove_project(home: Path, path: Path | str) -> bool:
    normalized = _normalize_path(path)
    rows = load_registry(home)
    kept = [row for row in rows if row.get("path") != normalized]
    if len(kept) == len(rows):
        return False
    save_registry(home, kept)
    return True


def list_projects(home: Path) -> list[dict[str, Any]]:
    return load_registry(home)


def ensure_seeded(home: Path, path: Path | str) -> dict[str, Any]:
    """Auto-register *path* (bare ``pipeline-kit portal serve`` with no prior registry)."""
    normalized = _normalize_path(path)
    for row in load_registry(home):
        if row.get("path") == normalized:
            return row
    return add_project(home, path)
