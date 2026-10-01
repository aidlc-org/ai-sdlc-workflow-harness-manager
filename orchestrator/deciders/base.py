"""Model decision contract. The engine calls this; it does not talk to a vendor."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


class DecisionError(Exception):
    """The step cannot run because the chosen model is not in the catalog."""


@dataclass(frozen=True)
class DecisionRequest:
    step_id: str
    job: str
    user_request: str
    workflow: str
    change_class: str
    prior_status: str
    catalog: tuple[str, ...]
    pin: str = ""
    model_info: dict[str, dict] = field(default_factory=dict)


@dataclass
class Decision:
    model: str
    reason: str
    decider: str
    fallback: str
    confidence: float | None = None
    probabilities: dict[str, float] = field(default_factory=dict)
    jev_model: str = ""
    jev_choice: str = ""
    evaluated: list[str] = field(default_factory=list)
    criteria: dict[str, dict] = field(default_factory=dict)
    capability: str = ""

    def to_routing(self) -> dict[str, object]:
        row: dict[str, object] = {
            "chosen": self.model,
            "reason": self.reason,
            "decider": self.decider,
            "fallback": self.fallback,
        }
        if self.confidence is not None:
            row["confidence"] = self.confidence
        if self.probabilities:
            row["probabilities"] = dict(self.probabilities)
        if self.jev_model:
            row["jev_model"] = self.jev_model
        if self.jev_choice:
            row["jev_choice"] = self.jev_choice
        if self.evaluated:
            row["evaluated"] = list(self.evaluated)
        return row

    def format(self, step_id: str) -> str:
        parts = [
            "model",
            "step=%s" % step_id,
            "chosen=%s" % self.model,
            "reason=%s" % self.reason,
            "decider=%s" % self.decider,
        ]
        if self.confidence is not None:
            parts.append("confidence=%.2f" % self.confidence)
        if self.jev_choice and self.jev_choice != self.model:
            parts.append("jev_choice=%s" % self.jev_choice)
        lines = [" ".join(parts)]
        if self.capability:
            lines.append("  need: %s" % self.capability)
        lines.append("  basis: %s" % self._basis())
        if self.evaluated:
            lines.append("  sent: %s" % ", ".join(self.evaluated))
        scores = self._scores_line()
        if scores:
            lines.append(scores)
        return "\n".join(lines)

    def summary_line(self, step_id: str) -> str:
        bits = [step_id, "chosen=%s" % self.model, "reason=%s" % self.reason]
        if self.jev_choice and self.jev_choice != self.model:
            bits.append("jev=%s" % self.jev_choice)
        if self.confidence is not None:
            bits.append("confidence=%.2f" % self.confidence)
        return "  " + "  ".join(bits)

    def _basis(self) -> str:
        picked = self.jev_choice or self.model
        score = self.probabilities.get(picked)
        score_text = " (%.2f)" % score if score is not None else ""
        if self.reason == "pin":
            return "Pinned %s. Jev was not asked." % self.model
        if self.reason == "config":
            return "Config set %s. Jev was not asked." % self.model
        if self.reason == "fixed":
            return "Fixed decider used %s." % self.model
        if self.reason == "jev_unavailable":
            return "Jev did not answer. Fallback %s runs." % self.model
        if self.reason == "low_confidence":
            return (
                "Jev picked %s%s. Confidence %.2f is below the floor, so fallback %s runs."
                % (picked, score_text, self.confidence or 0.0, self.model)
            )
        if self.reason == "jev":
            return "Jev picked %s%s. That model runs." % (self.model, score_text)
        return "Used %s because %s." % (self.model, self.reason)

    def _scores_line(self) -> str:
        ranked = sorted(self.probabilities.items(), key=lambda item: item[1], reverse=True)
        if not ranked:
            count = len(self.evaluated)
            if count:
                return "  catalog: %s models sent to Jev" % count
            return ""
        shown = ranked[:5]
        bits = ["%s %.2f" % (name, score) for name, score in shown]
        extra = len(ranked) - len(shown)
        suffix = " (+%s)" % extra if extra else ""
        return "  scores: %s%s" % ("; ".join(bits), suffix)


class ModelDecider(Protocol):
    name: str

    def decide(self, request: DecisionRequest) -> Decision: ...


_JOBS = {
    "product-manager-agent": "Writes the product requirements.",
    "ui-designer-agent": "Writes the UI design contract and mockups.",
    "intake-agent": "Turns the tracker issue into an intake.",
    "architect-agent": "Writes the architecture.",
    "ba-agent": "Writes the business analysis and handoff.",
    "ba-critic-agent": "Reviews the business analysis.",
    "developer-agent": "Implements the change.",
    "developer-critic-agent": "Reviews the implementation.",
    "bug-analyst-agent": "Analyzes the bug.",
    "devops-agent": "Prepares delivery.",
    "retro-agent": "Writes the retro.",
    "knowledge-curator-agent": "Curates test knowledge.",
    "tester-agent": "Runs the test layers.",
}


def capability_for(step_id: str) -> str:
    """What kind of model this agent needs. Jev matches a catalog id to this."""
    if step_id.startswith("tester-agent"):
        return (
            "verification: follow test instructions and inspect code. "
            "Prefer a fast coding model over a heavy planning model."
        )
    if step_id.endswith("-critic-agent") or step_id in {"ba-critic-agent", "developer-critic-agent"}:
        return (
            "review: find gaps, contradictions, and missing acceptance criteria. "
            "Prefer a reasoning model over a fast coding model."
        )
    if step_id in {"product-manager-agent", "intake-agent", "ba-agent", "ui-designer-agent"}:
        return (
            "planning: write requirements, scope, and acceptance criteria. "
            "Prefer a reasoning model. A fast coding model is a poor fit."
        )
    if step_id == "architect-agent":
        return (
            "architecture: choose structure, boundaries, and tradeoffs. "
            "Prefer a reasoning model. A fast coding model is a poor fit."
        )
    if step_id in {"developer-agent", "bug-analyst-agent"}:
        return (
            "implementation: edit code and fix defects. "
            "Prefer a fast coding model over a heavy planning model."
        )
    if step_id == "devops-agent":
        return "delivery: prepare build and release steps. Prefer a precise coding model."
    if step_id in {"retro-agent", "knowledge-curator-agent"}:
        return "writing: summarize what happened. A smaller writing model is enough."
    return "general: match the model to the agent id %s." % step_id


def job_for(step_id: str) -> str:
    if step_id.startswith("tester-agent-"):
        layer = step_id.removeprefix("tester-agent-")
        return "Runs the %s test layer." % layer
    if step_id.endswith("-critic-agent"):
        return "Reviews the previous agent's work."
    return _JOBS.get(step_id, "Performs the %s step." % step_id)
