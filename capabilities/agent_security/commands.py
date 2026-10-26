"""pipeline-kit security subcommands."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from .config import (
    default_config,
    load_agent_security_config,
    save_agent_security_config,
    state_dir_for,
    validate_config,
)
from .ledger import FINDINGS_FILE, count_lines, flush_pending_projection, read_jsonl
from .providers import copilot_cli, uber_adr
from .providers.registry import list_provider_names, load_providers

HEALTH_FILE = "provider-health.jsonl"
EVENTS_FILE = "session-events.jsonl"


def cmd_install(project: Path, *, mode: str = "audit") -> int:
    pack = project / ".pipeline"
    if not pack.is_dir():
        print("no .pipeline — run pipeline-kit init first", file=sys.stderr)
        return 64
    if mode not in {"audit", "warn", "block"}:
        print(f"invalid mode: {mode}", file=sys.stderr)
        return 64
    try:
        save_agent_security_config(project, {"enabled": True, "mode": mode})
    except (OSError, ValueError, json.JSONDecodeError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 64
    state = state_dir_for(project)
    state.mkdir(parents=True, exist_ok=True)
    print(f"agent_security enabled mode={mode}")
    print(f"state_dir={state}")
    print("Hooks already call the evaluator when enabled; no separate hook merge required.")
    print("Install optional collector: pip install -e \".[agent-security]\"")
    return 0


def cmd_uninstall(project: Path) -> int:
    try:
        save_agent_security_config(project, {"enabled": False})
    except (OSError, ValueError, json.JSONDecodeError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 64
    print("agent_security disabled; ledgers and checkpoints retained under .pipeline/state/security/")
    return 0


def cmd_status(project: Path) -> int:
    cfg = load_agent_security_config(project)
    state = state_dir_for(project, cfg)
    findings = count_lines(state / FINDINGS_FILE)
    events = count_lines(state / EVENTS_FILE)
    health_rows = read_jsonl(state / HEALTH_FILE)
    last_health = health_rows[-1] if health_rows else None
    print(f"enabled\t{cfg.get('enabled') is True}")
    print(f"mode\t{cfg.get('mode')}")
    print(f"fail_mode\t{cfg.get('fail_mode')}")
    print(f"sources\t{','.join(cfg.get('sources') or [])}")
    print(f"state_dir\t{state}")
    print(f"findings\t{findings}")
    print(f"session_events\t{events}")
    print(f"providers\t{','.join(list_provider_names())}")
    if last_health:
        print(f"last_health\t{last_health.get('state')}\t{last_health.get('reason')}")
    return 0


def cmd_scan(project: Path, *, sources: list[str] | None = None) -> int:
    cfg = load_agent_security_config(project)
    state = state_dir_for(project, cfg)
    state.mkdir(parents=True, exist_ok=True)
    wanted = tuple(sources or cfg.get("sources") or ["cursor", "copilot-cli"])

    summaries: list[dict[str, Any]] = []

    # Uber ADR (cursor primarily)
    adr = uber_adr.scan(state, wanted)
    summaries.append(
        {
            "provider": adr.provider,
            "adr_version": adr.adr_version,
            "new_events": adr.new_events,
            "health": list(adr.health),
        }
    )

    # Native Copilot CLI collector
    if any(s in {"copilot-cli", "copilot"} for s in wanted):
        copilot = copilot_cli.scan(state, wanted)
        summaries.append(copilot)

    total = sum(int(s.get("new_events") or 0) for s in summaries)
    print(json.dumps({"new_events": total, "providers": summaries}, indent=2))
    return 0


def cmd_flush(project: Path) -> int:
    cfg = load_agent_security_config(project)
    state = state_dir_for(project, cfg)
    result = flush_pending_projection(project, state)
    print(json.dumps(result, indent=2))
    return 0


def cmd_doctor(project: Path) -> int:
    cfg = load_agent_security_config(project)
    problems = validate_config(cfg)
    state = state_dir_for(project, cfg)
    info: list[str] = []
    required: dict[str, bool] = {}

    required["config valid"] = not problems
    for problem in problems:
        info.append(f"config: {problem}")

    required["state dir writable"] = True
    try:
        state.mkdir(parents=True, exist_ok=True)
        probe = state / ".doctor-write-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError as exc:
        required["state dir writable"] = False
        info.append(f"state dir: {exc}")

    # Provider health
    for provider in load_providers(cfg):
        name = provider.name() if hasattr(provider, "name") else type(provider).__name__
        try:
            rows = provider.health() if hasattr(provider, "health") else []
        except Exception as exc:  # noqa: BLE001
            required[f"provider {name}"] = False
            info.append(f"{name}: {type(exc).__name__}")
            continue
        ok = True
        for row in rows or []:
            state_name = row.get("state") if isinstance(row, dict) else None
            if state_name in {"provider_unavailable", "version_untested"}:
                ok = False
            info.append(f"{name}: {row.get('state')} — {row.get('reason')}")
        required[f"provider {name}"] = ok or name in {"uber-adr-sensor", "copilot-cli-native"}
        # Collectors may be missing on a machine; that is informational, not fatal.

    # Cursor path discovery
    cursor_paths = [p for p in uber_adr.cursor_db_candidates() if p.is_file()]
    if cursor_paths:
        info.append(f"cursor db: {cursor_paths[0]}")
    else:
        info.append("cursor db: not found on this host")

    copilot_roots = copilot_cli.discover_session_roots()
    if copilot_roots:
        info.append(f"copilot-cli roots: {', '.join(str(r) for r in copilot_roots)}")
    else:
        info.append("copilot-cli roots: not found")

    print(f"enabled\t{cfg.get('enabled') is True}")
    print(f"mode\t{cfg.get('mode')}")
    for key, ok in required.items():
        print(f"{'ok' if ok else 'FAIL'}\t{key}")
    for line in info:
        print(f"info\t{line}")
    return 0 if all(required.values()) or cfg.get("enabled") is not True else (0 if not problems else 1)


def security_doctor_checks(root: Path) -> tuple[list[str], dict[str, bool]]:
    """Integrate with pipeline-kit doctor."""
    info: list[str] = []
    required: dict[str, bool] = {}
    project = root if (root / ".pipeline").is_dir() else root.parent
    cfg_path = project / ".pipeline" / "config.json"
    if not cfg_path.is_file() and (root / "config.json").is_file():
        # pack root
        try:
            data = json.loads((root / "config.json").read_text(encoding="utf-8"))
            cfg = data.get("agent_security") if isinstance(data, dict) else {}
            cfg = cfg if isinstance(cfg, dict) else {}
        except (OSError, json.JSONDecodeError):
            cfg = {}
    else:
        cfg = load_agent_security_config(project) if cfg_path.is_file() else default_config()

    if cfg.get("enabled") is True:
        info.append(f"agent_security.enabled mode={cfg.get('mode')}")
        problems = validate_config(cfg)
        required["agent_security config"] = not problems
        for problem in problems:
            info.append(problem)
    else:
        info.append("agent_security is off (pipeline-kit security install)")
    return info, required
