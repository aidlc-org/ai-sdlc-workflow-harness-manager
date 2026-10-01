"""Incremental ledger export. Offset commits only after a successful ship."""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from pipeline_observability.adapters.base import AdapterConfig
from pipeline_observability.adapters.datadog import DatadogAdapter
from pipeline_observability.adapters.langfuse import LangfuseAdapter, otel_attributes
from pipeline_observability.adapters.otlp import OtlpAdapter
from pipeline_observability.normalize import load_ledger, parse_transcript
from pipeline_observability.pricing import is_placeholder_model, observation_usage_attrs
from pipeline_observability.scoring import TOOL_EVENTS, score_events

SCORE_NAMES = (
    "tool_calls_total",
    "tool_calls_legitimate",
    "waste_ratio",
    "wrong_tool_count",
    "out_of_contract_count",
    "read_amplification",
    "search_thrash",
    "edit_churn",
    "discovery_ratio",
    "retry_ratio",
    "denied_count",
    "verify_coverage",
    "integrity_pass",
    "allowlist_unused_count",
    "context_peak_percent",
)

# Run-level Starter 7 scores (roadmap/eval-harness-langfuse.md). Additive: never
# reuse or repurpose a SCORE_NAMES entry. Attached to the root observation.
RUN_SCORE_NAMES = (
    "task_complete",
    "hitl_count",
    "hitl_wait_s",
    "critic_retry_count",
    "secret_leak_count",
)
STEP_SUCCESS_SCORE = "step_success"

# Same pattern as kit/pipeline/hooks/obs/obs_lib.py (hooks are not importable here).
SECRET_RE = re.compile(
    r"(?i)((?:sk-lf-|sk-|pk-lf-|ghp_|github_pat_|xox[baprs]-|AKIA)"
    r"[A-Za-z0-9_\-]{8,}|Bearer\s+[A-Za-z0-9._\-]{8,})"
)
VERDICT_RE = re.compile(r"\b(approve-with-nits|changes-required|approve)\b", re.I)
HANDOFF_SUCCESS_RE = re.compile(r"\bSUCCESS\b", re.I)

UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
EVENT_TYPES = {
    "sessionStart",
    "sessionEnd",
    "beforeSubmitPrompt",
    "preCompact",
    "stop",
    "SessionStart",
    "SessionEnd",
    "Stop",
}
MAX_IO = 4000


def load_dotenv(repo: Path) -> None:
    path = repo / ".env"
    if not path.is_file():
        return
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            if key and not os.environ.get(key):
                os.environ[key] = value
    except OSError:
        return


def load_obs_config(repo: Path) -> dict[str, Any]:
    path = repo / ".pipeline" / "config.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    block = data.get("agent_observability") if isinstance(data, dict) else {}
    return block if isinstance(block, dict) else {}


def _parse_ts(value: Any) -> int:
    if not isinstance(value, str) or not value:
        return int(datetime.now(timezone.utc).timestamp() * 1_000_000_000)
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return int(stamp.timestamp() * 1_000_000_000)
    except ValueError:
        return int(datetime.now(timezone.utc).timestamp() * 1_000_000_000)


def _iso(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return value.replace("Z", "+00:00") if value.endswith("Z") else value


def otel32(value: str | None) -> str:
    raw = (value or "unknown").strip()
    hexed = re.sub(r"[^0-9a-fA-F]", "", raw).lower()
    if len(hexed) >= 32:
        return hexed[:32]
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def otel16(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def session_id(conversation: str | None) -> str:
    raw = (conversation or "unknown").strip()
    return raw if UUID_RE.match(raw) else raw


def distinct_generation(conversation: str | None, generation: str | None) -> bool:
    if not generation:
        return False
    return otel32(generation) != otel32(conversation)


def _clip(value: Any, limit: int = MAX_IO) -> str | None:
    if value is None:
        return None
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    if len(text) > limit:
        return text[:limit] + f"...[truncated {len(text) - limit} chars]"
    return text


def _span(
    *,
    trace_id: str,
    span_id: str,
    name: str,
    start: int,
    end: int,
    parent: str | None,
    attrs: dict[str, Any],
) -> dict[str, Any]:
    if end < start:
        end = start + 1_000_000
    body: dict[str, Any] = {
        "traceId": trace_id,
        "spanId": span_id,
        "name": name,
        "kind": 1,
        "startTimeUnixNano": str(start),
        "endTimeUnixNano": str(end),
        "attributes": otel_attributes(attrs),
    }
    if parent:
        body["parentSpanId"] = parent
    return body


def _common(
    *,
    session: str,
    user: str | None,
    name: str,
    tags: list[str],
    slug: str | None,
    workflow: str | None,
    extra: dict[str, Any] | None = None,
    kit_version: str | None = None,
) -> dict[str, Any]:
    attrs: dict[str, Any] = {
        "langfuse.session.id": session,
        "langfuse.trace.name": name,
        "langfuse.trace.tags": tags,
        "langfuse.trace.metadata.slug": slug,
        "langfuse.trace.metadata.workflow": workflow,
        "pipeline.kit_version": kit_version,
        "langfuse.trace.metadata.kit_version": kit_version,
    }
    if user:
        attrs["langfuse.user.id"] = user
        attrs["user.id"] = user
    if extra:
        attrs.update(extra)
    return attrs


def _first(events: list[dict[str, Any]], key: str) -> Any:
    for item in events:
        value = item.get(key)
        if value not in (None, "", []):
            return value
    return None


def _last(events: list[dict[str, Any]], key: str) -> Any:
    for item in reversed(events):
        value = item.get(key)
        if value not in (None, "", []):
            return value
    return None


USAGE_EVENTS = frozenset(
    {"afterAgentResponse", "AfterAgentResponse", "stop", "Stop", "agentStop"}
)


def _generation_model(group: list[dict[str, Any]]) -> str | None:
    last_any: str | None = None
    last_real: str | None = None
    for item in group:
        pair: list[str] = []
        for key in ("model_id", "model"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                pair.append(value.strip())
        if not pair:
            continue
        last_any = pair[0]
        for stripped in pair:
            if not is_placeholder_model(stripped):
                last_real = stripped
                break
    return last_real or last_any


def _token_int(tokens: Any, key: str) -> int:
    if not isinstance(tokens, dict):
        return 0
    value = tokens.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return max(0, int(value))


def _obs_prices(repo: Path | None) -> Mapping[str, Any] | None:
    if repo is None:
        return None
    raw = load_obs_config(repo).get("model_prices")
    return raw if isinstance(raw, dict) else None


def _generation_usage(
    group: list[dict[str, Any]],
    *,
    model: str | None = None,
    prices: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Langfuse usage_details (exclusive buckets) plus priced cost_details when known."""
    input_tokens = 0
    output_tokens = 0
    cache_read = 0
    cache_write = 0
    found = False
    for item in group:
        if item.get("event") not in USAGE_EVENTS:
            continue
        tokens = item.get("tokens")
        if not isinstance(tokens, dict) or not tokens:
            continue
        found = True
        input_tokens = max(input_tokens, _token_int(tokens, "input_tokens"))
        output_tokens = max(output_tokens, _token_int(tokens, "output_tokens"))
        cache_read = max(cache_read, _token_int(tokens, "cache_read_tokens"))
        cache_write = max(cache_write, _token_int(tokens, "cache_write_tokens"))
    if not found:
        return {}
    return observation_usage_attrs(
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read=cache_read,
        cache_write=cache_write,
        prices=prices,
    )


def _tool_obs_type(event: dict[str, Any]) -> str:
    if event.get("tool_kind") in {"read", "search"}:
        return "retriever"
    return "tool"


def _tool_io(event: dict[str, Any]) -> tuple[str | None, str | None]:
    incoming = event.get("tool_input") or event.get("command") or event.get("target_path") or event.get("pattern")
    outgoing = event.get("tool_output")
    return _clip(incoming), _clip(outgoing)


def _user_prompt(events: list[dict[str, Any]]) -> str | None:
    for item in events:
        if item.get("event") == "beforeSubmitPrompt":
            text = item.get("prompt") or item.get("text")
            if isinstance(text, str) and text.strip():
                return text.strip()
    path = _last(events, "transcript_path")
    user, _assistant = parse_transcript(path if isinstance(path, str) else None)
    return user


def _assistant_output(events: list[dict[str, Any]]) -> str | None:
    for item in reversed(events):
        if item.get("event") == "afterAgentResponse":
            text = item.get("text") or item.get("prompt")
            if isinstance(text, str) and text.strip():
                return text.strip()
    for item in reversed(events):
        if item.get("event") in {"stop", "Stop"} and item.get("status"):
            return str(item.get("status"))
    path = _last(events, "transcript_path")
    _user, assistant = parse_transcript(path if isinstance(path, str) else None)
    return assistant


def _parent_for_tool(event: dict[str, Any], *, root: str, gens: dict[str, str], agents: dict[str, str], conv: str) -> str:
    sid = event.get("subagent_id")
    if isinstance(sid, str) and sid in agents:
        return agents[sid]
    gid = event.get("generation_id")
    if distinct_generation(conv, gid if isinstance(gid, str) else None) and gid in gens:
        return gens[str(gid)]
    return root


def _pack_id() -> str:
    return os.environ.get("PIPELINE_EVAL_PACK_ID") or "pipeline-kit"


def _marker_version(path: Path) -> str | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    value = data.get("version")
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return None


def kit_version(repo: Path | None) -> str:
    """Installed pipeline-kit version for traces. Fail-open; never raise."""
    env = os.environ.get("PIPELINE_KIT_VERSION", "").strip()
    if env:
        return env
    if repo is not None:
        for rel in (
            Path(".pipeline") / "install.json",
            Path(".pipeline") / "state" / "obs" / "install.json",
        ):
            found = _marker_version(repo / rel)
            if found:
                return found
    return "unknown"


def _read_text(path: Path, limit: int = 200_000) -> str:
    try:
        if not path.is_file() or path.stat().st_size > limit:
            return ""
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _feature_root(repo: Path, slug: str) -> Path:
    try:
        from pipeline_kit.paths import feature_dir as _fd

        return _fd(repo, str(slug))
    except Exception:
        return repo / "features" / str(slug)


def _handoff_file(repo: Path | None, slug: str | None, step: str | None) -> Path | None:
    if repo is None or not slug:
        return None
    root = _feature_root(repo, str(slug))
    if not root.is_dir():
        return None
    try:
        files = sorted(set(root.glob("HANDOFF*.md")) | set(root.glob("**/HANDOFF*.md")))
    except OSError:
        return None
    if step:
        short = str(step).replace("-agent", "").lower()
        preferred = [item for item in files if short in item.name.lower()]
        files = preferred or files
    return files[-1] if files else None


def _step_eval(repo: Path | None, slug: str | None, step: str | None) -> dict[str, Any]:
    """HANDOFF clip + SUCCESS flag + critic verdict for one step. Fail-open."""
    out: dict[str, Any] = {"handoff": None, "success": None, "verdict": None}
    path = _handoff_file(repo, slug, step)
    if path is None:
        return out
    text = _read_text(path)
    if not text:
        return out
    out["success"] = bool(HANDOFF_SUCCESS_RE.search(text))
    match = VERDICT_RE.search(text)
    if match:
        out["verdict"] = match.group(1).lower()
    out["handoff"] = _clip(text[-1200:], 1500)
    return out


def _skill_names(allowed: Any) -> list[str]:
    """Skill folder names from a step's allowed_reads (SKILL.md paths). No fake spans."""
    names: list[str] = []
    if not isinstance(allowed, list):
        return names
    for item in allowed:
        text = str(item).replace("\\", "/")
        if "/skills/" in text or text.startswith("skills/"):
            tail = text.split("skills/", 1)[1]
            name = tail.split("/", 1)[0]
            if name and name not in names:
                names.append(name)
    return names


def _workflow_chain(repo: Path | None, workflow: str | None, change: str | None) -> list[str]:
    """Expected agent steps from .pipeline/config.json (chain or classes). Gates (@…) excluded."""
    if repo is None or not workflow:
        return []
    try:
        data = json.loads((repo / ".pipeline" / "config.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    flows = data.get("workflows") if isinstance(data, dict) else None
    block = flows.get(str(workflow)) if isinstance(flows, dict) else None
    if not isinstance(block, dict):
        return []
    chain = block.get("chain")
    if not (isinstance(chain, list) and chain):
        classes = block.get("classes")
        chain = classes.get(str(change)) if isinstance(classes, dict) and change else None
    if not isinstance(chain, list):
        return []
    return [str(item) for item in chain if isinstance(item, str) and not str(item).startswith("@")]


def _deploy_health(repo: Path | None, slug: str | None) -> bool | None:
    if repo is None or not slug:
        return None
    text = _read_text(_feature_root(repo, str(slug)) / "deploy-result.env")
    if not text:
        return None
    return "OVERALL=passed" in text


def _secret_leak_count(repo: Path | None, slug: str | None) -> int | None:
    """SECRET_RE hits across features/{slug} artifacts. None = N/A (no artifacts)."""
    if repo is None or not slug:
        return None
    root = _feature_root(repo, str(slug))
    if not root.is_dir():
        return None
    count = 0
    try:
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.suffix.lower() in {".md", ".env", ".txt", ".json"}:
                count += len(SECRET_RE.findall(_read_text(path, limit=512_000)))
    except OSError:
        return count
    return count


def _hitl_metrics(events: list[dict[str, Any]]) -> tuple[int, float]:
    """Extra user prompts after the first = HITL touches; wait = gap since prior event."""
    count = 0
    wait_s = 0.0
    prev_ts: int | None = None
    seen_first = False
    for item in events:
        ts = _parse_ts(item.get("ts"))
        if item.get("event") == "beforeSubmitPrompt":
            if seen_first:
                count += 1
                if prev_ts is not None and ts > prev_ts:
                    wait_s += (ts - prev_ts) / 1_000_000_000
            seen_first = True
        prev_ts = ts
    return count, round(wait_s, 1)


def _critic_retry_count(events: list[dict[str, Any]]) -> int:
    """Same-step re-spawns (distinct subagent ids − 1) on non-critic steps."""
    subs: dict[str, set[str]] = defaultdict(set)
    for item in events:
        sid = item.get("subagent_id")
        step = item.get("step")
        if isinstance(sid, str) and sid and isinstance(step, str) and step:
            subs[step].add(sid)
    return sum(max(0, len(ids) - 1) for step, ids in subs.items() if "critic" not in step)


def build_conversation_spans(
    events: list[dict[str, Any]],
    steps: list[dict[str, Any]],
    repo: Path | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    scores: list[dict[str, Any]] = []
    meta: dict[str, Any] = {}
    if not events:
        return spans, scores, meta
    conv = str(_first(events, "conversation_id") or _first(events, "session_id") or "unknown")
    trace_id = otel32(conv)
    session = session_id(conv)
    root = otel16(f"root:{conv}")
    user = _first(events, "user_email")
    slug = _last(events, "slug")
    workflow = _first(events, "workflow") or _last(events, "workflow")
    harness = str(_first(events, "harness") or "cursor")
    change = None
    for step in steps:
        if step.get("slug") == slug and step.get("change_class"):
            change = step.get("change_class")
            break
    tags = [harness]
    if workflow:
        tags.append(str(workflow))
    if change:
        tags.append(str(change))
    mode = _first(events, "composer_mode")
    if mode:
        tags.append(str(mode))
    tags.append("agent")
    steps_ran = sorted({str(item.get("step")) for item in events if item.get("step")})
    for step_tag in steps_ran:
        if step_tag not in tags:
            tags.append(step_tag)
    tags.append(f"pack_id={_pack_id()}")
    kit_ver = kit_version(repo)
    if kit_ver:
        tags.append(f"kit_version={kit_ver}")
    prices = _obs_prices(repo)
    # Session groups the parent chat + Task traces of one pipeline run. Trace id unchanged.
    if workflow and slug:
        session = f"{workflow}:{slug}"
    expected_steps = _workflow_chain(repo, str(workflow) if workflow else None, str(change) if change else None)
    name = f"{workflow}:{slug}" if workflow and slug else (str(slug) if slug else conv[:12])
    prompt = _user_prompt(events)
    output = _assistant_output(events)
    start = _parse_ts(events[0].get("ts"))
    end = _parse_ts(events[-1].get("ts"))
    root_extra = {
        "langfuse.observation.type": "agent",
        "langfuse.observation.input": prompt,
        "langfuse.observation.output": output,
        "langfuse.trace.input": prompt,
        "langfuse.trace.output": output,
        "pipeline.slug": slug,
        "pipeline.workflow": workflow,
        "pipeline.pack_id": _pack_id(),
        "pipeline.kit_version": kit_ver,
        "langfuse.trace.metadata.pack_id": _pack_id(),
        "langfuse.trace.metadata.kit_version": kit_ver,
        "langfuse.trace.metadata.steps_ran": steps_ran or None,
        "langfuse.trace.metadata.steps_expected": expected_steps or None,
    }
    spans.append(
        _span(
            trace_id=trace_id,
            span_id=root,
            name=name,
            start=start,
            end=end,
            parent=None,
            attrs=_common(
                session=session,
                user=user,
                name=name,
                tags=tags,
                slug=slug,
                workflow=workflow,
                extra=root_extra,
                kit_version=kit_ver,
            ),
        )
    )
    gens: dict[str, str] = {}
    by_gen: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in events:
        gid = item.get("generation_id")
        if distinct_generation(conv, gid if isinstance(gid, str) else None):
            by_gen[str(gid)].append(item)
    for gid, group in by_gen.items():
        span_id = otel16(f"gen:{gid}")
        gens[gid] = span_id
        g_start = _parse_ts(group[0].get("ts"))
        g_end = _parse_ts(group[-1].get("ts"))
        first_tool = next((row for row in group if row.get("event") in TOOL_EVENTS), None)
        model = _generation_model(group)
        params = _last(group, "model_params")
        extra = {
            "langfuse.observation.type": "generation",
            "langfuse.observation.metadata.cursor_generation_id": gid,
            "langfuse.observation.model.name": model,
            "gen_ai.request.model": model,
            "langfuse.observation.input": prompt,
            "langfuse.observation.output": output if not any(g.get("subagent_id") for g in group) else None,
            "langfuse.observation.completion_start_time": _iso(first_tool.get("ts") if first_tool else None),
            "langfuse.observation.model.parameters": json.dumps(params) if params else None,
            "pipeline.slug": slug,
            "pipeline.kit_version": kit_ver,
        }
        prices = _obs_prices(repo)
        extra.update(_generation_usage(group, model=model, prices=prices))
        if first_tool and first_tool.get("ts") and group[0].get("ts"):
            extra["pipeline.score.time_to_first_tool_ms"] = max(
                0, int((_parse_ts(first_tool.get("ts")) - g_start) / 1_000_000)
            )
        spans.append(
            _span(
                trace_id=trace_id,
                span_id=span_id,
                name=f"generation {model or gid[:8]}",
                start=g_start,
                end=g_end,
                parent=root,
                attrs=_common(session=session, user=user, name=name, tags=tags, slug=slug, workflow=workflow, extra=extra, kit_version=kit_ver),
            )
        )
    agents: dict[str, str] = {}
    by_agent: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in events:
        sid = item.get("subagent_id")
        if isinstance(sid, str) and sid:
            by_agent[sid].append(item)
    for sid, group in by_agent.items():
        span_id = otel16(f"agent:{sid}")
        agents[sid] = span_id
        a_start = _parse_ts(group[0].get("ts"))
        a_end = _parse_ts(group[-1].get("ts"))
        step_name = str(_first(group, "step") or _first(group, "subagent_type") or "subagent")
        step_slug = _first(group, "slug") or slug
        step_eval = _step_eval(repo, str(step_slug) if step_slug else None, step_name)
        status = _last(group, "status")
        # Judges only see this observation's I/O: attach the HANDOFF clip here.
        # No artifacts on disk -> output stays the plain status (previous behavior).
        if step_eval["handoff"] or step_eval["verdict"]:
            step_output: Any = json.dumps(
                {
                    "status": status,
                    "handoff": step_eval["handoff"],
                    "critic_verdict": step_eval["verdict"],
                },
                ensure_ascii=False,
            )
        else:
            step_output = status
        skills = _skill_names(_first(group, "allowed_reads"))
        extra = {
            "langfuse.observation.type": "agent",
            "langfuse.observation.input": _clip(_first(group, "task"), 4000),
            "langfuse.observation.output": step_output,
            "pipeline.step": step_name,
            "pipeline.slug": step_slug,
            "pipeline.workflow": workflow,
            "pipeline.change_class": change,
            "pipeline.skills": skills or None,
            "langfuse.observation.metadata.subagent_id": sid,
            "langfuse.observation.metadata.subagent_name": step_name,
            "langfuse.observation.metadata.pipeline.skills": skills or None,
        }
        spans.append(
            _span(
                trace_id=trace_id,
                span_id=span_id,
                name=f"pipeline.step {step_name}",
                start=a_start,
                end=a_end,
                parent=root,
                attrs=_common(session=session, user=user, name=name, tags=tags, slug=slug, workflow=workflow, extra=extra, kit_version=kit_ver),
            )
        )
    for index, event in enumerate(events):
        ev_name = str(event.get("event") or "hook")
        start_ns = _parse_ts(event.get("ts"))
        duration = int(event.get("duration_ms") or 1) * 1_000_000
        end_ns = start_ns + max(duration, 1_000_000)
        shared = _common(
            session=session,
            user=user,
            name=name,
            tags=tags,
            slug=event.get("slug") or slug,
            workflow=event.get("workflow") or workflow,
            extra={"pipeline.step": event.get("step"), "pipeline.slug": event.get("slug") or slug},
            kit_version=kit_ver,
        )
        if ev_name in TOOL_EVENTS:
            tool_id = str(event.get("tool_use_id") or f"{conv}:{index}")
            incoming, outgoing = _tool_io(event)
            obs_type = _tool_obs_type(event)
            extra = {
                **shared,
                "langfuse.observation.type": obs_type,
                "langfuse.observation.input": incoming,
                "langfuse.observation.output": outgoing,
                "tool.name": event.get("tool_name"),
                "tool.kind": event.get("tool_kind"),
                "tool.verdict": event.get("verdict"),
                "tool.confidence": event.get("confidence"),
                "tool.path": event.get("target_path"),
            }
            if event.get("ok") is False:
                extra["langfuse.observation.level"] = "ERROR"
            spans.append(
                _span(
                    trace_id=trace_id,
                    span_id=otel16(f"tool:{tool_id}"),
                    name=f"{obs_type}: {event.get('tool_name') or ev_name}",
                    start=start_ns,
                    end=end_ns,
                    parent=_parent_for_tool(event, root=root, gens=gens, agents=agents, conv=conv),
                    attrs=extra,
                )
            )
            continue
        if ev_name in EVENT_TYPES:
            extra = {
                **shared,
                "langfuse.observation.type": "event",
                "langfuse.observation.input": _clip(event.get("prompt") or event.get("task")),
                "langfuse.observation.output": event.get("status") or _clip(event.get("text")),
            }
            if event.get("context_usage_percent") is not None:
                extra["langfuse.observation.metadata.context_peak_percent"] = event.get("context_usage_percent")
            if ev_name in {"stop", "Stop"} and event.get("status") == "aborted":
                extra["langfuse.observation.level"] = "WARNING"
            spans.append(
                _span(
                    trace_id=trace_id,
                    span_id=otel16(f"event:{conv}:{ev_name}:{event.get('ts')}"),
                    name=f"event {ev_name}",
                    start=start_ns,
                    end=end_ns,
                    parent=root,
                    attrs=extra,
                )
            )
    step_spans = {span["name"].replace("pipeline.step ", ""): span["spanId"] for span in spans if span["name"].startswith("pipeline.step ")}
    for step in steps:
        step_name = str(step.get("step") or "unattributed")
        obs_id = step_spans.get(step_name) or root
        for score_name in SCORE_NAMES:
            value = step.get(score_name)
            if value is None:
                continue
            scores.append(
                {
                    "id": otel32(f"{trace_id}:{step_name}:{score_name}"),
                    "traceId": trace_id,
                    "observationId": obs_id,
                    "name": score_name,
                    "value": float(value) if isinstance(value, (int, float)) else 0.0,
                    "dataType": "NUMERIC",
                    "comment": f"step={step_name} slug={step.get('slug')}",
                }
            )
    # Starter 7 (roadmap/eval-harness-langfuse.md). Fail-open + N/A != 0: scores are
    # only emitted when repo artifacts are addressable (slug known); never crash flush.
    step_success: dict[str, bool | None] = {}
    integrity_ok = True
    for step in steps:
        step_name = str(step.get("step") or "unattributed")
        raw_integrity = step.get("integrity_pass")
        if isinstance(raw_integrity, (int, float)) and float(raw_integrity) < 1.0:
            integrity_ok = False
        step_slug = step.get("slug") or slug
        if repo is None or not step_slug or step_name == "unattributed":
            continue
        success = _step_eval(repo, str(step_slug), step_name)["success"]
        step_success[step_name] = success
        scores.append(
            {
                "id": otel32(f"{trace_id}:{step_name}:{STEP_SUCCESS_SCORE}"),
                "traceId": trace_id,
                "observationId": step_spans.get(step_name) or root,
                "name": STEP_SUCCESS_SCORE,
                "value": 1.0 if success else 0.0,
                "dataType": "NUMERIC",
                "comment": f"step={step_name} slug={step_slug} handoff={'found' if success is not None else 'missing'}",
            }
        )
    if repo is not None and slug:
        aborted = any(
            item.get("event") in {"stop", "Stop"} and item.get("status") == "aborted" for item in events
        )
        check = list(expected_steps) or [name_ for name_ in step_success]
        complete: bool | None = None
        if check:
            complete = True
            for step_name in check:
                success = step_success.get(step_name)
                if success is None:
                    success = _step_eval(repo, str(slug), step_name)["success"]
                if success is not True:
                    complete = False
                    break
            if "devops-agent" in check or "devops-agent" in step_success:
                complete = complete and _deploy_health(repo, str(slug)) is True
            if aborted or not integrity_ok:
                complete = False
        hitl_count, hitl_wait = _hitl_metrics(events)
        leaks = _secret_leak_count(repo, str(slug))
        run_values: list[tuple[str, float | None, str]] = [
            ("task_complete", None if complete is None else (1.0 if complete else 0.0), "BOOLEAN"),
            ("hitl_count", float(hitl_count), "NUMERIC"),
            ("hitl_wait_s", float(hitl_wait), "NUMERIC"),
            ("critic_retry_count", float(_critic_retry_count(events)), "NUMERIC"),
            ("secret_leak_count", None if leaks is None else float(leaks), "NUMERIC"),
        ]
        run_comment = f"slug={slug} workflow={workflow} aborted={aborted}"
        for score_name, value, data_type in run_values:
            if value is None:
                continue  # N/A stays N/A, never 0
            scores.append(
                {
                    "id": otel32(f"{trace_id}:run:{score_name}"),
                    "traceId": trace_id,
                    "observationId": root,
                    "name": score_name,
                    "value": value,
                    "dataType": data_type,
                    "comment": run_comment,
                }
            )
    meta = {
        "trace_id": trace_id,
        "session_id": session,
        "slug": slug,
        "workflow": workflow,
        "change_class": change,
        "prompt": prompt,
        "output": output,
        "user": user,
        "name": name,
        "kit_version": kit_ver,
    }
    return spans, scores, meta


def build_otlp(report: dict[str, Any], adapter: LangfuseAdapter) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    del adapter
    events = list(report.get("events") or [])
    steps = list(report.get("steps") or [])
    repo_raw = report.get("repo")
    repo = Path(str(repo_raw)) if repo_raw else None
    kit_ver = kit_version(repo)
    if not events:
        for step in steps:
            events.extend(step.get("events") or [])
    by_conv: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in events:
        key = str(item.get("conversation_id") or item.get("session_id") or "unknown")
        by_conv[key].append(item)
    spans: list[dict[str, Any]] = []
    scores: list[dict[str, Any]] = []
    datasets: list[dict[str, Any]] = []
    for conv, group in by_conv.items():
        conv_steps = [step for step in steps if any(ev.get("conversation_id") == conv or (not ev.get("conversation_id") and conv == "unknown") for ev in (step.get("events") or [step]))]
        if not conv_steps:
            conv_steps = [
                step
                for step in steps
                if any(item.get("step") == step.get("step") for item in group)
            ] or steps
        part_spans, part_scores, meta = build_conversation_spans(group, conv_steps, repo=repo)
        spans.extend(part_spans)
        scores.extend(part_scores)
        if meta:
            datasets.append(meta)
    payload = {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": otel_attributes(
                        {
                            "service.name": "pipeline-kit-obs",
                            "service.version": kit_ver,
                            "pipeline.kit_version": kit_ver,
                        }
                    )
                },
                "scopeSpans": [{"scope": {"name": "pipeline-kit-obs", "version": kit_ver}, "spans": spans}],
            }
        ]
    }
    return payload, scores, datasets


def make_adapter(repo: Path, cfg: dict[str, Any]) -> Any:
    load_dotenv(repo)
    name = str(cfg.get("adapter") or "langfuse")
    host = (
        os.environ.get("LANGFUSE_BASE_URL")
        or os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
        or "https://cloud.langfuse.com"
    )
    config = AdapterConfig(
        name=name,
        host=host,
        public_key=os.environ.get("LANGFUSE_PUBLIC_KEY", ""),
        secret_key=os.environ.get("LANGFUSE_SECRET_KEY", ""),
        api_key=os.environ.get("DD_API_KEY") or "",
    )
    if name == "datadog":
        return DatadogAdapter(config)
    if name == "otlp":
        return OtlpAdapter(config)
    return LangfuseAdapter(config)


def _offset_path(repo: Path) -> Path:
    return repo / ".pipeline" / "state" / "obs" / "offset.json"


def read_offset(repo: Path) -> int:
    path = _offset_path(repo)
    if not path.is_file():
        return 0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    value = data.get("offset") if isinstance(data, dict) else 0
    return int(value) if isinstance(value, int) else 0


def write_offset(repo: Path, offset: int) -> None:
    path = _offset_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"offset": offset}, indent=2) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


def _ship_dataset(adapter: LangfuseAdapter, items: list[dict[str, Any]], cfg: dict[str, Any]) -> tuple[int, str | None]:
    name = str(cfg.get("dataset") or "pipeline-kit-agent-runs")
    ok, detail = adapter.ensure_dataset(name)
    if not ok:
        return 0, detail
    shipped = 0
    for meta in items:
        prompt = meta.get("prompt") or meta.get("slug") or "unknown"
        item_key = f"{meta.get('change_class') or 'na'}:{prompt}"
        item_id = otel32(item_key)
        ok, detail = adapter.upsert_dataset_item(
            {
                "id": item_id,
                "datasetName": name,
                "input": {
                    "prompt": meta.get("prompt"),
                    "slug": meta.get("slug"),
                    "change_class": meta.get("change_class"),
                    "workflow": meta.get("workflow"),
                },
                "expectedOutput": {"integrity_pass": 1},
                "metadata": {"source": "pipeline-kit-obs", "kit_version": meta.get("kit_version")},
                "sourceTraceId": meta.get("trace_id"),
            }
        )
        if not ok:
            return shipped, detail
        run_name = f"{meta.get('slug') or 'run'}:{str(meta.get('trace_id'))[:8]}"
        ok, detail = adapter.create_dataset_run_item(
            {
                "runName": run_name,
                "runDescription": str(meta.get("name") or ""),
                "datasetItemId": item_id,
                "traceId": meta.get("trace_id"),
            }
        )
        if not ok:
            return shipped, detail
        shipped += 1
    return shipped, None


def flush_project(repo: Path) -> dict[str, Any]:
    cfg = load_obs_config(repo)
    if cfg.get("enabled") is not True:
        return {"ok": True, "skipped": "disabled"}
    ledger = repo / ".pipeline" / "state" / "obs" / "events.jsonl"
    offset = read_offset(repo)
    rows, new_offset = load_ledger(ledger, offset=offset)
    if not rows:
        return {"ok": True, "skipped": "no new events", "offset": offset}
    report = score_events(repo, rows)
    adapter = make_adapter(repo, cfg)
    if not isinstance(adapter, LangfuseAdapter):
        # Stub adapters (datadog, otlp) skip cleanly; ledger and offset are retained
        # so a later switch to langfuse re-ships the same rows.
        return {
            "ok": True,
            "skipped": f"adapter {cfg.get('adapter')} not implemented; ledger retained",
            "offset": offset,
        }
    if not adapter.config.public_key or not adapter.config.secret_key:
        return {"ok": False, "error": "LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY missing"}
    payload, scores, datasets = build_otlp(report, adapter)
    ok, detail = adapter.post_traces(payload)
    if not ok:
        return {"ok": False, "error": detail, "offset": offset}
    ok, score_detail = adapter.post_scores(scores)
    if not ok:
        return {"ok": False, "error": score_detail, "offset": offset}
    dataset_count, dataset_error = _ship_dataset(adapter, datasets, cfg)
    write_offset(repo, new_offset)
    result: dict[str, Any] = {
        "ok": True,
        "events": len(rows),
        "steps": len(report.get("steps") or []),
        "scores": len(scores),
        "traces": len(datasets),
        "dataset_items": dataset_count,
        "offset": new_offset,
    }
    if dataset_error:
        result["dataset_error"] = dataset_error
    return result
