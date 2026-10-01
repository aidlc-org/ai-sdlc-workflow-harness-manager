"""External memory bank: paths, index, CLI, MCP tools."""

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


def _init_project(app: Path) -> None:
    assert _run_cli(["init", str(app), "--ide", "none"]) == 0
    assert (app / ".pipeline" / "config.json").is_file()


def test_paths_local_default(tmp_path: Path):
    from pipeline_kit.paths import artifact_root, feature_dir, feature_rel, memory_enabled

    app = tmp_path / "app"
    app.mkdir()
    (app / ".pipeline").mkdir()
    (app / ".pipeline" / "config.json").write_text("{}\n", encoding="utf-8")
    cfg = {}
    assert memory_enabled(cfg) is False
    assert artifact_root(app, cfg) == app.resolve()
    assert feature_dir(app, "demo", cfg) == (app / "features" / "demo").resolve()
    assert feature_rel(app, "demo", cfg) == "features/demo"


def test_paths_memory_flat(tmp_path: Path):
    from pipeline_kit.paths import feature_dir, feature_rel, load_pipeline_config, memory_enabled

    app = tmp_path / "app"
    bank = tmp_path / "bank"
    app.mkdir()
    bank.mkdir()
    (app / ".pipeline").mkdir()
    cfg = {
        "memory": {
            "enabled": True,
            "root": str(bank),
            "layout": "flat",
        },
        "product": {"artifact_dir": "features"},
    }
    (app / ".pipeline" / "config.json").write_text(json.dumps(cfg) + "\n", encoding="utf-8")
    loaded = load_pipeline_config(app)
    assert memory_enabled(loaded) is True
    dest = feature_dir(app, "auth-fix", loaded)
    assert dest == (bank / "features" / "auth-fix").resolve()
    assert feature_rel(app, "auth-fix", loaded) == str(dest)


def test_paths_memory_namespaced(tmp_path: Path):
    from pipeline_kit.paths import artifact_root, feature_dir, index_db_path

    app = tmp_path / "app"
    bank = tmp_path / "bank"
    app.mkdir()
    bank.mkdir()
    (app / ".pipeline").mkdir()
    cfg = {
        "memory": {
            "enabled": True,
            "root": str(bank),
            "project_id": "acme",
            "layout": "namespaced",
            "index": {"engine": "fts5", "path": ".memory/index.sqlite"},
        }
    }
    (app / ".pipeline" / "config.json").write_text(json.dumps(cfg) + "\n", encoding="utf-8")
    assert artifact_root(app, cfg) == (bank / "projects" / "acme").resolve()
    assert feature_dir(app, "s1", cfg) == (bank / "projects" / "acme" / "features" / "s1").resolve()
    assert index_db_path(app, cfg) == (bank / ".memory" / "index.sqlite").resolve()


def test_chunk_classify_and_slug():
    from pipeline_memory.index.chunk import classify_kind, extract_project_id, extract_slug

    assert classify_kind("features/x/request.md") == "request"
    assert classify_kind("features/x/decisions.md") == "decision"
    assert classify_kind("features/x/HANDOFF-architect.md") == "handoff"
    assert extract_slug("features/dark-mode/prd.md") == "dark-mode"
    assert extract_slug("projects/acme/features/dark-mode/prd.md") == "dark-mode"
    assert extract_project_id("projects/acme/features/dark-mode/prd.md") == "acme"


def test_fts_index_and_search(tmp_path: Path):
    from pipeline_memory.index import get_backend

    root = tmp_path / "bank"
    feat = root / "features" / "login"
    feat.mkdir(parents=True)
    (feat / "decisions.md").write_text(
        "# OAuth choice\n\nWe selected OAuth2 for the login gateway.\n",
        encoding="utf-8",
    )
    (feat / "request.md").write_text("# Request\n\nAdd SSO login.\n", encoding="utf-8")
    db = root / ".memory" / "index.sqlite"
    backend = get_backend("fts5")
    n = backend.rebuild(db, root)
    assert n >= 2
    hits = backend.search(db, "OAuth2 login", limit=5)
    assert hits
    assert any(h.kind == "decision" for h in hits)
    assert any("login" in h.slug for h in hits)


def test_memory_cli_link_index_search(tmp_path: Path):
    app = tmp_path / "app"
    bank = tmp_path / "bank"
    app.mkdir()
    _init_project(app)

    assert _run_cli(["memory", "link", str(bank), str(app), "--project-id", "demo"]) == 0
    cfg = json.loads((app / ".pipeline" / "config.json").read_text(encoding="utf-8"))
    assert cfg["memory"]["enabled"] is True
    assert cfg["memory"]["project_id"] == "demo"
    assert (bank / "README.md").is_file()
    assert (bank / ".gitignore").is_file()
    assert (app / ".pipeline" / "memory.link.json").is_file()

    # Seed an artifact under the namespaced layout and index it
    slug_dir = bank / "projects" / "demo" / "features" / "paywall"
    slug_dir.mkdir(parents=True)
    (slug_dir / "decisions.md").write_text(
        "# Billing\n\nUse Stripe for subscriptions.\n",
        encoding="utf-8",
    )
    assert _run_cli(["memory", "index", str(app)]) == 0
    assert (bank / ".memory" / "index.sqlite").is_file()

    assert _run_cli(["memory", "search", "Stripe subscriptions", str(app), "--json"]) == 0
    assert _run_cli(["memory", "status", str(app)]) == 0
    assert _run_cli(["memory", "doctor", str(app)]) == 0

    assert _run_cli(["memory", "unlink", str(app)]) == 0
    cfg2 = json.loads((app / ".pipeline" / "config.json").read_text(encoding="utf-8"))
    assert cfg2["memory"]["enabled"] is False


def test_memory_import_local(tmp_path: Path):
    app = tmp_path / "app"
    bank = tmp_path / "bank"
    app.mkdir()
    _init_project(app)
    local = app / "features" / "legacy"
    local.mkdir(parents=True)
    (local / "request.md").write_text("# Legacy\n\nBring me over.\n", encoding="utf-8")

    assert _run_cli(["memory", "link", str(bank), str(app)]) == 0
    assert _run_cli(["memory", "import-local", str(app)]) == 0
    dest = bank / "features" / "legacy" / "request.md"
    assert dest.is_file()
    assert "Bring me over" in dest.read_text(encoding="utf-8")


def test_mcp_tools_search_and_list(tmp_path: Path):
    from pipeline_memory.mcp_server import MemoryContext, call_tool

    app = tmp_path / "app"
    bank = tmp_path / "bank"
    app.mkdir()
    bank.mkdir()
    (app / ".pipeline").mkdir()
    cfg = {
        "memory": {"enabled": True, "root": str(bank), "layout": "flat"},
        "product": {"artifact_dir": "features"},
    }
    (app / ".pipeline" / "config.json").write_text(json.dumps(cfg) + "\n", encoding="utf-8")
    feat = bank / "features" / "alpha"
    feat.mkdir(parents=True)
    (feat / "architecture.md").write_text(
        "# Architecture\n\nEvent-driven checkout bus.\n",
        encoding="utf-8",
    )
    (feat / "request.md").write_text("# Request\n\nCheckout rewrite.\n", encoding="utf-8")

    ctx = MemoryContext(app)
    hits = call_tool(ctx, "memory_search", {"query": "checkout event", "limit": 5})
    assert isinstance(hits, list)
    assert hits
    slugs = call_tool(ctx, "memory_list_slugs", {})
    assert "alpha" in slugs
    files = call_tool(ctx, "memory_list_files", {"slug": "alpha"})
    assert "architecture.md" in files
    why = call_tool(ctx, "memory_why", {"question": "checkout bus"})
    assert isinstance(why, list)
    got = call_tool(ctx, "memory_get", {"slug": "alpha", "rel": "request.md"})
    assert "Checkout rewrite" in got.get("content", "")


def test_hook_is_artifact_path_with_memory(tmp_path: Path):
    import importlib.util

    lib_path = REPO / "kit" / "pipeline" / "hooks" / "lib.py"
    spec = importlib.util.spec_from_file_location("hook_lib_mem", lib_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    bank = tmp_path / "bank"
    bank.mkdir()
    cfg = {
        "memory": {"enabled": True, "root": str(bank), "layout": "flat"},
        "product": {"artifact_dir": "features"},
    }
    assert mod.is_artifact_path("features/x/prd.md", cfg, tmp_path) is True
    abs_path = str((bank / "features" / "x" / "prd.md").resolve())
    (bank / "features" / "x").mkdir(parents=True)
    (bank / "features" / "x" / "prd.md").write_text("x", encoding="utf-8")
    assert mod.is_artifact_path(abs_path, cfg, tmp_path) is True
    assert mod.is_artifact_path("src/main.py", cfg, tmp_path) is False


def test_cmd_memory_entrypoint_kwargs(tmp_path: Path):
    from pipeline_memory.commands import cmd_memory_entrypoint

    app = tmp_path / "app"
    bank = tmp_path / "bank"
    app.mkdir()
    (app / ".pipeline").mkdir()
    (app / ".pipeline" / "config.json").write_text("{}\n", encoding="utf-8")
    assert cmd_memory_entrypoint(command="link", project=app, root=str(bank), init=True) == 0
    assert cmd_memory_entrypoint(command="status", project=app) == 0
    assert cmd_memory_entrypoint(command="nope", project=app) == 2
