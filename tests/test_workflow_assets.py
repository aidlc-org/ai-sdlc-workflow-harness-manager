"""Workflow JSON lists skills; assets expand from those skills on demand."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LOADER = REPO / "kit" / "pipeline" / "loader" / "context_pack.py"
PACK = REPO / "kit" / "pipeline"


def _loader():
    spec = importlib.util.spec_from_file_location("kit_context_pack", LOADER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _workflow(name: str) -> dict:
    return json.loads((PACK / "workflows" / f"{name}.json").read_text(encoding="utf-8"))


def _declared(doc: dict, step: str) -> list[str]:
    context = doc["context"]
    block = context["parent"] if step == "parent" else context["steps"][step]
    return list(block["files"])


def test_workflow_json_does_not_preload_skill_assets():
    for name in (
        "feature-development",
        "jira-story",
        "jira-epic",
        "jira-bug",
        "github-story",
        "github-epic",
        "github-bug",
        "ask",
        "test-knowledge-bootstrap",
        "repo-assessment",
    ):
        doc = _workflow(name)
        for rel in _declared(doc, "parent"):
            assert "/assets/" not in rel, f"{name} parent still lists {rel}"
        for step, block in (doc["context"].get("steps") or {}).items():
            for rel in block["files"]:
                assert "/assets/" not in rel, f"{name} {step} still lists {rel}"


def test_architect_assets_expand_from_skills():
    mod = _loader()
    doc = _workflow("feature-development")
    declared = mod.files_for_step(doc, "architect-agent")
    assert all("/assets/" not in item for item in declared)
    allowed = mod.files_for_step(doc, "architect-agent", PACK)
    seed = mod.seed_reads_for(allowed)
    assert ".pipeline/agents/architect-agent.md" in seed
    assert ".pipeline/skills/architecture-design/SKILL.md" in seed
    assert (
        ".pipeline/skills/architecture-visualization/assets/diagram-manifest-template.json"
        in allowed
    )
    assert (
        ".pipeline/skills/architecture-visualization/assets/diagram-manifest-template.json"
        not in seed
    )
    assert ".pipeline/skills/feature-development/assets/pipeline-state.md" in allowed
    assert ".pipeline/skills/feature-development/assets/pipeline-state.md" not in seed
    assert ".pipeline/skills/feature-development/assets/architecture-template.md" in allowed
    assert ".pipeline/skills/feature-development/assets/architecture-template.md" not in seed


def test_pm_templates_come_from_product_planning_skill():
    mod = _loader()
    doc = _workflow("feature-development")
    allowed = mod.files_for_step(doc, "product-manager-agent", PACK)
    seed = mod.seed_reads_for(allowed)
    assert ".pipeline/skills/product-planning/SKILL.md" in seed
    assert ".pipeline/skills/feature-development/assets/prd-template.md" in allowed
    assert ".pipeline/skills/feature-development/assets/prd-template.md" not in seed
    assert ".pipeline/skills/feature-development/assets/pipeline-state.md" in allowed
    assert ".pipeline/skills/feature-development/assets/pipeline-state.md" not in seed
    assert (
        ".pipeline/skills/feature-development/assets/pipeline-state-template.json"
        not in seed
    )
    assert (
        ".pipeline/skills/feature-development/assets/agent-state-template.json"
        not in seed
    )


def test_jira_architect_still_allowlists_diagram_policy():
    mod = _loader()
    doc = _workflow("jira-story")
    allowed = mod.files_for_step(doc, "architect-agent", PACK)
    assert ".pipeline/skills/architecture-visualization/SKILL.md" in allowed
    assert (
        ".pipeline/skills/feature-development/assets/architecture-diagrams-policy.md"
        in allowed
    )


def test_jira_intake_allowlists_api_script():
    mod = _loader()
    doc = _workflow("jira-story")
    allowed = mod.files_for_step(doc, "intake-agent", PACK)
    seed = mod.seed_reads_for(allowed)
    assert ".pipeline/skills/jira-intake/SKILL.md" in seed
    assert ".pipeline/skills/jira-intake/scripts/jira_api.py" in allowed
    assert ".pipeline/skills/jira-intake/scripts/jira_api.py" not in seed


def test_github_intake_allowlists_api_script():
    mod = _loader()
    doc = _workflow("github-story")
    allowed = mod.files_for_step(doc, "intake-agent", PACK)
    seed = mod.seed_reads_for(allowed)
    assert ".pipeline/skills/github-intake/SKILL.md" in seed
    assert ".pipeline/skills/github-intake/scripts/github_api.py" in allowed
    assert ".pipeline/skills/github-intake/scripts/github_api.py" not in seed


def test_activate_writes_one_seed_bundle(tmp_path: Path):
    mod = _loader()
    project = tmp_path / "app"
    project.mkdir()
    data = mod.activate(
        project,
        "feature-development",
        "product-manager-agent",
        "try-pm",
        pack=PACK,
    )
    assert data["seed_bundle"] == "features/try-pm/step-context.md"
    bundle = project / "features" / "try-pm" / "step-context.md"
    text = bundle.read_text(encoding="utf-8")
    assert ".pipeline/agents/product-manager-agent.md" in text
    assert ".pipeline/skills/product-planning/SKILL.md" in text
    assert "----- BEGIN .pipeline/agents/product-manager-agent.md -----" in text
    assert "----- BEGIN .pipeline/skills/product-planning/SKILL.md -----" in text
    assert "----- BEGIN .pipeline/skills/feature-development/assets/prd-template.md -----" not in text
    assert "----- BEGIN .pipeline/skills/feature-development/assets/pipeline-state.md -----" not in text
    assert ".pipeline/skills/product-planning/SKILL.md" in data["seed_reads"]
    assert ".pipeline/skills/feature-development/assets/prd-template.md" not in data["seed_reads"]
    assert ".pipeline/skills/feature-development/assets/pipeline-state.md" not in data["seed_reads"]
    assert data["seed_bundle"] not in data["seed_reads"]
