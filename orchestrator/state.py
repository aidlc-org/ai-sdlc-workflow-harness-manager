"""Run cursor plus the features/{slug}/pipeline-state.json contract (local or memory root)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipeline_orchestrator.graph import Node, WorkflowSpec

try:
    from pipeline_kit.paths import feature_dir as _feature_dir
    from pipeline_kit.paths import feature_rel as _feature_rel
    from pipeline_kit.paths import load_pipeline_config
except ImportError:  # pragma: no cover — source without package layout
    from paths import feature_dir as _feature_dir  # type: ignore
    from paths import feature_rel as _feature_rel  # type: ignore
    from paths import load_pipeline_config  # type: ignore


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run_path(project: Path, slug: str) -> Path:
    return project / ".pipeline" / "state" / "runs" / f"{slug}.json"


def feature_dir(project: Path, slug: str) -> Path:
    return _feature_dir(project, slug)


def _state_path_str(project: Path, slug: str, agent: str) -> str:
    path = agent_state_path(project, slug, agent)
    try:
        return path.relative_to(Path(project).resolve()).as_posix()
    except ValueError:
        return str(path)


def pipeline_state_path(project: Path, slug: str) -> Path:
    return feature_dir(project, slug) / "pipeline-state.json"


def agent_state_path(project: Path, slug: str, agent: str) -> Path:
    return feature_dir(project, slug) / "state" / f"{agent}.json"


def signoff_path(project: Path, slug: str, gate: str) -> Path:
    return feature_dir(project, slug) / f"signoff-{gate}.md"


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def node_id(node: Node) -> str:
    return node.id


def request_path(project: Path, slug: str) -> Path:
    return feature_dir(project, slug) / "request.md"


def new_run(
    *,
    project: Path,
    spec: WorkflowSpec,
    slug: str,
    change_class: str,
    runner: str,
    kit_version: str,
    chain: list[Node],
    user_request: str = "",
) -> dict[str, Any]:
    now = utc_now()
    request_text = (user_request or "").strip()
    if request_text:
        dest = request_path(project, slug)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(request_text + "\n", encoding="utf-8")
    steps = {
        node_id(node): {
            "status": "pending",
            "handoff_status": "",
            "attempts": 0,
            "agent_id": None,
            "run_id": None,
            "model": getattr(node, "model", None),
            "context_digest": None,
            "state_path": _state_path_str(project, slug, node.id)
            if node.__class__.__name__ == "AgentStep" or node.__class__.__name__ == "LayerFan"
            else None,
            "finished_at": None,
        }
        for node in chain
    }
    gates = {
        node.id: {"status": "pending", "approved_at": None, "note": None}
        for node in chain
        if node.__class__.__name__ == "SignoffGate"
    }
    run = {
        "version": 1,
        "slug": slug,
        "workflow": spec.name,
        "workflow_provider": spec.provider,
        "kit_version": kit_version,
        "change_class": change_class,
        "runner": runner,
        "status": "running",
        "current_node": node_id(chain[0]) if chain else None,
        "exit_hint": 0,
        "started_at": now,
        "updated_at": now,
        "retry_cap": 2,
        "steps": steps,
        "gates": gates,
        "retries": {},
        "node_ids": [node_id(n) for n in chain],
        "user_request": request_text,
        "artifact_dir": _feature_rel(project, slug),
    }
    board = {
        "version": 1,
        "slug": slug,
        "workflow": spec.name,
        "change_class": change_class,
        "updated_at": now,
        "current_step": run["current_node"] or "done",
        "current_status": "not_started" if chain else "completed",
        "artifact_dir": run["artifact_dir"],
        "steps": {
            key: {
                "status": "pending",
                "handoff_status": "",
                "state_path": _state_path_str(project, slug, key),
                "updated_at": "",
            }
            for key in steps
        },
        "waves": {},
    }
    write_json(run_path(project, slug), run)
    write_json(pipeline_state_path(project, slug), board)
    return run


def save_run(project: Path, run: dict[str, Any]) -> None:
    run["updated_at"] = utc_now()
    write_json(run_path(project, run["slug"]), run)
    board = load_json(pipeline_state_path(project, run["slug"])) or {}
    board.update(
        {
            "version": 1,
            "slug": run["slug"],
            "workflow": run["workflow"],
            "change_class": run["change_class"],
            "updated_at": run["updated_at"],
            "current_step": run["current_node"] or "done",
            "current_status": run["status"],
            "artifact_dir": run.get("artifact_dir") or _feature_rel(project, run["slug"]),
        }
    )
    steps = board.setdefault("steps", {})
    for key, row in run.get("steps", {}).items():
        dest = steps.setdefault(key, {})
        dest["status"] = row.get("status") or dest.get("status") or "pending"
        dest["handoff_status"] = row.get("handoff_status") or ""
        dest["state_path"] = row.get("state_path") or _state_path_str(project, run["slug"], key)
        dest["updated_at"] = row.get("finished_at") or dest.get("updated_at") or ""
    write_json(pipeline_state_path(project, run["slug"]), board)


def load_run(project: Path, slug: str) -> dict[str, Any]:
    data = load_json(run_path(project, slug))
    if data is None:
        raise FileNotFoundError(f"no orchestrator run at {run_path(project, slug)}")
    return data
