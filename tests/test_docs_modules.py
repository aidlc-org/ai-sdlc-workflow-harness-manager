"""Codebase docs platform: modules yaml, wiki layout, parallel extract."""

from __future__ import annotations

import json
import os
import runpy
import stat
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
INSTALL = REPO / "install.py"


def _run_cli(argv: list[str]) -> int:
    ns = runpy.run_path(str(INSTALL))
    return int(ns["cli_main"](argv))


def _write_modules(app: Path, body: str) -> None:
    cfg = app / ".pipeline" / "docs-modules.yaml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(body, encoding="utf-8")


def test_docs_package_never_imports_graphify() -> None:
    import re

    banned = re.compile(r"^\s*(import graphify|from graphify)\b", re.M)
    root = REPO / "capabilities" / "docs"
    for path in root.glob("*.py"):
        assert banned.search(path.read_text(encoding="utf-8")) is None, path.name


def test_init_modules_writes_template_and_wiki(tmp_path: Path) -> None:
    app = tmp_path / "app"
    app.mkdir()
    assert _run_cli(["docs", "init-modules", str(app)]) == 0
    assert (app / ".pipeline" / "docs-modules.yaml").is_file()
    assert (app / "wiki" / "codebase" / "README.md").is_file()
    assert (app / "wiki" / "codebase" / "INDEX.md").is_file()
    assert (app / "wiki" / "codebase" / "modules").is_dir()
    # second call is idempotent
    assert _run_cli(["docs", "init-modules", str(app)]) == 0


def test_load_modules_parses_yaml_subset(tmp_path: Path) -> None:
    from pipeline_docs.config import DocsConfigError, load_modules

    app = tmp_path / "app"
    (app / "services" / "billing").mkdir(parents=True)
    (app / "services" / "billing" / "x.py").write_text("x=1\n", encoding="utf-8")
    _write_modules(
        app,
        """
modules:
  - id: billing
    name: Billing
    path: services/billing
    tech: [java, spring]
    enabled: true
  - id: off
    name: Off
    path: services/billing
    enabled: false
""",
    )
    mods = load_modules(app)
    assert [m.id for m in mods] == ["billing", "off"]
    assert mods[0].tech == ["java", "spring"]
    assert mods[1].enabled is False


def test_load_modules_rejects_bad_id_and_missing_path(tmp_path: Path) -> None:
    from pipeline_docs.config import DocsConfigError, load_modules

    app = tmp_path / "app"
    app.mkdir()
    _write_modules(
        app,
        """
modules:
  - id: BadId
    path: .
""",
    )
    with pytest.raises(DocsConfigError, match="invalid module id"):
        load_modules(app)

    (app / "svc").mkdir()
    _write_modules(
        app,
        """
modules:
  - id: ok
    path: missing-dir
""",
    )
    with pytest.raises(DocsConfigError, match="does not exist"):
        load_modules(app)


def test_extract_modules_parallel_copies_to_wiki(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pipeline_docs.extract import extract_modules
    from pipeline_docs.layout_wiki import module_graph_path

    app = tmp_path / "app"
    for name in ("a", "b"):
        d = app / "mod" / name
        d.mkdir(parents=True)
        (d / "main.py").write_text(f"# {name}\n", encoding="utf-8")
    _write_modules(
        app,
        """
modules:
  - id: moda
    name: A
    path: mod/a
  - id: modb
    name: B
    path: mod/b
""",
    )

    calls: list[list[str]] = []

    class _Done:
        def __init__(self) -> None:
            self.returncode = 0
            self.stdout = ""
            self.stderr = ""

    def runner(cmd, **kwargs):
        calls.append(list(cmd))
        cwd = Path(kwargs.get("cwd") or app)
        # Official CLI: extract <rel> from project root → <rel>/graphify-out/
        target = cmd[2] if len(cmd) > 2 else "."
        if target in {".", "./"}:
            out = cwd / "graphify-out"
        else:
            out = cwd / target / "graphify-out"
        out.mkdir(parents=True, exist_ok=True)
        (out / "graph.json").write_text(
            json.dumps({"nodes": [{"id": target}]}) + "\n",
            encoding="utf-8",
        )
        return _Done()

    monkeypatch.setattr(
        "pipeline_plugins.graphify.graphify_executable", lambda: "graphify"
    )
    manifest = extract_modules(app, workers=2, runner=runner)
    assert manifest["ok"] == 2
    assert manifest["failed"] == 0
    assert module_graph_path(app, "moda").is_file()
    assert module_graph_path(app, "modb").is_file()
    # parallel-safe: each extract targets a module path from project root
    assert len(calls) == 2
    assert all(c[0] == "graphify" and c[1] == "extract" for c in calls)
    targets = sorted(c[2] for c in calls)
    assert targets == ["mod/a", "mod/b"]


def test_merge_modules_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app = tmp_path / "app"
    for name in ("a", "b"):
        d = app / "mod" / name
        d.mkdir(parents=True)
        (d / "x.py").write_text("x=1\n", encoding="utf-8")
        gdir = app / "wiki" / "codebase" / "modules" / f"mod{name}" / "graph"
        gdir.mkdir(parents=True)
        (gdir / "graph.json").write_text("{}\n", encoding="utf-8")
    _write_modules(
        app,
        """
modules:
  - id: moda
    path: mod/a
  - id: modb
    path: mod/b
""",
    )

    class _Done:
        returncode = 0
        stdout = ""
        stderr = ""

    def runner(cmd, **_kwargs):
        # graphify merge-graphs ... --out target
        assert "merge-graphs" in cmd
        out_idx = cmd.index("--out")
        Path(cmd[out_idx + 1]).write_text('{"merged": true}\n', encoding="utf-8")
        return _Done()

    monkeypatch.setattr(
        "pipeline_plugins.graphify.graphify_executable", lambda: "graphify"
    )
    monkeypatch.setattr("pipeline_plugins.graphify.subprocess.run", runner)
    # merge_graphs uses _run_graphify → need patch at call site used by commands
    def _fake_merge(project, inputs, out=None):
        target = Path(out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('{"merged": true}\n', encoding="utf-8")
        return target

    monkeypatch.setattr("pipeline_docs.commands.merge_graphs", _fake_merge)
    assert _run_cli(["docs", "merge-modules", str(app)]) == 0
    sys_g = app / "wiki" / "codebase" / "system" / "graph" / "graph.json"
    assert sys_g.is_file()


def test_link_index_and_agents(tmp_path: Path) -> None:
    app = tmp_path / "app"
    (app / "mod" / "a").mkdir(parents=True)
    (app / "mod" / "a" / "x.py").write_text("x=1\n", encoding="utf-8")
    _write_modules(
        app,
        """
modules:
  - id: moda
    name: Module A
    path: mod/a
""",
    )
    assert _run_cli(["docs", "init-modules", str(app)]) == 0
    g = app / "wiki" / "codebase" / "modules" / "moda" / "graph"
    g.mkdir(parents=True)
    (g / "graph.json").write_text("{}\n", encoding="utf-8")
    (app / "wiki" / "codebase" / "modules" / "moda" / "README.md").write_text(
        "# A\n", encoding="utf-8"
    )
    assert _run_cli(["docs", "link-index", str(app)]) == 0
    idx = (app / "wiki" / "codebase" / "INDEX.md").read_text(encoding="utf-8")
    assert "`moda`" in idx
    assert "yes" in idx
    (app / "AGENTS.md").write_text("# App\n\nBlurb.\n", encoding="utf-8")
    assert _run_cli(["docs", "link-agents", str(app)]) == 0
    agents = (app / "AGENTS.md").read_text(encoding="utf-8")
    assert "pipeline-kit:codebase-docs start" in agents
    assert "wiki/codebase/modules/moda/README.md" in agents


def test_status_without_config(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    app = tmp_path / "app"
    app.mkdir()
    code = _run_cli(["docs", "status", str(app)])
    assert code == 0
    out = capsys.readouterr().out
    assert "docs-modules.yaml: absent" in out or "absent" in out


def test_extract_graph_at_module_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pipeline_plugins.graphify import extract_graph_at

    app = tmp_path / "app"
    mod = app / "services" / "pay"
    mod.mkdir(parents=True)
    (mod / "a.py").write_text("a=1\n", encoding="utf-8")
    dest = app / "wiki" / "codebase" / "modules" / "pay" / "graph" / "graph.json"
    seen: dict[str, object] = {}

    class _Done:
        returncode = 0
        stdout = ""
        stderr = ""

    def runner(cmd, **kwargs):
        seen["cmd"] = list(cmd)
        seen["cwd"] = Path(kwargs["cwd"])
        target = cmd[2]
        out = Path(kwargs["cwd"]) / target / "graphify-out"
        out.mkdir(parents=True, exist_ok=True)
        (out / "graph.json").write_text('{"n":1}\n', encoding="utf-8")
        return _Done()

    monkeypatch.setattr(
        "pipeline_plugins.graphify.graphify_executable", lambda: "graphify"
    )
    path = extract_graph_at(app, path="services/pay", dest=dest, runner=runner)
    assert path == dest
    assert dest.is_file()
    assert seen["cwd"] == app.resolve()
    assert seen["cmd"][:3] == ["graphify", "extract", "services/pay"]
    # scratch module graphify-out removed after wiki copy
    assert not (mod / "graphify-out").exists()


def test_merge_graphs_out_kwarg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pipeline_plugins.graphify import merge_graphs

    app = tmp_path / "app"
    app.mkdir()
    g1 = tmp_path / "g1.json"
    g2 = tmp_path / "g2.json"
    g1.write_text("{}\n", encoding="utf-8")
    g2.write_text("{}\n", encoding="utf-8")
    out = app / "wiki" / "codebase" / "system" / "graph" / "graph.json"
    seen: dict[str, list[str]] = {}

    class _Done:
        returncode = 0
        stdout = ""
        stderr = ""

    def runner(cmd, **_kwargs):
        seen["cmd"] = list(cmd)
        Path(cmd[cmd.index("--out") + 1]).write_text('{"ok":1}\n', encoding="utf-8")
        return _Done()

    monkeypatch.setattr(
        "pipeline_plugins.graphify.graphify_executable", lambda: "graphify"
    )
    # _run_graphify uses runner directly via merge_graphs runner param
    result = merge_graphs(app, [g1, g2], out=out, runner=runner)
    assert result == out
    assert out.is_file()
    assert "merge-graphs" in seen["cmd"]
    assert str(out) in seen["cmd"]
