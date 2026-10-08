"""Kit model policy: decide which model a step should use.

Enforcement:
  - Orchestrator mode (`pipeline-kit run`) applies the model via the Cursor SDK.
  - Kit mode records a decision on every loader activate for a specialist step.
    Agent CLIs may honor it when spawning a Task/subagent; IDE chat does not
    force the model. This module never talks to an IDE spawn API.

No third-party deps. Optional use of pipeline_orchestrator.deciders when installed.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

DEFAULT_FALLBACK = "grok-4.6"
DEFAULT_DECIDER = "fixed"
DEFAULT_CANDIDATES = (
    
    "grok-4.5",
    "grok-4.6",
    "grok-4.7",
    "claude-opus-5",
    "gpt-5.5",
    "gpt-5.6-sol",
)

# Parent / gate tokens are not specialist agents.
_SKIP_STEPS = frozenset(
    {
        "parent",
        "@waves",
        "@signoff:requirements",
        "@signoff:architect",
        "@signoff:ba",
    }
)

_FRONT_MODEL = re.compile(
    r"(?m)^model:\s*[`'\"]?([^\s`'\"]+)[`'\"]?\s*$"
)
_ROUTE_CLASS = re.compile(
    r"(?im)(?:\*\*change_class:\*\*|change_class:)\s*(micro|minor|feature)\b"
)


def routing_enabled() -> bool:
    raw = (os.environ.get("PIPELINE_KIT_MODEL_ROUTING") or "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def is_specialist_step(step: str) -> bool:
    name = (step or "").strip()
    if not name or name in _SKIP_STEPS:
        return False
    if name.startswith("@"):
        return False
    return True


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _orchestrator_block(pack: Path, project: Path | None = None) -> dict[str, Any]:
    # Prefer the project pack so customer pins win over a bundled/read-only pack root.
    roots: list[Path] = []
    if project is not None:
        roots.append(project / ".pipeline")
    roots.append(pack)
    seen: set[Path] = set()
    for root in roots:
        try:
            resolved = root.resolve()
        except OSError:
            resolved = root
        if resolved in seen:
            continue
        seen.add(resolved)
        data = _load_json(root / "config.json")
        block = data.get("orchestrator")
        if isinstance(block, dict):
            return block
    return {}


def _read_steps(models: dict[str, Any]) -> dict[str, str]:
    steps: dict[str, str] = {}
    raw = models.get("steps") if isinstance(models.get("steps"), dict) else {}
    for key, value in raw.items():
        if isinstance(value, str) and value.strip():
            steps[str(key)] = value.strip()
        elif isinstance(value, list) and value and isinstance(value[0], str) and value[0].strip():
            steps[str(key)] = value[0].strip()
    return steps


def _read_candidates(models: dict[str, Any]) -> list[str]:
    if "candidates" not in models:
        return list(DEFAULT_CANDIDATES)
    raw = models.get("candidates")
    if raw is None or raw == []:
        return []
    if isinstance(raw, str) and raw.strip():
        return [raw.strip()]
    if not isinstance(raw, list):
        return list(DEFAULT_CANDIDATES)
    out: list[str] = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
        elif isinstance(item, dict):
            model_id = str(item.get("id") or item.get("name") or "").strip()
            if model_id:
                out.append(model_id)
    return out


def _agent_frontmatter_model(pack: Path, step: str) -> str:
    path = pack / "agents" / f"{step}.md"
    if not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    if end < 0:
        return ""
    header = text[3:end]
    match = _FRONT_MODEL.search(header)
    if not match:
        return ""
    # Strip optional Cursor-style suffixes: grok-4.6[effort=high]
    return match.group(1).split("[", 1)[0].strip()


def _change_class_from_route(project: Path, slug: str) -> str:
    parent = slug.strip().strip("/").split("/", 1)[0]
    if not parent:
        return ""
    path = project / "features" / parent / "route.md"
    if not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    match = _ROUTE_CLASS.search(text)
    return (match.group(1) or "").lower() if match else ""


def _catalog_for_kit(block: dict[str, Any]) -> tuple[str, ...]:
    models = block.get("models") if isinstance(block.get("models"), dict) else {}
    candidates = _read_candidates(models if isinstance(models, dict) else {})
    fallback = str(block.get("fallback_model") or DEFAULT_FALLBACK).strip() or DEFAULT_FALLBACK
    ids = list(candidates)
    if fallback and fallback not in ids:
        ids.insert(0, fallback)
    steps = _read_steps(models if isinstance(models, dict) else {})
    for value in steps.values():
        if value and value not in ids:
            ids.append(value)
    if not ids:
        ids = [fallback]
    return tuple(ids)


def _fixed_decision(
    *,
    step: str,
    catalog: tuple[str, ...],
    block: dict[str, Any],
    pin: str = "",
) -> dict[str, Any]:
    models = block.get("models") if isinstance(block.get("models"), dict) else {}
    steps = _read_steps(models if isinstance(models, dict) else {})
    fallback = str(block.get("fallback_model") or DEFAULT_FALLBACK).strip() or DEFAULT_FALLBACK
    if fallback not in catalog:
        fallback = catalog[0]
    pin = (pin or "").strip()
    if pin:
        if pin in catalog:
            return {
                "chosen": pin,
                "reason": "pin",
                "decider": "fixed",
                "fallback": fallback,
                "apply": "advisory",
            }
        return {
            "chosen": fallback,
            "reason": "pin_not_in_catalog",
            "decider": "fixed",
            "fallback": fallback,
            "pin_rejected": pin,
            "apply": "advisory",
        }
    step_model = (steps.get(step) or "").strip()
    if step_model:
        if step_model in catalog:
            return {
                "chosen": step_model,
                "reason": "config",
                "decider": "fixed",
                "fallback": fallback,
                "apply": "advisory",
            }
        return {
            "chosen": fallback,
            "reason": "config_not_in_catalog",
            "decider": "fixed",
            "fallback": fallback,
            "config_rejected": step_model,
            "apply": "advisory",
        }
    return {
        "chosen": fallback,
        "reason": "fixed",
        "decider": "fixed",
        "fallback": fallback,
        "apply": "advisory",
    }


def _try_orchestrator_decide(
    project: Path,
    *,
    step: str,
    workflow: str,
    change_class: str,
    user_request: str,
    pin: str,
    catalog: tuple[str, ...],
) -> dict[str, Any] | None:
    """Use the same decider package as orchestrator when importable."""
    try:
        from pipeline_orchestrator.deciders.base import DecisionRequest
        from pipeline_orchestrator.deciders.factory import make_decider
        from pipeline_orchestrator.deciders.base import job_for
    except ImportError:
        return None
    try:
        decider = make_decider(project)
        decision = decider.decide(
            DecisionRequest(
                step_id=step,
                job=job_for(step),
                user_request=user_request or "",
                workflow=workflow,
                change_class=change_class or "",
                prior_status="",
                catalog=catalog,
                pin=pin,
            )
        )
    except Exception as exc:  # noqa: BLE001 — kit must never fail the loader
        return {
            "chosen": catalog[0] if catalog else DEFAULT_FALLBACK,
            "reason": "decider_error",
            "decider": "error",
            "fallback": catalog[0] if catalog else DEFAULT_FALLBACK,
            "error": str(exc)[:200],
            "apply": "advisory",
        }
    row = decision.to_routing()
    row["apply"] = "advisory"
    row["capability"] = getattr(decision, "capability", "") or ""
    return row


def resolve_model(
    *,
    project: Path,
    pack: Path,
    step: str,
    workflow: str,
    slug: str = "",
    change_class: str = "",
    user_request: str = "",
    pin: str = "",
) -> dict[str, Any] | None:
    """Return a routing dict for a specialist step, or None when skipped."""
    if not routing_enabled():
        return {
            "chosen": None,
            "reason": "disabled",
            "decider": "off",
            "apply": "off",
        }
    if not is_specialist_step(step):
        return None

    block = _orchestrator_block(pack, project)
    if not change_class and slug:
        change_class = _change_class_from_route(project, slug)

    catalog = _catalog_for_kit(block)
    agent_pin = (pin or "").strip() or _agent_frontmatter_model(pack, step)

    # Kit default is fixed (offline, no TypeSafe). Opt into jev only when
    # PIPELINE_KIT_MODEL_DECIDER=jev and orchestrator extra is installed.
    env_decider = (os.environ.get("PIPELINE_KIT_MODEL_DECIDER") or "").strip().lower()
    cfg_decider = str(block.get("decider") or DEFAULT_DECIDER).strip().lower()
    want_jev = env_decider == "jev" or (not env_decider and cfg_decider == "jev")

    if want_jev and (os.environ.get("PIPELINE_KIT_MODEL_DECIDER") or "").strip().lower() == "jev":
        via = _try_orchestrator_decide(
            project,
            step=step,
            workflow=workflow,
            change_class=change_class,
            user_request=user_request,
            pin=agent_pin,
            catalog=catalog,
        )
        if via is not None:
            via.setdefault("apply", "advisory")
            via["runtime"] = "kit"
            via["step"] = step
            via["workflow"] = workflow
            via["change_class"] = change_class or None
            return via

    # Always-safe path: fixed pins / fallback (same config keys as orchestrator).
    decision = _fixed_decision(step=step, catalog=catalog, block=block, pin=agent_pin)
    decision["runtime"] = "kit"
    decision["step"] = step
    decision["workflow"] = workflow
    decision["change_class"] = change_class or None
    decision["note"] = (
        "Kit records this model for agent-CLI Task spawn when the CLI supports "
        "a model field. IDE chat does not enforce it. Use pipeline-kit run "
        "(orchestrator) for enforced model routing."
    )
    return decision


def write_routing(project: Path, slug: str, decision: dict[str, Any]) -> str | None:
    """Persist last decision under features/{slug}/model-routing.json."""
    safe = slug.strip().strip("/")
    if not safe or ".." in safe.split("/"):
        return None
    root = project / "features" / safe
    root.mkdir(parents=True, exist_ok=True)
    path = root / "model-routing.json"
    history: list[Any] = []
    if path.is_file():
        try:
            prior = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(prior, dict) and isinstance(prior.get("history"), list):
                history = list(prior["history"])
            elif isinstance(prior, list):
                history = prior
        except (OSError, json.JSONDecodeError):
            history = []
    history.append(decision)
    # Keep the file bounded.
    history = history[-50:]
    payload = {"latest": decision, "history": history}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return f"features/{safe}/model-routing.json".replace("\\", "/")
