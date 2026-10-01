"""Advance an orchestrator run. Async so waves can fan out."""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Any

from pipeline_orchestrator import EXIT_GATE, EXIT_OK, EXIT_STARTUP, EXIT_STEP
from pipeline_orchestrator.context import compose_prompt
from pipeline_orchestrator.deciders.base import Decision, DecisionError, DecisionRequest, ModelDecider, job_for
from pipeline_orchestrator.deciders.factory import make_decider
from pipeline_orchestrator.events import emit
from pipeline_orchestrator.graph import AgentStep, LayerFan, Node, SignoffGate, WaveFan, WorkflowSpec
from pipeline_orchestrator.runners.base import AgentRunner, StepRequest, StepResult
from pipeline_orchestrator.state import (
    load_run,
    new_run,
    node_id,
    save_run,
    signoff_path,
    utc_now,
)
from pipeline_orchestrator.verify import is_critic_reject, is_ok, step_advanced


def parse_children(project: Path, slug: str) -> list[str]:
    from pipeline_orchestrator.state import feature_dir

    path = feature_dir(project, slug) / "spec-order.md"
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.lower().startswith("**children:**"):
            raw = line.split(":", 1)[1]
            return [part.strip() for part in raw.replace("*", "").split(",") if part.strip()]
    return []


def _approved(project: Path, slug: str, gate: str, run: dict[str, Any]) -> bool:
    row = (run.get("gates") or {}).get(gate) or {}
    if str(row.get("status") or "") == "approved":
        return True
    path = signoff_path(project, slug, gate)
    if path.is_file() and "SIGNOFF: approved" in path.read_text(encoding="utf-8"):
        row["status"] = "approved"
        return True
    return False


def _previous_agent(chain: list[Node], index: int) -> AgentStep | None:
    for node in reversed(chain[:index]):
        if isinstance(node, AgentStep):
            return node
    return None


def _model_rejected(error: str) -> bool:
    text = (error or "").lower()
    if "model" not in text:
        return False
    return any(
        token in text
        for token in ("invalid", "unknown", "not found", "unsupported", "unavailable", "rejected", "not available")
    )


def _load_catalog(runner: AgentRunner, run: dict[str, Any]) -> tuple[list[str], dict[str, dict]]:
    cached = run.get("model_catalog")
    cached_info = run.get("model_info")
    if isinstance(cached, list) and cached and isinstance(cached_info, dict):
        ids = [str(item).strip() for item in cached if str(item).strip()]
        info = {str(key): value for key, value in cached_info.items() if isinstance(value, dict)}
        return ids, info
    listed = runner.list_models()
    ids = [str(item).strip() for item in listed if str(item).strip()]
    raw = getattr(runner, "model_info", None)
    info: dict[str, dict] = {}
    if callable(raw):
        loaded = raw()
        if isinstance(loaded, dict):
            info = {str(key): value for key, value in loaded.items() if isinstance(value, dict)}
    run["model_catalog"] = ids
    run["model_info"] = info
    return ids, info


async def _run_agent(
    *,
    project: Path,
    spec: WorkflowSpec,
    run: dict[str, Any],
    step: AgentStep,
    runner: AgentRunner,
    decider: ModelDecider,
    catalog: list[str],
    model_info: dict[str, dict] | None = None,
    extra: dict[str, str] | None = None,
    spec_dir: Path | None = None,
) -> tuple[int | None, StepResult | None]:
    slug = run["slug"]
    extra = dict(extra or {})
    extra.setdefault("USER_REQUEST", str(run.get("user_request") or "").strip())
    emit(
        project,
        "step_start",
        slug=slug,
        step=step.id,
        workflow=spec.name,
        workflow_provider=spec.provider,
    )
    started = utc_now()
    try:
        prompt, digest = compose_prompt(
            step=step,
            workflow=spec.name,
            change_class=str(run["change_class"]),
            slug=slug,
            project=project,
            extra=extra,
            spec_dir=spec_dir,
        )
    except (FileNotFoundError, ValueError) as exc:
        run["status"] = "error"
        run["exit_hint"] = EXIT_STARTUP
        save_run(project, run)
        emit(project, "step_end", slug=slug, step=step.id, error=str(exc))
        print(str(exc))
        return EXIT_STARTUP, None
    prior = ""
    if step.prior_agent:
        prior = str(((run.get("steps") or {}).get(step.prior_agent) or {}).get("handoff_status") or "")
    try:
        decision = decider.decide(
            DecisionRequest(
                step_id=step.id,
                job=job_for(step.id),
                user_request=str(run.get("user_request") or ""),
                workflow=spec.name,
                change_class=str(run.get("change_class") or ""),
                prior_status=prior,
                catalog=tuple(catalog),
                pin=step.model,
                model_info=dict(model_info or {}),
            )
        )
    except DecisionError as exc:
        run["status"] = "error"
        run["exit_hint"] = EXIT_STEP
        save_run(project, run)
        emit(project, "step_end", slug=slug, step=step.id, error=str(exc))
        print(str(exc))
        return EXIT_STEP, None
    row = run["steps"].setdefault(step.id, {})
    row["routing"] = decision.to_routing()
    print(decision.format(step.id))
    result, attempts = await _execute(runner, prompt, step, slug, project, extra or {}, decision)
    row["attempts"] = int(row.get("attempts") or 0) + attempts
    row["agent_id"] = result.agent_id
    row["run_id"] = result.run_id
    row["model"] = result.model or decision.model
    row["context_digest"] = digest
    routing = row.get("routing")
    if isinstance(routing, dict) and result.model and result.model != decision.model:
        routing["fallback"] = result.model
        routing["cursor_rejected"] = decision.model
        print(
            "model step=%s chosen=%s reason=cursor_rejected decider=%s"
            % (step.id, result.model, decision.decider)
        )
    if result.startup_failure:
        run["status"] = "error"
        run["exit_hint"] = EXIT_STARTUP
        save_run(project, run)
        emit(project, "step_end", slug=slug, step=step.id, error=result.error, startup=True)
        print(result.error or "startup failure")
        return EXIT_STARTUP, result
    if not result.ok:
        run["status"] = "error"
        run["exit_hint"] = EXIT_STEP
        save_run(project, run)
        emit(project, "step_end", slug=slug, step=step.id, error=result.error)
        print(result.error or "step failed")
        return EXIT_STEP, result
    try:
        checked = step_advanced(project=project, slug=slug, agent=step.id, started_at=started)
    except ValueError as exc:
        run["status"] = "error"
        run["exit_hint"] = EXIT_STEP
        save_run(project, run)
        emit(project, "step_end", slug=slug, step=step.id, error=str(exc))
        print(str(exc))
        return EXIT_STEP, result
    row["status"] = "completed"
    row["handoff_status"] = checked["status"]
    row["finished_at"] = utc_now()
    emit(
        project,
        "step_end",
        slug=slug,
        step=step.id,
        handoff_status=checked["status"],
        agent_id=result.agent_id,
        run_id=result.run_id,
        tokens=result.tokens,
    )
    save_run(project, run)
    return None, result


def _load_retry_cap(project: Path, run: dict[str, Any]) -> int:
    import json

    cap = int(run.get("retry_cap") or 2)
    cfg = project / ".pipeline" / "config.json"
    if cfg.is_file():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
            gates = data.get("gates") if isinstance(data, dict) else None
            if isinstance(gates, dict) and gates.get("retry_cap") is not None:
                cap = int(gates["retry_cap"])
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass
    run["retry_cap"] = cap
    return cap


async def _execute(
    runner: AgentRunner,
    prompt: str,
    step: AgentStep,
    slug: str,
    project: Path,
    extra: dict[str, str],
    decision: Decision,
) -> tuple[StepResult, int]:
    request = StepRequest(
        prompt=prompt,
        step_id=step.id,
        slug=slug,
        project=project,
        model=decision.model,
        mcp=step.mcp,
        extra=extra,
    )
    result = await runner.run(request)
    if (
        not result.ok
        and not result.startup_failure
        and _model_rejected(result.error)
        and decision.fallback
        and decision.fallback != decision.model
    ):
        request = StepRequest(
            prompt=prompt,
            step_id=step.id,
            slug=slug,
            project=project,
            model=decision.fallback,
            mcp=step.mcp,
            extra=extra,
        )
        return await runner.run(request), 2
    return result, 1


async def advance(
    *,
    project: Path,
    spec: WorkflowSpec,
    run: dict[str, Any],
    runner: AgentRunner,
    spec_dir: Path | None = None,
    decider: ModelDecider | None = None,
) -> int:
    chain = spec.chain_for(str(run["change_class"]))
    ids = [node_id(n) for n in chain]
    run["node_ids"] = ids
    cap = _load_retry_cap(project, run)
    index = 0
    current = run.get("current_node")
    if current in ids:
        index = ids.index(current)
    emit(
        project,
        "run_start",
        slug=run["slug"],
        workflow=spec.name,
        kit_version=run.get("kit_version"),
        runner=run.get("runner"),
        workflow_provider=spec.provider,
    )
    if not chain:
        run["status"] = "completed"
        run["current_node"] = None
        run["exit_hint"] = EXIT_OK
        save_run(project, run)
        return EXIT_OK

    if decider is None:
        try:
            decider = make_decider(project)
        except ValueError as exc:
            run["status"] = "error"
            run["exit_hint"] = EXIT_STARTUP
            save_run(project, run)
            print(str(exc))
            return EXIT_STARTUP
    try:
        catalog, model_info = _load_catalog(runner, run)
    except Exception as exc:
        run["status"] = "error"
        run["exit_hint"] = EXIT_STARTUP
        save_run(project, run)
        print(str(exc))
        return EXIT_STARTUP
    if not catalog:
        run["status"] = "error"
        run["exit_hint"] = EXIT_STARTUP
        save_run(project, run)
        print("model catalog is empty")
        return EXIT_STARTUP
    save_run(project, run)

    while index < len(chain):
        node = chain[index]
        run["current_node"] = node_id(node)
        run["status"] = "running"
        save_run(project, run)

        if isinstance(node, SignoffGate):
            if _approved(project, run["slug"], node.id, run):
                run["gates"][node.id]["status"] = "approved"
                index += 1
                continue
            run["status"] = "awaiting_approval"
            run["exit_hint"] = EXIT_GATE
            save_run(project, run)
            emit(project, "gate_wait", slug=run["slug"], gate=node.id)
            print(f"awaiting approval: gate={node.id} slug={run['slug']}")
            print(f"  pipeline-kit approve --slug {run['slug']} --gate {node.id}")
            print(f"  pipeline-kit resume --slug {run['slug']}")
            return EXIT_GATE

        if isinstance(node, WaveFan):
            children = parse_children(project, run["slug"]) or [""]
            for child in children:
                child_slug = f"{run['slug']}/{child}" if child else run["slug"]
                for step_id in node.child_chain:
                    step = AgentStep(
                        id=step_id,
                        context_from=step_id,
                        prior_agent=None,
                    )
                    code, _ = await _run_agent(
                        project=project,
                        spec=spec,
                        run=run,
                        step=step,
                        runner=runner,
                        decider=decider,
                        catalog=catalog,
                        model_info=model_info,
                        extra={"FEATURE_SLUG": child_slug, "CHILD": child or run["slug"]},
                        spec_dir=spec_dir,
                    )
                    if code is not None:
                        return code
            index += 1
            continue

        if isinstance(node, LayerFan):
            async def one_layer(layer: str) -> int | None:
                step = AgentStep(id=f"tester-agent-{layer}", context_from="tester-agent")
                code, _ = await _run_agent(
                    project=project,
                    spec=spec,
                    run=run,
                    step=step,
                    runner=runner,
                    decider=decider,
                    catalog=catalog,
                    model_info=model_info,
                    extra={"TEST_LAYER": layer},
                    spec_dir=spec_dir,
                )
                return code

            codes = await asyncio.gather(*(one_layer(layer) for layer in node.layers))
            for code in codes:
                if code is not None:
                    return code
            joined = AgentStep(id="tester-agent", context_from="tester-agent")
            # join row for later prior_agent pointers
            run["steps"].setdefault("tester-agent", {})["status"] = "completed"
            run["steps"]["tester-agent"]["handoff_status"] = "SUCCESS"
            run["steps"]["tester-agent"]["finished_at"] = utc_now()
            save_run(project, run)
            index += 1
            continue

        if isinstance(node, AgentStep):
            code, _ = await _run_agent(
                project=project,
                spec=spec,
                run=run,
                step=node,
                runner=runner,
                decider=decider,
                catalog=catalog,
                model_info=model_info,
                spec_dir=spec_dir,
            )
            if code is not None:
                return code
            status = str((run["steps"].get(node.id) or {}).get("handoff_status") or "")
            if node.critic and is_critic_reject(status):
                prev = _previous_agent(chain, index)
                key = node.id
                used = int((run.get("retries") or {}).get(key) or 0)
                if prev is None or used >= cap:
                    run["status"] = "error"
                    run["exit_hint"] = EXIT_STEP
                    save_run(project, run)
                    emit(project, "retry", slug=run["slug"], step=node.id, exhausted=True)
                    return EXIT_STEP
                run.setdefault("retries", {})[key] = used + 1
                emit(project, "retry", slug=run["slug"], step=prev.id, attempt=used + 1)
                run["steps"][prev.id]["status"] = "pending"
                run["current_node"] = prev.id
                save_run(project, run)
                index = ids.index(prev.id)
                continue
            if status.lower() == "blocked":
                run["status"] = "blocked"
                run["exit_hint"] = EXIT_STEP
                save_run(project, run)
                print(f"blocked: step={node.id} slug={run['slug']}")
                art = run.get("artifact_dir") or f"features/{run['slug']}"
                print(f"  see {art}/questions.md and HANDOFF-*.md")
                print(
                    f"  update {art}/request.md then: "
                    f"pipeline-kit resume --slug {run['slug']}"
                )
                return EXIT_STEP
            if not is_ok(status) and status.lower() not in {"success", "assumptions_used"}:
                # still advance if SUCCESS-like; otherwise fail closed
                if status and not is_ok(status):
                    run["status"] = "error"
                    run["exit_hint"] = EXIT_STEP
                    save_run(project, run)
                    return EXIT_STEP
            index += 1
            continue

        index += 1

    run["status"] = "completed"
    run["current_node"] = None
    run["exit_hint"] = EXIT_OK
    save_run(project, run)
    print(f"PIPELINE_COMPLETE slug={run['slug']}")
    return EXIT_OK


def start_run(
    *,
    project: Path,
    spec: WorkflowSpec,
    slug: str,
    change_class: str,
    runner_name: str,
    kit_version: str,
    user_request: str = "",
) -> dict[str, Any]:
    chain = spec.chain_for(change_class)
    return new_run(
        project=project,
        spec=spec,
        slug=slug,
        change_class=change_class,
        runner=runner_name,
        kit_version=kit_version,
        chain=chain,
        user_request=user_request,
    )
