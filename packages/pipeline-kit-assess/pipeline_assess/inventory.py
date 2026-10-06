"""Installed agent artifacts and the folders each one applies to."""

from __future__ import annotations

import json
import re
from pathlib import Path

from pipeline_plugins.graphify import graphify_owned_files

_GLOBS = re.compile(r"^globs:\s*[\"']?(.+)", re.MULTILINE)
_TYPE = re.compile(r"\*+\.([A-Za-z0-9]+)")
_TYPE_GROUP = re.compile(r"\*+\.\{([^}]+)\}")
_NAME = re.compile(r"^name:\s*[\"']?([^\"'\n]+)", re.MULTILINE)
_FOLDER = re.compile(r"(?<![\w./-])([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+)/")


def _head(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:4000]
    except OSError:
        return ""


def _scopes(path: Path) -> list[str]:
    text = _head(path)
    found: list[str] = []
    match = _GLOBS.search(text)
    if match:
        for piece in match.group(1).split(","):
            cleaned = piece.strip().strip("\"'").split("*")[0].rstrip("/")
            if cleaned:
                found.append(cleaned)
    for folder in _FOLDER.findall(text):
        if folder.startswith(("http", ".git")):
            continue
        if folder not in found:
            found.append(folder.rstrip("/"))
    return found


def _extensions(text: str) -> set[str]:
    found = {match.group(1).lower() for match in _TYPE.finditer(text)}
    for match in _TYPE_GROUP.finditer(text):
        for part in match.group(1).split(","):
            part = part.strip().lower().lstrip(".")
            if part.isalnum():
                found.add(part)
    return found


def _skill_name(path: Path) -> str:
    match = _NAME.search(_head(path))
    return match.group(1).strip() if match else path.parent.name


def collect_inventory(project: Path) -> dict:
    pack = project / ".pipeline"
    mode = "kit"
    marker = pack / "install.json"
    if marker.is_file():
        try:
            data = json.loads(marker.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("mode"):
                mode = str(data["mode"])
        except (OSError, json.JSONDecodeError):
            mode = "kit"
    workflows: list[str] = []
    workflow_dir = pack / "workflows"
    if workflow_dir.is_dir():
        for path in sorted(workflow_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                workflows.append(path.stem)
                continue
            name = data.get("name") if isinstance(data, dict) else None
            workflows.append(
                name.strip() if isinstance(name, str) and name.strip() else path.stem
            )
    skills: list[str] = []
    skill_root = pack / "skills"
    if skill_root.is_dir():
        for path in sorted(skill_root.glob("*/SKILL.md")):
            skills.append(_skill_name(path))
    agents_dir = pack / "agents"
    agents = (
        [path.stem for path in sorted(agents_dir.glob("*.md"))]
        if agents_dir.is_dir()
        else []
    )
    extensions_dir = project / "pipeline_extensions"
    extensions = (
        [path.stem.replace("_", "-") for path in sorted(extensions_dir.glob("*.py"))]
        if extensions_dir.is_dir()
        else []
    )
    owned = set(graphify_owned_files(project))
    artifacts: list[dict] = []
    rule_exts: set[str] = set()

    def add(kind: str, name: str, path: Path, *, repo_wide: bool = False) -> None:
        rel = (
            str(path.relative_to(project))
            if path.is_relative_to(project)
            else str(path)
        )
        if rel in owned or path.name in owned:
            return
        if kind == "rule":
            rule_exts.update(_extensions(_head(path)))
        artifacts.append(
            {
                "kind": kind,
                "name": name,
                "path": rel,
                "scopes": [] if repo_wide else _scopes(path),
                "repo_wide": repo_wide,
            }
        )

    for name in ("AGENTS.md", "CLAUDE.md", ".cursorrules"):
        path = project / name
        if path.is_file():
            add("guidance", name, path, repo_wide=True)
    rules = project / ".cursor" / "rules"
    if rules.is_dir():
        for path in sorted(rules.glob("*")):
            if path.is_file() and path.name != ".gitkeep":
                add("rule", path.name, path)
    claude_rules = project / ".claude" / "rules"
    if claude_rules.is_dir():
        for path in sorted(claude_rules.glob("*")):
            if path.is_file():
                add("rule", path.name, path)
    pack_rules = pack / "rules"
    if pack_rules.is_dir():
        for path in sorted(pack_rules.glob("*")):
            if path.is_file() and path.name != ".gitkeep":
                add("rule", path.name, path)
    for path in (
        sorted((project / ".github" / "skills").glob("*/SKILL.md"))
        if (project / ".github" / "skills").is_dir()
        else []
    ):
        add("skill", _skill_name(path), path)
    hooks = pack / "hooks"
    if hooks.is_dir():
        for path in sorted(hooks.glob("*")):
            if path.is_file() and path.name != ".gitkeep":
                add("hook", path.name, path)
    config = {}
    config_path = pack / "config.json"
    if config_path.is_file():
        try:
            loaded = json.loads(config_path.read_text(encoding="utf-8"))
            config = loaded if isinstance(loaded, dict) else {}
        except (OSError, json.JSONDecodeError):
            config = {}
    flags = _flags(config)
    return {
        "mode": mode,
        "workflows": workflows,
        "skills": skills,
        "agents": agents,
        "extensions": extensions,
        "artifacts": artifacts,
        "flags": flags,
        "verify_rules": _verify_count(config),
        "deploy_auto": _deploy_auto(config),
        "has_agents_md": (project / "AGENTS.md").is_file() and "AGENTS.md" not in owned,
        "has_claude": (project / ".claude").is_dir(),
        "has_claude_md": (project / "CLAUDE.md").is_file(),
        "rule_extensions": sorted(rule_exts),
    }


def _flags(config: dict) -> dict[str, bool]:
    design = (
        config.get("test_design") if isinstance(config.get("test_design"), dict) else {}
    )
    diagrams = (
        config.get("architecture_diagrams")
        if isinstance(config.get("architecture_diagrams"), dict)
        else {}
    )
    obs = (
        config.get("agent_observability")
        if isinstance(config.get("agent_observability"), dict)
        else {}
    )
    intake = config.get("intake") if isinstance(config.get("intake"), dict) else {}
    jira = intake.get("jira") if isinstance(intake.get("jira"), dict) else {}
    github = intake.get("github") if isinstance(intake.get("github"), dict) else {}
    return {
        "test-design": bool(design.get("enabled")),
        "playwright": bool(design.get("playwright")),
        "archify": bool(diagrams.get("enabled")),
        "agent-observability": bool(obs.get("enabled")),
        "jira-intake": bool(jira.get("enabled")),
        "github-intake": bool(github.get("enabled")),
    }


def _verify_count(config: dict) -> int:
    verify = config.get("verify") if isinstance(config.get("verify"), dict) else {}
    rules = verify.get("rules") if isinstance(verify, dict) else []
    return len(rules) if isinstance(rules, list) else 0


def _deploy_auto(config: dict) -> bool:
    deploy = config.get("deploy") if isinstance(config.get("deploy"), dict) else {}
    targets = deploy.get("targets") if isinstance(deploy, dict) else []
    if not isinstance(targets, list) or not targets:
        return True
    return targets == ["auto"]


def covers(artifact: dict, folder: str) -> bool:
    if artifact.get("repo_wide"):
        return False
    for scope in artifact.get("scopes") or []:
        if (
            folder == scope
            or folder.startswith(scope + "/")
            or scope.startswith(folder + "/")
        ):
            return True
    return False
