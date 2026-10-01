"""First-party workflow graphs. Custom workflows register beside these; they never replace them."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AgentStep:
    id: str
    model: str = ""
    mcp: tuple[str, ...] = ()
    context_files: tuple[str, ...] = ()
    context_from: str | None = None
    prior_agent: str | None = None
    critic: bool = False


@dataclass(frozen=True)
class SignoffGate:
    id: str
    artifact_hint: str = ""


@dataclass(frozen=True)
class WaveFan:
    id: str = "@waves"
    child_chain: tuple[str, ...] = ("developer-agent", "developer-critic-agent")


@dataclass(frozen=True)
class LayerFan:
    id: str = "tester-agent"
    layers: tuple[str, ...] = ("unit", "api", "ui")
    context_from: str | None = "tester-agent"


Node = AgentStep | SignoffGate | WaveFan | LayerFan


@dataclass
class WorkflowSpec:
    name: str
    provider: str = "pipeline-kit"
    version: str = ""
    default_change_class: str = "feature"
    nodes: list[Node] = field(default_factory=list)
    classes: dict[str, list[Node]] = field(default_factory=dict)

    def chain_for(self, change_class: str) -> list[Node]:
        if self.classes:
            key = change_class.strip().lower() or self.default_change_class
            if key not in self.classes:
                raise ValueError(f"unknown change class {change_class!r} for {self.name}")
            return list(self.classes[key])
        return list(self.nodes)


def _kit_step(step_id: str, **kwargs: Any) -> AgentStep:
    return AgentStep(id=step_id, context_from=step_id, **kwargs)


def feature_development() -> WorkflowSpec:
    micro = [
        _kit_step("developer-agent"),
        LayerFan(),
        _kit_step("devops-agent", prior_agent="tester-agent"),
        _kit_step("retro-agent", prior_agent="devops-agent"),
    ]
    minor = [
        _kit_step("developer-agent"),
        _kit_step("developer-critic-agent", prior_agent="developer-agent", critic=True),
        LayerFan(),
        _kit_step("devops-agent", prior_agent="tester-agent"),
        _kit_step("retro-agent", prior_agent="devops-agent"),
    ]
    feature = [
        _kit_step("product-manager-agent"),
        _kit_step("ui-designer-agent", prior_agent="product-manager-agent"),
        SignoffGate("requirements", artifact_hint="prd.md"),
        _kit_step("architect-agent", prior_agent="product-manager-agent"),
        SignoffGate("architect", artifact_hint="architecture.md"),
        _kit_step("ba-agent", prior_agent="architect-agent"),
        _kit_step("ba-critic-agent", prior_agent="ba-agent", critic=True),
        SignoffGate("ba", artifact_hint="HANDOFF.md"),
        WaveFan(),
        LayerFan(),
        _kit_step("devops-agent", prior_agent="tester-agent"),
        _kit_step("retro-agent", prior_agent="devops-agent"),
    ]
    return WorkflowSpec(
        name="feature-development",
        default_change_class="feature",
        classes={"micro": micro, "minor": minor, "feature": feature},
    )


def jira_story() -> WorkflowSpec:
    return WorkflowSpec(
        name="jira-story",
        default_change_class="feature",
        nodes=[
            _kit_step("intake-agent"),
            SignoffGate("requirements", artifact_hint="intake.md"),
            _kit_step("architect-agent", prior_agent="intake-agent"),
            SignoffGate("architect", artifact_hint="architecture.md"),
            _kit_step("ba-agent", prior_agent="architect-agent"),
            _kit_step("ba-critic-agent", prior_agent="ba-agent", critic=True),
            SignoffGate("ba", artifact_hint="HANDOFF.md"),
            WaveFan(),
            LayerFan(),
            _kit_step("devops-agent", prior_agent="tester-agent"),
            _kit_step("retro-agent", prior_agent="devops-agent"),
        ],
    )


def jira_epic() -> WorkflowSpec:
    spec = jira_story()
    spec.name = "jira-epic"
    return spec


def jira_bug() -> WorkflowSpec:
    return WorkflowSpec(
        name="jira-bug",
        default_change_class="minor",
        nodes=[
            _kit_step("intake-agent"),
            _kit_step("bug-analyst-agent", prior_agent="intake-agent"),
            _kit_step("developer-agent", prior_agent="bug-analyst-agent"),
            _kit_step("developer-critic-agent", prior_agent="developer-agent", critic=True),
            LayerFan(),
            _kit_step("devops-agent", prior_agent="tester-agent"),
            _kit_step("retro-agent", prior_agent="devops-agent"),
        ],
    )


def ask() -> WorkflowSpec:
    return WorkflowSpec(name="ask", nodes=[])


def repo_assessment() -> WorkflowSpec:
    return WorkflowSpec(name="repo-assessment", nodes=[])


def test_knowledge_bootstrap() -> WorkflowSpec:
    return WorkflowSpec(
        name="test-knowledge-bootstrap",
        nodes=[_kit_step("knowledge-curator-agent")],
    )


BUILTIN: dict[str, WorkflowSpec] = {
    spec.name: spec
    for spec in (
        feature_development(),
        jira_story(),
        jira_epic(),
        jira_bug(),
        ask(),
        repo_assessment(),
        test_knowledge_bootstrap(),
    )
}


def builtin_names() -> list[str]:
    return list(BUILTIN)
