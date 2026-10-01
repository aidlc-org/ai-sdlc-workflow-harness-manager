"""Fail-closed checks after a step and the `pipeline-kit verify` report."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pipeline_orchestrator.graph import BUILTIN
from pipeline_orchestrator.state import agent_state_path, feature_dir, load_json


CRITIC_FAIL = {"changes-required", "changes_required"}
OK_STATUSES = {"success", "assumptions_used", "approve", "approve-with-nits", "approved"}


def _display_path(path: Path, project: Path) -> str:
    try:
        return str(path.relative_to(Path(project).resolve()))
    except ValueError:
        return str(path)


def parse_status_from_text(text: str) -> str:
    for raw in text.splitlines():
        line = raw.strip()
        lower = line.lower()
        if lower.startswith("**status:**"):
            return line.split(":", 1)[1].strip().strip("*").strip()
        if lower.startswith("**verdict:**"):
            return line.split(":", 1)[1].strip().strip("*").strip()
    return ""


def step_advanced(*, project: Path, slug: str, agent: str, started_at: str) -> dict[str, Any]:
    path = agent_state_path(project, slug, agent)
    data = load_json(path)
    if data is None:
        raise ValueError(f"missing agent state: {_display_path(path, project)}")
    updated = str(data.get("updated_at") or "")
    if started_at and updated and updated < started_at:
        raise ValueError(f"agent state did not advance: {_display_path(path, project)}")
    status = str(data.get("status") or "")
    if not status:
        base = feature_dir(project, slug)
        handoff = base / "HANDOFF.md"
        alt = base / f"HANDOFF-{agent}.md"
        for candidate in (handoff, alt):
            if candidate.is_file():
                status = parse_status_from_text(candidate.read_text(encoding="utf-8"))
                if status:
                    break
    if not status:
        raise ValueError(f"agent state {path.name} has no status")
    return {"status": status, "state": data, "path": path}


def is_critic_reject(status: str) -> bool:
    return status.strip().lower() in CRITIC_FAIL


def is_ok(status: str) -> bool:
    return status.strip().lower() in OK_STATUSES or status.strip().upper() in {
        "SUCCESS",
        "ASSUMPTIONS_USED",
    }


def read_install_mode(project: Path) -> str:
    marker = project / ".pipeline" / "install.json"
    if not marker.is_file():
        return "kit"
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "kit"
    if isinstance(data, dict):
        return str(data.get("mode") or "kit")
    return "kit"


def config_chain_disagrees(project: Path) -> list[str]:
    warnings: list[str] = []
    cfg_path = project / ".pipeline" / "config.json"
    if not cfg_path.is_file():
        return warnings
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ["config.json is not valid JSON"]
    workflows = cfg.get("workflows") if isinstance(cfg, dict) else None
    if not isinstance(workflows, dict):
        return warnings
    for name, spec in BUILTIN.items():
        block = workflows.get(name)
        if not isinstance(block, dict):
            continue
        if spec.classes:
            classes = block.get("classes")
            if not isinstance(classes, dict):
                continue
            for cls, nodes in spec.classes.items():
                expected = [n.id for n in nodes]
                got = classes.get(cls)
                if isinstance(got, list) and got != expected:
                    warnings.append(
                        f"config.json workflows.{name}.classes.{cls} differs from the sealed graph "
                        f"(orchestrator ignores config chains)"
                    )
    return warnings


def cmd_verify(project: Path) -> int:
    from install import version

    mode = read_install_mode(project)
    print(f"mode: {mode}")
    print(f"kit_version: {version()}")
    marker = project / ".pipeline" / "install.json"
    if marker.is_file():
        data = json.loads(marker.read_text(encoding="utf-8"))
        print(f"scope: {data.get('scope')}")
    if mode == "orchestrator":
        key = bool(os.environ.get("CURSOR_API_KEY", "").strip())
        print(f"CURSOR_API_KEY: {'set' if key else 'missing'}")
        print("first_party_workflows:")
        for name in BUILTIN:
            print(f"  - {name} (pipeline-kit)")
        warns = config_chain_disagrees(project)
        for line in warns:
            print(f"warning: {line}")
        print("orchestrator briefs are loaded from the wheel; disk markdown is not executed.")
        return 4 if warns else 0
    print("kit mode: orchestration still lives in the copied pack.")
    return 0
