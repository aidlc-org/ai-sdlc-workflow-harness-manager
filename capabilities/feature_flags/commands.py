"""Toggle kit-owned capabilities without a second source of truth."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

from knowledge.overlay import OverlayError, enable_test_design, init_overlay
from pipeline_plugins.archify import (
    ArchifyError,
    architecture_diagrams_enabled,
    disable_architecture_diagrams,
    enable_architecture_diagrams,
)

FEATURE_IDS = (
    "test-design",
    "playwright",
    "telemetry",
    "tester",
    "archify",
    "jira-intake",
    "github-intake",
    "agent-observability",
)

TELEMETRY_WORKFLOWS = ("feature-development", "jira-story", "jira-epic", "github-story", "github-epic")
TESTER_POLICY = Path("skills/feature-development/assets/tester-policy.md")
CONFIG_REL = Path(".pipeline") / "config.json"


class FeatureError(ValueError):
    """Capability cannot be toggled."""


def cmd_list() -> int:
    rows = (
        ("test-design", "QA overlay + test-designer (knowledge init)"),
        ("playwright", "Generate specs from cases.json (needs test-design)"),
        ("telemetry", "telemetry-agent in waves (off by default)"),
        ("tester", "tester wave on micro / minor / feature"),
        ("archify", "Architect HTML diagrams (flag only; plugins install the skill)"),
        ("jira-intake", "Tracker intake from issue keys"),
        ("github-intake", "GitHub Issues/PR intake (gh CLI, API, or MCP)"),
        ("agent-observability", "Agent-run traces/scores (not telemetry-agent)"),
    )
    for ident, note in rows:
        print(f"{ident}\t{note}")
    print("Enable/disable writes .pipeline/config.json (and tester-policy.md for tester).")
    print("Chat overrides (RUN_TESTER, RUN_TELEMETRY, RUN_ARCHITECT) still win for one run.")
    return 0


def cmd_status(project: Path) -> int:
    try:
        snapshots = _snapshot(project)
    except FeatureError as exc:
        print(str(exc), file=sys.stderr)
        return 64
    width = max(len(ident) for ident in FEATURE_IDS)
    for ident in FEATURE_IDS:
        state, detail = snapshots[ident]
        print(f"{ident.ljust(width)}  {state.ljust(3)}  {detail}")
    return 0


def cmd_enable(project: Path, name: str) -> int:
    return _toggle(project, name, on=True)


def cmd_disable(project: Path, name: str) -> int:
    return _toggle(project, name, on=False)


def _toggle(project: Path, name: str, *, on: bool) -> int:
    if name not in FEATURE_IDS:
        print(f"unknown feature: {name}", file=sys.stderr)
        print("known:", ", ".join(FEATURE_IDS), file=sys.stderr)
        return 64
    handlers: dict[str, Callable[[Path, bool], None]] = {
        "test-design": _set_test_design,
        "playwright": _set_playwright,
        "telemetry": _set_telemetry,
        "tester": _set_tester,
        "archify": _set_archify,
        "jira-intake": _set_jira,
        "github-intake": _set_github,
        "agent-observability": _set_obs,
    }
    try:
        handlers[name](project, on)
    except (FeatureError, OverlayError, ArchifyError) as exc:
        print(str(exc), file=sys.stderr)
        return 64
    print(f"{name}: {'on' if on else 'off'}")
    return 0


def snapshot(project: Path) -> dict[str, tuple[str, str]]:
    """Public alias of ``_snapshot`` for callers outside this module (e.g. the enterprise portal)."""
    return _snapshot(project)


def _snapshot(project: Path) -> dict[str, tuple[str, str]]:
    cfg = _load_config(project)
    design = cfg.get("test_design") if isinstance(cfg.get("test_design"), dict) else {}
    intake = cfg.get("intake") if isinstance(cfg.get("intake"), dict) else {}
    jira = (
        intake.get("jira")
        if isinstance(intake, dict) and isinstance(intake.get("jira"), dict)
        else {}
    )
    github = (
        intake.get("github")
        if isinstance(intake, dict) and isinstance(intake.get("github"), dict)
        else {}
    )
    skips = _telemetry_off(cfg)
    tester = _tester_on(project)
    return {
        "test-design": ("on" if design.get("enabled") is True else "off", "test_design.enabled"),
        "playwright": (
            "on" if design.get("playwright") is True else "off",
            "test_design.playwright",
        ),
        "telemetry": ("off" if skips else "on", "workflows.*.skips.skip_telemetry"),
        "tester": ("on" if tester else "off", "tester-policy.md run_tester"),
        "archify": (
            "on" if architecture_diagrams_enabled(project) else "off",
            "architecture_diagrams.enabled",
        ),
        "jira-intake": (
            "on" if jira.get("enabled") is True else "off",
            "intake.jira.enabled",
        ),
        "github-intake": (
            "on" if github.get("enabled") is True else "off",
            "intake.github.enabled",
        ),
        "agent-observability": (
            "on" if _obs_on(cfg) else "off",
            "agent_observability.enabled",
        ),
    }


def _set_test_design(project: Path, on: bool) -> None:
    if on:
        init_overlay(project)
        enable_test_design(project)
        return
    data = _load_config(project)
    block = data.get("test_design")
    if not isinstance(block, dict):
        block = {}
    block["enabled"] = False
    data["test_design"] = block
    _write_config(project, data)


def _set_playwright(project: Path, on: bool) -> None:
    data = _load_config(project)
    block = data.get("test_design")
    if not isinstance(block, dict):
        block = {}
    if on and block.get("enabled") is not True:
        raise FeatureError("enable test-design first (pipeline-kit features enable test-design)")
    block["playwright"] = on
    block["design_only"] = not on
    data["test_design"] = block
    _write_config(project, data)


def _set_telemetry(project: Path, on: bool) -> None:
    data = _load_config(project)
    workflows = data.get("workflows")
    if not isinstance(workflows, dict):
        raise FeatureError("no workflows in .pipeline/config.json")
    for name in TELEMETRY_WORKFLOWS:
        entry = workflows.get(name)
        if not isinstance(entry, dict):
            continue
        skips = entry.get("skips")
        if not isinstance(skips, dict):
            skips = {}
        skips["skip_telemetry"] = not on
        entry["skips"] = skips
        workflows[name] = entry
    _write_config(project, data)


def _set_tester(project: Path, on: bool) -> None:
    path = project / ".pipeline" / TESTER_POLICY
    if not path.is_file():
        raise FeatureError(f"missing {path}")
    text = path.read_text(encoding="utf-8")
    value = "true" if on else "false"
    updated, count = re.subn(
        r"^(\| (?:micro|minor|feature) \|) (true|false)( \|)",
        rf"\1 {value}\3",
        text,
        flags=re.M,
    )
    if count < 3:
        raise FeatureError("could not update tester-policy.md run_tester column")
    path.write_text(updated, encoding="utf-8")


def _set_archify(project: Path, on: bool) -> None:
    if on:
        enable_architecture_diagrams(project)
        return
    disable_architecture_diagrams(project)


def _obs_on(cfg: dict[str, Any]) -> bool:
    block = cfg.get("agent_observability")
    return isinstance(block, dict) and block.get("enabled") is True


def _set_obs(project: Path, on: bool) -> None:
    data = _load_config(project)
    block = data.get("agent_observability")
    if not isinstance(block, dict):
        block = {
            "enabled": False,
            "adapter": "langfuse",
            "sample_rate": 1.0,
            "redact": [".env", "*secret*", "*credential*"],
            "max_field_chars": 8000,
            "flush_on": ["subagentStop", "sessionEnd"],
            "retention_days": 14,
        }
    block["enabled"] = on
    data["agent_observability"] = block
    _write_config(project, data)


def _set_jira(project: Path, on: bool) -> None:
    data = _load_config(project)
    intake = data.get("intake")
    if not isinstance(intake, dict):
        intake = {}
    jira = intake.get("jira")
    if not isinstance(jira, dict):
        jira = {}
    jira["enabled"] = on
    intake["jira"] = jira
    data["intake"] = intake
    _write_config(project, data)


def _set_github(project: Path, on: bool) -> None:
    data = _load_config(project)
    intake = data.get("intake")
    if not isinstance(intake, dict):
        intake = {}
    github = intake.get("github")
    if not isinstance(github, dict):
        github = {}
    github["enabled"] = on
    intake["github"] = github
    data["intake"] = intake
    _write_config(project, data)


def _telemetry_off(cfg: dict[str, Any]) -> bool:
    workflows = cfg.get("workflows")
    if not isinstance(workflows, dict):
        return True
    flags = []
    for name in TELEMETRY_WORKFLOWS:
        entry = workflows.get(name)
        skips = entry.get("skips") if isinstance(entry, dict) else None
        if isinstance(skips, dict):
            flags.append(skips.get("skip_telemetry") is True)
    return bool(flags) and all(flags)


def _tester_on(project: Path) -> bool:
    path = project / ".pipeline" / TESTER_POLICY
    if not path.is_file():
        return True
    text = path.read_text(encoding="utf-8")
    found = re.findall(
        r"^\| (?:micro|minor|feature) \| (true|false) \|",
        text,
        flags=re.M,
    )
    if not found:
        return True
    return all(value == "true" for value in found)


def _load_config(project: Path) -> dict[str, Any]:
    path = project / CONFIG_REL
    if not path.is_file():
        raise FeatureError("no .pipeline/config.json — run pipeline-kit init first")
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FeatureError(f"invalid config: {exc}") from exc
    if not isinstance(loaded, dict):
        raise FeatureError("config.json must be an object")
    return loaded


def _write_config(project: Path, data: dict[str, Any]) -> None:
    path = project / CONFIG_REL
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
