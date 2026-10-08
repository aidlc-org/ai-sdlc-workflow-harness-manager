"""Installer tests. Writes only under tmp_path."""

from __future__ import annotations

import importlib.util
import json
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
INSTALL = REPO / "install.py"


def _run(argv: list[str]) -> int:
    ns = runpy.run_path(str(INSTALL))
    return int(ns["main"](argv))


def _run_cli(argv: list[str]) -> int:
    ns = runpy.run_path(str(INSTALL))
    return int(ns["cli_main"](argv))


def test_source_layout_keeps_import_names():
    from layout import SOURCE_PACKAGES, install_source_importers

    install_source_importers()
    for name, path in SOURCE_PACKAGES.items():
        assert path.is_dir(), name
        assert (path / "__init__.py").is_file(), name
    import knowledge
    import pipeline_eval
    import pipeline_features
    import pipeline_observability
    import pipeline_orchestrator
    import pipeline_plugins
    from pipeline_kit import paths as pk_paths

    assert Path(knowledge.__file__).resolve().is_relative_to(REPO / "capabilities" / "knowledge")
    assert Path(pipeline_plugins.__file__).resolve().is_relative_to(REPO / "capabilities" / "plugins")
    assert Path(pipeline_orchestrator.__file__).resolve().is_relative_to(REPO / "orchestrator")
    assert Path(pk_paths.__file__).resolve() == (REPO / "paths.py").resolve()
    assert callable(pk_paths.feature_dir)


def test_source_pack_is_bundled_kit():
    ns = runpy.run_path(str(INSTALL))
    pack = ns["source_pack"]()
    assert pack == ns["bundled_pack"]()
    assert (pack / "workflows" / "ask.json").is_file()


def test_default_args_create_project_pipeline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    assert _run(["--ide", "none"]) == 0
    assert (tmp_path / ".pipeline" / "workflows" / "ask.json").is_file()
    assert (tmp_path / ".pipeline" / "install.json").is_file()


def test_project_install_and_uninstall(tmp_path: Path):
    app = tmp_path / "app"
    app.mkdir()
    assert _run(["--project", str(app), "--ide", "none"]) == 0
    assert (app / ".pipeline" / "loader" / "load_workflow.py").is_file()
    assert (app / ".pipeline" / "workflows" / "ask.json").is_file()
    assert (app / ".pipeline" / "agents" / "developer-agent.md").is_file()
    assert (app / ".pipeline" / "agents" / "architect-agent.md").is_file()
    assert (app / ".pipeline" / "config.json").is_file()
    cfg_after = json.loads((app / ".pipeline" / "config.json").read_text(encoding="utf-8"))
    feature_chain = cfg_after["workflows"]["feature-development"]["classes"]["feature"]
    assert "architect-agent" in feature_chain
    assert "@signoff:requirements" in feature_chain
    assert "@signoff:architect" in feature_chain
    assert "@signoff:ba" in feature_chain
    assert cfg_after["gates"]["require_planning_signoff_before_build"] is True
    assert (app / ".pipeline" / "install.json").is_file()
    assert (app / ".pipeline" / "docs" / "CUSTOMER-GUIDE.md").is_file()
    assert (app / ".pipeline" / "docs" / "DOCUMENT-STANDARD.md").is_file()
    guide = (app / ".pipeline" / "docs" / "CUSTOMER-GUIDE.md").read_text(encoding="utf-8")
    assert "customer guide" in guide.lower()
    assert "chorus" not in guide.lower()
    script = (app / ".pipeline" / "skills" / "local-deployment" / "scripts" / "deploy-local.sh").read_text(
        encoding="utf-8"
    )
    assert "placeholder" in script.lower()
    assert "ecommerce-store" not in script
    assert "chorus" not in script.lower()
    assert not (app / ".cursor").exists()
    cfg = json.loads((app / ".pipeline" / "config.json").read_text(encoding="utf-8"))
    assert cfg["verify"]["rules"] == []
    assert "ask" in cfg["workflows"]
    assert _run(["--uninstall", "--project", str(app)]) == 0
    assert not (app / ".pipeline" / "install.json").exists()
    assert not (app / ".pipeline" / "loader" / "load_workflow.py").exists()


def test_project_ide_claude_code(tmp_path: Path):
    app = tmp_path / "app"
    app.mkdir()
    assert _run(["--project", str(app), "--ide", "claude-code"]) == 0
    skill = app / ".claude" / "skills" / "run-workflow" / "SKILL.md"
    assert skill.is_file()
    assert not (app / ".cloud").exists()


def test_project_ide_cursor_and_agent_stubs(tmp_path: Path):
    app = tmp_path / "app"
    app.mkdir()
    assert _run(["--project", str(app), "--ide", "cursor", "--agent-stubs"]) == 0
    skill = app / ".cursor" / "skills" / "run-workflow" / "SKILL.md"
    stub = app / ".cursor" / "agents" / "developer-agent.md"
    arch_stub = app / ".cursor" / "agents" / "architect-agent.md"
    assert skill.is_file()
    assert stub.is_file()
    assert arch_stub.is_file()
    assert ".pipeline/agents/architect-agent.md" in arch_stub.read_text(encoding="utf-8")
    text = stub.read_text(encoding="utf-8")
    assert ".pipeline/agents/developer-agent.md" in text
    assert "Thin Cursor stub" in text


def test_merge_config_does_not_clobber(tmp_path: Path):
    app = tmp_path / "app"
    (app / ".pipeline").mkdir(parents=True)
    existing = {
        "version": 1,
        "workflows": {"custom": {"chain": []}},
        "verify": {"rules": [{"match": "/src/", "message": "keep me"}]},
    }
    (app / ".pipeline" / "config.json").write_text(
        json.dumps(existing, indent=2) + "\n", encoding="utf-8"
    )
    assert _run(["--project", str(app), "--ide", "none"]) == 0
    cfg = json.loads((app / ".pipeline" / "config.json").read_text(encoding="utf-8"))
    assert cfg["workflows"]["custom"] == {"chain": []}
    assert "ask" in cfg["workflows"]
    assert cfg["verify"]["rules"] == [{"match": "/src/", "message": "keep me"}]


def test_user_install(tmp_path: Path):
    home = tmp_path / "home"
    home.mkdir()
    assert _run(["--user", "--ide", "cursor", "--home", str(home)]) == 0
    assert (home / ".pipeline" / "workflows" / "ask.json").is_file()
    assert (home / ".pipeline" / "config.json").is_file()
    assert (home / ".cursor" / "skills" / "run-workflow" / "SKILL.md").is_file()
    marker = json.loads((home / ".pipeline" / "install.json").read_text(encoding="utf-8"))
    assert marker["scope"] == "user"
    assert any(name.endswith("ask.json") for name in marker["files"])
    assert _run(["--uninstall", "--user", "--home", str(home)]) == 0
    assert not (home / ".pipeline" / "install.json").exists()
    assert not (home / ".cursor" / "skills" / "run-workflow" / "SKILL.md").exists()


def test_dry_run_writes_nothing(tmp_path: Path):
    app = tmp_path / "app"
    app.mkdir()
    assert _run(["--project", str(app), "--ide", "none", "--dry-run"]) == 0
    assert not (app / ".pipeline").exists()


def test_cli_init_doctor_workflows_and_uninstall(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    app = tmp_path / "app"
    app.mkdir()

    assert _run_cli(["init", str(app), "--ide", "cursor"]) == 0
    assert _run_cli(["doctor", str(app), "--ide", "cursor"]) == 0
    doctor_output = capsys.readouterr().out
    version = (REPO / "VERSION").read_text(encoding="utf-8").strip()
    assert f"pipeline-kit {version} is ready" in doctor_output
    assert "ok  cursor adapter" in doctor_output

    assert _run_cli(["workflows", str(app)]) == 0
    workflows_output = capsys.readouterr().out.splitlines()
    assert "ask" in workflows_output
    assert "feature-development" in workflows_output

    assert _run_cli(["uninstall", str(app)]) == 0
    assert not (app / ".pipeline" / "install.json").exists()


def test_cli_setup_and_update_user_pack(tmp_path: Path):
    home = tmp_path / "home"
    home.mkdir()

    assert _run_cli(["setup", "--ide", "none", "--home", str(home)]) == 0
    assert _run_cli(["update", "--user", "--ide", "none", "--home", str(home)]) == 0
    assert _run_cli(["doctor", "--user", "--home", str(home)]) == 0
    assert _run_cli(["workflows", "--user", "--home", str(home)]) == 0


def test_architect_step_allowlist_installs(tmp_path: Path):
    app = tmp_path / "app"
    app.mkdir()
    assert _run(["--project", str(app), "--ide", "none"]) == 0
    loader = app / ".pipeline" / "loader" / "load_workflow.py"

    result = subprocess.run(
        [
            sys.executable,
            str(loader),
            "--workflow",
            "feature-development",
            "--step",
            "architect-agent",
            "--slug",
            "try-architect",
        ],
        cwd=app,
        check=True,
        capture_output=True,
        text=True,
    )
    pack = json.loads((app / "features" / "try-architect" / "context-pack.json").read_text())
    assert pack["step"] == "architect-agent"
    assert ".pipeline/agents/architect-agent.md" in pack["allowed_reads"]
    assert ".pipeline/skills/architecture-design/SKILL.md" in pack["allowed_reads"]
    assert ".pipeline/skills/architecture-visualization/SKILL.md" in pack["allowed_reads"]
    assert (
        ".pipeline/skills/architecture-visualization/assets/diagram-manifest-template.json"
        in pack["allowed_reads"]
    )
    assert ".pipeline/skills/feature-development/assets/pipeline-state.md" in pack["allowed_reads"]
    assert result.returncode == 0


def test_architect_allowlist_covers_jira_workflows(tmp_path: Path):
    app = tmp_path / "app"
    app.mkdir()
    assert _run(["--project", str(app), "--ide", "none"]) == 0
    import importlib.util

    loader = app / ".pipeline" / "loader" / "context_pack.py"
    spec = importlib.util.spec_from_file_location("installed_context_pack", loader)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for workflow in ("jira-story", "jira-epic"):
        assert (
            module.main(
                [
                    "--workflow",
                    workflow,
                    "--step",
                    "architect-agent",
                    "--slug",
                    f"try-{workflow}",
                    "--repo-root",
                    str(app),
                ]
            )
            == 0
        )
        pack = json.loads(
            (app / "features" / f"try-{workflow}" / "context-pack.json").read_text()
        )
        assert ".pipeline/skills/architecture-visualization/SKILL.md" in pack["allowed_reads"]
        assert (
            ".pipeline/skills/feature-development/assets/architecture-diagrams-policy.md"
            in pack["allowed_reads"]
        )


def test_prd_and_pipeline_state_are_installed(tmp_path: Path):
    app = tmp_path / "app"
    app.mkdir()
    assert _run(["--project", str(app), "--ide", "none"]) == 0
    assets = app / ".pipeline" / "skills" / "feature-development" / "assets"
    assert (assets / "prd-template.md").is_file()
    assert (assets / "pipeline-state.md").is_file()
    assert (assets / "pipeline-state-template.json").is_file()
    assert (assets / "agent-state-template.json").is_file()
    prd = (assets / "prd-template.md").read_text(encoding="utf-8")
    assert "As-is" in prd
    assert "To-be" in prd
    arch = (assets / "architecture-template.md").read_text(encoding="utf-8")
    assert "Concerns" in arch
    assert "```mermaid" in arch
    assert "Enhanced diagram artifacts" in arch
    assert (assets / "handoff-architect-template.md").read_text(encoding="utf-8").count(
        "archify_status"
    )
    viz = app / ".pipeline" / "skills" / "architecture-visualization"
    assert (viz / "SKILL.md").is_file()
    assert (viz / "assets" / "diagram-manifest-template.json").is_file()
    policy = (
        app / ".pipeline" / "skills" / "feature-development" / "assets" / "architecture-diagrams-policy.md"
    )
    assert policy.is_file()
    cfg = json.loads((app / ".pipeline" / "config.json").read_text(encoding="utf-8"))
    assert cfg["architecture_diagrams"]["enabled"] is False
    assert cfg["architecture_diagrams"]["fallback"] == "mermaid"
    prompt = (assets / "parent-task-prompt.md").read_text(encoding="utf-8")
    assert "PIPELINE_STATE_PATH" in prompt
    assert "PRIOR_STATE_PATH" in prompt
    assert "ARCHIFY_ENABLED" in prompt
    cfg = json.loads((app / ".pipeline" / "config.json").read_text(encoding="utf-8"))
    assert cfg["workflows"]["feature-development"]["plan_source"] == "prd.md"
    pm = (app / ".pipeline" / "agents" / "product-manager-agent.md").read_text(encoding="utf-8")
    assert "prd.md" in pm
    assert "plan.md" not in pm or "PRD" in pm


FORBIDDEN_PACK_TOKENS = (
    "chorus",
    "ecommerce-store",
    "northline",
    "canvas-engine",
    "canvas_engine",
    "canvas_agent",
    "identityiq",
    "jsonlogger",
    "shop-1842",
    "dark-factory",
)


def test_bump_semver_parts():
    ns = runpy.run_path(str(INSTALL))
    assert ns["bump_semver"]("1.2.0", "patch") == "1.2.1"
    assert ns["bump_semver"]("1.2.9", "minor") == "1.3.0"
    assert ns["bump_semver"]("1.2.0", "major") == "2.0.0"
    with pytest.raises(ValueError):
        ns["parse_semver"]("v1")


def test_version_show_prints_file(capsys: pytest.CaptureFixture[str]):
    assert _run_cli(["version"]) == 0
    assert capsys.readouterr().out.strip() == (REPO / "VERSION").read_text(encoding="utf-8").strip()


def _kit_checkout(root: Path, *, git: bool = True, init: bool = False) -> Path:
    """A minimal tree that looks like the pipeline-kit source to the version command."""
    (root / "kit" / "pipeline").mkdir(parents=True)
    (root / "install.py").write_text("# stub\n", encoding="utf-8")
    (root / "pyproject.toml").write_text('[project]\nname = "pipeline-kit"\n', encoding="utf-8")
    (root / "VERSION").write_text("1.2.0\n", encoding="utf-8")
    (root / "website").mkdir()
    (root / "website" / "package.json").write_text(
        '{\n  "name": "pipeline-kit-docs",\n  "version": "1.2.0"\n}\n',
        encoding="utf-8",
    )
    if init:
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        for key, value in (("user.email", "kit@example.test"), ("user.name", "Kit Test")):
            subprocess.run(["git", "-C", str(root), "config", key, value], check=True)
        subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(root), "commit", "-qm", "init"], check=True)
    elif git:
        (root / ".git").mkdir()
    return root


def test_version_bump_and_set_from_checkout(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    repo = _kit_checkout(tmp_path / "pipeline-kit")
    website = repo / "website"

    assert _run_cli(["version", "bump", "patch", "--repo", str(repo)]) == 0
    out = capsys.readouterr().out
    assert "1.2.0 -> 1.2.1" in out
    assert (repo / "VERSION").read_text(encoding="utf-8") == "1.2.1\n"
    assert '"version": "1.2.1"' in (website / "package.json").read_text(encoding="utf-8")

    assert _run_cli(["version", "set", "2.0.0", "--repo", str(repo)]) == 0
    assert (repo / "VERSION").read_text(encoding="utf-8") == "2.0.0\n"
    assert _run_cli(["version", "bump", "minor", "--repo", str(repo), "--dry-run"]) == 0
    dry = capsys.readouterr().out
    assert "would set 2.0.0 -> 2.1.0" in dry
    assert (repo / "VERSION").read_text(encoding="utf-8") == "2.0.0\n"


def test_version_refuses_non_git(tmp_path: Path):
    repo = _kit_checkout(tmp_path / "pipeline-kit", git=False)
    assert _run_cli(["version", "bump", "patch", "--repo", str(repo)]) == 64
    assert (repo / "VERSION").read_text(encoding="utf-8") == "1.2.0\n"


def test_version_commits_and_tags_in_kit_checkout(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    repo = _kit_checkout(tmp_path / "pipeline-kit", init=True)

    assert _run_cli(["version", "bump", "minor", "--repo", str(repo), "--commit", "--tag"]) == 0
    out = capsys.readouterr().out
    assert "Release 1.3.0" in out

    log = subprocess.run(
        ["git", "-C", str(repo), "log", "-1", "--pretty=%s"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert log.stdout.strip() == "Release 1.3.0"
    tags = subprocess.run(
        ["git", "-C", str(repo), "tag", "--list"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "v1.3.0" in tags.stdout
    status = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert status.stdout.strip() == ""


def test_version_tag_requires_commit(tmp_path: Path):
    repo = _kit_checkout(tmp_path / "pipeline-kit", init=True)
    assert _run_cli(["version", "bump", "patch", "--repo", str(repo), "--tag"]) == 64
    assert (repo / "VERSION").read_text(encoding="utf-8") == "1.2.0\n"


def test_version_uses_env_checkout_from_unrelated_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    repo = _kit_checkout(tmp_path / "pipeline-kit")
    project = tmp_path / "customer-app"
    project.mkdir()
    monkeypatch.chdir(project)
    monkeypatch.setenv("PIPELINE_KIT_REPO", str(repo))

    assert _run_cli(["version", "bump", "patch"]) == 0
    assert (repo / "VERSION").read_text(encoding="utf-8") == "1.2.1\n"
    assert not (project / "VERSION").exists()


def test_version_refuses_installed_copy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    installed = _kit_checkout(tmp_path / "site-packages" / "pipeline_kit", git=False)
    project = tmp_path / "customer-app"
    project.mkdir()
    monkeypatch.chdir(project)
    monkeypatch.delenv("PIPELINE_KIT_REPO", raising=False)

    spec = importlib.util.spec_from_file_location("install_under_test", INSTALL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "HERE", installed)

    with pytest.raises(ValueError, match="installed, not a checkout"):
        module.resolve_kit_checkout()


def test_pack_markdown_is_portable_and_headed():
    pack = REPO / "kit" / "pipeline"
    missing_type: list[str] = []
    leaks: list[str] = []
    headed = {".md", ".mdc"}
    for path in sorted(pack.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".md", ".mdc", ".sh", ".json"}:
            continue
        text = path.read_text(encoding="utf-8")
        lower = text.lower()
        rel = str(path.relative_to(pack))
        for token in FORBIDDEN_PACK_TOKENS:
            if token in lower:
                leaks.append(f"{rel}: {token}")
        if path.suffix.lower() in headed and "| Type |" not in text:
            missing_type.append(rel)
    assert leaks == [], "pack files still name a demo product:\n" + "\n".join(leaks)
    assert missing_type == [], "pack markdown missing Type header:\n" + "\n".join(missing_type)
    assert (pack / "docs" / "DOCUMENT-STANDARD.md").is_file()
    assert (pack / "docs" / "CUSTOMER-GUIDE.md").is_file()
