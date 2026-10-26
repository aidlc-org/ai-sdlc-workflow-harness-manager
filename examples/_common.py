"""Shared helpers for example smoke scripts. Standard library only, no network."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / "install.py"


def env(home: Path | None = None) -> dict[str, str]:
    e = dict(os.environ)
    e["PYTHONUTF8"] = "1"
    e["PYTHONIOENCODING"] = "utf-8"
    if home is not None:
        e["HOME"] = e["USERPROFILE"] = str(home)
    return e


def kit(*args: str, home: Path | None = None, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run `python install.py <args>` and capture text output."""
    return subprocess.run(
        [sys.executable, str(INSTALL), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=env(home), cwd=str(cwd) if cwd else None, timeout=90,
    )


def out(p: subprocess.CompletedProcess) -> str:
    return (p.stdout or "") + (p.stderr or "")


def check(cond: bool, msg: str) -> None:
    if not cond:
        print(f"FAIL: {msg}")
        raise SystemExit(1)
    print(f"ok: {msg}")


def stack_smoke(example_dir: Path, expected_files: list[str]) -> None:
    """Copy <example_dir>/skeleton to a temp dir, init, doctor, assert files."""
    with tempfile.TemporaryDirectory() as tmp:
        proj = Path(tmp) / "proj"
        shutil.copytree(example_dir / "skeleton", proj)
        r = kit("init", str(proj), "--ide", "none")
        check(r.returncode == 0, f"init exits 0 ({out(r)[-200:]!r})")
        for rel in expected_files:
            check((proj / rel).exists(), f"{rel} exists after init")
        d = kit("doctor", str(proj), "--ide", "none")
        check(d.returncode == 0, "doctor exits 0")
        check("is ready" in out(d), "doctor says ready")
        print("PASS")


def readme_commands(readme: Path) -> list[list[str]]:
    """Return `pipeline-kit ...` commands found in fenced code blocks, as token lists."""
    import re
    import shlex

    cmds: list[list[str]] = []
    for block in re.findall(r"```[a-z]*\n(.*?)```", readme.read_text(encoding="utf-8"), flags=re.S):
        for line in block.splitlines():
            line = line.strip().rstrip("\\").strip()
            if line.startswith("pipeline-kit "):
                cmds.append(shlex.split(line)[1:])
    return cmds


def validate_commands(readme: Path) -> int:
    """Every documented command must exist, and every --flag must appear in its --help."""
    cmds = readme_commands(readme)
    check(bool(cmds), f"{readme.parent.name}: README has pipeline-kit commands")
    for tokens in cmds:
        head = [t for t in tokens[:2] if t.replace("-", "").isalpha() and not t.startswith("-")]
        # keep the command and, if present, its subcommand; positionals are harmless for --help
        h = kit(*head, "--help")
        check(h.returncode == 0, f"`pipeline-kit {' '.join(head)}` exists")
        for t in tokens:
            if t.startswith("--"):
                flag = t.split("=")[0]
                check(flag in out(h), f"`{' '.join(head)}` accepts {flag}")
    return len(cmds)
