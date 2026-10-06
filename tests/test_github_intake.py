"""intake.github.connection and the read-only REST helper."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "kit" / "pipeline" / "skills" / "github-intake" / "scripts" / "github_api.py"
CONFIG = REPO / "kit" / "pipeline" / "config.json"


def _mod():
    spec = importlib.util.spec_from_file_location("github_api", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pack_config_defaults_github_cli_off():
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    github = data["intake"]["github"]
    assert github["enabled"] is False
    assert github["connection"] == "cli"
    assert github["cli"]["bin"] == "gh"
    assert "{N}" in github["cli"]["issue_view"]
    assert "{REPO}" in github["cli"]["issue_view"]
    assert data["workflows"]["github-story"]["source"] == "github"
    assert data["workflows"]["github-bug"]["plan_source"] == "rca.md"


def test_parse_ref_and_issue_payload():
    mod = _mod()
    assert mod.parse_ref("acme/app#12") == ("acme", "app", "12")
    assert mod.parse_ref("https://github.com/acme/app/issues/12") == ("acme", "app", "12")
    assert mod.parse_ref("https://github.com/acme/app/pull/9") == ("acme", "app", "9")
    assert mod.parse_ref("#7", "acme/app") == ("acme", "app", "7")
    raw = {
        "number": 12,
        "title": "Login",
        "body": "Must login\nThen save",
        "state": "open",
        "html_url": "https://github.com/acme/app/issues/12",
        "user": {"login": "ada"},
        "assignees": [{"login": "bob"}],
        "labels": [{"name": "bug"}],
        "comments": [],
    }
    out = mod.issue_payload(raw, "acme", "app")
    assert out["key"] == "acme/app#12"
    assert out["issue_type"] == "bug"
    assert out["summary"] == "Login"
    assert "Must login" in out["description"]
    assert out["reporter"] == "ada"
    assert out["assignee"] == "bob"


def test_api_helper_refuses_missing_token(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]):
    mod = _mod()
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with pytest.raises(SystemExit) as exc:
        mod.cmd_issue_get("acme/app#1")
    assert exc.value.code == mod.AUTH
    err = capsys.readouterr().err
    assert "GH_TOKEN" in err


def test_parse_ref_bare_number_without_repo_exits(capsys: pytest.CaptureFixture[str]):
    mod = _mod()
    with pytest.raises(SystemExit) as exc:
        mod.parse_ref("#12")
    assert exc.value.code == mod.USAGE
    assert "GITHUB_REPO" in capsys.readouterr().err
