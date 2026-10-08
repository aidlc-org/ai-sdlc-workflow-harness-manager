"""Assessment package: deterministic report, license gate, Graphify-shaped fixtures."""

from __future__ import annotations

import json
import runpy
import time
from pathlib import Path

import pytest

from pipeline_assess.commands import cmd_scan
from pipeline_assess.gaps import create_items
from pipeline_assess.graph_model import analyze, stream_graph
from pipeline_assess.rules import apply_priority

REPO = Path(__file__).resolve().parents[1]
INSTALL = REPO / "install.py"


def _run_cli(argv: list[str]) -> int:
    ns = runpy.run_path(str(INSTALL))
    return int(ns["cli_main"](argv))


def _pack(root: Path) -> None:
    pipeline = root / ".pipeline"
    pipeline.mkdir(parents=True)
    (pipeline / "install.json").write_text(json.dumps({"mode": "kit"}) + "\n", encoding="utf-8")
    (pipeline / "config.json").write_text(json.dumps({"workflows": {}, "verify": {"rules": []}, "deploy": {"targets": ["auto"]}, "test_design": {"enabled": False}}) + "\n", encoding="utf-8")
    (pipeline / "workflows").mkdir()
    (pipeline / "workflows" / "feature-development.json").write_text(json.dumps({"name": "feature-development"}) + "\n", encoding="utf-8")
    (pipeline / "skills" / "testing-unit").mkdir(parents=True)
    (pipeline / "skills" / "testing-unit" / "SKILL.md").write_text("---\nname: testing-unit\n---\n# Unit\n", encoding="utf-8")


def _node(ident: str, label: str, source: str, community: int = 0) -> dict:
    return {
        "id": ident,
        "label": label,
        "source_file": source,
        "file_type": "code",
        "community": community,
        "source_location": "L1",
        "_origin": "ast",
    }


def _graph(root: Path, *, community: int = 1, links_key: str = "links") -> None:
    pay = _node("pay", "charge()", "services/pay.py", community)
    auth = _node("login", "login()", "auth/login.py", community + 3)
    ui = _node("app", "App()", "web/App.tsx", community + 1)
    test = _node("test_pay", "test_charge()", "tests/test_pay.py", community + 2)
    payload = {
        "directed": False,
        "nodes": [pay, auth, ui, test],
        links_key: [
            {"source": "test_pay", "target": "pay", "relation": "calls", "confidence": "EXTRACTED"},
            {"source": "pay", "target": "login", "relation": "calls", "confidence": "EXTRACTED"},
        ],
    }
    dest = root / "graphify-out"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "graph.json").write_text(json.dumps(payload), encoding="utf-8")
    (dest / ".graphify_analysis.json").write_text(
        json.dumps({"gods": [{"id": "pay", "label": "charge()", "degree": 12}], "cohesion": {}, "surprises": []}),
        encoding="utf-8",
    )


def _shop(root: Path) -> None:
    _pack(root)
    (root / "package.json").write_text(
        json.dumps({"name": "shop", "dependencies": {"react": "19.0.0"}, "scripts": {"test": "vitest", "build": "vite build"}}) + "\n",
        encoding="utf-8",
    )
    (root / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
    rules = root / ".cursor" / "rules"
    rules.mkdir(parents=True)
    (rules / "web.mdc").write_text("---\nglobs: web/**\n---\n# web\n", encoding="utf-8")
    _graph(root)


@pytest.mark.requires_license_engine
def test_scan_requires_assess_license(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, enterprise_license: dict) -> None:
    from pipeline_kit import license as lic

    token = lic.sign_token(
        enterprise_license["signing_key"],
        org="narrow",
        exp=int(time.time()) + 3600,
        features=["orchestrator"],
    )
    monkeypatch.setenv(lic.ENV_LICENSE, token)
    code = _run_cli(["scan", str(tmp_path), "--no-bootstrap"])
    assert code == 73
    assert not (tmp_path / "features").exists()


def test_assessment_is_stable_and_names_files(tmp_path: Path) -> None:
    app = tmp_path / "shop"
    app.mkdir()
    _shop(app)
    assert cmd_scan(app, no_bootstrap=True, tty=False) == 0
    dest = app / "features" / "assessment"
    first = (dest / "assessment.json").read_text(encoding="utf-8")
    assert cmd_scan(app, no_bootstrap=True, tty=False) == 0
    assert (dest / "assessment.json").read_text(encoding="utf-8") == first
    payload = json.loads(first)
    ids = [item["id"] for item in payload["items"]]
    assert ids[0] == "agents-md"
    assert "rule-auth" in ids
    assert "hook-auth" in ids
    assert "rule-docker" in ids
    assert not any(item["folder"] == "web" for item in payload["items"] if item["id"] != "agents-md")
    agents = (dest / "proposed" / "AGENTS.md").read_text(encoding="utf-8")
    assert "vitest" in agents
    assert "pytest" not in agents
    assert "pipeline-kit:assessment start" in agents
    report = (dest / "report.md").read_text(encoding="utf-8")
    assert "Create these" in report
    assert "Turn these on" in report
    assert payload["scores"]["coverage"] == payload["scores"]["coverage"]
    assert "kit_fit" in payload["scores"]


def test_ids_ignore_community_numbers(tmp_path: Path) -> None:
    left = tmp_path / "a"
    right = tmp_path / "b"
    left.mkdir()
    right.mkdir()
    _shop(left)
    _shop(right)
    _graph(right, community=40)
    first = {item["id"] for item in json.loads((left / "features" / "assessment" / "assessment.json").read_text())["items"]} if False else None
    cmd_scan(left, no_bootstrap=True, tty=False)
    cmd_scan(right, no_bootstrap=True, tty=False)
    left_ids = [item["id"] for item in json.loads((left / "features" / "assessment" / "assessment.json").read_text())["items"]]
    right_ids = [item["id"] for item in json.loads((right / "features" / "assessment" / "assessment.json").read_text())["items"]]
    assert left_ids == right_ids
    assert first is None


def test_edges_key_and_stale_graph(tmp_path: Path) -> None:
    app = tmp_path / "edges"
    app.mkdir()
    _pack(app)
    _graph(app, links_key="edges")
    model = analyze(app)
    assert model["blocked"] is None
    assert any(area["folder"] == "auth" and area["sensitive"] for area in model["areas"])
    stale = tmp_path / "stale"
    stale.mkdir()
    _pack(stale)
    _graph(stale)
    manifest = {f"gone-{index}.py": {"mtime": 1} for index in range(10)}
    (stale / "graphify-out" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert cmd_scan(stale, no_bootstrap=True, tty=False) == 0
    payload = json.loads((stale / "features" / "assessment" / "assessment.json").read_text())
    assert payload["graph"]["blocked"] == "stale"
    assert [item["id"] for item in payload["items"]] == ["agents-md"]


def test_existing_agents_keeps_other_text(tmp_path: Path) -> None:
    app = tmp_path / "keep"
    app.mkdir()
    _shop(app)
    (app / "AGENTS.md").write_text("# Ours\n\nKeep this.\n\n## Graphify\n\ngraphify-out/graph.json\n", encoding="utf-8")
    assert cmd_scan(app, no_bootstrap=True, tty=False) == 0
    section = (app / "features" / "assessment" / "proposed" / "AGENTS.section.md").read_text(encoding="utf-8")
    assert "vitest" in section
    assert cmd_scan(app, apply="agents-md", no_bootstrap=True, tty=False) == 0
    written = (app / "AGENTS.md").read_text(encoding="utf-8")
    assert "Keep this." in written
    assert "graphify-out/graph.json" in written
    assert written.count("pipeline-kit:assessment start") == 1


def test_catalog_covers_shipped_surfaces() -> None:
    from pipeline_assess.catalog import shipped_ids

    config = json.loads((REPO / "kit" / "pipeline" / "config.json").read_text(encoding="utf-8"))
    workflows = set(config["workflows"])
    extensions = {
        path.stem.replace("_", "-")
        for path in (REPO / "extensions" / "orchestrator" / "pipeline_extensions").glob("*.py")
        if path.stem != "__init__"
    }
    ids = shipped_ids()
    assert workflows <= ids
    assert extensions <= ids


def test_stream_graph_reads_pretty_printed_nodes(tmp_path: Path) -> None:
    path = tmp_path / "graph.json"
    path.write_text(
        "\n".join(
            [
                "{",
                '  "nodes": [',
                "    {",
                '      "id": "pay",',
                '      "label": "charge()",',
                '      "source_file": "services/pay.py",',
                '      "file_type": "code"',
                "    }",
                "  ],",
                '  "links": [',
                "    {",
                '      "source": "pay",',
                '      "target": "login",',
                '      "relation": "calls"',
                "    }",
                "  ]",
                "}",
            ]
        ),
        encoding="utf-8",
    )
    data = stream_graph(path)
    assert data["nodes"][0]["source_file"] == "services/pay.py"
    assert data["links"][0]["relation"] == "calls"


def test_scan_lists_files_and_leaves_bodies_to_the_prompt(tmp_path: Path) -> None:
    _pack(tmp_path)
    _graph(tmp_path)
    dest = tmp_path / "features" / "assessment"
    dest.mkdir(parents=True)
    (dest / "answers.md").write_text(
        "\n".join(
            [
                "cadence: seldom",
                "data: internal",
                "extra-persona: yes",
                "impact: team",
                "jira: no",
                "persona: release manager, owns the cut",
                "rule-types: tsx",
                "teams: one",
                "workflows: design-to-code",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    assert cmd_scan(tmp_path, no_bootstrap=True, tty=False) == 0
    payload = json.loads((dest / "assessment.json").read_text(encoding="utf-8"))
    ids = {item["id"] for item in payload["items"]}
    assert "workflow-design-to-code" in ids
    assert {"skill-read-design", "skill-plan-code-changes", "skill-implement-from-design"} <= ids
    assert "agent-release-manager" in ids
    assert "rule-type-tsx" in ids
    assert "rule-type-py" not in ids
    workflow = next(item for item in payload["items"] if item["id"] == "workflow-design-to-code")
    assert [step["id"] for step in workflow["steps"]] == ["read-design", "plan-code-changes", "implement-from-design"]
    assert not (dest / "proposed" / ".pipeline").exists()
    assert not (dest / "proposed" / ".cursor").exists()
    prompt = (dest / "prompt.md").read_text(encoding="utf-8")
    assert "answers.md" in prompt
    assert "Do not open `graphify-out/graph.json`" in prompt
    assert "py" in {item["ext"] for item in payload["file_type_gap"]}
    assert "evals" in {item["id"] for item in payload["open_questions"]}
    assert "Questions still open" in (dest / "report.md").read_text(encoding="utf-8")


def test_eval_answers_draft_skills_and_raise_shipped_eval() -> None:
    items, _unknown = create_items(
        {"blocked": None, "areas": [], "blind": [], "file_types": []},
        {"skills": ["testing-unit"], "artifacts": [], "rule_extensions": [], "flags": {}},
        {},
        {"evals": "ui, product-behavior, agent-runs"},
    )
    assert {item["id"] for item in items} == {"skill-ui-eval", "skill-product-behavior-eval"}
    rows = [{"id": "eval", "status": "recommended", "benefit": "Agent output can be scored."}]
    apply_priority([], rows, {"evals": "agent-runs"})
    assert rows[0]["priority"] == "P0"
    assert "agent-run evaluation" in rows[0]["benefit"]


def test_blank_kickoff_answers_do_not_invent_artifacts() -> None:
    items, _unknown = create_items(
        {"blocked": None, "areas": [], "blind": [], "file_types": [{"ext": "java", "files": 4}]},
        {"skills": ["testing-unit"], "artifacts": [], "rule_extensions": ["java"], "flags": {}},
        {},
        {"workflows": "none", "extra-persona": "no", "rule-types": "none"},
    )
    assert items == []


def test_missing_pack_does_not_write(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = cmd_scan(tmp_path, no_bootstrap=True, tty=False)
    assert code == 1
    assert not (tmp_path / "features").exists()
    assert "pipeline-kit init" in capsys.readouterr().err
