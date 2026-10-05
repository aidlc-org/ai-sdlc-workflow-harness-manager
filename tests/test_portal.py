"""Portal package: registry CRUD, print-free snapshot shape, and the HTTP server's
auth/read/write/conflict behavior. Writes only under tmp_path."""

from __future__ import annotations

import json
import runpy
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[1]
INSTALL = REPO / "install.py"


def _run_cli(argv: list[str]) -> int:
    ns = runpy.run_path(str(INSTALL))
    return int(ns["cli_main"](argv))


def _init(app: Path) -> None:
    assert _run_cli(["init", str(app), "--ide", "none"]) == 0


# ------------------------------------------------------------------ registry


def test_registry_add_remove_list_round_trip(tmp_path: Path):
    from pipeline_portal import registry

    home = tmp_path / "home"
    project = tmp_path / "app"
    project.mkdir()

    assert registry.list_projects(home) == []
    row = registry.add_project(home, project, team="payments", label="Checkout API")
    assert row["team"] == "payments"
    assert row["label"] == "Checkout API"

    rows = registry.list_projects(home)
    assert len(rows) == 1
    assert rows[0]["path"] == Path(project).resolve().as_posix()

    # idempotent: re-adding updates in place, does not duplicate
    registry.add_project(home, project, team="risk")
    rows = registry.list_projects(home)
    assert len(rows) == 1
    assert rows[0]["team"] == "risk"

    assert registry.remove_project(home, project) is True
    assert registry.list_projects(home) == []
    assert registry.remove_project(home, project) is False


def test_portal_cli_add_list_remove(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    home = tmp_path / "home"
    app = tmp_path / "app"
    app.mkdir()
    _init(app)

    assert _run_cli(["portal", "add", str(app), "--team", "payments", "--home", str(home)]) == 0
    assert _run_cli(["portal", "list", "--home", str(home)]) == 0
    out = capsys.readouterr().out
    assert "payments" in out
    assert str(app) in out or app.name in out

    assert _run_cli(["portal", "remove", str(app), "--home", str(home)]) == 0
    assert _run_cli(["portal", "remove", str(app), "--home", str(home)]) == 1


# ------------------------------------------------------------------ snapshot


def test_fleet_row_reports_feature_flags_after_init(tmp_path: Path):
    from pipeline_portal import snapshot

    app = tmp_path / "app"
    app.mkdir()
    _init(app)

    row = snapshot.fleet_row(app)
    assert row["installed"] is True
    assert row["mode"] == "kit"
    assert row["features"]["flags"]["telemetry"]["state"] == "off"
    # Freshly installed by this same checkout: never reported as behind.
    assert row["current_kit_version"] == (REPO / "VERSION").read_text(encoding="utf-8").strip()
    assert row["behind"] is False
    assert row["runs"] == []
    assert row["boards"] == []


def test_fleet_row_degrades_on_missing_path(tmp_path: Path):
    from pipeline_portal import snapshot

    row = snapshot.safe_fleet_row(tmp_path / "does-not-exist")
    assert row["reachable"] is False
    assert row["installed"] is False


def test_fleet_row_on_uninstalled_project_does_not_crash(tmp_path: Path):
    from pipeline_portal import snapshot

    app = tmp_path / "bare"
    app.mkdir()
    row = snapshot.fleet_row(app)
    assert row["reachable"] is True
    assert row["installed"] is False


def test_fleet_row_flags_a_project_behind_the_running_kit_version(tmp_path: Path):
    from pipeline_portal import snapshot

    app = tmp_path / "app"
    app.mkdir()
    _init(app)

    marker_path = app / ".pipeline" / "install.json"
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    marker["version"] = "0.0.1"
    marker_path.write_text(json.dumps(marker), encoding="utf-8")

    row = snapshot.fleet_row(app)
    assert row["version"] == "0.0.1"
    assert row["behind"] is True


def test_project_snapshot_deep_has_plugins_extensions_doctor(tmp_path: Path):
    from pipeline_portal import snapshot

    app = tmp_path / "app"
    app.mkdir()
    _init(app)

    data = snapshot.project_snapshot(app, deep=True)
    assert data["installed"] is True
    assert "plugins" in data and "graphify" in data["plugins"]
    assert data["extensions"]["mode"] == "kit"
    assert any(wf["name"] == "feature-development" for wf in data["extensions"]["workflows"])
    assert data["doctor"]["total"] >= 2
    assert data["config_mtime"] is not None


def test_health_snapshot_without_ledger(tmp_path: Path):
    from pipeline_portal import snapshot

    app = tmp_path / "app"
    app.mkdir()
    _init(app)

    health = snapshot.health_snapshot(app)
    assert health["available"] is False


# ------------------------------------------------------------------ server


@pytest.fixture
def running_server(tmp_path: Path):
    from pipeline_portal.server import make_server

    app = tmp_path / "app"
    home = tmp_path / "home"
    app.mkdir()
    _init(app)

    server, url, token = make_server(project=app, home=home, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    try:
        yield {"app": app, "home": home, "port": port, "token": token, "base": f"http://127.0.0.1:{port}"}
    finally:
        server.shutdown()
        server.server_close()


def _get(base: str, path: str, *, token: str | None = None) -> tuple[int, dict[str, Any]]:
    url = f"{base}{path}"
    if token:
        url += ("&" if "?" in path else "?") + f"t={token}"
    try:
        with urllib.request.urlopen(url) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        return exc.code, json.loads(body) if body else {}


def _post(base: str, path: str, payload: dict[str, Any], *, token: str | None = None) -> tuple[int, dict[str, Any]]:
    url = f"{base}{path}"
    if token:
        url += ("&" if "?" in path else "?") + f"t={token}"
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        return exc.code, json.loads(body) if body else {}


def test_server_rejects_missing_and_wrong_token(running_server):
    status, _ = _get(running_server["base"], "/api/fleet")
    assert status == 401
    status, _ = _get(running_server["base"], "/api/fleet", token="wrong-token")
    assert status == 401


def test_server_accepts_correct_token_and_serves_fleet(running_server):
    status, data = _get(running_server["base"], "/api/fleet", token=running_server["token"])
    assert status == 200
    assert len(data["projects"]) == 1
    assert data["projects"][0]["path"] == Path(running_server["app"]).resolve().as_posix()


def test_server_serves_static_index_without_token(running_server):
    with urllib.request.urlopen(f"{running_server['base']}/") as resp:
        assert resp.status == 200
        assert b"pipeline-kit portal" in resp.read()


def test_server_toggle_writes_config_and_audit_line(running_server):
    base, token, app = running_server["base"], running_server["token"], running_server["app"]
    status, data = _post(
        base, "/api/features/toggle", {"path": str(app), "id": "telemetry", "on": True}, token=token
    )
    assert status == 200
    assert data["exit_code"] == 0

    cfg = json.loads((app / ".pipeline" / "config.json").read_text(encoding="utf-8"))
    assert cfg["workflows"]["feature-development"]["skips"]["skip_telemetry"] is False

    audit = (app / ".pipeline" / "state" / "portal" / "audit.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(audit) == 1
    row = json.loads(audit[0])
    assert row["action"] == "feature_toggle"
    assert row["id"] == "telemetry"
    assert row["on"] is True


def test_server_rejects_stale_config_mtime_with_409(running_server):
    base, token, app = running_server["base"], running_server["token"], running_server["app"]
    status, data = _post(
        base,
        "/api/features/toggle",
        {"path": str(app), "id": "telemetry", "on": True, "config_mtime": 1.0},
        token=token,
    )
    assert status == 409
    assert "config.json changed" in data["error"]


def test_read_only_server_blocks_writes(tmp_path: Path):
    from pipeline_portal.server import make_server

    app = tmp_path / "app"
    home = tmp_path / "home"
    app.mkdir()
    _init(app)

    server, _url, token = make_server(project=app, home=home, port=0, read_only=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_address[1]}"
        status, data = _post(
            base, "/api/features/toggle", {"path": str(app), "id": "telemetry", "on": True}, token=token
        )
        assert status == 403
        assert "read-only" in data["error"]
    finally:
        server.shutdown()
        server.server_close()


def test_make_server_rejects_non_loopback_without_allow_remote(tmp_path: Path):
    from pipeline_portal.server import make_server

    app = tmp_path / "app"
    app.mkdir()
    _init(app)
    with pytest.raises(ValueError):
        make_server(project=app, home=tmp_path / "home", host="0.0.0.0", port=0)
