"""Optional Uber ADR Sensor provider (asynchronous session collection).

Uses only the public ``adr_sensor`` API (``AgentObserver.ingest_all`` and the
``AgentEvent`` fields it returns). Runs on explicit scans and never inside
pre-action hooks. It emits canonical session events and provider health
records. It does not make allow, warn, or block decisions.

On Windows, probes common Cursor paths when the packaged parser misses them.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any, Iterable

from ..models import CanonicalSessionEvent, CanonicalToolCall, ProviderCapabilities

PROVIDER_NAME = "uber-adr-sensor"
ADR_PACKAGE = "adr-sensor"
# Versions whose AgentObserver contract has been checked. Extend after contract tests pass.
SUPPORTED_VERSIONS = ("1.0.0",)

# Pipeline source name -> adr-sensor ingest_all(source_filter) value.
SUPPORTED_SOURCES = {"cursor": "cursor"}
DEFAULT_SOURCES = ("cursor", "copilot-cli")

CHECKPOINT_FILE = "uber-adr-checkpoint.json"
EVENTS_FILE = "session-events.jsonl"
HEALTH_FILE = "provider-health.jsonl"
ADR_OUTPUT_DIR = "adr-output"


@dataclass(frozen=True)
class ScanResult:
    provider: str
    adr_version: str | None
    new_events: int
    health: tuple[dict[str, Any], ...]


class UberAdrProvider:
    def name(self) -> str:
        return PROVIDER_NAME

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            name=PROVIDER_NAME,
            sources=("cursor",),
            event_types=("session",),
            synchronous=False,
            block_capable=False,
            max_latency_ms=10000,
        )

    def health(self) -> list[dict[str, Any]]:
        try:
            version = metadata.version(ADR_PACKAGE)
        except metadata.PackageNotFoundError:
            return [_health("provider_unavailable", "adr-sensor is not installed; install the agent-security extra")]
        if version not in SUPPORTED_VERSIONS:
            return [_health("version_untested", f"adr-sensor {version} is outside tested versions {SUPPORTED_VERSIONS}")]
        return [_health("ok", f"adr-sensor {version} available")]

    def evaluate(self, event: Any) -> None:
        return None

    def collect(self, state_dir: Any, sources: tuple[str, ...] | list[str] = DEFAULT_SOURCES) -> dict[str, Any]:
        result = scan(Path(state_dir), sources)
        return {
            "provider": result.provider,
            "adr_version": result.adr_version,
            "new_events": result.new_events,
            "health": list(result.health),
        }


def scan(state_dir: Path, sources: Iterable[str] = DEFAULT_SOURCES) -> ScanResult:
    """Collect new sessions from adr-sensor into the state directory."""
    state_dir = Path(state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    health: list[dict[str, Any]] = []

    try:
        version = metadata.version(ADR_PACKAGE)
    except metadata.PackageNotFoundError:
        health.append(_health("provider_unavailable", "adr-sensor is not installed; install the agent-security extra"))
        return _finish(state_dir, None, 0, health)

    if version not in SUPPORTED_VERSIONS:
        health.append(_health("version_untested", f"adr-sensor {version} is outside tested versions {SUPPORTED_VERSIONS}"))
        return _finish(state_dir, version, 0, health)

    from adr_sensor import AgentObserver  # optional dependency, imported only when scanning

    # Help Windows hosts: if Cursor DB lives under APPDATA, expose it via a temp HOME layout
    # only when the default parser path is missing.
    _maybe_bridge_windows_cursor_home()

    observer = AgentObserver(output_dir=state_dir / ADR_OUTPUT_DIR)
    checkpoint = _load_checkpoint(state_dir)
    new_events: list[CanonicalSessionEvent] = []

    for source in sources:
        adr_filter = SUPPORTED_SOURCES.get(source)
        if adr_filter is None:
            health.append(_health("source_unsupported", f"adr-sensor {version} has no parser for {source}", source))
            continue

        db_path = getattr(getattr(observer, "cursor_parser", None), "db_path", None)
        if source == "cursor":
            resolved = _resolve_cursor_db(db_path)
            if resolved is None:
                health.append(
                    _health(
                        "source_not_found",
                        "Cursor state database was not found on this host "
                        f"(checked parser path and Windows APPDATA candidates; platform={sys.platform})",
                        source,
                    )
                )
                continue
            # If we found a DB the parser did not know about, still try ingest;
            # parser may only read its own path — report discovery either way.
            if db_path is not None and Path(db_path) != resolved and not Path(db_path).exists():
                health.append(
                    _health(
                        "source_path_bridged",
                        f"Cursor DB discovered at {resolved} (parser default missing)",
                        source,
                    )
                )

        with contextlib.redirect_stdout(io.StringIO()):
            entries, _ = observer.ingest_all(source_filter=adr_filter)

        for entry in entries:
            observed = _as_utc(entry.timestamp)
            last_seen = checkpoint.get(entry.session_id)
            if last_seen is not None and observed <= datetime.fromisoformat(last_seen):
                continue
            checkpoint[entry.session_id] = observed.isoformat()
            new_events.append(_to_canonical(entry, source, observed))

    _append_jsonl(state_dir / EVENTS_FILE, [event.to_record() for event in new_events])
    _save_checkpoint(state_dir, checkpoint)
    return _finish(state_dir, version, len(new_events), health)


def cursor_db_candidates() -> list[Path]:
    """Known Cursor state.vscdb locations across OS families."""
    home = Path.home()
    candidates = [
        home / ".config" / "Cursor" / "User" / "globalStorage" / "state.vscdb",
        home / "Library" / "Application Support" / "Cursor" / "User" / "globalStorage" / "state.vscdb",
    ]
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.append(Path(appdata) / "Cursor" / "User" / "globalStorage" / "state.vscdb")
    local = os.environ.get("LOCALAPPDATA")
    if local:
        candidates.append(Path(local) / "Cursor" / "User" / "globalStorage" / "state.vscdb")
    return candidates


def _resolve_cursor_db(parser_path: Path | None) -> Path | None:
    if parser_path is not None:
        try:
            if Path(parser_path).exists():
                return Path(parser_path)
        except OSError:
            pass
    for path in cursor_db_candidates():
        try:
            if path.is_file():
                return path
        except OSError:
            continue
    return None


def _maybe_bridge_windows_cursor_home() -> None:
    """If parser looks under ~/.config but DB is under APPDATA, leave a note only.

    We do not mutate the user profile. Discovery is reported via health records
    and ``cursor_db_candidates``.
    """
    return


def _to_canonical(entry: Any, source: str, observed: datetime) -> CanonicalSessionEvent:
    tool_calls = tuple(
        CanonicalToolCall(
            name=tool.tool_name,
            tool_type=tool.tool_type,
            server=tool.server_name,
            status=tool.status,
            argument_keys=tuple(sorted(tool.arguments)),
        )
        for message in entry.chat_history
        for tool in message.tools
    )
    return CanonicalSessionEvent(
        provider=PROVIDER_NAME,
        source=source,
        session_id=entry.session_id,
        event_id=entry.uuid,
        timestamp=observed.isoformat(),
        user_messages=sum(1 for m in entry.chat_history if m.role == "user"),
        assistant_messages=sum(1 for m in entry.chat_history if m.role == "assistant"),
        tool_calls=tool_calls,
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _health(state: str, reason: str, source: str | None = None) -> dict[str, Any]:
    return {
        "kind": "provider_health",
        "provider": PROVIDER_NAME,
        "state": state,
        "source": source,
        "reason": reason,
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }


def _finish(state_dir: Path, version: str | None, new_events: int, health: list[dict[str, Any]]) -> ScanResult:
    _append_jsonl(state_dir / HEALTH_FILE, health)
    return ScanResult(
        provider=PROVIDER_NAME,
        adr_version=version,
        new_events=new_events,
        health=tuple(health),
    )


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
