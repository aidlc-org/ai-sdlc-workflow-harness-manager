"""Render cases.json as stepwise procedures a later Playwright pass can follow."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class RenderError(ValueError):
    """cases.json is missing or not renderable."""


def _feature_base(project: Path, slug: str) -> Path:
    try:
        from pipeline_kit.paths import feature_dir
    except ImportError:
        try:
            from paths import feature_dir  # type: ignore
        except ImportError:
            return project / "features" / slug
    return feature_dir(project, slug)


def _feature_display(project: Path, slug: str) -> str:
    """Project-relative path when local; absolute path string when memory-linked."""
    try:
        from pipeline_kit.paths import feature_rel
    except ImportError:
        try:
            from paths import feature_rel  # type: ignore
        except ImportError:
            return f"features/{slug}"
    return feature_rel(project, slug)


def render_case_views(project: Path, slug: str) -> list[Path]:
    feature_root = _feature_base(project, slug)
    design = feature_root / "test-design"
    cases_path = design / "cases.json"
    if not cases_path.is_file():
        raise RenderError(f"missing {cases_path}")
    payload = json.loads(cases_path.read_text(encoding="utf-8"))
    cases = payload.get("cases") if isinstance(payload, dict) else None
    if not isinstance(cases, list):
        raise RenderError("cases.json must contain a cases array")
    design.mkdir(parents=True, exist_ok=True)
    feature_root.mkdir(parents=True, exist_ok=True)
    rel = _feature_display(project, slug)
    return [
        _write(feature_root / "qa-test-cases.md", _qa_cases_markdown(slug, cases, rel)),
        _write(design / "test-plan-view.md", _test_plan_markdown(slug, cases, rel)),
    ]


def _qa_cases_markdown(slug: str, cases: list[Any], feature_rel: str = "") -> str:
    base = feature_rel or f"features/{slug}"
    index_rows = [_index_row(index, item) for index, item in enumerate(cases, start=1)]
    index = "\n".join(index_rows) if index_rows else "| — | — | — | — | — |"
    procedures = "\n\n".join(
        _procedure(index, item) for index, item in enumerate(cases, start=1)
    ) or "_No cases._"
    return (
        f"# Test cases — {slug}\n\n"
        f"**Test plan:** {base}/test-plan.md\n"
        f"**Source:** {base}/test-design/cases.json\n"
        "**Status:** Ready for review (design-only)\n\n"
        "Each `ui` / browser `e2e` case below is a numbered click-path. "
        "A later Playwright pass maps one `test('TC-N')` to one case. "
        "Do not replace these steps with catalog IDs.\n\n"
        "## Index\n\n"
        "| ID | Spec | AC | Layer | Title |\n"
        "|----|------|----|-------|-------|\n"
        f"{index}\n\n"
        "## Procedures\n\n"
        f"{procedures}\n\n"
        "## Coverage\n\n"
        "- Generated from reviewed `cases.json`. Tester executes the existing path.\n"
        "- Do not invent extra browser cases in this file.\n"
        "- Never paste real passwords. Use project test-env names only.\n"
    )


def _test_plan_markdown(slug: str, cases: list[Any], feature_rel: str = "") -> str:
    base = feature_rel or f"features/{slug}"
    layers: dict[str, int] = {}
    lines: list[str] = []
    for item in cases:
        if not isinstance(item, dict):
            continue
        layer = str(item.get("level") or item.get("layer") or "unspecified")
        layers[layer] = layers.get(layer, 0) + 1
        ident = item.get("id") or "TC"
        title = item.get("title") or item.get("what") or ident
        lines.append(f"- **{ident}** ({layer}): {title}")
    layer_rows = (
        "\n".join(f"| {name} | {count} |" for name, count in sorted(layers.items()))
        or "| — | 0 |"
    )
    case_list = "\n".join(lines) or "- none"
    return (
        f"# Test plan — {slug}\n\n"
        "**change_class:** feature\n"
        f"**spec_order:** {base}/spec-order.md\n"
        f"**Source:** {base}/test-design/cases.json\n\n"
        "## Layer rollup\n\n"
        "| Layer | Case count |\n"
        "|-------|------------|\n"
        f"{layer_rows}\n\n"
        "## Cases\n\n"
        f"{case_list}\n\n"
        f"Full click-paths live in `{base}/qa-test-cases.md`.\n"
    )


def _index_row(index: int, item: Any) -> str:
    if not isinstance(item, dict):
        return f"| TC-{index} | — | — | — | — |"
    ident = _cell(item.get("id") or f"TC-{index}")
    spec = _cell(item.get("spec") or item.get("child") or "—")
    ac = _cell(item.get("ac") or "—")
    layer = _cell(item.get("level") or item.get("layer") or "—")
    title = _cell(item.get("title") or item.get("what") or "—")
    return f"| {ident} | {spec} | {ac} | {layer} | {title} |"


def _procedure(index: int, item: Any) -> str:
    if not isinstance(item, dict):
        return f"### TC-{index}\n\n_Invalid case._"
    ident = item.get("id") or f"TC-{index}"
    title = item.get("title") or item.get("what") or ident
    spec = item.get("spec") or item.get("child") or "—"
    ac = item.get("ac") or "—"
    fr = item.get("fr") or "—"
    layer = item.get("level") or item.get("layer") or "—"
    kind = item.get("type") or item.get("technique") or "—"
    pre = _numbered(item.get("preconditions") or item.get("fixtures"), prefer=("text", "do", "name", "id"))
    steps = _numbered(
        item.get("steps") or item.get("actions"),
        prefer=("do", "text", "name", "id"),
    )
    expected = _numbered(
        item.get("expected") or item.get("oracles"),
        prefer=("see", "text", "name", "id"),
    )
    return (
        f"### {ident} — {title}\n\n"
        f"**Spec:** {spec} · **AC:** {ac} · **FR:** {fr} · "
        f"**Layer:** {layer} · **Type:** {kind}\n\n"
        f"**Preconditions**\n\n{pre}\n\n"
        f"**Steps**\n\n{steps}\n\n"
        f"**Expected**\n\n{expected}"
    )


def _numbered(value: Any, *, prefer: tuple[str, ...]) -> str:
    items = value if isinstance(value, list) else ([] if value in {None, ""} else [value])
    if not items:
        return "_none_"
    lines: list[str] = []
    for index, item in enumerate(items, start=1):
        text = _step_text(item, prefer)
        if text:
            lines.append(f"{index}. {text}")
    return "\n".join(lines) or "_none_"


def _step_text(item: Any, prefer: tuple[str, ...]) -> str:
    if not isinstance(item, dict):
        return str(item).strip()
    prose = ""
    for key in prefer:
        raw = item.get(key)
        if isinstance(raw, str) and raw.strip() and key != "id":
            prose = raw.strip()
            break
    ident = item.get("id") or item.get("action_id") or item.get("oracle_id") or item.get("fixture_id")
    if prose and ident and ident not in prose:
        return f"{prose} (`{ident}`)"
    if prose:
        return prose
    if isinstance(ident, str) and ident.strip():
        return ident.strip()
    return ""


def _cell(value: Any) -> str:
    text = " ".join(str(value).split())
    return text.replace("|", "/") or "—"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
