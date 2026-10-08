"""Kit loader model policy. Offline; does not call orchestrator runners."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
LOADER = REPO / "kit" / "pipeline" / "loader" / "context_pack.py"
POLICY = REPO / "kit" / "pipeline" / "loader" / "model_policy.py"
PACK = REPO / "kit" / "pipeline"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def policy():
    return _load(POLICY, "kit_model_policy")


@pytest.fixture()
def loader():
    return _load(LOADER, "kit_context_pack_model")


def _write_pack(tmp: Path, orchestrator: dict) -> Path:
    pack = tmp / ".pipeline"
    pack.mkdir(parents=True)
    (pack / "config.json").write_text(
        json.dumps({"version": 1, "orchestrator": orchestrator}) + "\n",
        encoding="utf-8",
    )
    # Minimal workflow so activate can run against real kit pack when needed.
    return pack


def test_parent_step_skips_model(policy, tmp_path: Path):
    pack = _write_pack(tmp_path, {"fallback_model": "composer-2.5", "models": {"steps": {}}})
    out = policy.resolve_model(
        project=tmp_path,
        pack=pack,
        step="parent",
        workflow="feature-development",
        slug="demo",
    )
    assert out is None


def test_fixed_pin_from_config_steps(policy, tmp_path: Path):
    pack = _write_pack(
        tmp_path,
        {
            "decider": "jev",
            "fallback_model": "composer-2.5",
            "models": {
                "steps": {"developer-agent": "gpt-5.5"},
                "candidates": ["composer-2.5", "gpt-5.5", "claude-opus-5"],
            },
        },
    )
    out = policy.resolve_model(
        project=tmp_path,
        pack=pack,
        step="developer-agent",
        workflow="feature-development",
        slug="demo",
    )
    assert out is not None
    assert out["chosen"] == "gpt-5.5"
    assert out["reason"] == "config"
    assert out["decider"] == "fixed"
    assert out["apply"] == "advisory"
    assert out["runtime"] == "kit"


def test_fallback_when_no_pin(policy, tmp_path: Path):
    pack = _write_pack(
        tmp_path,
        {
            "fallback_model": "claude-opus-5",
            "models": {"candidates": ["composer-2.5", "claude-opus-5"], "steps": {}},
        },
    )
    out = policy.resolve_model(
        project=tmp_path,
        pack=pack,
        step="product-manager-agent",
        workflow="feature-development",
        slug="x",
    )
    assert out is not None
    assert out["chosen"] == "claude-opus-5"
    assert out["reason"] == "fixed"


def test_cli_pin_wins(policy, tmp_path: Path):
    pack = _write_pack(
        tmp_path,
        {
            "fallback_model": "composer-2.5",
            "models": {
                "steps": {"developer-agent": "gpt-5.5"},
                "candidates": ["composer-2.5", "gpt-5.5", "claude-opus-5"],
            },
        },
    )
    out = policy.resolve_model(
        project=tmp_path,
        pack=pack,
        step="developer-agent",
        workflow="feature-development",
        slug="x",
        pin="claude-opus-5",
    )
    assert out is not None
    assert out["chosen"] == "claude-opus-5"
    assert out["reason"] == "pin"


def test_routing_disabled_env(policy, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PIPELINE_KIT_MODEL_ROUTING", "0")
    pack = _write_pack(tmp_path, {"fallback_model": "composer-2.5", "models": {"steps": {}}})
    out = policy.resolve_model(
        project=tmp_path,
        pack=pack,
        step="developer-agent",
        workflow="feature-development",
        slug="x",
    )
    assert out is not None
    assert out["reason"] == "disabled"
    assert out["chosen"] is None


def test_activate_writes_chosen_model(loader, tmp_path: Path):
    # Use real kit pack workflows + a project-local config with a pin.
    project = tmp_path / "app"
    project.mkdir()
    pack = project / ".pipeline"
    # Copy minimal: symlink/copy config from kit pack is heavy; point pack-root at kit.
    cfg = json.loads((PACK / "config.json").read_text(encoding="utf-8"))
    cfg.setdefault("orchestrator", {})
    cfg["orchestrator"]["fallback_model"] = "composer-2.5"
    cfg["orchestrator"].setdefault("models", {})["steps"] = {
        "developer-agent": "gpt-5.5",
    }
    cfg["orchestrator"]["models"]["candidates"] = [
        "composer-2.5",
        "gpt-5.5",
        "claude-opus-5",
    ]
    pack.mkdir()
    (pack / "config.json").write_text(json.dumps(cfg) + "\n", encoding="utf-8")
    # Need workflows from kit pack — use pack_root override via activate(pack=).
    data = loader.activate(
        project,
        "feature-development",
        "developer-agent",
        "demo-feature",
        pack=PACK,
        change_class="micro",
    )
    # activate used PACK for workflows but model policy reads project .pipeline
    # first then pack. Project has the pin config; policy prefers pack arg's
    # config first in _orchestrator_block(pack, project) — pack first.
    # So pin may come from kit pack empty steps. Force pin via activate pin=.
    data = loader.activate(
        project,
        "feature-development",
        "developer-agent",
        "demo-feature",
        pack=PACK,
        change_class="micro",
        pin="gpt-5.5",
    )
    assert data.get("chosen_model") == "gpt-5.5"
    assert data.get("model", {}).get("reason") == "pin"
    assert data.get("model", {}).get("apply") == "advisory"
    routing = project / "features" / "demo-feature" / "model-routing.json"
    assert routing.is_file()
    body = json.loads(routing.read_text(encoding="utf-8"))
    assert body["latest"]["chosen"] == "gpt-5.5"
    pack_json = project / "features" / "demo-feature" / "context-pack.json"
    assert pack_json.is_file()
    saved = json.loads(pack_json.read_text(encoding="utf-8"))
    assert saved.get("chosen_model") == "gpt-5.5"


def test_activate_parent_has_no_model(loader, tmp_path: Path):
    project = tmp_path / "app"
    project.mkdir()
    data = loader.activate(
        project,
        "feature-development",
        "parent",
        "demo-parent",
        pack=PACK,
    )
    assert "chosen_model" not in data
    assert data.get("model") is None or "model" not in data


def test_write_routing_history(policy, tmp_path: Path):
    d1 = {"chosen": "a", "reason": "fixed", "step": "developer-agent"}
    d2 = {"chosen": "b", "reason": "config", "step": "product-manager-agent"}
    rel = policy.write_routing(tmp_path, "s1", d1)
    assert rel == "features/s1/model-routing.json"
    policy.write_routing(tmp_path, "s1", d2)
    body = json.loads((tmp_path / "features" / "s1" / "model-routing.json").read_text(encoding="utf-8"))
    assert body["latest"]["chosen"] == "b"
    assert len(body["history"]) == 2
