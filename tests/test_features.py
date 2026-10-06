"""features CLI writes existing config keys; init defaults stay unchanged."""

from __future__ import annotations

import json
import runpy
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
INSTALL = REPO / "install.py"


def _run_cli(argv: list[str]) -> int:
    ns = runpy.run_path(str(INSTALL))
    return int(ns["cli_main"](argv))


def _init(app: Path) -> None:
    assert _run_cli(["init", str(app), "--ide", "none"]) == 0


def test_features_status_matches_init_defaults(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    app = tmp_path / "app"
    app.mkdir()
    _init(app)
    assert _run_cli(["features", "status", str(app)]) == 0
    out = capsys.readouterr().out
    assert "test-design" in out and "off" in out
    assert "playwright" in out
    assert "telemetry" in out
    assert "tester" in out
    assert "agent-observability" in out
    assert "github-intake" in out
    cfg = json.loads((app / ".pipeline" / "config.json").read_text())
    assert cfg["test_design"]["enabled"] is not True
    assert cfg["intake"]["github"]["enabled"] is not True
    assert cfg["workflows"]["feature-development"]["skips"]["skip_telemetry"] is True


def test_features_enable_disable_telemetry_keeps_other_skips(tmp_path: Path):
    app = tmp_path / "app"
    app.mkdir()
    _init(app)
    assert _run_cli(["features", "enable", "telemetry", str(app)]) == 0
    cfg = json.loads((app / ".pipeline" / "config.json").read_text())
    assert cfg["workflows"]["feature-development"]["skips"]["skip_telemetry"] is False
    assert cfg["workflows"]["jira-bug"]["skips"]["skip_telemetry"] is True
    assert _run_cli(["features", "disable", "telemetry", str(app)]) == 0
    cfg = json.loads((app / ".pipeline" / "config.json").read_text())
    assert cfg["workflows"]["feature-development"]["skips"]["skip_telemetry"] is True


def test_features_playwright_requires_test_design(tmp_path: Path):
    app = tmp_path / "app"
    app.mkdir()
    _init(app)
    assert _run_cli(["features", "enable", "playwright", str(app)]) == 64
    assert _run_cli(["features", "enable", "test-design", str(app)]) == 0
    cfg = json.loads((app / ".pipeline" / "config.json").read_text())
    assert cfg["test_design"]["enabled"] is True
    assert _run_cli(["features", "disable", "test-design", str(app)]) == 0
    cfg = json.loads((app / ".pipeline" / "config.json").read_text())
    assert cfg["test_design"]["enabled"] is False
    assert (app / "test-knowledge" / "manifest.json").is_file()


def test_features_enable_github_intake(tmp_path: Path):
    app = tmp_path / "app"
    app.mkdir()
    _init(app)
    assert _run_cli(["features", "enable", "github-intake", str(app)]) == 0
    cfg = json.loads((app / ".pipeline" / "config.json").read_text())
    assert cfg["intake"]["github"]["enabled"] is True
    assert _run_cli(["features", "disable", "github-intake", str(app)]) == 0
    cfg = json.loads((app / ".pipeline" / "config.json").read_text())
    assert cfg["intake"]["github"]["enabled"] is False
