"""Native GitHub Copilot CLI session collector (async, not inline).

Reads session JSONL from well-known Copilot CLI directories. Does not scrape
VS Code Copilot Chat storage. Argument values and prompts are never persisted.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from ..models import CanonicalSessionEvent, CanonicalToolCall, ProviderCapabilities

PROVIDER_NAME = "copilot-cli-native"
CHECKPOINT_FILE = "copilot-cli-checkpoint.json"
EVENTS_FILE = "session-events.jsonl"
HEALTH_FILE = "provider-health.jsonl"


class CopilotCliProvider:
    def name(self) -> str:
        return PROVIDER_NAME

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            name=PROVIDER_NAME,
            sources=("copilot-cli",),
            event_types=("session",),
            synchronous=False,
            block_capable=False,
            max_latency_ms=5000,
        )

    def health(self) -> list[dict[str, Any]]:
        roots = discover_session_roots()
        if not roots:
            return [
                _health(
                    "source_not_found",
                    "no Copilot CLI session directory found on this host",
                    "copilot-cli",
                )
            ]
        return [
            _health("ok", f"found session roots: {', '.join(str(r) for r in roots)}", "copilot-cli")
        ]

    def evaluate(self, event: Any) -> None:
        return None

    def collect(self, state_dir: Any, sources: tuple[str, ...] | list[str] = ("copilot-cli",)) -> dict[str, Any]:
        return scan(Path(state_dir), sources)


def discover_session_roots(home: Path | None = None) -> list[Path]:
    """Return existing directories that may hold Copilot CLI session logs."""
    home = Path(home) if home is not None else Path.home()
    candidates = [
        home / ".copilot" / "session-state",
        home / ".copilot" / "sessions",
        home / ".copilot",
        home / ".github" / "copilot" / "sessions",
    ]
    # Only probe APPDATA when using the real home (tests pass an explicit home).
    if home == Path.home():
        appdata = os.environ.get("APPDATA")
        if appdata:
            candidates.append(Path(appdata) / "GitHub Copilot CLI")
            candidates.append(Path(appdata) / "github-copilot")
        local = os.environ.get("LOCALAPPDATA")
        if local:
            candidates.append(Path(local) / "github-copilot")
    found: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        try:
            if not path.is_dir():
                continue
        except OSError:
            continue
        key = str(path.resolve()).lower()
        if key in seen:
            continue
        try:
            next(path.iterdir())
        except (OSError, StopIteration):
            continue
        seen.add(key)
        found.append(path)
    return found


def scan(
    state_dir: Path,
    sources: Iterable[str] = ("copilot-cli",),
    *,
    home: Path | None = None,
) -> dict[str, Any]:
    state_dir = Path(state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    health: list[dict[str, Any]] = []
    wanted = {str(s) for s in sources}
    if "copilot-cli" not in wanted and "copilot" not in wanted:
        return {"provider": PROVIDER_NAME, "new_events": 0, "health": health}

    roots = discover_session_roots(home=home)
    if not roots:
        health.append(
            _health(
                "source_not_found",
                "no Copilot CLI session directory found on this host",
                "copilot-cli",
            )
        )
        _append_jsonl(state_dir / HEALTH_FILE, health)
        return {"provider": PROVIDER_NAME, "new_events": 0, "health": health}

    checkpoint = _load_checkpoint(state_dir)
    new_events: list[CanonicalSessionEvent] = []

    for root in roots:
        for session_file in _iter_session_files(root):
            session_id = session_file.stem
            try:
                mtime = datetime.fromtimestamp(session_file.stat().st_mtime, tz=timezone.utc)
            except OSError:
                continue
            last = checkpoint.get(session_id)
            if last is not None and mtime <= datetime.fromisoformat(last):
                continue
            event = _parse_session_file(session_file, session_id, mtime)
            if event is None:
                continue
            checkpoint[session_id] = mtime.isoformat()
            new_events.append(event)

    _append_jsonl(state_dir / EVENTS_FILE, [e.to_record() for e in new_events])
    _save_checkpoint(state_dir, checkpoint)
    health.append(
        _health(
            "ok",
            f"scanned {len(roots)} root(s); new_events={len(new_events)}",
            "copilot-cli",
        )
    )
    _append_jsonl(state_dir / HEALTH_FILE, health)
    return {
        "provider": PROVIDER_NAME,
        "new_events": len(new_events),
        "health": health,
        "roots": [str(r) for r in roots],
    }


def _iter_session_files(root: Path) -> list[Path]:
    files: list[Path] = []
    patterns = ("*.jsonl", "events.jsonl", "session.json", "*.json")
    for pattern in patterns:
        try:
            files.extend(root.rglob(pattern))
        except OSError:
            continue
    # de-dupe, skip huge trees by capping
    out: list[Path] = []
    seen: set[str] = set()
    for path in files:
        if not path.is_file():
            continue
        if path.name in {"config.json", "settings.json", "package.json"}:
            continue
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        out.append(path)
        if len(out) >= 200:
            break
    return out


def _parse_session_file(path: Path, session_id: str, when: datetime) -> CanonicalSessionEvent | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if not text.strip():
        return None

    tool_calls: list[CanonicalToolCall] = []
    user_messages = 0
    assistant_messages = 0
    event_id = session_id

    if path.suffix == ".jsonl" or path.name.endswith(".jsonl"):
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            role = str(row.get("role") or row.get("type") or "").lower()
            if role in {"user", "human"}:
                user_messages += 1
            elif role in {"assistant", "model", "bot"}:
                assistant_messages += 1
            tool = _tool_from_row(row)
            if tool:
                tool_calls.append(tool)
            eid = row.get("id") or row.get("event_id") or row.get("uuid")
            if isinstance(eid, str) and eid.strip():
                event_id = eid.strip()
    else:
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None
        if isinstance(data, dict):
            messages = data.get("messages") or data.get("events") or data.get("history") or []
            if isinstance(messages, list):
                for row in messages:
                    if not isinstance(row, dict):
                        continue
                    role = str(row.get("role") or "").lower()
                    if role == "user":
                        user_messages += 1
                    elif role == "assistant":
                        assistant_messages += 1
                    tool = _tool_from_row(row)
                    if tool:
                        tool_calls.append(tool)
            eid = data.get("id") or data.get("session_id")
            if isinstance(eid, str) and eid.strip():
                event_id = eid.strip()
                session_id = eid.strip()
        elif isinstance(data, list):
            for row in data:
                if isinstance(row, dict):
                    tool = _tool_from_row(row)
                    if tool:
                        tool_calls.append(tool)

    # Skip empty noise files with no signal
    if user_messages == 0 and assistant_messages == 0 and not tool_calls:
        # Still record a minimal session so checkpoint advances when file has content
        if len(text) < 20:
            return None

    return CanonicalSessionEvent(
        provider=PROVIDER_NAME,
        source="copilot-cli",
        session_id=f"copilot-cli_{session_id}",
        event_id=str(event_id),
        timestamp=when.isoformat(),
        user_messages=user_messages,
        assistant_messages=assistant_messages,
        tool_calls=tuple(tool_calls),
    )


def _tool_from_row(row: dict[str, Any]) -> CanonicalToolCall | None:
    name = row.get("tool_name") or row.get("toolName") or row.get("name") or row.get("tool")
    if not isinstance(name, str) or not name.strip():
        # nested tool call objects
        tool = row.get("tool") or row.get("toolCall") or row.get("function")
        if isinstance(tool, dict):
            name = tool.get("name") or tool.get("tool_name")
            args = tool.get("arguments") or tool.get("args") or {}
        else:
            return None
    else:
        args = row.get("arguments") or row.get("args") or row.get("toolArgs") or {}
    if not isinstance(name, str) or not name.strip():
        return None
    keys: tuple[str, ...] = ()
    if isinstance(args, dict):
        keys = tuple(sorted(str(k) for k in args.keys()))
    elif isinstance(args, str) and args.lstrip()[:1] == "{":
        try:
            parsed = json.loads(args)
        except json.JSONDecodeError:
            parsed = {}
        if isinstance(parsed, dict):
            keys = tuple(sorted(str(k) for k in parsed.keys()))
    status = row.get("status")
    status_s = str(status) if status is not None else None
    return CanonicalToolCall(
        name=name.strip(),
        tool_type=str(row.get("tool_type") or "tool_call"),
        server=(str(row["server"]) if isinstance(row.get("server"), str) else None),
        status=status_s,
        argument_keys=keys,
    )


def _health(state: str, reason: str, source: str | None = None) -> dict[str, Any]:
    return {
        "kind": "provider_health",
        "provider": PROVIDER_NAME,
        "state": state,
        "source": source,
        "reason": reason,
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }


def _load_checkpoint(state_dir: Path) -> dict[str, str]:
    path = state_dir / CHECKPOINT_FILE
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _save_checkpoint(state_dir: Path, checkpoint: dict[str, str]) -> None:
    path = state_dir / CHECKPOINT_FILE
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(checkpoint, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def _append_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    if not records:
        return
    with open(path, "a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
