"""Smoke: every workflow in the README is listed by `workflows`, and vice versa."""
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import check, kit, out  # noqa: E402

readme = (Path(__file__).resolve().parent / "README.md").read_text(encoding="utf-8")
documented = set(re.findall(r"^\| `([a-z][a-z-]*)` \|", readme, flags=re.M))
check(len(documented) >= 10, f"README documents {len(documented)} workflows")

with tempfile.TemporaryDirectory() as tmp:
    proj = Path(tmp) / "proj"
    proj.mkdir()
    r = kit("init", str(proj), "--ide", "none")
    check(r.returncode == 0, "init exits 0")
    w = kit("workflows", str(proj))
    check(w.returncode == 0, "workflows exits 0")
    listed = {ln.strip() for ln in w.stdout.splitlines() if re.fullmatch(r"[a-z][a-z-]*", ln.strip())}
    listed -= {"mode", "scope"}
    check(documented == listed, f"README matches workflows output (diff: {documented ^ listed})")
print("PASS")
