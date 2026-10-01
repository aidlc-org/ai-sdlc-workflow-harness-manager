"""UI designer start gates, consult cap, and mockup-copy write deny."""

from __future__ import annotations

import json
import os
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
INSTALL = REPO / "install.py"

MOCKUP = """<!doctype html>
<html lang="en">
  <head>
    <style>:root { --focus-ring: #0a0; --color-bg: #fff; }</style>
  </head>
  <body>
    <a href="#main">Skip to content</a>
    <main id="main">Leave list</main>
  </body>
</html>
"""


def _init(app: Path) -> None:
    ns = runpy.run_path(str(INSTALL))
    assert int(ns["main"](["--project", str(app), "--ide", "none"])) == 0


def _env() -> dict[str, str]:
    env = os.environ.copy()
    for key in ("PIPELINE_HOOK_SKIP", "PIPELINE_ALLOW_ALL", "CHORUS_TASK_ID", "CHORUS_PORTAL"):
        env.pop(key, None)
    return env


def _hook(app: Path, script: str, payload: dict) -> dict:
    proc = subprocess.run(
        [sys.executable, str(app / ".pipeline" / "hooks" / script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=str(app),
        env=_env(),
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def _route(app: Path, slug: str, **fields: str) -> None:
    folder = app / "features" / slug
    folder.mkdir(parents=True, exist_ok=True)
    rows = {
        "change_class": "feature",
        "workflow": "feature-development",
        "work_source": "text",
        "skip_ui_designer": "false",
        "skip_architect": "false",
        "skip_pm": "false",
        "skip_telemetry": "true",
    }
    rows.update(fields)
    lines = [f"**{key}:** {value}" if key in {"change_class", "workflow", "work_source"} else f"{key}: {value}" for key, value in rows.items()]
    (folder / "route.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _ready(path: Path, body: str = "**status:** SUCCESS\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


@pytest.fixture
def app(tmp_path: Path) -> Path:
    root = tmp_path / "app"
    root.mkdir()
    _init(root)
    return root


def test_ui_designer_denied_when_skipped(app: Path):
    _route(app, "leave-app", skip_ui_designer="true")
    _ready(app / "features" / "leave-app" / "HANDOFF-pm.md")
    (app / "features" / "leave-app" / "prd.md").write_text("# prd\n", encoding="utf-8")
    out = _hook(
        app,
        "subagent-start.py",
        {
            "subagent_type": "ui-designer-agent",
            "prompt": "FEATURE_SLUG: leave-app\nUI_JOB: full\n",
        },
    )
    assert out["permission"] == "deny"


def test_ui_designer_denied_on_micro(app: Path):
    _route(app, "rename-btn", change_class="micro", skip_ui_designer="true")
    out = _hook(
        app,
        "subagent-start.py",
        {
            "subagent_type": "ui-designer-agent",
            "prompt": "FEATURE_SLUG: rename-btn\nUI_JOB: full\n",
        },
    )
    assert out["permission"] == "deny"


def test_ui_designer_denied_without_pm_handoff(app: Path):
    _route(app, "leave-app")
    (app / "features" / "leave-app" / "prd.md").write_text("# prd\n", encoding="utf-8")
    out = _hook(
        app,
        "subagent-start.py",
        {
            "subagent_type": "ui-designer-agent",
            "prompt": "FEATURE_SLUG: leave-app\nUI_JOB: full\n",
        },
    )
    assert out["permission"] == "deny"


def test_ui_designer_denied_without_prd(app: Path):
    _route(app, "leave-app")
    _ready(app / "features" / "leave-app" / "HANDOFF-pm.md")
    out = _hook(
        app,
        "subagent-start.py",
        {
            "subagent_type": "ui-designer-agent",
            "prompt": "FEATURE_SLUG: leave-app\nUI_JOB: full\n",
        },
    )
    assert out["permission"] == "deny"


def test_ui_designer_allowed_after_pm(app: Path):
    _route(app, "leave-app")
    _ready(app / "features" / "leave-app" / "HANDOFF-pm.md")
    (app / "features" / "leave-app" / "prd.md").write_text("# prd\n", encoding="utf-8")
    out = _hook(
        app,
        "subagent-start.py",
        {
            "subagent_type": "ui-designer-agent",
            "prompt": "FEATURE_SLUG: leave-app\nUI_JOB: full\n",
        },
    )
    assert out["permission"] == "allow"


def test_architect_denied_without_ui_handoff_on_feature(app: Path):
    _route(app, "leave-app", skip_ui_designer="false")
    out = _hook(
        app,
        "subagent-start.py",
        {
            "subagent_type": "architect-agent",
            "prompt": "FEATURE_SLUG: leave-app\n",
        },
    )
    assert out["permission"] == "deny"


def test_architect_jira_story_does_not_need_ui_handoff(app: Path):
    _route(app, "story-1", workflow="jira-story", skip_ui_designer="false")
    out = _hook(
        app,
        "subagent-start.py",
        {
            "subagent_type": "architect-agent",
            "prompt": "FEATURE_SLUG: story-1\n",
        },
    )
    assert out["permission"] == "allow"


def test_ui_consult_requires_resume_agent(app: Path):
    _route(app, "leave-app")
    _ready(app / "features" / "leave-app" / "HANDOFF-pm.md")
    (app / "features" / "leave-app" / "prd.md").write_text("# prd\n", encoding="utf-8")
    out = _hook(
        app,
        "subagent-start.py",
        {
            "subagent_type": "ui-designer-agent",
            "prompt": "FEATURE_SLUG: leave-app\nUI_JOB: consult\n",
        },
    )
    assert out["permission"] == "deny"


def test_ui_consult_blocked_at_cap(app: Path):
    _route(app, "leave-app")
    _ready(app / "features" / "leave-app" / "HANDOFF-pm.md")
    (app / "features" / "leave-app" / "prd.md").write_text("# prd\n", encoding="utf-8")
    consult = app / "features" / "leave-app" / "ui"
    consult.mkdir(parents=True)
    (consult / "consult-1.md").write_text("# consult\n", encoding="utf-8")
    out = _hook(
        app,
        "subagent-start.py",
        {
            "subagent_type": "ui-designer-agent",
            "prompt": (
                "FEATURE_SLUG: leave-app\nUI_JOB: consult\n"
                "RESUME_AGENT: architect-agent\n"
            ),
        },
    )
    assert out["permission"] == "deny"


def test_ui_consult_cap_override(app: Path):
    _route(app, "leave-app")
    _ready(app / "features" / "leave-app" / "HANDOFF-pm.md")
    (app / "features" / "leave-app" / "prd.md").write_text("# prd\n", encoding="utf-8")
    consult = app / "features" / "leave-app" / "ui"
    consult.mkdir(parents=True)
    (consult / "consult-1.md").write_text("# consult\n", encoding="utf-8")
    out = _hook(
        app,
        "subagent-start.py",
        {
            "subagent_type": "ui-designer-agent",
            "prompt": (
                "FEATURE_SLUG: leave-app\nUI_JOB: consult\n"
                "RESUME_AGENT: architect-agent\nCONSULT_UI: true\n"
            ),
        },
    )
    assert out["permission"] == "allow"


def test_developer_feature_denied_without_ba_signoff(app: Path):
    _route(app, "leave-app")
    (app / "features" / "leave-app" / "specification.md").write_text("# spec\n", encoding="utf-8")
    out = _hook(
        app,
        "subagent-start.py",
        {
            "subagent_type": "developer-agent",
            "prompt": "FEATURE_SLUG: leave-app\nnext_agent: developer-agent\n",
        },
    )
    assert out["permission"] == "deny"


def test_developer_feature_allowed_with_ba_signoff(app: Path):
    _route(app, "leave-app")
    (app / "features" / "leave-app" / "specification.md").write_text("# spec\n", encoding="utf-8")
    _ready(app / "features" / "leave-app" / "signoff-ba.md", "**SIGNOFF:** approved\n")
    out = _hook(
        app,
        "subagent-start.py",
        {
            "subagent_type": "developer-agent",
            "prompt": "FEATURE_SLUG: leave-app\n",
        },
    )
    assert out["permission"] == "allow"


def test_pre_write_denies_mockup_html_in_src(app: Path):
    out = _hook(
        app,
        "pre-write.py",
        {
            "subagent_type": "developer-agent",
            "path": "src/pages/leave-list.html",
            "contents": MOCKUP,
        },
    )
    assert out["permission"] == "deny"


def test_pre_write_allows_mockups_under_features(app: Path):
    out = _hook(
        app,
        "pre-write.py",
        {
            "subagent_type": "ui-designer-agent",
            "path": "features/leave-app/ui/leave-list.html",
            "contents": MOCKUP,
        },
    )
    assert out["permission"] == "allow"


def test_pre_write_denies_ui_path_reference_in_product_source(app: Path):
    out = _hook(
        app,
        "pre-write.py",
        {
            "subagent_type": "developer-agent",
            "path": "src/App.tsx",
            "contents": "import x from '../../features/leave-app/ui/leave-list.html';\n",
        },
    )
    assert out["permission"] == "deny"


def test_pre_write_allows_normal_app_source(app: Path):
    out = _hook(
        app,
        "pre-write.py",
        {
            "subagent_type": "developer-agent",
            "path": "src/App.tsx",
            "contents": "export default function App() { return <main>Leave</main>; }\n",
        },
    )
    assert out["permission"] == "allow"


def test_pre_write_denies_filename_matching_on_disk_mockup(app: Path):
    ui = app / "features" / "leave-app" / "ui"
    ui.mkdir(parents=True)
    (ui / "leave-list.html").write_text(MOCKUP, encoding="utf-8")
    out = _hook(
        app,
        "pre-write.py",
        {
            "subagent_type": "developer-agent",
            "path": "src/pages/leave-list.html",
            "contents": "<html><body>copied</body></html>\n",
        },
    )
    assert out["permission"] == "deny"
