"""Compose step prompts from the wheel (kit briefs) or an associate package."""

from __future__ import annotations

import json
import re
from pathlib import Path

from pipeline_orchestrator.graph import AgentStep
from pipeline_orchestrator.pack import kit_pack_root, normalize_pack_rel

PROMPT_BUDGET = 400_000
ISOLATION = Path(__file__).resolve().parent / "prompts" / "isolation.txt"
_LINK_HREF = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
STATE_ASSETS = (
    "skills/feature-development/assets/pipeline-state.md",
    "skills/feature-development/assets/pipeline-state-template.json",
    "skills/feature-development/assets/agent-state-template.json",
)


def _is_asset(rel: str) -> bool:
    return "/assets/" in rel.replace("\\", "/")


def _markdown_hrefs(text: str) -> list[str]:
    out: list[str] = []
    for raw in _LINK_HREF.findall(text):
        href = raw.split()[0].strip().strip("<>\"'")
        href = href.split("#")[0].split("?")[0]
        if not href or href.startswith(("http://", "https://", "mailto:")):
            continue
        out.append(href)
    return out


def expand_skill_assets(files: list[str], root: Path) -> list[str]:
    seen: list[str] = []

    def add(rel: str) -> None:
        item = normalize_pack_rel(rel)
        if item and item not in seen:
            seen.append(item)

    for item in files:
        add(item)

    root = root.resolve()
    for item in list(seen):
        if item.endswith("/SKILL.md") and item.startswith("skills/"):
            assets_dir = root / Path(item).parent / "assets"
            if assets_dir.is_dir():
                for path in sorted(assets_dir.rglob("*")):
                    if path.is_file():
                        add(path.relative_to(root).as_posix())

    for item in list(seen):
        if not item.endswith(".md"):
            continue
        source = root / item
        if not source.is_file():
            continue
        try:
            text = source.read_text(encoding="utf-8")
        except OSError:
            continue
        for href in _markdown_hrefs(text):
            try:
                resolved = (source.parent / href).resolve()
                rel_to_root = resolved.relative_to(root).as_posix()
            except (OSError, ValueError):
                continue
            if _is_asset(rel_to_root) and resolved.is_file():
                add(rel_to_root)

    is_repo_assessment = any("skills/repo-assessment/SKILL.md" in item for item in files)
    has_agent = any(item.startswith("agents/") for item in files)
    if has_agent or not is_repo_assessment:
        for asset in STATE_ASSETS:
            if (root / asset).is_file():
                add(asset)
    return seen


def seed_files(files: list[str]) -> list[str]:
    return [item for item in files if not _is_asset(item)]


def files_for_kit_step(workflow: str, step: str) -> list[str]:
    root = kit_pack_root()
    path = root / "workflows" / f"{workflow}.json"
    if not path.is_file():
        path = root / "workflows" / "feature-development.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    context = data.get("context") or {}
    if step == "parent":
        block = context.get("parent") or {}
    else:
        block = (context.get("steps") or {}).get(step) or {}
    files = block.get("files") or []
    declared = [normalize_pack_rel(item) for item in files if isinstance(item, str)]
    return expand_skill_assets(declared, root)


def _read_rel(rel: str, *, project: Path, spec_dir: Path | None) -> tuple[str, str]:
    if rel.startswith("kit:"):
        rel = files_for_kit_step("feature-development", rel[4:])[0] if ":" in rel else rel
    if rel.startswith("kit:"):
        rels = files_for_kit_step("feature-development", rel.split(":", 1)[1])
        chunks = []
        for item in rels:
            text = (kit_pack_root() / item).read_text(encoding="utf-8")
            chunks.append(f"## {item}\n\n{text}")
        return rel, "\n\n".join(chunks)
    kit = kit_pack_root() / rel
    if kit.is_file():
        return rel, kit.read_text(encoding="utf-8")
    if spec_dir is not None:
        local = spec_dir / rel
        if local.is_file():
            return rel, local.read_text(encoding="utf-8")
        brief = spec_dir / "briefs" / Path(rel).name
        if brief.is_file():
            return str(brief.relative_to(spec_dir)), brief.read_text(encoding="utf-8")
    project_rel = project / rel
    if project_rel.is_file():
        return rel, project_rel.read_text(encoding="utf-8")
    raise FileNotFoundError(f"context file not found: {rel}")


def resolve_context_files(step: AgentStep, workflow: str) -> list[str]:
    if step.context_files:
        out: list[str] = []
        for item in step.context_files:
            if item.startswith("kit:"):
                out.extend(files_for_kit_step("feature-development", item.split(":", 1)[1]))
            else:
                out.append(item)
        return out
    source = step.context_from or step.id
    try:
        return files_for_kit_step(workflow, source)
    except Exception:
        return files_for_kit_step("feature-development", source)


def compose_prompt(
    *,
    step: AgentStep,
    workflow: str,
    change_class: str,
    slug: str,
    project: Path,
    extra: dict[str, str] | None = None,
    spec_dir: Path | None = None,
) -> tuple[str, str]:
    import hashlib

    isolation = ISOLATION.read_text(encoding="utf-8") if ISOLATION.is_file() else ""
    files = resolve_context_files(step, workflow)
    seed = seed_files(files)
    assets = [item for item in files if item not in seed]
    parts = [isolation.strip(), ""]
    fields = {
        "WORKFLOW": workflow,
        "CHANGE_CLASS": change_class,
        "REPO_ROOT": str(project.resolve()),
        "FEATURE_SLUG": slug,
        "PIPELINE_STATE_PATH": f"features/{slug}/pipeline-state.json",
        "PRIOR_STATE_PATH": (
            f"features/{slug}/state/{step.prior_agent}.json" if step.prior_agent else "none"
        ),
        "STEP": step.id,
    }
    if extra:
        fields.update(extra)
    parts.append("## Run fields\n")
    for key, value in fields.items():
        parts.append(f"{key}: {value}")
    parts.append("")
    kit_context = f"features/{slug}/kit-context"
    parts.append(
        f"You are {step.id}. Follow the inlined brief and skills below. "
        "Do not read `.pipeline/agents` or `.pipeline/skills` from disk — they are not installed in orchestrator mode. "
        "When an inlined skill or brief names an asset, Read it from "
        f"{kit_context}/ (same relative path). Do not preload every kit-context file. "
        "Write artifacts under features/{slug}/ only. "
        f"Write features/{slug}/state/{step.id}.json when done. "
        "Return a short HANDOFF with **status:** SUCCESS | BLOCKED | ASSUMPTIONS_USED | changes-required."
    )
    parts.append("")
    if assets:
        dest = project / "features" / slug / "kit-context"
        parts.append("## Named skill assets (read only when a skill names them)\n")
        for rel in assets:
            name, text = _read_rel(rel, project=project, spec_dir=spec_dir)
            out = dest / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text, encoding="utf-8")
            parts.append(f"- `{name}` → `{kit_context}/{rel}`")
        parts.append("")
    for rel in seed:
        name, text = _read_rel(rel, project=project, spec_dir=spec_dir)
        parts.append(f"\n----- BEGIN {name} -----\n{text}\n----- END {name} -----\n")
    prompt = "\n".join(parts)
    if len(prompt) > PROMPT_BUDGET:
        raise ValueError(
            f"composed prompt for {step.id} is {len(prompt)} chars (budget {PROMPT_BUDGET})"
        )
    digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    return prompt, digest
