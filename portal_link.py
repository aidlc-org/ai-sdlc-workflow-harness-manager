"""Report a project's local state to a pipeline portal.

Metadata only: kit version and mode, which features are on, plugin and package
state, observability status, run and gate status, the license state (never the
token), and the names of failed doctor checks. It never sends file contents,
file paths, ``config.json``, prompts, source or the license token.

The project authenticates with a per-project ingest key. The connection (portal
URL + key) is kept in ``~/.pipeline/portal.json`` (owner-only where the OS
supports it), or in ``PIPELINE_PORTAL_URL`` / ``PIPELINE_PORTAL_KEY`` for CI.

Local changes flow to the portal; nothing flows back. Reporting is best effort:
a failure prints one line and never changes a command's exit code, because the
next report carries the full state anyway.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

SCHEMA = 1
ENV_URL = "PIPELINE_PORTAL_URL"
ENV_KEY = "PIPELINE_PORTAL_KEY"
TIMEOUT = 4.0
MAX_ITEMS = 100
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}

# command -> subcommands that change what the portal shows (None = any)
PUSH_RULES: dict[str, set[str] | None] = {
    "init": None,
    "update": None,
    "uninstall": None,
    "plugins": {"install", "uninstall"},
    "features": {"enable", "disable"},
    "obs": {"install", "uninstall", "flush"},
    "memory": {"link", "import-local"},
    "knowledge": {"init", "extract"},
    "scan": None,
    "run": None,
    "resume": None,
    "approve": None,
    "license": {"activate"},
}


class PortalLinkError(Exception):
    """A connection problem the user can act on."""


# -- connection --------------------------------------------------------------------


def connection_path(home: Path | None = None) -> Path:
    return (home or Path.home()) / ".pipeline" / "portal.json"


def _key(project: Path) -> str:
    return Path(project).expanduser().resolve().as_posix()


def _read_all(home: Path | None) -> dict[str, Any]:
    try:
        data = json.loads(connection_path(home).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "connections": {}}
    return data if isinstance(data, dict) and isinstance(data.get("connections"), dict) else {"version": 1, "connections": {}}


def load_connection(project: Path, home: Path | None = None) -> dict[str, str] | None:
    url, key = os.environ.get(ENV_URL, "").strip(), os.environ.get(ENV_KEY, "").strip()
    if url and key:
        return {"url": url.rstrip("/"), "key": key}
    row = _read_all(home)["connections"].get(_key(project))
    if isinstance(row, dict) and row.get("url") and row.get("key"):
        return {"url": str(row["url"]), "key": str(row["key"])}
    return None


def validate_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise PortalLinkError("the portal URL must start with https:// (or http:// for localhost)")
    if parsed.scheme == "http" and (parsed.hostname or "") not in LOCAL_HOSTS:
        raise PortalLinkError("the ingest key would travel unencrypted; use an https:// portal URL")
    return url.strip().rstrip("/")


def save_connection(project: Path, url: str, key: str, home: Path | None = None) -> None:
    data = _read_all(home)
    data["connections"][_key(project)] = {"url": url, "key": key}
    path = connection_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass


def remove_connection(project: Path, home: Path | None = None) -> bool:
    data = _read_all(home)
    if data["connections"].pop(_key(project), None) is None:
        return False
    connection_path(home).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return True


# -- building the report -------------------------------------------------------------


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _kit_info(project: Path) -> dict[str, Any]:
    marker = _read_json(project / ".pipeline" / "install.json")
    if marker is None:
        return {"installed": False}
    installed = marker.get("version")
    running = None
    behind = None
    try:
        from pipeline_kit.install import parse_semver, version

        running = version()
        behind = parse_semver(str(installed)) < parse_semver(running) if installed else None
    except Exception:  # noqa: BLE001 - a version quirk must never block a report
        pass
    return {
        "installed": True,
        "version": installed,
        "running": running,
        "behind": behind,
        "mode": marker.get("mode") or "kit",
        "scope": marker.get("scope"),
    }


def _features(project: Path) -> dict[str, str]:
    try:
        from pipeline_features.commands import snapshot

        return {name: str(state) for name, (state, _detail) in snapshot(project).items()}
    except Exception:  # noqa: BLE001
        return {}


def _plugins(project: Path) -> dict[str, Any]:
    out: dict[str, Any] = {}
    try:
        from pipeline_plugins.graphify import graph_freshness

        state = (graph_freshness(project) or {}).get("state")
        out["graphify"] = {"graph": str(state) if state else "unknown"}
    except Exception:  # noqa: BLE001
        pass
    try:
        from pipeline_plugins.archify import architecture_diagrams_enabled

        out["archify"] = {"enabled": bool(architecture_diagrams_enabled(project))}
    except Exception:  # noqa: BLE001
        pass
    return out


def _packages() -> dict[str, bool]:
    import importlib.util

    def has(name: str) -> bool:
        try:
            return importlib.util.find_spec(name) is not None
        except (ImportError, ValueError):
            return False

    return {"assess": has("pipeline_assess"), "memory": has("pipeline_memory")}


def _observability(project: Path) -> dict[str, Any]:
    ledger = project / ".pipeline" / "state" / "obs" / "events.jsonl"
    cfg: dict[str, Any] = {}
    offset = 0
    try:
        from pipeline_observability.export import load_obs_config, read_offset

        cfg, offset = load_obs_config(project), read_offset(project)
    except Exception:  # noqa: BLE001
        pass
    size = ledger.stat().st_size if ledger.is_file() else 0
    return {
        "enabled": cfg.get("enabled") is True,
        "adapter": str(cfg.get("adapter") or "langfuse"),
        "unflushed_bytes": max(0, size - offset),
    }


def _runs(project: Path) -> list[dict[str, Any]]:
    out = []
    runs_dir = project / ".pipeline" / "state" / "runs"
    for path in sorted(runs_dir.glob("*.json")) if runs_dir.is_dir() else []:
        run = _read_json(path)
        if not run:
            continue
        gates = run.get("gates") or {}
        out.append({
            "slug": str(run.get("slug") or path.stem),
            "workflow": run.get("workflow"),
            "status": run.get("status"),
            "current_node": run.get("current_node"),
            "updated_at": run.get("updated_at"),
            "pending_gates": sorted(g for g, info in gates.items() if (info or {}).get("status") != "approved"),
        })
    out.sort(key=lambda r: str(r.get("updated_at") or ""), reverse=True)
    return out[:MAX_ITEMS]


def _boards(project: Path) -> list[dict[str, Any]]:
    cfg = _read_json(project / ".pipeline" / "config.json") or {}
    try:
        from pipeline_kit.paths import artifact_dir_name, artifact_root

        root = artifact_root(project, cfg) / artifact_dir_name(cfg)
    except Exception:  # noqa: BLE001
        root = project / "features"
    out = []
    for slug_dir in sorted(p for p in root.iterdir() if p.is_dir()) if root.is_dir() else []:
        board = _read_json(slug_dir / "pipeline-state.json")
        if not board:
            continue
        out.append({
            "slug": str(board.get("slug") or slug_dir.name),
            "workflow": board.get("workflow"),
            "current_step": board.get("current_step"),
            "current_status": board.get("current_status"),
            "updated_at": board.get("updated_at"),
        })
    out.sort(key=lambda b: str(b.get("updated_at") or ""), reverse=True)
    return out[:MAX_ITEMS]


def _doctor(project: Path) -> dict[str, Any]:
    pack = project / ".pipeline"
    checks = {"install marker": (pack / "install.json").is_file(), "configuration": (pack / "config.json").is_file()}
    for loader in (
        lambda: __import__("knowledge.doctor", fromlist=["x"]).graphify_doctor_checks(project),
        lambda: __import__("pipeline_plugins.archify", fromlist=["x"]).archify_doctor_checks(project),
        lambda: __import__("pipeline_observability.commands", fromlist=["x"]).obs_doctor_checks(pack),
    ):
        try:
            _info, extra = loader()
            checks.update(extra)
        except Exception:  # noqa: BLE001 - an absent capability is not a failed check
            continue
    return {"passed": sum(1 for v in checks.values() if v), "total": len(checks), "failed": sorted(k for k, v in checks.items() if not v)}


def _license() -> dict[str, Any]:
    try:
        from pipeline_kit import license as lic

        claims = lic.verify_token(lic.read_token())
    except Exception as exc:  # noqa: BLE001
        reason = str(exc)
        return {"state": "expired" if reason == "expired" else "missing"}
    days_left = max(0, int((claims["exp"] - time.time()) // 86400))
    return {
        "state": "expiring" if days_left <= 30 else "active",
        "org": claims["org"],
        "days_left": days_left,
        "expires": time.strftime("%Y-%m-%d", time.gmtime(claims["exp"])),
        "features": sorted(claims["features"]),
    }


def build_report(project: Path, reason: str) -> dict[str, Any]:
    project = Path(project).expanduser().resolve()
    kit = _kit_info(project)
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "reason": reason,
        "sent_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "project": {"name": project.name},
        "kit": kit,
        "packages": _packages(),
        "license": _license(),
    }
    if kit.get("installed"):
        report.update(
            features=_features(project),
            plugins=_plugins(project),
            observability=_observability(project),
            runs=_runs(project),
            boards=_boards(project),
            doctor=_doctor(project),
        )
    return report


# -- transport -----------------------------------------------------------------------


def _request(method: str, url: str, key: str, body: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": "pipeline-kit-portal-link"},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:  # noqa: S310 - scheme checked in validate_url
            return resp.status, json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            payload = {}
        return exc.code, payload
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise PortalLinkError(f"cannot reach {url.split('/api/')[0]}: {getattr(exc, 'reason', exc)}") from exc


def _explain(status: int, payload: dict[str, Any]) -> str:
    err = payload.get("error") or {}
    msg = err.get("message") or f"HTTP {status}"
    if status == 401:
        return "the portal did not accept this key. Copy it again from the portal, or rotate it there."
    return f"{msg}{' ' + err['hint'] if err.get('hint') else ''}"


def ping(url: str, key: str) -> dict[str, Any]:
    status, payload = _request("GET", f"{url}/api/ingest/v1/ping", key)
    if status != 200:
        raise PortalLinkError(_explain(status, payload))
    return payload


def push(project: Path, reason: str, *, home: Path | None = None) -> dict[str, Any]:
    conn = load_connection(project, home)
    if not conn:
        raise PortalLinkError("this project is not connected. Run: pipeline-kit portal connect --url URL --key KEY")
    status, payload = _request("POST", f"{conn['url']}/api/ingest/v1/report", conn["key"], build_report(project, reason))
    if status != 200:
        raise PortalLinkError(_explain(status, payload))
    return payload


def should_push(command: str, subcommand: str | None) -> bool:
    if command not in PUSH_RULES:
        return False
    allowed = PUSH_RULES[command]
    return allowed is None or (subcommand or "") in allowed


def push_after(command: str, subcommand: str | None, project: Path, *, home: Path | None = None) -> None:
    """Called after a command that changed local state. Silent when not connected."""
    if not should_push(command, subcommand) or load_connection(project, home) is None:
        return
    try:
        push(project, f"{command}{'.' + subcommand if subcommand else ''}", home=home)
    except PortalLinkError as exc:
        print(f"portal: could not report this change ({exc}). It will be included in the next report.", file=sys.stderr)
    except Exception as exc:  # noqa: BLE001 - reporting must never break the command
        print(f"portal: could not report this change ({exc}).", file=sys.stderr)


# -- commands ------------------------------------------------------------------------


def cmd_connect(project: Path, *, url: str, key: str, home: Path | None = None) -> int:
    try:
        url = validate_url(url)
    except PortalLinkError as exc:
        print(f"portal: {exc}", file=sys.stderr)
        return 64
    if not key.strip():
        print("portal: --key is required (create one in the portal under Projects)", file=sys.stderr)
        return 64
    try:
        who = ping(url, key.strip())
    except PortalLinkError as exc:
        print(f"portal: {exc}", file=sys.stderr)
        return 1
    save_connection(project, url, key.strip(), home)
    try:
        push(project, "connect", home=home)
    except PortalLinkError as exc:
        print(f"portal: connected, but the first report failed ({exc}). Run: pipeline-kit portal push", file=sys.stderr)
        return 1
    print(f"connected to {who.get('org', 'the portal')} as project '{who.get('project', project.name)}'")
    return 0


def cmd_status(project: Path, *, home: Path | None = None) -> int:
    conn = load_connection(project, home)
    if not conn:
        print("not connected")
        return 0
    print(f"portal: {conn['url']}")
    try:
        who = ping(conn["url"], conn["key"])
    except PortalLinkError as exc:
        print(f"status: unreachable or rejected ({exc})")
        return 1
    print(f"project: {who.get('project')}  organization: {who.get('org')}")
    print(f"last report: {who.get('last_report') or 'never'}")
    return 0


def cmd_push(project: Path, *, home: Path | None = None) -> int:
    try:
        push(project, "manual", home=home)
    except PortalLinkError as exc:
        print(f"portal: {exc}", file=sys.stderr)
        return 1
    print("reported")
    return 0


def cmd_disconnect(project: Path, *, home: Path | None = None) -> int:
    if remove_connection(project, home):
        print("disconnected. The portal keeps its last report; rotate or delete the project there if needed.")
    else:
        print("not connected")
    return 0
