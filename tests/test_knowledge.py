"""Knowledge CLI: official Graphify only, opt-in overlay, no homemade graph."""

from __future__ import annotations

import json
import os
import runpy
import stat
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
INSTALL = REPO / "install.py"


def _run_cli(argv: list[str]) -> int:
    ns = runpy.run_path(str(INSTALL))
    return int(ns["cli_main"](argv))


def _init_pack(app: Path) -> None:
    assert _run_cli(["init", str(app), "--ide", "none"]) == 0


def _fake_exe(path: Path, *, exit_code: int = 0, stderr: str = "", stdout: str = "") -> None:
    """Create a PATH-visible executable that works on Windows and POSIX."""
    if os.name == "nt":
        cmd = Path(str(path) + ".cmd")
        lines = ["@echo off"]
        if stdout:
            lines.append(f"echo {stdout}")
        if stderr:
            lines.append(f"echo {stderr} 1>&2")
        lines.append(f"exit /b {exit_code}")
        cmd.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
        return
    body = "#!/bin/sh\n"
    if stdout:
        body += f"echo {stdout}\n"
    if stderr:
        body += f"echo {stderr} >&2\n"
    body += f"exit {exit_code}\n"
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def test_knowledge_package_never_imports_graphify():
    import re

    banned = re.compile(r"^\s*(import graphify|from graphify)\b", re.M)
    for path in (
        list((REPO / "capabilities" / "knowledge").glob("*.py"))
        + list((REPO / "capabilities" / "plugins").glob("*.py"))
        + list((REPO / "capabilities" / "feature_flags").glob("*.py"))
        + list((REPO / "packages" / "pipeline-kit-assess" / "pipeline_assess").glob("*.py"))
    ):
        assert banned.search(path.read_text(encoding="utf-8")) is None, path.name


def test_init_and_update_do_not_enable_test_design(tmp_path: Path):
    app = tmp_path / "app"
    app.mkdir()
    _init_pack(app)
    cfg = json.loads((app / ".pipeline" / "config.json").read_text(encoding="utf-8"))
    block = cfg.get("test_design") or {}
    assert block.get("enabled") is not True
    assert "test-designer-agent" not in cfg["workflows"]["feature-development"]["classes"]["feature"]
    assert _run_cli(["update", str(app), "--ide", "none"]) == 0
    cfg = json.loads((app / ".pipeline" / "config.json").read_text(encoding="utf-8"))
    block = cfg.get("test_design") or {}
    assert block.get("enabled") is not True


def test_knowledge_init_enables_overlay_without_extract(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    app = tmp_path / "app"
    app.mkdir()
    _init_pack(app)
    assert _run_cli(["knowledge", "init", str(app)]) == 0
    out = capsys.readouterr().out
    assert "test_design.enabled: true" in out
    cfg = json.loads((app / ".pipeline" / "config.json").read_text(encoding="utf-8"))
    assert cfg["test_design"]["enabled"] is True
    assert cfg["test_design"]["graph_provider"] == "graphify-cli"
    assert (app / "test-knowledge" / "manifest.json").is_file()
    assert (app / "test-knowledge" / "actions.json").is_file()
    assert not (app / "graphify-out" / "graph.json").exists()


def test_knowledge_status_without_graphify(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    app = tmp_path / "app"
    app.mkdir()
    monkeypatch.setenv("PATH", str(tmp_path / "empty-bin"))
    (tmp_path / "empty-bin").mkdir()
    assert _run_cli(["knowledge", "status", str(app)]) == 0
    out = capsys.readouterr().out
    assert "graphify: missing" in out
    assert "uv tool install graphifyy && graphify install" in out
    assert "graphify extract . --code-only" in out
    assert "test_design.enabled: false" in out


def test_extract_missing_graphify_writes_no_graph(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    app = tmp_path / "app"
    app.mkdir()
    monkeypatch.setenv("PATH", str(tmp_path / "empty-bin"))
    (tmp_path / "empty-bin").mkdir()
    assert _run_cli(["knowledge", "extract", str(app)]) == 1
    err = capsys.readouterr().err
    assert "uv tool install graphifyy && graphify install" in err
    assert "graphify extract . --code-only" in err
    assert not (app / "graphify-out" / "graph.json").exists()


def test_extract_failed_cli_writes_no_graph(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    app = tmp_path / "app"
    app.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _fake_exe(bin_dir / "graphify", exit_code=2, stderr="official-fail")
    monkeypatch.setenv("PATH", str(bin_dir))
    assert _run_cli(["knowledge", "extract", str(app)]) == 1
    err = capsys.readouterr().err
    assert "graphify extract failed" in err
    assert "uv tool install graphifyy && graphify install" in err
    assert not (app / "graphify-out" / "graph.json").exists()


def test_doctor_stays_ready_without_graphify(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    app = tmp_path / "app"
    app.mkdir()
    _init_pack(app)
    monkeypatch.setenv("PATH", str(tmp_path / "empty-bin"))
    (tmp_path / "empty-bin").mkdir()
    assert _run_cli(["doctor", str(app), "--ide", "none"]) == 0
    out = capsys.readouterr().out
    assert "info  graphify: missing" in out
    assert "info  graphify-out/graph.json: absent" in out
    version = (REPO / "VERSION").read_text(encoding="utf-8").strip()
    assert f"pipeline-kit {version} is ready" in out


def test_doctor_fails_when_enabled_and_graph_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    app = tmp_path / "app"
    app.mkdir()
    _init_pack(app)
    assert _run_cli(["knowledge", "init", str(app)]) == 0
    monkeypatch.setenv("PATH", str(tmp_path / "empty-bin"))
    (tmp_path / "empty-bin").mkdir()
    assert _run_cli(["doctor", str(app), "--ide", "none"]) == 1


def test_promote_valid_candidates(tmp_path: Path):
    app = tmp_path / "app"
    app.mkdir()
    _init_pack(app)
    assert _run_cli(["knowledge", "init", str(app)]) == 0
    run = app / "test-knowledge" / "_candidates" / "run-1"
    run.mkdir(parents=True)
    (run / "actions.json").write_text(
        json.dumps(
            {
                "version": 1,
                "items": [
                    {"id": "ACT-submit", "name": "submit", "evidence": "inferred"}
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    assert _run_cli(["knowledge", "validate", str(app), "--run", "run-1"]) == 0
    assert _run_cli(["knowledge", "promote", str(app), "--run", "run-1"]) == 0
    promoted = json.loads((app / "test-knowledge" / "actions.json").read_text())
    assert promoted["items"][0]["id"] == "ACT-submit"


def test_render_writes_feature_views_only(tmp_path: Path):
    app = tmp_path / "app"
    app.mkdir()
    design = app / "features" / "demo-slug" / "test-design"
    design.mkdir(parents=True)
    (design / "cases.json").write_text(
        json.dumps(
            {
                "version": 1,
                "cases": [
                    {
                        "id": "TC-1",
                        "title": "Operator opens Run from the left nav",
                        "spec": "child-a",
                        "ac": "AC-1",
                        "fr": "FR-1",
                        "level": "ui",
                        "type": "happy",
                        "fixtures": [
                            {
                                "id": "FIX-session",
                                "text": "Browser at the local operator-console base URL",
                            }
                        ],
                        "actions": ["ACT-nav-run"],
                        "oracles": ["ORC-run-form"],
                        "steps": [
                            {
                                "do": "Open the local operator console in the browser",
                                "action_id": "ACT-open-console",
                            },
                            {
                                "do": "Click Run in the left-hand navigation",
                                "action_id": "ACT-nav-run",
                            },
                        ],
                        "expected": [
                            {
                                "see": "The Run page shows the start-run form",
                                "oracle_id": "ORC-run-form",
                            }
                        ],
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    assert _run_cli(["knowledge", "render", str(app), "--slug", "demo-slug"]) == 0
    cases = (app / "features" / "demo-slug" / "qa-test-cases.md").read_text()
    assert "TC-1" in cases
    assert "Click Run in the left-hand navigation" in cases
    assert "The Run page shows the start-run form" in cases
    assert "**Steps**" in cases
    plan_view = (app / "features" / "demo-slug" / "test-design" / "test-plan-view.md").read_text()
    assert "features/demo-slug/qa-test-cases.md" in plan_view
    assert "features/{slug}/qa-test-cases.md" not in plan_view
    assert not (app / "automation-tests").exists()


def test_test_designer_allowlist_installs(tmp_path: Path):
    app = tmp_path / "app"
    app.mkdir()
    _init_pack(app)
    loader = app / ".pipeline" / "loader" / "load_workflow.py"
    result = subprocess.run(
        [
            sys.executable,
            str(loader),
            "--workflow",
            "feature-development",
            "--step",
            "test-designer-agent",
            "--slug",
            "try-designer",
        ],
        cwd=app,
        check=True,
        capture_output=True,
        text=True,
    )
    pack = json.loads((app / "features" / "try-designer" / "context-pack.json").read_text())
    assert pack["step"] == "test-designer-agent"
    assert ".pipeline/agents/test-designer-agent.md" in pack["allowed_reads"]
    assert ".pipeline/skills/test-design/SKILL.md" in pack["allowed_reads"]
    assert result.returncode == 0


def test_bootstrap_workflow_installs(tmp_path: Path):
    app = tmp_path / "app"
    app.mkdir()
    _init_pack(app)
    loader = app / ".pipeline" / "loader" / "load_workflow.py"
    subprocess.run(
        [
            sys.executable,
            str(loader),
            "--workflow",
            "test-knowledge-bootstrap",
            "--step",
            "knowledge-curator-agent",
            "--slug",
            "qa-knowledge-bootstrap",
        ],
        cwd=app,
        check=True,
        capture_output=True,
        text=True,
    )
    pack = json.loads(
        (app / "features" / "qa-knowledge-bootstrap" / "context-pack.json").read_text()
    )
    assert pack["step"] == "knowledge-curator-agent"
    assert ".pipeline/agents/knowledge-curator-agent.md" in pack["allowed_reads"]


def _write_cases(app: Path, slug: str, *, auth: bool = True) -> None:
    design = app / "features" / slug / "test-design"
    design.mkdir(parents=True)
    fixtures = (
        [{"id": "FIX-OPERATOR-SIGNED-IN", "kind": "auth", "text": "signed in"}]
        if auth
        else [{"id": "FIX-session", "text": "browser"}]
    )
    (design / "cases.json").write_text(
        json.dumps(
            {
                "version": 1,
                "cases": [
                    {
                        "id": "TC-1",
                        "title": "Open Run",
                        "level": "ui",
                        "fixtures": fixtures,
                        "steps": [
                            {
                                "do": "Open the console",
                                "action_id": "ACT-open-console",
                                "verb": "goto",
                            },
                            {
                                "do": "Sign in with env names",
                                "action_id": "ACT-login",
                                "verb": "fill",
                                "value_from_env": "E2E_PRODUCER_USERNAME",
                                "control": {"role": "textbox", "name": "Email"},
                            },
                            {
                                "do": "Click Run in the left-hand navigation",
                                "action_id": "ACT-nav-run",
                                "verb": "click",
                                "control": {"role": "link", "name": "Run"},
                            },
                        ],
                        "expected": [{"see": "Start run"}],
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_playwright_codegen_writes_spec_and_skips_login_when_auth(tmp_path: Path):
    app = tmp_path / "app"
    app.mkdir()
    _init_pack(app)
    _write_cases(app, "demo-slug", auth=True)
    locators = {
        "version": 1,
        "cases": {
            "TC-1": {
                "steps": [
                    {"index": 3, "role": "link", "name": "Run"},
                ]
            }
        },
    }
    (app / "features" / "demo-slug" / "test-design" / "locators.json").write_text(
        json.dumps(locators, indent=2) + "\n", encoding="utf-8"
    )
    assert _run_cli(["knowledge", "playwright", str(app), "--slug", "demo-slug"]) == 0
    spec = (app / "automation-tests" / "specs" / "demo-slug" / "TC-1.spec.ts").read_text()
    assert "test('TC-1 Open Run'" in spec
    assert "storageState" in spec
    assert "ACT-login" not in spec
    assert "getByRole(\"link\", { name: \"Run\" })" in spec
    assert (app / "automation-tests" / "specs" / "demo-slug" / "auth.setup.ts").is_file()


def test_playwright_missing_locators_writes_no_spec(tmp_path: Path):
    app = tmp_path / "app"
    app.mkdir()
    _init_pack(app)
    _write_cases(app, "demo-slug", auth=False)
    assert _run_cli(["knowledge", "playwright", str(app), "--slug", "demo-slug"]) == 1
    assert not (app / "automation-tests").exists()


def test_init_pack_skips_telemetry_and_runs_tester_on_micro(tmp_path: Path):
    app = tmp_path / "app"
    app.mkdir()
    _init_pack(app)
    cfg = json.loads((app / ".pipeline" / "config.json").read_text(encoding="utf-8"))
    assert cfg["workflows"]["feature-development"]["skips"]["skip_telemetry"] is True
    assert "telemetry-agent" not in cfg["waves"]["child_chain"]
    assert cfg["workflows"]["feature-development"]["classes"]["micro"][1] == "tester-agent"
    assert cfg["test_design"]["enabled"] is not True
    policy = (app / ".pipeline" / "skills" / "feature-development" / "assets" / "tester-policy.md").read_text()
    assert "| micro | true |" in policy


def test_knowledge_init_enables_playwright_flag(tmp_path: Path):
    app = tmp_path / "app"
    app.mkdir()
    _init_pack(app)
    assert _run_cli(["knowledge", "init", str(app)]) == 0
    cfg = json.loads((app / ".pipeline" / "config.json").read_text(encoding="utf-8"))
    assert cfg["test_design"]["playwright"] is True
    assert cfg["test_design"]["design_only"] is False
