"""Reporting local state to a portal: metadata only, push on change, never breaks a command."""

from __future__ import annotations

import json
import runpy
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
GOOD_KEY = "pk_test_good"


def _cli(argv: list[str]) -> int:
    return int(runpy.run_path(str(REPO / "install.py"))["cli_main"](argv))


class FakePortal:
    def __init__(self) -> None:
        self.reports: list[dict] = []
        self.pings = 0
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):  # noqa: D102
                pass

            def _auth(self) -> bool:
                return self.headers.get("Authorization") == f"Bearer {GOOD_KEY}"

            def _send(self, status: int, body: dict) -> None:
                raw = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self):  # noqa: N802
                if not self._auth():
                    return self._send(401, {"error": {"code": "bad_key", "message": "bad key"}})
                outer.pings += 1
                self._send(200, {"ok": True, "org": "Acme", "project": "demo", "last_report": None})

            def do_POST(self):  # noqa: N802
                if not self._auth():
                    return self._send(401, {"error": {"code": "bad_key", "message": "bad key"}})
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                outer.reports.append(body)
                self._send(200, {"ok": True})

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def portal():
    p = FakePortal()
    yield p
    p.stop()


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, enterprise_license):
    from pipeline_kit import license as lic

    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    try:
        import pipeline_license as eng

        monkeypatch.setattr(eng.Path, "home", lambda: home)
        assert eng.FEATURES
    except ImportError:
        # Public CI: enterprise_license opens has_feature/require without the engine.
        pass
    # Keep enterprise_license token / open gates; only clear portal connection env.
    for name in ("PIPELINE_PORTAL_URL", "PIPELINE_PORTAL_KEY"):
        monkeypatch.delenv(name, raising=False)
    assert "portal" in lic.FEATURES
    app = tmp_path / "checkout-api"
    app.mkdir()
    assert _cli(["init", str(app), "--ide", "none"]) == 0
    return app, home


def test_report_is_metadata_only(env):
    from pipeline_kit import portal_link

    app, _ = env
    report = portal_link.build_report(app, "manual")
    text = json.dumps(report)
    assert report["schema"] == 1 and report["project"] == {"name": "checkout-api"}
    assert report["kit"]["installed"] is True and report["kit"]["mode"] == "kit"
    assert isinstance(report["features"], dict) and report["features"]
    assert "config" not in report and "token" not in text
    assert str(app) not in text and app.parent.as_posix() not in text  # no filesystem paths
    assert report["doctor"]["total"] >= 2


def test_report_for_uninstalled_project_is_small(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from pipeline_kit import portal_link

    report = portal_link.build_report(tmp_path, "manual")
    assert report["kit"] == {"installed": False} and "features" not in report


def test_connect_verifies_the_key_then_reports(env, portal):
    app, home = env
    assert _cli(["portal", "connect", str(app), "--url", portal.url, "--key", GOOD_KEY]) == 0
    assert portal.pings == 1
    assert [r["reason"] for r in portal.reports] == ["connect"]
    stored = json.loads((home / ".pipeline" / "portal.json").read_text())
    assert next(iter(stored["connections"].values())) == {"url": portal.url, "key": GOOD_KEY}


def test_connect_rejects_a_bad_key_without_saving(env, portal, capsys):
    app, home = env
    assert _cli(["portal", "connect", str(app), "--url", portal.url, "--key", "wrong"]) == 1
    assert "did not accept this key" in capsys.readouterr().err
    assert not (home / ".pipeline" / "portal.json").exists()


def test_connect_refuses_plain_http_to_a_remote_host(env, capsys):
    app, _ = env
    assert _cli(["portal", "connect", str(app), "--url", "http://portal.example.com", "--key", "k"]) == 64
    assert "https://" in capsys.readouterr().err


def test_changes_flow_to_the_portal(env, portal):
    app, _ = env
    assert _cli(["portal", "connect", str(app), "--url", portal.url, "--key", GOOD_KEY]) == 0
    portal.reports.clear()
    assert _cli(["features", "enable", "telemetry", str(app)]) == 0
    assert [r["reason"] for r in portal.reports] == ["features.enable"]
    assert portal.reports[0]["features"]["telemetry"] == "on"
    assert _cli(["features", "disable", "telemetry", str(app)]) == 0
    assert portal.reports[-1]["features"]["telemetry"] == "off"


def test_read_only_commands_do_not_report(env, portal):
    app, _ = env
    _cli(["portal", "connect", str(app), "--url", portal.url, "--key", GOOD_KEY])
    portal.reports.clear()
    assert _cli(["features", "list"]) == 0
    assert _cli(["plugins", "list"]) == 0
    assert portal.reports == []


def test_unconnected_project_stays_silent(env, capsys):
    app, _ = env
    capsys.readouterr()
    assert _cli(["features", "enable", "telemetry", str(app)]) == 0
    assert "portal:" not in capsys.readouterr().err


def test_a_dead_portal_never_breaks_the_command(env, portal, capsys):
    app, _ = env
    assert _cli(["portal", "connect", str(app), "--url", portal.url, "--key", GOOD_KEY]) == 0
    portal.stop()
    capsys.readouterr()
    assert _cli(["features", "enable", "telemetry", str(app)]) == 0
    err = capsys.readouterr().err
    assert "could not report this change" in err and "next report" in err


def test_env_connection_wins_for_ci(env, portal, monkeypatch):
    app, _ = env
    monkeypatch.setenv("PIPELINE_PORTAL_URL", portal.url)
    monkeypatch.setenv("PIPELINE_PORTAL_KEY", GOOD_KEY)
    assert _cli(["features", "enable", "telemetry", str(app)]) == 0
    assert portal.reports and portal.reports[-1]["reason"] == "features.enable"


def test_status_push_and_disconnect(env, portal, capsys):
    app, home = env
    _cli(["portal", "connect", str(app), "--url", portal.url, "--key", GOOD_KEY])
    capsys.readouterr()
    assert _cli(["portal", "status", str(app)]) == 0
    assert "organization: Acme" in capsys.readouterr().out
    portal.reports.clear()
    assert _cli(["portal", "push", str(app)]) == 0
    assert portal.reports[0]["reason"] == "manual"
    assert _cli(["portal", "disconnect", str(app)]) == 0
    assert _cli(["portal", "push", str(app)]) == 1
    assert "not connected" in capsys.readouterr().err
