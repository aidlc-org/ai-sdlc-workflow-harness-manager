"""intake.jira.connection and the read-only REST helper."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "kit" / "pipeline" / "skills" / "jira-intake" / "scripts" / "jira_api.py"
CONFIG = REPO / "kit" / "pipeline" / "config.json"


def _mod():
    spec = importlib.util.spec_from_file_location("jira_api", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pack_config_defaults_to_mcp_connection():
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    jira = data["intake"]["jira"]
    assert jira["connection"] == "mcp"
    assert jira["cli"]["bin"] == "jira"
    assert "{KEY}" in jira["cli"]["issue_view"]
    assert "{JQL}" in jira["cli"]["search"]


def test_flatten_adf_and_issue_payload():
    mod = _mod()
    adf = {
        "type": "doc",
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "Must login"}]},
            {"type": "paragraph", "content": [{"type": "text", "text": "Then save"}]},
        ],
    }
    text = mod.flatten_adf(adf)
    assert "Must login" in text
    assert "Then save" in text
    raw = {
        "key": "ABC-1",
        "fields": {
            "summary": "Login",
            "issuetype": {"name": "Story"},
            "status": {"name": "To Do"},
            "priority": {"name": "High"},
            "description": adf,
            "labels": ["auth"],
            "components": [{"name": "web"}],
            "reporter": {"displayName": "Ada"},
            "assignee": {"displayName": "Bob"},
            "parent": {},
            "issuelinks": [{"outwardIssue": {"key": "ABC-2"}}],
            "attachment": [{"filename": "shot.png"}],
            "comment": {"comments": []},
        },
        "renderedFields": {},
    }
    out = mod.issue_payload(raw)
    assert out["key"] == "ABC-1"
    assert out["issue_type"] == "Story"
    assert out["summary"] == "Login"
    assert "Must login" in out["description"]
    assert out["reporter"] == "Ada"
    assert out["linked_issues"] == ["ABC-2"]
    assert out["attachments"] == ["shot.png"]


def test_api_helper_refuses_missing_env(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]):
    mod = _mod()
    monkeypatch.delenv("JIRA_BASE_URL", raising=False)
    monkeypatch.delenv("JIRA_API_TOKEN", raising=False)
    monkeypatch.delenv("JIRA_TOKEN", raising=False)
    with pytest.raises(SystemExit) as exc:
        mod.cmd_issue_get("ABC-1")
    assert exc.value.code == mod.USAGE
    err = capsys.readouterr().err
    assert "JIRA_BASE_URL" in err
