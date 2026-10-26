"""Security findings ledger and redacted observability projection."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable

from .models import Decision, DecisionAction, Finding

FINDINGS_FILE = "findings.jsonl"
DECISIONS_FILE = "decisions.jsonl"
OBS_REL = Path(".pipeline") / "state" / "obs" / "events.jsonl"


def ensure_state_dir(state_dir: Path) -> Path:
    state_dir = Path(state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


def append_findings(
    state_dir: Path,
    findings: Iterable[Finding],
    *,
    effective_action: DecisionAction | None = None,
    mode: str | None = None,
) -> int:
    records = [
        f.to_record(effective_action=effective_action, mode=mode) for f in findings
    ]
    return _append_jsonl(ensure_state_dir(state_dir) / FINDINGS_FILE, records)


def append_decision(state_dir: Path, decision: Decision, *, mode: str | None = None) -> None:
    _append_jsonl(
        ensure_state_dir(state_dir) / DECISIONS_FILE,
        [decision.to_record(mode=mode)],
    )


def project_to_observability(
    project: Path,
    *,
    findings: Iterable[Finding] = (),
    decision: Decision | None = None,
    health: Iterable[dict[str, Any]] = (),
    mode: str | None = None,
) -> int:
    """Append redacted security_* rows to the obs ledger (no secrets)."""
    rows: list[dict[str, Any]] = []
    for finding in findings:
        row = finding.to_record(effective_action=decision.action if decision else None, mode=mode)
        row["kind"] = "security_finding"
        rows.append(_obs_slim(row))
    if decision is not None:
        row = decision.to_record(mode=mode)
        rows.append(_obs_slim(row))
    for item in health:
        if isinstance(item, dict):
            slim = dict(item)
            slim.setdefault("kind", "security_provider_health")
            rows.append(_obs_slim(slim))
    if not rows:
        return 0
    path = project / OBS_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    return _append_jsonl(path, rows)


def count_lines(path: Path) -> int:
    if not path.is_file():
        return 0
    count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                count += 1
    return count


def read_jsonl(path: Path, *, limit: int | None = None) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                rows.append(parsed)
            if limit is not None and len(rows) >= limit:
                break
    return rows


def flush_pending_projection(project: Path, state_dir: Path) -> dict[str, Any]:
    """Copy findings not yet mirrored into obs (idempotent-ish via checkpoint file)."""
    state_dir = ensure_state_dir(state_dir)
    findings_path = state_dir / FINDINGS_FILE
    checkpoint_path = state_dir / "obs-projection-offset.txt"
    offset = 0
    if checkpoint_path.is_file():
        try:
            offset = int(checkpoint_path.read_text(encoding="utf-8").strip() or "0")
        except ValueError:
            offset = 0
    if not findings_path.is_file():
        return {"projected": 0, "offset": offset}
    with findings_path.open("rb") as handle:
        handle.seek(offset)
        chunk = handle.read()
        new_offset = handle.tell()
    if not chunk:
        return {"projected": 0, "offset": offset}
    text = chunk.decode("utf-8", errors="replace")
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            parsed = dict(parsed)
            parsed["kind"] = "security_finding"
            rows.append(_obs_slim(parsed))
    projected = 0
    if rows:
        obs_path = project / OBS_REL
        obs_path.parent.mkdir(parents=True, exist_ok=True)
        projected = _append_jsonl(obs_path, rows)
    checkpoint_path.write_text(str(new_offset), encoding="utf-8")
    return {"projected": projected, "offset": new_offset}


def _obs_slim(row: dict[str, Any]) -> dict[str, Any]:
    """Drop anything that could hold free-form secrets; keep metric dimensions."""
    keep = {
        "kind",
        "finding_id",
        "provider",
        "rule_id",
        "category",
        "technique",
        "severity",
        "confidence",
        "recommended_action",
        "effective_action",
        "action",
        "mode",
        "source",
        "session_id",
        "event_type",
        "latency_ms",
        "timed_out",
        "error",
        "state",
        "reason",
        "observed_at",
        "schema_version",
        "finding_ids",
    }
    slim = {key: row[key] for key in keep if key in row}
    # Never carry evidence detail strings into obs (may mention path patterns).
    if "evidence" in row and isinstance(row["evidence"], list):
        slim["evidence_count"] = len(row["evidence"])
        slim["evidence_rules"] = [
            item.get("rule_id")
            for item in row["evidence"]
            if isinstance(item, dict) and item.get("rule_id")
        ]
    return slim


def _append_jsonl(path: Path, records: list[dict[str, Any]]) -> int:
    if not records:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return len(records)
