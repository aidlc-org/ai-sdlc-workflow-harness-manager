"""Pure, print-free read model for one pipeline-kit project.

Every function here either reads a documented pack-state JSON file directly
(``install.json``, ``config.json``, ``.pipeline/state/runs/*.json``,
``features/{slug}/pipeline-state.json``) or calls an existing capability
function that already returns structured data (``graphify_status``,
``archify_status``, ``overlay_status``, the ``*_doctor_checks`` triplet,
``score_ledger``). Nothing here prints, and nothing here imports or
executes code that lives *inside* a target project (no
``pipeline_extensions/*.py``, no copied ``.pipeline/loader/*.py``) — those
vary per project and per version, so nothing project-local is ever put on
``sys.path`` or exec'd. Two tiers, by cost:

* ``fleet_row`` — cheap, file-stat only. Safe to call for every registered
  project on every fleet poll.
* ``project_snapshot(..., deep=True)`` — also calls the doctor-check triplet
  and ``graphify_status`` (both may shell out). Only call this for the one
  project the admin has open.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _pack_dir(project: Path) -> Path:
    return project / ".pipeline"


def _current_kit_version() -> str | None:
    """The kit version *this portal process* ships with — read once, pure,
    no side effects (``install.py:version()`` just reads the ``VERSION`` file)."""
    try:
        from pipeline_kit.install import version

        return version()
    except Exception:  # noqa: BLE001 - never block a snapshot over this
        return None


def _version_behind(installed: str | None, current: str | None) -> bool | None:
    if not installed or not current:
        return None
    try:
        from pipeline_kit.install import parse_semver

        return parse_semver(installed) < parse_semver(current)
    except Exception:  # noqa: BLE001 - fall back to a plain string compare
        return installed != current


def install_info(project: Path) -> dict[str, Any]:
    pack = _pack_dir(project)
    marker = _read_json(pack / "install.json")
    if marker is None:
        return {"installed": False, "pack_dir": str(pack)}
    installed_version = marker.get("version")
    current_version = _current_kit_version()
    return {
        "installed": True,
        "pack_dir": str(pack),
        "scope": marker.get("scope"),
        "mode": marker.get("mode") or "kit",
        "version": installed_version,
        "current_kit_version": current_version,
        "behind": _version_behind(installed_version, current_version),
        "file_count": len(marker.get("files") or []),
    }


def doctor_checks(project: Path) -> dict[str, Any]:
    """Recomposes install.py ``doctor()``'s check set without importing it.

    Each capability's doctor hook is optional on this host; a missing one
    is reported as an info line, never a crash — one unlicensed or
    partially-installed capability must not take down the whole panel.
    """
    pack = _pack_dir(project)
    checks: dict[str, bool] = {
        "install marker": (pack / "install.json").is_file(),
        "configuration": (pack / "config.json").is_file(),
    }
    info: list[str] = []
    for label, loader in (
        ("graphify", lambda: __import__("knowledge.doctor", fromlist=["graphify_doctor_checks"]).graphify_doctor_checks(project)),
        ("archify", lambda: __import__("pipeline_plugins.archify", fromlist=["archify_doctor_checks"]).archify_doctor_checks(project)),
        ("obs", lambda: __import__("pipeline_observability.commands", fromlist=["obs_doctor_checks"]).obs_doctor_checks(pack)),
    ):
        try:
            extra_info, extra_checks = loader()
        except Exception as exc:  # noqa: BLE001 - one capability's absence must not blank the panel
            info.append(f"{label} doctor unavailable: {exc}")
            continue
        info.extend(extra_info)
        checks.update(extra_checks)
    passed = sum(1 for value in checks.values() if value)
    return {"checks": checks, "info": info, "passed": passed, "total": len(checks), "ok": passed == len(checks)}


def features_snapshot(project: Path) -> dict[str, Any]:
    try:
        from pipeline_features.commands import snapshot as feature_snapshot
    except ImportError:
        return {"available": False, "flags": {}}
    try:
        data = feature_snapshot(project)
    except Exception as exc:  # noqa: BLE001 - e.g. missing config.json
        return {"available": False, "error": str(exc), "flags": {}}
    return {
        "available": True,
        "flags": {name: {"state": state, "config_key": detail} for name, (state, detail) in data.items()},
    }


def plugins_snapshot(project: Path, *, deep: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {}
    try:
        from pipeline_plugins.graphify import graph_freshness

        out["graphify"] = {"freshness": graph_freshness(project)}
        if deep:
            from pipeline_plugins.graphify import graphify_status

            out["graphify"].update(graphify_status())
    except Exception as exc:  # noqa: BLE001 - plugin absence is a normal, displayed state
        out["graphify"] = {"state": "unknown", "error": str(exc)}
    try:
        from pipeline_plugins.archify import architecture_diagrams_enabled

        out["archify"] = {"enabled": architecture_diagrams_enabled(project)}
        if deep:
            from pipeline_plugins.archify import archify_status

            out["archify"].update(archify_status(project))
    except Exception as exc:  # noqa: BLE001
        out["archify"] = {"state": "unknown", "error": str(exc)}
    try:
        from knowledge.overlay import overlay_status

        out["knowledge_overlay"] = overlay_status(project)
    except Exception as exc:  # noqa: BLE001
        out["knowledge_overlay"] = {"error": str(exc)}
    return out


def observability_snapshot(project: Path) -> dict[str, Any]:
    pack = _pack_dir(project)
    ledger = pack / "state" / "obs" / "events.jsonl"
    cfg: dict[str, Any] = {}
    offset = 0
    try:
        from pipeline_observability.export import load_obs_config, read_offset

        cfg = load_obs_config(project)
        offset = read_offset(project)
    except Exception:  # noqa: BLE001 - obs package optional
        pass
    size = ledger.stat().st_size if ledger.is_file() else 0
    return {
        "enabled": cfg.get("enabled") is True,
        "adapter": cfg.get("adapter") or "langfuse",
        "ledger_bytes": size,
        "flushed_bytes": offset,
        "unflushed_bytes": max(0, size - offset),
    }


def extensions_snapshot(project: Path, cfg: dict[str, Any], *, mode: str) -> dict[str, Any]:
    """Lists workflows. Orchestrator associate workflows are *declared*, never loaded —
    importing ``pipeline_extensions/*.py`` would execute the target project's own code."""
    if mode == "orchestrator":
        first_party: list[str] = []
        try:
            from pipeline_orchestrator.graph import BUILTIN

            first_party = sorted(BUILTIN)
        except Exception:  # noqa: BLE001
            pass
        associate: list[str] = []
        ext_dir = project / "pipeline_extensions"
        if ext_dir.is_dir():
            associate = sorted(p.stem for p in ext_dir.glob("*.py") if not p.name.startswith("_"))
        return {
            "mode": "orchestrator",
            "first_party": first_party,
            "associate_declared": associate,
            "note": "associate workflows are declared from disk, not imported, by the portal",
        }
    pack = _pack_dir(project)
    workflows_dir = pack / "workflows"
    rows: list[dict[str, Any]] = []
    if workflows_dir.is_dir():
        for path in sorted(workflows_dir.glob("*.json")):
            data = _read_json(path) or {}
            name = data.get("name") or path.stem
            wf_cfg = (cfg.get("workflows") or {}).get(name) or {}
            rows.append(
                {
                    "name": name,
                    "configured": bool(wf_cfg),
                    "classes": sorted((wf_cfg.get("classes") or {}).keys()) or None,
                    "chain_length": len(wf_cfg.get("chain") or []) or None,
                }
            )
    return {"mode": "kit", "workflows": rows}


def _artifact_root(project: Path, cfg: dict[str, Any]) -> Path:
    try:
        from pipeline_kit.paths import artifact_dir_name, artifact_root

        return artifact_root(project, cfg) / artifact_dir_name(cfg)
    except Exception:  # noqa: BLE001 - fall back to the plain default
        return project / "features"


def runs_snapshot(project: Path) -> list[dict[str, Any]]:
    """Orchestrator-mode run state — read directly, no dependency on the
    (heavier) ``pipeline_orchestrator`` package for a flat, documented JSON file."""
    runs_dir = _pack_dir(project) / "state" / "runs"
    out: list[dict[str, Any]] = []
    if not runs_dir.is_dir():
        return out
    for path in sorted(runs_dir.glob("*.json")):
        run = _read_json(path)
        if not run:
            continue
        gates = run.get("gates") or {}
        out.append(
            {
                "slug": run.get("slug") or path.stem,
                "workflow": run.get("workflow"),
                "status": run.get("status"),
                "current_node": run.get("current_node"),
                "change_class": run.get("change_class"),
                "updated_at": run.get("updated_at"),
                "pending_gates": sorted(gate for gate, info in gates.items() if (info or {}).get("status") != "approved"),
                "retries": run.get("retries") or {},
            }
        )
    return out


def boards_snapshot(project: Path, cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """Kit-mode progress — the parent-maintained board at ``features/{slug}/pipeline-state.json``."""
    root = _artifact_root(project, cfg)
    out: list[dict[str, Any]] = []
    if not root.is_dir():
        return out
    for slug_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        board = _read_json(slug_dir / "pipeline-state.json")
        if not board:
            continue
        out.append(
            {
                "slug": board.get("slug") or slug_dir.name,
                "workflow": board.get("workflow"),
                "change_class": board.get("change_class"),
                "current_step": board.get("current_step"),
                "current_status": board.get("current_status"),
                "updated_at": board.get("updated_at"),
            }
        )
    return out


def fleet_row(project: Path) -> dict[str, Any]:
    """Cheap tier: file stats only, used for every project on every fleet poll."""
    project = Path(project).expanduser()
    if not project.is_dir():
        return {"path": str(project), "reachable": False, "installed": False}
    info = install_info(project)
    if not info["installed"]:
        return {"path": str(project), "reachable": True, **info}
    cfg = _read_json(project / ".pipeline" / "config.json") or {}
    mode = info.get("mode") or "kit"
    return {
        "path": str(project),
        "reachable": True,
        **info,
        "features": features_snapshot(project),
        "observability": observability_snapshot(project),
        "runs": runs_snapshot(project),
        "boards": boards_snapshot(project, cfg),
    }


def safe_fleet_row(project: Path) -> dict[str, Any]:
    """Never raises — one bad repo must not fail the whole fleet response."""
    try:
        return fleet_row(project)
    except Exception as exc:  # noqa: BLE001
        return {"path": str(project), "reachable": False, "installed": False, "error": str(exc)}


def project_snapshot(project: Path, *, deep: bool = True) -> dict[str, Any]:
    """Full drill-down for one project: setup tabs plus runs/boards.

    ``deep=True`` (the default here) additionally calls the doctor-check
    triplet and ``graphify_status``/``archify_status``, both of which may
    shell out — call this only for the single project the admin has open,
    never in a fleet-wide loop (use ``safe_fleet_row`` there instead).
    """
    project = Path(project).expanduser().resolve()
    row = fleet_row(project)
    if not row.get("installed"):
        return row
    cfg_path = project / ".pipeline" / "config.json"
    cfg = _read_json(cfg_path) or {}
    mode = row.get("mode") or "kit"
    row["plugins"] = plugins_snapshot(project, deep=deep)
    row["extensions"] = extensions_snapshot(project, cfg, mode=mode)
    row["config"] = cfg
    # Round-tripped by the UI on every write so the server can reject a
    # toggle against config.json that changed since this snapshot was read
    # (see server.py:_config_conflict) — guards a concurrent CLI edit.
    row["config_mtime"] = cfg_path.stat().st_mtime if cfg_path.is_file() else None
    if deep:
        row["doctor"] = doctor_checks(project)
    return row


def health_snapshot(project: Path) -> dict[str, Any]:
    """Per-step quality scores from the observability ledger. Only call this
    for a single project's Health tab — ``score_ledger`` reads the whole
    ledger and is too expensive to run on every fleet poll."""
    project = Path(project).expanduser().resolve()
    ledger = _pack_dir(project) / "state" / "obs" / "events.jsonl"
    if not ledger.is_file():
        return {"available": False, "reason": "no ledger yet"}
    try:
        from pipeline_observability.scoring import score_ledger
    except ImportError:
        return {"available": False, "reason": "pipeline_observability not installed"}
    try:
        report = score_ledger(project, ledger)
    except Exception as exc:  # noqa: BLE001 - a malformed ledger must not 500 the Health tab
        return {"available": False, "reason": str(exc)}
    steps = [{key: value for key, value in step.items() if key != "events"} for step in report.get("steps") or []]
    return {"available": True, "event_count": report.get("event_count"), "steps": steps}
