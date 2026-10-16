"""Built-in and entry-point discovery for security providers."""

from __future__ import annotations

from importlib.metadata import entry_points
from typing import Any, Callable

from .local_policy import LocalPolicyProvider

ENTRY_POINT_GROUP = "pipeline_kit.agent_security.providers"

# Lazy factories so optional deps are not imported until needed.
_BUILTIN: dict[str, Callable[[], Any]] = {
    "local-policy": LocalPolicyProvider,
}


def _register_optional() -> None:
    if "uber-adr-sensor" not in _BUILTIN:
        from .uber_adr import UberAdrProvider

        _BUILTIN["uber-adr-sensor"] = UberAdrProvider
    if "copilot-cli-native" not in _BUILTIN:
        from .copilot_cli import CopilotCliProvider

        _BUILTIN["copilot-cli-native"] = CopilotCliProvider


def list_provider_names() -> list[str]:
    _register_optional()
    names = set(_BUILTIN)
    for ep in _entry_points():
        names.add(ep.name)
    return sorted(names)


def load_providers(
    cfg: dict[str, Any] | None = None,
    *,
    inline_only: bool = False,
) -> list[Any]:
    """Instantiate enabled providers ordered by priority (lower first)."""
    _register_optional()
    cfg = cfg or {}
    declared = cfg.get("providers")
    if not isinstance(declared, list) or not declared:
        declared = [
            {"name": "local-policy", "enabled": True, "priority": 100, "inline": True},
            {"name": "uber-adr-sensor", "enabled": True, "priority": 200, "inline": False},
            {"name": "copilot-cli-native", "enabled": True, "priority": 210, "inline": False},
        ]

    specs: list[tuple[int, str, dict[str, Any]]] = []
    for item in declared:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name or item.get("enabled") is False:
            continue
        if inline_only and item.get("inline") is False:
            continue
        if not inline_only and item.get("inline") is True and cfg.get("_collect_skip_inline"):
            continue
        priority = int(item.get("priority") or 500)
        specs.append((priority, name, item))
    specs.sort(key=lambda row: (row[0], row[1]))

    external = {ep.name: ep for ep in _entry_points()}
    loaded: list[Any] = []
    seen: set[str] = set()
    for _priority, name, _item in specs:
        if name in seen:
            continue
        seen.add(name)
        factory = _BUILTIN.get(name)
        if factory is None and name in external:
            try:
                factory = external[name].load()
            except Exception:
                continue
        if factory is None:
            continue
        try:
            provider = factory() if callable(factory) else factory
        except Exception:
            continue
        loaded.append(provider)
    return loaded


def _entry_points() -> list[Any]:
    try:
        eps = entry_points()
    except Exception:
        return []
    if hasattr(eps, "select"):
        return list(eps.select(group=ENTRY_POINT_GROUP))
    return list(eps.get(ENTRY_POINT_GROUP, []))  # type: ignore[arg-type]
