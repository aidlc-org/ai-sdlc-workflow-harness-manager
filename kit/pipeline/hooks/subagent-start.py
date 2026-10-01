#!/usr/bin/env python3
"""subagentStart: require the previous pipeline artifact before the next specialist."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import portal_owns_gate, emit_permission, load_config, load_payload, prompt_text, subagent_type

ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_config()
DEFAULT_WORKFLOW = "feature-development"
CRITIC_OK = re.compile(r"CRITIC_VERDICT:\s*(approve|approve-with-nits)\b", re.I)
STATUS_OK = re.compile(r"\*\*status:\*\*\s*SUCCESS|\bSTATUS:\s*SUCCESS\b", re.I)
STATUS_READY = re.compile(
    r"\*\*status:\*\*\s*(SUCCESS|ASSUMPTIONS_USED)|\bSTATUS:\s*(SUCCESS|ASSUMPTIONS_USED)\b",
    re.I,
)
SIGNOFF_OK = re.compile(r"FEATURE_SIGNOFF:\s*passed\b", re.I)
PLANNING_OK = re.compile(r"(?m)^\*\*SIGNOFF:\*\*\s*approved\b|^SIGNOFF:\s*approved\b", re.I)
UI_JOB = re.compile(r"UI_JOB:\s*(full|consult)\b", re.I)
RESUME_AGENT = re.compile(r"RESUME_AGENT:\s*(architect-agent|ba-agent)\b", re.I)
CONSULT_UI = re.compile(r"CONSULT_UI:\s*true\b", re.I)
SLUG = re.compile(r"FEATURE_SLUG:\s*([a-z0-9][a-z0-9-]*(?:/[a-z0-9][a-z0-9-]*)?)", re.I)
FLAG = re.compile(
    r"^skip_(ba|ba_critic|telemetry|developer_critic|tester|pm|ui_designer|architect):\s*(true|false)\s*$",
    re.I | re.M,
)
CLASS = re.compile(r"\*\*change_class:\*\*\s*(micro|minor|feature)|change_class:\s*(micro|minor|feature)", re.I)
CHILDREN = re.compile(r"\*\*children:\*\*\s*(.+)", re.I)
WORKFLOW = re.compile(r"\*\*workflow:\*\*\s*([a-z0-9][a-z0-9_-]*)|^workflow:\s*([a-z0-9][a-z0-9_-]*)\s*$", re.I | re.M)
SOURCE = re.compile(r"\*\*work_source:\*\*\s*([a-z]+)|^work_source:\s*([a-z]+)\s*$", re.I | re.M)

GATES = {
    "ba-critic-agent": ("HANDOFF.md", "ready", "Blocked ba-critic-agent: BA HANDOFF is not ready"),
    "developer-agent": ("HANDOFF-telemetry.md", "status", "Blocked developer-agent: telemetry HANDOFF is not SUCCESS"),
    "developer-critic-agent": ("HANDOFF-developer.md", "status", "Blocked developer-critic: developer HANDOFF is not SUCCESS"),
    "retro-agent": ("HANDOFF-devops.md", "status", "Blocked retro-agent: devops HANDOFF is not SUCCESS"),
}


def _slug(payload: dict) -> str:
    env = os.environ.get("FEATURE_SLUG", "").strip()
    if env:
        return env
    match = SLUG.search(prompt_text(payload))
    return match.group(1) if match else ""


def _parent(slug: str) -> str:
    return slug.split("/", 1)[0] if slug else ""


def _workflow_config(workflow: str) -> dict:
    workflows = CONFIG.get("workflows")
    if not isinstance(workflows, dict):
        return {}
    entry = workflows.get(workflow)
    return entry if isinstance(entry, dict) else {}


def _plan_source(workflow: str) -> str:
    value = _workflow_config(workflow).get("plan_source")
    return value if isinstance(value, str) and value.strip() else "plan.md"


def _is_bug_workflow(workflow: str) -> bool:
    """A workflow is a bug workflow when its configured chain uses the analyst."""
    chain = _workflow_config(workflow).get("chain")
    return isinstance(chain, list) and "bug-analyst-agent" in chain


def _consult_cap() -> int:
    gates = CONFIG.get("gates")
    if isinstance(gates, dict):
        raw = gates.get("consult_cap")
        if isinstance(raw, int) and raw >= 0:
            return raw
    return 1


def _route(slug: str) -> dict[str, str]:
    parent = _parent(slug)
    path = ROOT / "features" / parent / "route.md" if parent else Path()
    if not path.is_file():
        return {"change_class": "feature", "workflow": DEFAULT_WORKFLOW, "work_source": "text"}
    text = path.read_text(encoding="utf-8", errors="replace")
    flags = {"change_class": "feature", "workflow": DEFAULT_WORKFLOW, "work_source": "text"}
    found = CLASS.search(text)
    if found:
        flags["change_class"] = (found.group(1) or found.group(2) or "feature").lower()
    workflow = WORKFLOW.search(text)
    if workflow:
        flags["workflow"] = (workflow.group(1) or workflow.group(2)).lower()
    source = SOURCE.search(text)
    if source:
        flags["work_source"] = (source.group(1) or source.group(2)).lower()
    # Config skips are defaults; an explicit route.md line always wins.
    configured = _workflow_config(flags["workflow"]).get("skips")
    if isinstance(configured, dict):
        for key, value in configured.items():
            if key.startswith("skip_"):
                flags[key] = "true" if value else "false"
    for match in FLAG.finditer(text):
        flags[f"skip_{match.group(1).lower()}"] = match.group(2).lower()
    return flags


def _ok(path: Path, mode: str | None) -> bool:
    if not path.is_file():
        return False
    if mode is None:
        return True
    text = path.read_text(encoding="utf-8", errors="replace")
    if mode == "critic":
        return bool(CRITIC_OK.search(text))
    if mode == "status":
        return bool(STATUS_OK.search(text))
    if mode == "ready":
        return bool(STATUS_READY.search(text))
    if mode == "signoff":
        return bool(SIGNOFF_OK.search(text))
    if mode == "planning":
        return bool(PLANNING_OK.search(text))
    return True


def _feat(slug: str, name: str) -> Path:
    return ROOT / "features" / slug / name


def _children(parent: str) -> list[str]:
    path = _feat(parent, "spec-order.md")
    if not path.is_file():
        return []
    match = CHILDREN.search(path.read_text(encoding="utf-8", errors="replace"))
    if not match:
        return []
    return [part.strip().strip("`") for part in match.group(1).split(",") if part.strip()]


def _all_child_critics(parent: str) -> tuple[bool, str]:
    kids = _children(parent)
    if kids:
        missing = []
        for child in kids:
            path = _feat(f"{parent}/{child}", "HANDOFF-developer-critic.md")
            if not _ok(path, "critic"):
                missing.append(str(path))
        if missing:
            return False, f"Blocked tester-agent: child critic not approved ({', '.join(missing)})"
        return True, "tester-agent may run; all child developer-critics approved"
    flat = _feat(parent, "HANDOFF-developer-critic.md")
    if _ok(flat, "critic"):
        return True, "tester-agent may run; found HANDOFF-developer-critic.md"
    return False, f"Blocked tester-agent: developer critic has not approved ({flat})"


def main() -> int:
    if portal_owns_gate():
        return emit_permission(True, "external portal owns this session")
    payload = load_payload()
    kind = subagent_type(payload).lower().replace("_", "-")
    slug = _slug(payload)
    if kind in {
        "intake-agent",
        "product-manager-agent",
        "ui-designer-agent",
        "ba-agent",
        "ba-critic-agent",
        "bug-analyst-agent",
        "telemetry-agent",
        "developer-agent",
        "developer-critic-agent",
        "tester-agent",
        "devops-agent",
        "retro-agent",
    } and not slug:
        return emit_permission(
            True,
            f"{kind} started without FEATURE_SLUG; parent must pass slug so artifact gates can run.",
        )

    route = _route(slug) if slug else {"change_class": "feature", "workflow": DEFAULT_WORKFLOW}
    skip = {k: v == "true" for k, v in route.items() if k.startswith("skip_")}
    parent = _parent(slug)
    change = route.get("change_class", "feature")
    workflow = route.get("workflow", DEFAULT_WORKFLOW)

    if kind == "intake-agent":
        # First step of a tracker workflow: route.md is written after intake classifies the issue.
        return emit_permission(True, "intake-agent may run; it is the first step of a tracker workflow")

    if kind == "product-manager-agent":
        if skip.get("skip_pm") or change != "feature":
            return emit_permission(False, "Blocked product-manager-agent: skip_pm or change_class is not feature")
        route_path = _feat(parent, "route.md")
        if not route_path.is_file():
            return emit_permission(False, f"Blocked product-manager-agent: missing {route_path}")
        return emit_permission(True, "product-manager-agent may run; found route.md")

    if kind == "ui-designer-agent":
        if change != "feature":
            return emit_permission(
                False, "Blocked ui-designer-agent: skip_ui_designer or change_class is not feature"
            )
        text = prompt_text(payload)
        job_match = UI_JOB.search(text)
        consult = bool(job_match and job_match.group(1).lower() == "consult")
        consult_ui = bool(CONSULT_UI.search(text))
        if skip.get("skip_ui_designer") and not (consult and consult_ui):
            return emit_permission(
                False, "Blocked ui-designer-agent: skip_ui_designer or change_class is not feature"
            )
        if consult:
            if not RESUME_AGENT.search(text):
                return emit_permission(
                    False,
                    "Blocked ui-designer-agent consult: RESUME_AGENT must be architect-agent or ba-agent",
                )
            ui_dir = _feat(parent, "ui")
            n = len(list(ui_dir.glob("consult-*.md"))) if ui_dir.is_dir() else 0
            cap = _consult_cap()
            if n >= cap and not consult_ui:
                return emit_permission(
                    False,
                    f"Blocked ui-designer-agent consult: consult_cap={cap} reached. Set CONSULT_UI: true to override.",
                )
        pm = _feat(parent, "HANDOFF-pm.md")
        prd = _feat(parent, "prd.md")
        if not _ok(pm, "ready"):
            return emit_permission(False, f"Blocked ui-designer-agent: PM HANDOFF is not ready ({pm}).")
        if not prd.is_file():
            return emit_permission(False, f"Blocked ui-designer-agent: missing {prd}")
        return emit_permission(True, "ui-designer-agent may run; found HANDOFF-pm.md")

    if kind == "architect-agent":
        if skip.get("skip_architect"):
            return emit_permission(False, "Blocked architect-agent: route.md skip_architect=true")
        if (
            workflow == DEFAULT_WORKFLOW
            and change == "feature"
            and not skip.get("skip_ui_designer")
        ):
            ui = _feat(parent, "HANDOFF-ui.md")
            if not _ok(ui, "ready"):
                return emit_permission(
                    False, f"Blocked architect-agent: UI designer HANDOFF is not ready ({ui})."
                )
        return emit_permission(True, "architect-agent may run")

    if kind == "ba-agent":
        if skip.get("skip_ba"):
            return emit_permission(False, "Blocked ba-agent: route.md skip_ba=true")
        if skip.get("skip_pm"):
            source = _feat(parent, _plan_source(workflow))
            if not source.is_file():
                return emit_permission(
                    False,
                    f"Blocked ba-agent: skip_pm requires the plan source for workflow {workflow} ({source}).",
                )
            return emit_permission(True, f"ba-agent may run; found {source.name}")
        pm = _feat(parent, "HANDOFF-pm.md")
        if not _ok(pm, "ready"):
            return emit_permission(False, f"Blocked ba-agent: PM HANDOFF is not ready ({pm}).")
        return emit_permission(True, "ba-agent may run; found HANDOFF-pm.md")

    if kind == "bug-analyst-agent":
        intake = _feat(parent, "intake.md")
        if intake.is_file():
            return emit_permission(True, "bug-analyst-agent may run; found intake.md")
        if route.get("work_source") == "text" and _feat(parent, "route.md").is_file():
            return emit_permission(True, "bug-analyst-agent may run; text-sourced report in route.md")
        return emit_permission(False, f"Blocked bug-analyst-agent: missing intake ({intake}).")

    if kind == "ba-critic-agent":
        kids = _children(parent)
        if kids:
            missing = [c for c in kids if not _feat(f"{parent}/{c}", "specification.md").is_file()]
            if missing:
                return emit_permission(
                    False,
                    f"Blocked ba-critic-agent: missing child specification.md ({', '.join(missing)})",
                )
        elif not _feat(parent, "specification.md").is_file():
            return emit_permission(False, f"Blocked ba-critic-agent: missing specification.md ({_feat(parent, 'specification.md')})")
        handoff = _feat(parent, "HANDOFF.md")
        if not _ok(handoff, "ready"):
            return emit_permission(False, f"Blocked ba-critic-agent: BA HANDOFF is not ready ({handoff}).")
        return emit_permission(True, "ba-critic-agent may run; found BA HANDOFF")

    if kind == "telemetry-agent":
        if skip.get("skip_telemetry"):
            return emit_permission(False, "Blocked telemetry-agent: route.md skip_telemetry=true")
        critic = _feat(parent, "HANDOFF-ba-critic.md")
        if not _ok(critic, "critic"):
            return emit_permission(False, f"Blocked telemetry-agent: BA critic has not approved ({critic}).")
        return emit_permission(True, "telemetry-agent may run; found HANDOFF-ba-critic.md")

    if kind == "developer-agent" and _is_bug_workflow(workflow):
        analyst = _feat(parent, "HANDOFF-bug-analyst.md")
        if not _ok(analyst, "status"):
            return emit_permission(False, f"Blocked developer-agent: bug analyst HANDOFF is not SUCCESS ({analyst}).")
        rca = _feat(parent, "rca.md")
        if not rca.is_file():
            return emit_permission(False, f"Blocked developer-agent: missing root cause analysis ({rca}).")
        return emit_permission(True, "developer-agent may run; root cause approved")

    if kind == "developer-agent" and change == "feature":
        gates = CONFIG.get("gates") if isinstance(CONFIG.get("gates"), dict) else {}
        if gates.get("require_planning_signoff_before_build", True):
            ba_sign = _feat(parent, "signoff-ba.md")
            if not _ok(ba_sign, "planning"):
                return emit_permission(
                    False,
                    f"Blocked developer-agent: require_planning_signoff_before_build needs {ba_sign}",
                )

    if kind == "developer-agent" and skip.get("skip_telemetry"):
        patch = _feat(parent, "patch.md")
        if patch.is_file() or _feat(parent, "specification.md").is_file() or _feat(slug, "specification.md").is_file():
            return emit_permission(True, "developer-agent allowed (micro/minor skip_telemetry)")
        return emit_permission(False, f"Blocked developer-agent: skip_telemetry requires {patch}")

    if kind == "tester-agent":
        if skip.get("skip_tester"):
            return emit_permission(False, "Blocked tester-agent: route.md skip_tester=true")
        if skip.get("skip_developer_critic"):
            dev = _feat(parent, "HANDOFF-developer.md")
            if not _ok(dev, "status"):
                return emit_permission(False, f"Blocked tester-agent: developer HANDOFF is not SUCCESS ({dev}).")
            return emit_permission(True, "tester-agent may run; micro skip_developer_critic + developer SUCCESS")
        ok, reason = _all_child_critics(parent)
        return emit_permission(ok, reason)

    if kind == "devops-agent" and skip.get("skip_tester"):
        if skip.get("skip_developer_critic"):
            target, mode, deny = ("HANDOFF-developer.md", "status", "Blocked devops: developer HANDOFF not SUCCESS (micro)")
        else:
            target, mode, deny = (
                "HANDOFF-developer-critic.md",
                "critic",
                "Blocked devops: developer critic has not approved (minor)",
            )
        path = _feat(parent, target)
        if not _ok(path, mode):
            return emit_permission(False, f"{deny} ({path}).")
        return emit_permission(True, f"devops-agent may run; {target}")

    if kind == "devops-agent":
        tester = _feat(parent, "HANDOFF-tester.md")
        if not _ok(tester, "status"):
            return emit_permission(False, f"Blocked devops-agent: tester HANDOFF is not SUCCESS ({tester}).")
        signoff = _feat(parent, "qa-signoff.md")
        if not _ok(signoff, "signoff"):
            return emit_permission(False, f"Blocked devops-agent: FEATURE_SIGNOFF is not passed ({signoff}).")
        return emit_permission(True, "devops-agent may run; tester SUCCESS and FEATURE_SIGNOFF passed")

    gate = GATES.get(kind)
    if not gate:
        return emit_permission(True, "allow")

    filename, mode, deny = gate
    target = _feat(slug, filename)
    if not _ok(target, mode):
        return emit_permission(False, f"{deny} ({target}).")
    return emit_permission(True, f"{kind} may run; found {target.name}")


if __name__ == "__main__":
    raise SystemExit(main())
