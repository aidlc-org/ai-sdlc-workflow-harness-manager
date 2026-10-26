"""Docs drift guards: guide copies, CLI reference coverage, changelog vs VERSION."""

from __future__ import annotations

import ast
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CLI_DOC = REPO / "website" / "docs" / "reference" / "cli.md"


def _str_arg(call: ast.Call) -> str | None:
    if call.args and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str):
        return call.args[0].value
    return None


def cli_commands() -> tuple[set[str], set[tuple[str, ...]]]:
    """Top-level commands and (group, sub...) paths declared in install.py's argparse tree."""
    tree = ast.parse((REPO / "install.py").read_text(encoding="utf-8"))
    # variable name -> command path of the parser or subparsers object it holds
    paths: dict[str, tuple[str, ...]] = {}
    found: set[tuple[str, ...]] = set()

    calls: list[tuple[str | None, ast.Call]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            target = node.targets[0]
            calls.append((target.id if isinstance(target, ast.Name) else None, node.value))
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            calls.append((None, node.value))

    calls.sort(key=lambda item: item[1].lineno)
    for target, call in calls:
        # unwrap `x.add_parser("a").add_argument(...)` chains down to the add_parser call
        inner = call
        while (
            isinstance(inner.func, ast.Attribute)
            and isinstance(inner.func.value, ast.Call)
            and inner.func.attr not in {"add_parser", "add_subparsers"}
        ):
            inner = inner.func.value
        if not isinstance(inner.func, ast.Attribute) or not isinstance(inner.func.value, ast.Name):
            continue
        owner = inner.func.value.id
        if inner.func.attr == "add_subparsers" and owner in paths:
            if target:
                paths[target] = paths[owner]
        elif inner.func.attr == "add_parser":
            name = _str_arg(inner)
            if name is None:
                continue
            if owner == "commands":
                path = (name,)
            elif owner in paths:
                path = (*paths[owner], name)
            else:
                continue
            found.add(path)
            if target:
                paths[target] = path
        elif inner.func.attr == "add_subparsers" and owner == "parser":
            if target:
                paths[target] = ()
    # `commands` hangs off the root parser, whose path is empty
    top = {path[0] for path in found if len(path) == 1}
    return top, {path for path in found if len(path) > 1}


def test_cli_parse_finds_known_commands() -> None:
    top, nested = cli_commands()
    assert {"init", "doctor", "security", "eval", "memory"} <= top
    assert ("memory", "link") in nested


def test_cli_reference_covers_every_command() -> None:
    text = CLI_DOC.read_text(encoding="utf-8")
    top, nested = cli_commands()
    missing = [name for name in sorted(top) if not re.search(rf"`{re.escape(name)}[ `]", text)]
    for path in sorted(nested):
        group, leaf = path[0], path[-1]
        if " ".join(path) in text:
            continue
        # a group may list its subcommands in one line: `group a | b | c`
        blob = "\n".join(
            line for line in text.splitlines() if f"`{group} " in line or f"`{group}`" in line
        )
        if not re.search(rf"(?<![\w-]){re.escape(leaf)}(?![\w-])", blob):
            missing.append(" ".join(path))
    assert not missing, f"commands in install.py missing from reference/cli.md: {missing}"


def test_customer_guide_copy_matches_root() -> None:
    root = (REPO / "CUSTOMER-GUIDE.md").read_text(encoding="utf-8")
    shipped = (REPO / "kit" / "pipeline" / "docs" / "CUSTOMER-GUIDE.md").read_text(encoding="utf-8")
    assert root == shipped, (
        "kit/pipeline/docs/CUSTOMER-GUIDE.md differs from CUSTOMER-GUIDE.md. "
        "Edit the root file, then copy it over the shipped one."
    )


def test_version_has_changelog_heading() -> None:
    """The current VERSION needs a dated CHANGELOG heading; unreleased work sits above it."""
    version = (REPO / "VERSION").read_text(encoding="utf-8").strip()
    changelog = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    headings = re.findall(r"^## \[([^\]]+)\]( - \d{4}-\d{2}-\d{2})?", changelog, flags=re.MULTILINE)
    names = [name for name, _ in headings]
    assert names and names[0] == "Unreleased", "CHANGELOG.md must start with an [Unreleased] section"
    assert version in names, f"VERSION {version} has no '## [{version}] - YYYY-MM-DD' heading in CHANGELOG.md"
    assert dict(headings)[version], f"CHANGELOG heading for {version} needs a date"


def test_llms_txt_links_use_the_configured_site_url() -> None:
    config = (REPO / "website" / "docusaurus.config.ts").read_text(encoding="utf-8")
    url = re.search(r"^\s*url:\s*'([^']+)'", config, flags=re.MULTILINE)
    assert url, "website/docusaurus.config.ts has no url"
    base = url.group(1).rstrip("/")
    llms = (REPO / "website" / "static" / "llms.txt").read_text(encoding="utf-8")
    foreign = sorted({u for u in re.findall(r"\]\((https?://[^)]+)\)", llms) if not u.startswith(base)})
    assert not foreign, f"llms.txt links outside {base}: {foreign[:3]}"
