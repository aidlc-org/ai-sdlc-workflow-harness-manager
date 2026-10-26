"""Run every examples/*/smoke.py in a subprocess; each must exit 0."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SMOKES = sorted((ROOT / "examples").glob("*/smoke.py"))


def test_examples_found() -> None:
    assert len(SMOKES) >= 9


@pytest.mark.parametrize("smoke", SMOKES, ids=lambda p: p.parent.name)
def test_example_smoke(smoke: Path) -> None:
    r = subprocess.run(
        [sys.executable, str(smoke)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(ROOT), timeout=120,
    )
    assert r.returncode == 0, (r.stdout + r.stderr)[-2000:]
