"""`pipeline-kit version bump|set` moves [Unreleased] under the new version heading."""

from __future__ import annotations

import re
import runpy
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
INSTALL = REPO / "install.py"

CHANGELOG = """# Changelog

## [Unreleased]

### Added

- thing

## [1.2.0] - 2026-01-01

- old
"""


def _run_cli(argv: list[str]) -> int:
    ns = runpy.run_path(str(INSTALL))
    return int(ns["cli_main"](argv))


def _checkout(root: Path) -> Path:
    (root / "kit" / "pipeline").mkdir(parents=True)
    (root / "install.py").write_text("# stub\n", encoding="utf-8")
    (root / "pyproject.toml").write_text('[project]\nname = "pipeline-kit"\n', encoding="utf-8")
    (root / "VERSION").write_text("1.2.0\n", encoding="utf-8")
    (root / ".git").mkdir()
    (root / "CHANGELOG.md").write_text(CHANGELOG, encoding="utf-8")
    return root


def test_dry_run_leaves_changelog_alone(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    repo = _checkout(tmp_path / "kit")
    assert _run_cli(["version", "bump", "patch", "--repo", str(repo), "--dry-run"]) == 0
    assert "would move [Unreleased] under [1.2.1]" in capsys.readouterr().out
    assert (repo / "CHANGELOG.md").read_text(encoding="utf-8") == CHANGELOG


def test_bump_rolls_unreleased_under_dated_heading(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    repo = _checkout(tmp_path / "kit")
    assert _run_cli(["version", "bump", "patch", "--repo", str(repo)]) == 0
    assert "CHANGELOG.md" in capsys.readouterr().out
    text = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    pattern = r"## \[Unreleased\]\n\n## \[1\.2\.1\] - \d{4}-\d{2}-\d{2}\n\n### Added\n\n- thing"
    assert re.search(pattern, text)
    assert "## [1.2.0] - 2026-01-01" in text


def test_no_changelog_flag_skips_the_roll(tmp_path: Path):
    repo = _checkout(tmp_path / "kit")
    assert _run_cli(["version", "bump", "patch", "--repo", str(repo), "--no-changelog"]) == 0
    assert (repo / "CHANGELOG.md").read_text(encoding="utf-8") == CHANGELOG
    assert (repo / "VERSION").read_text(encoding="utf-8") == "1.2.1\n"


def test_existing_version_heading_is_not_duplicated(tmp_path: Path):
    repo = _checkout(tmp_path / "kit")
    assert _run_cli(["version", "set", "1.2.0", "--repo", str(repo)]) == 0  # already current
    assert _run_cli(["version", "set", "1.3.0", "--repo", str(repo)]) == 0
    assert _run_cli(["version", "set", "1.3.0", "--repo", str(repo)]) == 0
    text = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    assert text.count("## [1.3.0]") == 1
