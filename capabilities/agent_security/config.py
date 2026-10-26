"""Load and validate agent_security configuration from .pipeline/config.json."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

DEFAULT_AGENT_SECURITY: dict[str, Any] = {
    "_note": (
        "Opt-in agentic detection and response. Disabled by default. "
        "Modes: audit (record only), warn (allow + message), block (deny when thresholds met)."
    ),
    "enabled": False,
    "mode": "audit",
    "sources": ["cursor", "copilot-cli"],
    "providers": [
        {"name": "local-policy", "enabled": True, "priority": 100, "inline": True},
        {"name": "uber-adr-sensor", "enabled": True, "priority": 200, "inline": False},
        {"name": "copilot-cli-native", "enabled": True, "priority": 210, "inline": False},
    ],
    "inline_timeout_ms": 100,
    "fail_mode": "open",
    "block": {
        "minimum_severity": "high",
        "minimum_confidence": 0.9,
    },
    "capture": {
        "prompts": False,
        "tool_results": False,
        "max_field_chars": 4000,
    },
    "redact": [".env", "*secret*", "*credential*"],
    "retention_days": 14,
    "export_observability_projection": True,
    "state_dir": ".pipeline/state/security",
}

_VALID_MODES = frozenset({"audit", "warn", "block"})
_VALID_FAIL = frozenset({"open", "closed"})
_VALID_SEVERITY = frozenset({"low", "medium", "high", "critical"})


def default_config() -> dict[str, Any]:
    return deepcopy(DEFAULT_AGENT_SECURITY)


def load_agent_security_config(project: Path | None = None) -> dict[str, Any]:
    """Merge project/user config over defaults. Missing file means defaults."""
    cfg = default_config()
    path = _config_path(project)
    if path is None or not path.is_file():
        return cfg
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return cfg
    if not isinstance(data, dict):
        return cfg
    block = data.get("agent_security")
    if not isinstance(block, dict):
        return cfg
    return _merge(cfg, block)


def save_agent_security_config(project: Path, updates: dict[str, Any]) -> None:
    path = project / ".pipeline" / "config.json"
    if not path.is_file():
        raise FileNotFoundError(f"no .pipeline/config.json under {project}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("config.json must be an object")
    block = data.get("agent_security")
    if not isinstance(block, dict):
        block = default_config()
    block = _merge(block, updates)
    data["agent_security"] = block
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def state_dir_for(project: Path, cfg: dict[str, Any] | None = None) -> Path:
    cfg = cfg or load_agent_security_config(project)
    raw = cfg.get("state_dir") or ".pipeline/state/security"
    path = Path(str(raw))
    if not path.is_absolute():
        path = project / path
    return path


def validate_config(cfg: dict[str, Any]) -> list[str]:
    """Return human-readable problems; empty means OK."""
    problems: list[str] = []
    mode = str(cfg.get("mode") or "").lower()
    if mode not in _VALID_MODES:
        problems.append(f"mode must be one of {sorted(_VALID_MODES)}, got {mode!r}")
    fail = str(cfg.get("fail_mode") or "").lower()
    if fail not in _VALID_FAIL:
        problems.append(f"fail_mode must be one of {sorted(_VALID_FAIL)}, got {fail!r}")
    timeout = cfg.get("inline_timeout_ms")
    if not isinstance(timeout, (int, float)) or timeout <= 0:
        problems.append("inline_timeout_ms must be a positive number")
    block = cfg.get("block") if isinstance(cfg.get("block"), dict) else {}
    sev = str(block.get("minimum_severity") or "high").lower()
    if sev not in _VALID_SEVERITY:
        problems.append(f"block.minimum_severity invalid: {sev!r}")
    conf = block.get("minimum_confidence", 0.9)
    if not isinstance(conf, (int, float)) or not 0 <= float(conf) <= 1:
        problems.append("block.minimum_confidence must be between 0 and 1")
    return problems


def _config_path(project: Path | None) -> Path | None:
    candidates: list[Path] = []
    if project is not None:
        candidates.append(Path(project) / ".pipeline" / "config.json")
    candidates.append(Path.home() / ".pipeline" / "config.json")
    # Pack defaults when running from the kit repo itself.
    here = Path(__file__).resolve()
    pack = here.parents[2] / "kit" / "pipeline" / "config.json"
    candidates.append(pack)
    for path in candidates:
        if path.is_file():
            return path
    return None


def _merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(base)
    for key, value in overlay.items():
        if key == "_note":
            out[key] = value
            continue
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = deepcopy(value)
    return out
