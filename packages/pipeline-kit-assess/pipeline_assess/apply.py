"""Apply catalog ids and AGENTS.md. Rule, skill, and agent drafts stay under proposed/ until copied."""

from __future__ import annotations

import json
from pathlib import Path

from pipeline_assess.agents_md import apply_agents


class ApplyError(RuntimeError):
    pass


def _load(dest: Path) -> dict:
    path = dest / "assessment.json"
    if not path.is_file():
        raise ApplyError("assessment.json is missing. Run pipeline-kit scan first.")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ApplyError("assessment.json is not an object.")
    return data


def _catalog_row(payload: dict, ident: str) -> dict | None:
    for row in payload.get("catalog") or []:
        if row.get("id") == ident and row.get("status") == "recommended":
            return row
    return None


def _enable_flag(project: Path, name: str, *, dry_run: bool) -> str:
    from pipeline_features.commands import cmd_enable

    if dry_run:
        return f"would run: pipeline-kit features enable {name}\nreverse: pipeline-kit features disable {name}"
    code = cmd_enable(project, name)
    if code != 0:
        raise ApplyError(f"features enable {name} exited {code}")
    return f"enabled {name}. Reverse: pipeline-kit features disable {name}"


def _verify_stub(project: Path, *, dry_run: bool) -> str:
    path = project / ".pipeline" / "config.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    verify = data.setdefault("verify", {})
    rules = verify.setdefault("rules", [])
    stub = {
        "match": "/",
        "message": "Review this change against the assessment.",
        "expect": "",
    }
    if dry_run:
        return "would append a verify.rules stub with an empty expect"
    if stub not in rules:
        rules.append(stub)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return "appended verify.rules stub. Reverse: remove the stub from .pipeline/config.json"


def apply_ids(project: Path, dest: Path, ids: list[str], *, dry_run: bool) -> list[str]:
    payload = _load(dest)
    notes = []
    for ident in ids:
        if ident == "agents-md":
            proposal = dest / "proposed" / "AGENTS.md"
            merged = apply_agents(project, proposal, dry_run=dry_run)
            if dry_run:
                notes.append("dry-run agents-md:\n" + merged)
            else:
                notes.append("wrote AGENTS.md")
            continue
        row = _catalog_row(payload, ident)
        if row is None:
            raise ApplyError(
                f"{ident} is not a recommended catalog id in assessment.json"
            )
        if row.get("license_area"):
            notes.append(f"{ident} needs license {row['license_area']}. Not activated.")
            continue
        if ident in {
            "test-design",
            "playwright",
            "agent-observability",
            "jira-intake",
            "github-intake",
            "archify",
        }:
            flag = "archify" if ident == "archify" else ident
            if ident == "archify":
                if dry_run:
                    notes.append("would run: pipeline-kit plugins install archify")
                else:
                    from pipeline_plugins.commands import cmd_install

                    cmd_install(project, "archify", ide="none")
                    notes.append(
                        "archify flag enabled. Reverse: pipeline-kit plugins uninstall archify"
                    )
            else:
                notes.append(_enable_flag(project, flag, dry_run=dry_run))
            continue
        if ident == "verify-rules":
            notes.append(_verify_stub(project, dry_run=dry_run))
            continue
        notes.append(f"{ident}: {row.get('enable')}")
    return notes
