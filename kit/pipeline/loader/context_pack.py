"""Load a workflow step allowlist. No third-party deps.

Project root is where `features/` is written. Pack root is the `.pipeline`
directory that holds workflows and config: the project's `.pipeline` if
present, otherwise `~/.pipeline`.

Jira workflows ask the installed pipeline-kit license. Other workflows do not.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

PACK_DIRNAME = ".pipeline"
USER_PACK_DIRNAME = ".pipeline"


def _is_pack_dir(path: Path) -> bool:
    return (path / "config.json").is_file() or (path / "workflows").is_dir()


def project_root_from(start: Path | None = None) -> Path:
    here = (start or Path.cwd()).resolve()
    if here.is_file():
        here = here.parent
    for cur in (here, *here.parents):
        if _is_pack_dir(cur / PACK_DIRNAME):
            return cur
        if (cur / ".git").exists():
            return cur
    return Path.cwd().resolve()


def repo_root_from(start: Path | None = None) -> Path:
    """Alias for project_root_from (hooks and older callers)."""
    return project_root_from(start)


def user_pack_dir(home: Path | None = None) -> Path:
    return (home or Path.home()) / USER_PACK_DIRNAME


def pack_root_from(
    project: Path,
    *,
    pack_root: Path | None = None,
    home: Path | None = None,
) -> Path:
    if pack_root is not None:
        resolved = pack_root.resolve()
        if not _is_pack_dir(resolved):
            raise ValueError(f"not a pipeline pack: {resolved}")
        return resolved
    local = project.resolve() / PACK_DIRNAME
    if _is_pack_dir(local):
        return local
    user = user_pack_dir(home)
    if _is_pack_dir(user):
        return user
    raise ValueError("no pipeline pack found (project .pipeline or ~/.pipeline)")


def normalize_rel(path: str) -> str:
    rel = path.replace("\\", "/")
    while rel.startswith("./"):
        rel = rel[2:]
    return rel


_LINK_HREF = re.compile(r"\[[^\]]*\]\(([^)]+)\)")

STATE_ASSETS = (
    ".pipeline/skills/feature-development/assets/pipeline-state.md",
    ".pipeline/skills/feature-development/assets/pipeline-state-template.json",
    ".pipeline/skills/feature-development/assets/agent-state-template.json",
)


def _pack_rel(pipeline_rel: str) -> str:
    rel = normalize_rel(pipeline_rel)
    prefix = ".pipeline/"
    if rel.startswith(prefix):
        return rel[len(prefix) :]
    return rel


def _pipeline_rel(pack_rel: str) -> str:
    rel = normalize_rel(pack_rel)
    if rel.startswith(".pipeline/"):
        return rel
    return f".pipeline/{rel}"


def _is_asset(rel: str) -> bool:
    return "/assets/" in normalize_rel(rel)


def _markdown_hrefs(text: str) -> list[str]:
    out: list[str] = []
    for raw in _LINK_HREF.findall(text):
        href = raw.split()[0].strip().strip("<>\"'")
        href = href.split("#")[0].split("?")[0]
        if not href or href.startswith(("http://", "https://", "mailto:")):
            continue
        out.append(href)
    return out


def expand_skill_assets(files: list[str], pack: Path) -> list[str]:
    """Permit skill assets without listing them in workflow JSON.

    Workflow files list briefs and SKILL.md. Assets stay off the preload
    set; this only adds them to the allowlist so a specialist may Read
    them when the loaded skill or brief names them.
    """
    seen: list[str] = []

    def add(rel: str) -> None:
        item = normalize_rel(rel)
        if item and item not in seen:
            seen.append(item)

    for item in files:
        add(item)

    pack = pack.resolve()
    for item in list(seen):
        pack_rel = _pack_rel(item)
        if pack_rel.endswith("/SKILL.md") and pack_rel.startswith("skills/"):
            assets_dir = pack / Path(pack_rel).parent / "assets"
            if assets_dir.is_dir():
                for path in sorted(assets_dir.rglob("*")):
                    if path.is_file():
                        add(_pipeline_rel(path.relative_to(pack).as_posix()))

    for item in list(seen):
        if not item.endswith(".md"):
            continue
        source = pack / _pack_rel(item)
        if not source.is_file():
            continue
        try:
            text = source.read_text(encoding="utf-8")
        except OSError:
            continue
        for href in _markdown_hrefs(text):
            try:
                resolved = (source.parent / href).resolve()
                rel_to_pack = resolved.relative_to(pack).as_posix()
            except (OSError, ValueError):
                continue
            if _is_asset(rel_to_pack) and resolved.is_file():
                add(_pipeline_rel(rel_to_pack))

    is_repo_assessment = any(
        "skills/repo-assessment/SKILL.md" in normalize_rel(item) for item in files
    )
    has_agent = any("/agents/" in normalize_rel(item) for item in files)
    if has_agent or not is_repo_assessment:
        for asset in STATE_ASSETS:
            if (pack / _pack_rel(asset)).is_file():
                add(asset)

    return seen


def load_workflow_doc(pack: Path, workflow: str) -> dict[str, Any]:
    name = workflow.strip().lower()
    path = pack / "workflows" / f"{name}.json"
    if not path.is_file():
        raise ValueError(f"unknown workflow: {workflow} (missing {path})")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"invalid workflow pack: {path}")
    return data


def files_for_step(
    doc: dict[str, Any], step: str, pack: Path | None = None
) -> list[str]:
    context = doc.get("context")
    if not isinstance(context, dict):
        raise ValueError("workflow pack missing context")
    key = step.strip()
    if key == "parent":
        block = context.get("parent")
    else:
        steps = context.get("steps")
        if not isinstance(steps, dict):
            raise ValueError("workflow pack missing context.steps")
        block = steps.get(key)
    if not isinstance(block, dict):
        raise ValueError(f"unknown step: {step}")
    files = block.get("files")
    if not isinstance(files, list) or not all(isinstance(item, str) for item in files):
        raise ValueError(f"step {step} files must be a list of strings")
    declared = [normalize_rel(item) for item in files]
    if pack is None:
        return declared
    return expand_skill_assets(declared, pack)


def seed_reads_for(files: list[str]) -> list[str]:
    """Files the specialist should Read up front (briefs, skills, config)."""
    return [item for item in files if not _is_asset(item)]


def write_seed_bundle(project: Path, pack: Path, slug: str, seed: list[str]) -> str:
    """Concatenate seed files so the specialist Reads once, not per path."""
    safe = slug.strip().strip("/")
    if not safe or ".." in safe.split("/"):
        raise ValueError("invalid slug")
    rel = f"features/{safe}/step-context.md"
    dest = project / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    parts = [
        f"# Step context ({safe})",
        "",
        "Loaded together for this agent. Do not re-Read these pack files separately.",
        "When a skill below names an asset, Read that asset if it is on allowed_reads.",
        "",
    ]
    for item in seed:
        path = pack / _pack_rel(item)
        parts.append(f"----- BEGIN {item} -----")
        if path.is_file():
            parts.append(path.read_text(encoding="utf-8").rstrip())
        else:
            parts.append(f"(missing: {item})")
        parts.append(f"----- END {item} -----")
        parts.append("")
    dest.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8")
    return rel.replace("\\", "/")


def build_pack(
    workflow: str,
    step: str,
    slug: str,
    files: list[str],
    seed_bundle: str = "",
) -> dict[str, Any]:
    return {
        "workflow": workflow.strip().lower(),
        "step": step.strip(),
        "slug": slug.strip(),
        "allowed_reads": files,
        "seed_reads": seed_reads_for(files),
        "seed_bundle": seed_bundle,
    }


def write_pack(
    project: Path, pack: Path, slug: str, data: dict[str, Any]
) -> tuple[Path, Path]:
    safe = slug.strip().strip("/")
    if not safe or ".." in safe.split("/"):
        raise ValueError("invalid slug")
    artifact = project / "features" / safe / "context-pack.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    state = pack / "state" / "active-context.json"
    state.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, indent=2) + "\n"
    artifact.write_text(text, encoding="utf-8")
    state.write_text(text, encoding="utf-8")
    return artifact, state


def load_active_pack(pack: Path) -> dict[str, Any] | None:
    path = pack / "state" / "active-context.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    reads = data.get("allowed_reads")
    if not isinstance(reads, list):
        return None
    data["allowed_reads"] = [normalize_rel(item) for item in reads if isinstance(item, str)]
    return data


def activate(
    project: Path,
    workflow: str,
    step: str,
    slug: str,
    *,
    pack: Path | None = None,
    home: Path | None = None,
) -> dict[str, Any]:
    pack_dir = pack if pack is not None else pack_root_from(project, home=home)
    doc = load_workflow_doc(pack_dir, workflow)
    files = files_for_step(doc, step, pack_dir)
    seed = seed_reads_for(files)
    bundle = write_seed_bundle(project, pack_dir, slug, seed)
    data = build_pack(workflow, step, slug, files, seed_bundle=bundle)
    write_pack(project, pack_dir, slug, data)
    return data


def _require_jira(workflow: str) -> int:
    if workflow.strip().lower() not in {"jira-story", "jira-epic", "jira-bug"}:
        return 0
    require = None
    try:
        from pipeline_kit.license import require as require
    except ImportError:
        try:
            from license import require as require  # type: ignore
        except ImportError:
            require = None
    if require is None:
        sys.stderr.write("license: jira needs pipeline-kit license activate\n")
        return 73
    return int(require("jira"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Activate a workflow step allowlist.")
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--step", required=True)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--repo-root", default="", help="Project root (features/ live here).")
    parser.add_argument("--pack-root", default="", help="Override .pipeline pack directory.")
    args = parser.parse_args(argv)
    blocked = _require_jira(args.workflow)
    if blocked:
        return blocked
    project = Path(args.repo_root).resolve() if args.repo_root else project_root_from()
    pack_override = Path(args.pack_root).resolve() if args.pack_root else None
    try:
        pack_dir = pack_root_from(project, pack_root=pack_override)
        data = activate(project, args.workflow, args.step, args.slug, pack=pack_dir)
    except ValueError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1
    json.dump(data, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
