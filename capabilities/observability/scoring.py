"""Deterministic scoring of pipeline-kit agent runs. No LLM. No network."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from pipeline_observability.normalize import load_ledger, normalize_rows, dedupe_events

PATH_RE = re.compile(r"(?:`([^`]+\.[A-Za-z0-9]+)`|(?<![\w./])([\w./-]+\.[A-Za-z0-9]{1,8}))")
CAT_RE = re.compile(r"^(cat|head|tail|sed\s+-n)\b")
FIND_RE = re.compile(r"^(find|grep|rg)\b")
SUCCESS_RE = re.compile(r"\bSUCCESS\b", re.I)
TOOL_EVENTS = {
    "postToolUse",
    "PostToolUse",
    "afterShellExecution",
    "afterMCPExecution",
    "afterFileEdit",
    "postToolUseFailure",
    "PostToolUseFailure",
}


def _rel(path: str | None, repo: Path) -> str | None:
    if not path:
        return None
    raw = path.strip()
    try:
        resolved = Path(raw).expanduser()
        if resolved.is_absolute():
            return str(resolved.resolve().relative_to(repo.resolve()))
    except (OSError, ValueError):
        pass
    return raw.lstrip("./")


def _allowlisted(path: str | None, allowed: list[str], repo: Path) -> bool:
    rel = _rel(path, repo)
    if not rel:
        return False
    for item in allowed:
        candidate = str(item).lstrip("./")
        if rel == candidate or rel.startswith(candidate.rstrip("/") + "/") or candidate.endswith(rel):
            return True
    return False


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _parse_route(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        out[key.strip().lower().replace(" ", "_")] = value.strip()
    return out


def _extract_paths(text: str) -> set[str]:
    found: set[str] = set()
    for match in PATH_RE.finditer(text):
        value = match.group(1) or match.group(2)
        if value and "/" in value:
            found.add(value.lstrip("./"))
    return found


def _feature_root(repo: Path, slug: str) -> Path:
    try:
        from pipeline_kit.paths import feature_dir as _fd

        return _fd(repo, str(slug))
    except Exception:
        return repo / "features" / str(slug)


def _plan_paths(repo: Path, slug: str | None) -> set[str]:
    if not slug:
        return set()
    root = _feature_root(repo, str(slug))
    found: set[str] = set()
    for name in ("implementation-plan.md", "spec-order.md", "plan.md"):
        path = root / name
        if path.is_file():
            found |= _extract_paths(path.read_text(encoding="utf-8"))
    return found


def _handoff_success(repo: Path, slug: str | None, step: str | None) -> bool | None:
    if not slug:
        return None
    root = _feature_root(repo, str(slug))
    if not root.is_dir():
        return None
    files = sorted(root.glob("HANDOFF*.md")) + sorted(root.glob("**/HANDOFF*.md"))
    if step:
        preferred = [path for path in files if step.replace("-agent", "") in path.name.lower()]
        files = preferred or files
    if not files:
        return None
    return bool(SUCCESS_RE.search(files[-1].read_text(encoding="utf-8")))


def _verify_rules(cfg: dict[str, Any]) -> list[dict[str, str]]:
    verify = cfg.get("verify") if isinstance(cfg.get("verify"), dict) else {}
    rules = verify.get("rules") if isinstance(verify, dict) else []
    out: list[dict[str, str]] = []
    if not isinstance(rules, list):
        return out
    for item in rules:
        if isinstance(item, dict) and isinstance(item.get("match"), str) and item["match"]:
            out.append(
                {
                    "match": item["match"],
                    "expect": item["expect"] if isinstance(item.get("expect"), str) else "",
                    "message": item["message"] if isinstance(item.get("message"), str) else "",
                }
            )
    return out


def _readonly(cfg: dict[str, Any]) -> set[str]:
    product = cfg.get("product") if isinstance(cfg.get("product"), dict) else {}
    agents = product.get("readonly_agents") if isinstance(product, dict) else []
    return {str(item) for item in agents} if isinstance(agents, list) else set()


def _artifact_dir(cfg: dict[str, Any]) -> str:
    product = cfg.get("product") if isinstance(cfg.get("product"), dict) else {}
    value = product.get("artifact_dir") if isinstance(product, dict) else "features/"
    return str(value or "features/").rstrip("/") + "/"


def _bind_contexts(events: list[dict[str, Any]]) -> None:
    last_by_sub: dict[str, dict[str, Any]] = {}
    last_any: dict[str, Any] | None = None
    for event in events:
        context = event.get("step_context")
        if isinstance(context, dict):
            last_any = context
            sid = event.get("subagent_id")
            if isinstance(sid, str) and sid:
                last_by_sub[sid] = context
            event["workflow"] = context.get("workflow")
            event["step"] = context.get("step")
            event["slug"] = context.get("slug")
            event["allowed_reads"] = context.get("allowed_reads") or []
            continue
        sid = event.get("subagent_id")
        chosen = last_by_sub.get(sid) if isinstance(sid, str) else last_any
        if chosen:
            event["workflow"] = chosen.get("workflow")
            event["step"] = chosen.get("step")
            event["slug"] = chosen.get("slug")
            event["allowed_reads"] = chosen.get("allowed_reads") or []
        else:
            event.setdefault("step", None)
            event.setdefault("slug", None)
            event.setdefault("allowed_reads", [])


def _is_tool(event: dict[str, Any]) -> bool:
    if event.get("event") in TOOL_EVENTS:
        return True
    return False


def _wrong_tool(event: dict[str, Any]) -> bool:
    command = event.get("command") or ""
    return event.get("tool_kind") == "shell" and bool(CAT_RE.search(command) or FIND_RE.search(command))


def _verdict(
    event: dict[str, Any],
    *,
    repo: Path,
    readonly: set[str],
    artifact: str,
    plan_files: set[str],
    seen: dict[str, int],
) -> tuple[str, str]:
    step = event.get("step")
    if not step:
        return "unattributed", "high"
    kind = event.get("tool_kind")
    if kind == "read":
        key = f"read:{step}:{_rel(event.get('target_path'), repo)}"
        seen[key] = seen.get(key, 0) + 1
        if seen[key] > 1:
            return "wasted", "high"
        allowed = event.get("allowed_reads") or []
        if allowed and not _allowlisted(event.get("target_path"), list(allowed), repo):
            return "out-of-contract", "high"
        return "in-contract", "high"
    if kind == "search":
        raw_pattern = event.get("pattern")
        if not (isinstance(raw_pattern, str) and raw_pattern.strip()):
            return "wasted", "high"
        key = f"search:{step}:{raw_pattern or event.get('command')}"
        seen[key] = seen.get(key, 0) + 1
        return ("wasted", "high") if seen[key] > 1 else ("in-contract", "high")
    if kind == "shell":
        key = f"shell:{step}:{event.get('command')}"
        seen[key] = seen.get(key, 0) + 1
        if seen[key] > 1:
            return "wasted", "high"
        if _wrong_tool(event):
            return "wrong-tool", "high"
        return "in-contract", "high"
    if kind == "edit":
        rel = _rel(event.get("target_path"), repo)
        if rel and rel.startswith(artifact):
            return "in-contract", "high"
        if step in readonly and rel and not rel.startswith(artifact):
            return "out-of-contract", "high"
        if plan_files:
            if rel and any(rel == item or rel.endswith(item) or item.endswith(rel) for item in plan_files):
                return "in-contract", "low"
            return "out-of-contract", "low"
        return "in-contract", "low"
    return "in-contract", "low"


def _ratio(num: int, den: int) -> float:
    return 0.0 if den <= 0 else round(num / den, 4)


def _integrity(
    repo: Path,
    step: str,
    slug: str | None,
    edits: list[dict[str, Any]],
    shells: list[str],
    rules: list[dict[str, str]],
    claimed: bool | None,
) -> tuple[float, float, str]:
    owed: list[dict[str, str]] = []
    for edit in edits:
        rel = _rel(edit.get("target_path"), repo) or ""
        for rule in rules:
            if rule["match"] in rel:
                owed.append(rule)
    satisfied = 0
    confidence = "high"
    for rule in owed:
        expect = rule.get("expect") or ""
        if expect:
            if any(re.search(expect, command) for command in shells):
                satisfied += 1
            continue
        tokens = [token.lower() for token in re.findall(r"[A-Za-z0-9._-]{3,}", rule.get("message") or "")]
        keywords = [token for token in tokens if token in {"npm", "pytest", "mvn", "go", "dotnet"}]
        if keywords and any(any(token in command for token in keywords) for command in shells):
            satisfied += 1
            confidence = "low"
    coverage = _ratio(satisfied, len(owed)) if owed else 1.0
    integrity = 1.0
    if owed and claimed is True and coverage < 1.0:
        integrity = 0.0
    if step == "tester-agent" and claimed is True:
        if not any(re.search(r"(pytest|npm test|mvn .*test|go test)", command) for command in shells):
            integrity = 0.0
    if step == "devops-agent" and claimed is True:
        script = repo / ".pipeline" / "skills" / "local-deployment" / "scripts" / "deploy-local.sh"
        if script.is_file() and "OVERALL=failed" in script.read_text(encoding="utf-8"):
            integrity = 0.0
    return coverage, integrity, confidence


def score_events(repo: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    events = dedupe_events(normalize_rows(rows))
    _bind_contexts(events)
    cfg = _load_json(repo / ".pipeline" / "config.json")
    readonly = _readonly(cfg)
    artifact = _artifact_dir(cfg)
    rules = _verify_rules(cfg)
    steps_out: list[dict[str, Any]] = []
    by_step: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        by_step[str(event.get("step") or "unattributed")].append(event)
    for step, group in by_step.items():
        slug = next((item.get("slug") for item in group if item.get("slug")), None)
        route = _parse_route(_feature_root(repo, str(slug or "")) / "route.md")
        plan_files = _plan_paths(repo, slug)
        seen: dict[str, int] = {}
        tools = [item for item in group if _is_tool(item)]
        for item in tools:
            verdict, confidence = _verdict(
                item, repo=repo, readonly=readonly, artifact=artifact, plan_files=plan_files, seen=seen
            )
            item["verdict"] = verdict
            item["confidence"] = confidence
        wasted = sum(1 for item in tools if item.get("verdict") == "wasted")
        out_high = sum(
            1
            for item in tools
            if item.get("verdict") == "out-of-contract" and item.get("confidence") == "high"
        )
        reads = [item for item in tools if item.get("tool_kind") == "read"]
        searches = [item for item in tools if item.get("tool_kind") == "search"]
        edits = [item for item in tools if item.get("tool_kind") == "edit"]
        shells = [item.get("command") or "" for item in tools if item.get("tool_kind") == "shell"]
        first_edit = next((index for index, item in enumerate(tools) if item.get("tool_kind") == "edit"), None)
        discovery = first_edit if first_edit is not None else len(tools)
        allowed: list[str] = []
        for item in group:
            if item.get("allowed_reads"):
                allowed = list(item["allowed_reads"])
                break
        read_paths = {_rel(item.get("target_path"), repo) for item in reads}
        unused = sum(1 for item in allowed if _rel(str(item), repo) not in read_paths) if allowed else 0
        missing = [
            path for path in sorted(p for p in read_paths if p) if allowed and not _allowlisted(path, allowed, repo)
        ]
        peak = max(
            (
                float(item["context_usage_percent"])
                for item in group
                if isinstance(item.get("context_usage_percent"), (int, float))
            ),
            default=None,
        )
        reported = next(
            (int(item["tool_call_count"]) for item in reversed(group) if isinstance(item.get("tool_call_count"), int)),
            None,
        )
        claimed = _handoff_success(repo, slug, step)
        coverage, integrity, iconf = _integrity(repo, step, slug, edits, shells, rules, claimed)
        total = len(tools)
        tokens_in = sum(int((item.get("tokens") or {}).get("input_tokens") or 0) for item in group)
        tokens_out = sum(int((item.get("tokens") or {}).get("output_tokens") or 0) for item in group)
        steps_out.append(
            {
                "step": step,
                "slug": slug,
                "workflow": next((item.get("workflow") for item in group if item.get("workflow")), None),
                "change_class": route.get("change_class") or route.get("class"),
                "tool_calls_total": total,
                "tool_calls_legitimate": max(0, total - wasted - out_high),
                "waste_ratio": _ratio(wasted, total),
                "wrong_tool_count": sum(1 for item in tools if item.get("verdict") == "wrong-tool"),
                "out_of_contract_count": out_high,
                "read_amplification": _ratio(len(reads), max(len({i.get("target_path") for i in reads}), 1))
                if reads
                else 0.0,
                "search_thrash": _ratio(len(searches), max(len({i.get("pattern") or i.get("command") for i in searches}), 1))
                if searches
                else 0.0,
                "edit_churn": _ratio(len(edits), max(len({i.get("target_path") for i in edits}), 1)) if edits else 0.0,
                "discovery_ratio": _ratio(discovery, total),
                "retry_ratio": _ratio(sum(1 for item in tools if item.get("ok") is False), total),
                "denied_count": sum(1 for item in tools if item.get("failure_type") == "permission_denied"),
                "verify_coverage": coverage,
                "integrity_pass": integrity,
                "integrity_confidence": iconf,
                "allowlist_unused_count": unused,
                "allowlist_missing": missing[:20],
                "context_peak_percent": peak,
                "reported_tool_call_count": reported,
                "ledger_vs_reported_gap": (reported - total) if reported is not None else None,
                "input_tokens": tokens_in or None,
                "output_tokens": tokens_out or None,
                "events": tools,
            }
        )
    return {
        "repo": str(repo),
        "steps": steps_out,
        "events": events,
        "event_count": len(events),
        "cost_note": "Hooks do not send dollar cost. Flush prices generation spans from model + tokens when known.",
    }


def score_ledger(repo: Path, ledger: Path) -> dict[str, Any]:
    rows, _offset = load_ledger(ledger)
    return score_events(repo, rows)
