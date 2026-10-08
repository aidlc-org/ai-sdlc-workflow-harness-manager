"""Optional plugins: Graphify move stays compatible; Archify is opt-in."""

from __future__ import annotations

import json
import os
import runpy
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from pipeline_plugins.archify import (
    PINNED_VERSION,
    SOURCE_REPO,
    install_command,
    is_managed_archify,
    skill_dir,
    uninstall_skill,
)
from pipeline_plugins.graphify import register_command, uninstall_command

REPO = Path(__file__).resolve().parents[1]
INSTALL = REPO / "install.py"


def _run_cli(argv: list[str]) -> int:
    ns = runpy.run_path(str(INSTALL))
    return int(ns["cli_main"](argv))


def _init_pack(app: Path) -> None:
    assert _run_cli(["init", str(app), "--ide", "none"]) == 0


def _exe(path: Path, body: str) -> None:
    """PATH-visible shim. body is a tiny POSIX shell snippet; Windows gets a .cmd port."""
    if os.name == "nt":
        cmd = Path(str(path) + ".cmd")
        # Map the few patterns these tests plant.
        if '="$1" = "skill"' in body or '"$1" = "skill"' in body:
            text = '@echo off\r\nif "%~1"=="skill" exit /b 0\r\nexit /b 1\r\n'
        elif '"$1" = "--version"' in body or '="$1" = "--version"' in body:
            text = (
                '@echo off\r\n'
                'if "%~1"=="--version" (\r\n'
                '  echo v20.11.0\r\n'
                '  exit /b 0\r\n'
                ')\r\n'
                'exit /b 0\r\n'
            )
        elif body.strip() == "exit 0":
            text = "@echo off\r\nexit /b 0\r\n"
        elif body.strip() == "exit 1":
            text = "@echo off\r\nexit /b 1\r\n"
        else:
            # Best-effort: always succeed.
            text = "@echo off\r\nexit /b 0\r\n"
        cmd.write_text(text, encoding="utf-8")
        return
    path.write_text("#!/bin/sh\n" + body + "\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _plant_archify_skill(root: Path, *, version: str = "2.16") -> Path:
    directory = root / ".agents" / "skills" / "archify"
    (directory / "bin").mkdir(parents=True)
    (directory / "SKILL.md").write_text(
        (
            "---\n"
            "name: archify\n"
            f'version: "{version}"\n'
            "metadata:\n"
            f"  source: {SOURCE_REPO}\n"
            "---\n\n"
            "# Archify\n"
        ),
        encoding="utf-8",
    )
    (directory / "bin" / "archify.mjs").write_text("export {};\n", encoding="utf-8")
    return directory


def test_knowledge_graphify_reexports_plugin():
    import knowledge.graphify as compat
    import pipeline_plugins.graphify as plugin

    assert compat.extract_graph is plugin.extract_graph
    assert compat.register_skill is plugin.register_skill
    assert compat.GRAPH_DIR == "graphify-out"


def test_plugins_never_import_graphify_package():
    import re

    banned = re.compile(r"^\s*(import graphify|from graphify)\b", re.M)
    for path in (REPO / "capabilities" / "plugins").glob("*.py"):
        assert banned.search(path.read_text(encoding="utf-8")) is None, path.name


def test_archify_install_command_is_pinned():
    assert install_command(ide="cursor", scope="project") == [
        "gh",
        "skill",
        "install",
        "tt-a1i/archify",
        "archify",
        "--pin",
        "v2.16.0",
        "--agent",
        "cursor",
        "--scope",
        "project",
    ]
    assert install_command(ide="claude-code", scope="user")[-1] == "user"
    assert "github-copilot" in install_command(ide="github", scope="project")
    assert "main" not in install_command(ide="cursor", scope="project")


def test_graphify_register_and_uninstall_commands():
    assert register_command(ide="cursor") == ["graphify", "cursor", "install"]
    assert uninstall_command(ide="cursor") == ["graphify", "cursor", "uninstall"]
    assert uninstall_command(ide="none") is None


def test_init_does_not_enable_architecture_diagrams(tmp_path: Path):
    app = tmp_path / "app"
    app.mkdir()
    _init_pack(app)
    cfg = json.loads((app / ".pipeline" / "config.json").read_text(encoding="utf-8"))
    block = cfg.get("architecture_diagrams") or {}
    assert block.get("enabled") is not True
    assert block.get("fallback") == "mermaid"
    assert block.get("version") == PINNED_VERSION


def test_plugins_list(capsys: pytest.CaptureFixture[str]):
    assert _run_cli(["plugins", "list"]) == 0
    out = capsys.readouterr().out
    assert "graphify" in out
    assert "archify" in out
    assert PINNED_VERSION in out


def test_plugins_install_archify_enables_and_falls_back_without_gh(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    app = tmp_path / "app"
    app.mkdir()
    _init_pack(app)
    monkeypatch.setenv("PATH", str(tmp_path / "empty-bin"))
    (tmp_path / "empty-bin").mkdir()
    assert _run_cli(["plugins", "install", "archify", str(app), "--ide", "cursor"]) == 1
    err = capsys.readouterr().err
    assert "gh is not on PATH" in err
    cfg = json.loads((app / ".pipeline" / "config.json").read_text(encoding="utf-8"))
    assert cfg["architecture_diagrams"]["enabled"] is True
    assert cfg["architecture_diagrams"]["fallback"] == "mermaid"


def test_plugins_install_archify_none_enables_without_gh(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    app = tmp_path / "app"
    app.mkdir()
    _init_pack(app)
    monkeypatch.setenv("PATH", str(tmp_path / "empty-bin"))
    (tmp_path / "empty-bin").mkdir()
    assert _run_cli(["plugins", "install", "archify", str(app), "--ide", "none"]) == 0
    cfg = json.loads((app / ".pipeline" / "config.json").read_text(encoding="utf-8"))
    assert cfg["architecture_diagrams"]["enabled"] is True


def test_plugins_install_archify_pinned_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    app = tmp_path / "app"
    app.mkdir()
    _init_pack(app)
    _plant_archify_skill(app)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _exe(bin_dir / "gh", 'if [ "$1" = "skill" ]; then exit 0; fi\nexit 1')
    _exe(bin_dir / "node", 'if [ "$1" = "--version" ]; then echo v20.11.0; exit 0; fi\nexit 0')
    monkeypatch.setenv("PATH", str(bin_dir))
    assert _run_cli(["plugins", "install", "archify", str(app), "--ide", "cursor"]) == 0
    out = capsys.readouterr().out
    assert "registered Archify skill" in out
    assert "--pin v2.16.0" in out
    assert _run_cli(["plugins", "status", str(app), "--plugin", "archify", "--ide", "cursor"]) == 0
    status = capsys.readouterr().out
    assert "archify: ready" in status


def test_uninstall_archify_keeps_diagrams(tmp_path: Path):
    app = tmp_path / "app"
    app.mkdir()
    _init_pack(app)
    directory = _plant_archify_skill(app)
    diagrams = app / "features" / "demo" / "diagrams"
    diagrams.mkdir(parents=True)
    html = diagrams / "context.architecture.html"
    html.write_text("<html></html>", encoding="utf-8")
    cfg = json.loads((app / ".pipeline" / "config.json").read_text(encoding="utf-8"))
    cfg["architecture_diagrams"]["enabled"] = True
    (app / ".pipeline" / "config.json").write_text(json.dumps(cfg, indent=2) + "\n")
    assert _run_cli(["plugins", "uninstall", "archify", str(app), "--ide", "cursor"]) == 0
    assert not directory.exists()
    assert html.is_file()
    cfg = json.loads((app / ".pipeline" / "config.json").read_text(encoding="utf-8"))
    assert cfg["architecture_diagrams"]["enabled"] is False


def test_uninstall_archify_refuses_unmanaged_path(tmp_path: Path):
    app = tmp_path / "app"
    app.mkdir()
    decoy = app / ".agents" / "skills" / "archify"
    decoy.mkdir(parents=True)
    (decoy / "SKILL.md").write_text("# not archify\n", encoding="utf-8")
    with pytest.raises(Exception, match="not a managed"):
        uninstall_skill(app, ide="cursor")
    assert decoy.is_dir()


def test_is_managed_archify_rejects_escape(tmp_path: Path):
    app = tmp_path / "app"
    app.mkdir()
    outsider = tmp_path / "outside" / "archify"
    outsider.mkdir(parents=True)
    (outsider / "SKILL.md").write_text(
        f"---\nname: archify\nsource: {SOURCE_REPO}\n---\n",
        encoding="utf-8",
    )
    (outsider / "bin").mkdir()
    (outsider / "bin" / "archify.mjs").write_text("export {};\n")
    expected = (app / ".agents" / "skills").resolve()
    assert is_managed_archify(outsider, expected_root=expected) is False
    assert skill_dir(app, ide="cursor").name == "archify"


def test_uninstall_graphify_preserves_graph_without_purge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    app = tmp_path / "app"
    app.mkdir()
    graph = app / "graphify-out"
    graph.mkdir()
    (graph / "graph.json").write_text("{}", encoding="utf-8")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _exe(bin_dir / "graphify", "exit 0")
    monkeypatch.setenv("PATH", str(bin_dir))
    assert _run_cli(["plugins", "uninstall", "graphify", str(app), "--ide", "cursor"]) == 0
    out = capsys.readouterr().out
    assert "left graphify-out/" in out
    assert (graph / "graph.json").is_file()
    assert _run_cli(
        ["plugins", "uninstall", "graphify", str(app), "--ide", "cursor", "--purge"]
    ) == 0
    assert not graph.exists()


def test_doctor_stays_ready_without_archify(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    app = tmp_path / "app"
    app.mkdir()
    _init_pack(app)
    monkeypatch.setenv("PATH", str(tmp_path / "empty-bin"))
    (tmp_path / "empty-bin").mkdir()
    assert _run_cli(["doctor", str(app), "--ide", "none"]) == 0
    out = capsys.readouterr().out
    assert "info  archify: missing" in out
    version = (REPO / "VERSION").read_text(encoding="utf-8").strip()
    assert f"pipeline-kit {version} is ready" in out


def test_knowledge_extract_still_uses_official_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    app = tmp_path / "app"
    app.mkdir()
    monkeypatch.setenv("PATH", str(tmp_path / "empty-bin"))
    (tmp_path / "empty-bin").mkdir()
    assert _run_cli(["knowledge", "extract", str(app)]) == 1
    err = capsys.readouterr().err
    assert "uv tool install graphifyy && graphify install" in err
    assert not (app / "graphify-out" / "graph.json").exists()


def test_documented_plugin_commands_match_cli():
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    guide = (REPO / "CUSTOMER-GUIDE.md").read_text(encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import runpy, sys;\n"
                "ns = runpy.run_path(sys.argv[1]);\n"
                "raise SystemExit(ns['cli_main'](['plugins', '-h']))\n"
            ),
            str(INSTALL),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    combined = result.stdout + result.stderr
    assert "list" in combined
    assert "install" in combined
    assert "uninstall" in combined
    assert "status" in combined
    for token in (
        "pipeline-kit plugins list",
        "pipeline-kit plugins install archify",
        "pipeline-kit plugins install graphify",
        "pipeline-kit plugins uninstall",
        "pipeline-kit plugins status",
    ):
        assert token in readme, token
    assert "Optional plugins" in readme
    assert "mermaid" in guide.lower()
    assert "plugins uninstall" in guide
