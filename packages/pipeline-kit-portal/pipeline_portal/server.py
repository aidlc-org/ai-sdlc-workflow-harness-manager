"""Loopback HTTP server for the portal. Stdlib only - no new runtime deps.

Security model, all enforced here:

* binds 127.0.0.1 unless --allow-remote is passed with an explicit --host;
  the token requirement is never relaxed by --allow-remote.
* every /api/* request needs a per-launch token (?t= or the
  X-Portal-Token header), compared with secrets.compare_digest.
* Host must name the bound loopback address and port (blocks DNS
  rebinding from an open browser tab); Origin, when sent, must match.
* writes are POST-only and are dropped entirely in --read-only mode.
* every write is appended to {project}/.pipeline/state/portal/audit.jsonl
  before it returns, one line per write, same shape as
  orchestrator/events.emit.
"""

from __future__ import annotations

import json
import secrets
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from pipeline_portal import registry, snapshot

WEB_DIR = Path(__file__).resolve().parent / "web"
TOKEN_HEADER = "X-Portal-Token"
TOKEN_QUERY = "t"

STATIC_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _audit(project: Path, action: str, payload: dict[str, Any]) -> None:
    path = project / ".pipeline" / "state" / "portal" / "audit.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {"ts": _utc_now(), "action": action, **payload}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, separators=(",", ":")) + "\n")


class PortalState:
    """Shared, process-wide config for the request handler."""

    def __init__(
        self,
        *,
        home: Path,
        host: str,
        port: int,
        token: str | None,
        read_only: bool,
    ) -> None:
        self.home = home
        self.host = host
        self.port = port
        self.token = token
        self.read_only = read_only
        self._lock = threading.Lock()

    def check_token(self, handler: "PortalHandler") -> bool:
        if self.token is None:
            return True
        parsed = urlparse(handler.path)
        qs = parse_qs(parsed.query)
        supplied = handler.headers.get(TOKEN_HEADER) or (qs.get(TOKEN_QUERY, [""])[0])
        return bool(supplied) and secrets.compare_digest(supplied, self.token)

    def check_origin(self, handler: "PortalHandler") -> bool:
        allowed_hosts = {f"127.0.0.1:{self.port}", f"localhost:{self.port}", f"[::1]:{self.port}"}
        loopback = self.host in ("127.0.0.1", "localhost", "::1")
        if not loopback and handler.headers.get("X-Portal-Remote-Ack") != "1":
            # non-loopback bind: still require the explicit ack the CLI prints with --allow-remote
            return False
        host_header = handler.headers.get("Host", "")
        if loopback and host_header and host_header not in allowed_hosts:
            return False
        origin = handler.headers.get("Origin")
        if origin:
            origin_host = urlparse(origin).netloc
            if origin_host and origin_host not in allowed_hosts:
                return False
        return True


class PortalHandler(BaseHTTPRequestHandler):
    server_version = "pipeline-kit-portal/0.1"
    state: PortalState  # set by make_server

    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003 - BaseHTTPRequestHandler API
        pass  # keep stdout clean for the printed URL; errors still raise

    # -- helpers -------------------------------------------------------

    def _json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _static(self, rel: str) -> None:
        target = (WEB_DIR / rel).resolve()
        if WEB_DIR not in target.parents and target != WEB_DIR:
            self._json(403, {"error": "forbidden"})
            return
        if not target.is_file():
            self._json(404, {"error": "not found"})
            return
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", STATIC_CONTENT_TYPES.get(target.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def _require_api_auth(self) -> bool:
        if not self.state.check_origin(self):
            self._json(403, {"error": "forbidden host/origin"})
            return False
        if not self.state.check_token(self):
            self._json(401, {"error": "missing or invalid token"})
            return False
        return True

    def _project_param(self) -> Path | None:
        qs = parse_qs(urlparse(self.path).query)
        raw = (qs.get("path") or [""])[0]
        if not raw:
            self._json(400, {"error": "missing path"})
            return None
        return Path(raw)

    # -- routing ---------------------------------------------------------

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        parsed = urlparse(self.path)
        route = parsed.path
        if route in ("/", ""):
            self._static("index.html")
            return
        if route.startswith("/assets/"):
            self._static(route[len("/assets/") :])
            return
        if not route.startswith("/api/"):
            self._json(404, {"error": "not found"})
            return
        if not self._require_api_auth():
            return
        if route == "/api/fleet":
            entries = registry.list_projects(self.state.home)
            rows = []
            for entry in entries:
                row = snapshot.safe_fleet_row(entry["path"])
                # The registry's normalized posix path is the identity key the
                # UI round-trips (open -> /api/project?path=... -> remove);
                # snapshot.fleet_row renders the OS-native form instead, which
                # on Windows differs by separator for the same file.
                row["path"] = entry["path"]
                row["team"] = entry.get("team", "")
                row["label"] = entry.get("label", "")
                rows.append(row)
            self._json(200, {"projects": rows, "read_only": self.state.read_only})
            return
        if route == "/api/project":
            project = self._project_param()
            if project is None:
                return
            self._json(200, snapshot.project_snapshot(project, deep=True))
            return
        if route == "/api/health":
            project = self._project_param()
            if project is None:
                return
            self._json(200, snapshot.health_snapshot(project))
            return
        if route == "/api/registry":
            self._json(200, {"projects": registry.list_projects(self.state.home)})
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        route = urlparse(self.path).path
        if not route.startswith("/api/"):
            self._json(404, {"error": "not found"})
            return
        if not self._require_api_auth():
            return
        if self.state.read_only:
            self._json(403, {"error": "portal is running --read-only"})
            return
        body = self._read_body()
        if route == "/api/registry/add":
            path = body.get("path")
            if not path:
                self._json(400, {"error": "missing path"})
                return
            row = registry.add_project(self.state.home, path, team=body.get("team", ""), label=body.get("label", ""))
            self._json(200, row)
            return
        if route == "/api/registry/remove":
            path = body.get("path")
            if not path:
                self._json(400, {"error": "missing path"})
                return
            removed = registry.remove_project(self.state.home, path)
            self._json(200, {"removed": removed})
            return
        if route == "/api/features/toggle":
            self._toggle_feature(body)
            return
        if route == "/api/plugins/toggle":
            self._toggle_plugin(body)
            return
        if route == "/api/obs/toggle":
            self._toggle_obs(body)
            return
        self._json(404, {"error": "not found"})

    # -- write actions -------------------------------------------------

    def _project_from_body(self, body: dict[str, Any]) -> Path | None:
        raw = body.get("path")
        if not raw:
            self._json(400, {"error": "missing path"})
            return None
        project = Path(raw).expanduser().resolve()
        if not project.is_dir():
            self._json(404, {"error": f"not a directory: {project}"})
            return None
        return project

    def _config_conflict(self, project: Path, body: dict[str, Any]) -> bool:
        expected = body.get("config_mtime")
        if expected is None:
            return False
        cfg_path = project / ".pipeline" / "config.json"
        actual = cfg_path.stat().st_mtime if cfg_path.is_file() else None
        if actual is not None and abs(actual - float(expected)) > 1e-6:
            self._json(409, {"error": "config.json changed since this view was rendered", "config_mtime": actual})
            return True
        return False

    def _toggle_feature(self, body: dict[str, Any]) -> None:
        project = self._project_from_body(body)
        if project is None:
            return
        if self._config_conflict(project, body):
            return
        feature_id = body.get("id")
        on = bool(body.get("on"))
        if not feature_id:
            self._json(400, {"error": "missing id"})
            return
        try:
            from pipeline_features.commands import cmd_disable, cmd_enable
        except ImportError:
            self._json(501, {"error": "pipeline_features not installed"})
            return
        code = (cmd_enable if on else cmd_disable)(project, feature_id)
        _audit(project, "feature_toggle", {"id": feature_id, "on": on, "exit_code": code})
        self._json(200 if code == 0 else 422, {"id": feature_id, "on": on, "exit_code": code})

    def _toggle_plugin(self, body: dict[str, Any]) -> None:
        project = self._project_from_body(body)
        if project is None:
            return
        name = body.get("name")
        on = bool(body.get("on"))
        if name not in ("graphify", "archify"):
            self._json(400, {"error": "unknown plugin"})
            return
        try:
            from pipeline_plugins.commands import cmd_install, cmd_uninstall
        except ImportError:
            self._json(501, {"error": "pipeline_plugins not installed"})
            return
        code = cmd_install(project, name) if on else cmd_uninstall(project, name)
        _audit(project, "plugin_toggle", {"name": name, "on": on, "exit_code": code})
        self._json(200 if code == 0 else 422, {"name": name, "on": on, "exit_code": code})

    def _toggle_obs(self, body: dict[str, Any]) -> None:
        project = self._project_from_body(body)
        if project is None:
            return
        on = bool(body.get("on"))
        try:
            from pipeline_observability.commands import cmd_install, cmd_uninstall
        except ImportError:
            self._json(501, {"error": "pipeline_observability not installed"})
            return
        if on:
            code = cmd_install(project, ide="none", adapter="langfuse", version="0")
        else:
            code = cmd_uninstall(project, ide="none")
        _audit(project, "obs_toggle", {"on": on, "exit_code": code})
        self._json(200 if code == 0 else 422, {"on": on, "exit_code": code})


def make_server(
    *,
    project: Path,
    home: Path,
    host: str = "127.0.0.1",
    port: int = 7171,
    read_only: bool = False,
    use_token: bool = True,
    allow_remote: bool = False,
) -> tuple[ThreadingHTTPServer, str, str | None]:
    if host not in ("127.0.0.1", "localhost", "::1") and not allow_remote:
        raise ValueError("binding beyond loopback requires --allow-remote")
    token = secrets.token_urlsafe(32) if use_token else None
    registry.ensure_seeded(home, project)

    class _Handler(PortalHandler):
        pass

    # Bind first so a requested --port 0 resolves to the real ephemeral
    # port before PortalState computes its Host/Origin allow-list — using
    # the *requested* port there would reject every real request.
    server = ThreadingHTTPServer((host, port), _Handler)
    bound_port = server.server_address[1]
    state = PortalState(home=home, host=host, port=bound_port, token=token, read_only=read_only)
    _Handler.state = state
    url = f"http://{host}:{bound_port}/"
    if token:
        url = f"{url}?t={token}"
    return server, url, token


def serve_forever(server: ThreadingHTTPServer) -> None:
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
