"""Smoke: link a temp memory bank, index it, doctor it. Skips if the memory package is missing."""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import ROOT, check, kit, out, validate_commands  # noqa: E402

validate_commands(Path(__file__).resolve().parent / "README.md")

sys.path.insert(0, str(ROOT / "packages" / "pipeline-kit-memory"))
try:
    import pipeline_memory  # noqa: F401
except ImportError as exc:
    print(f"SKIP: pipeline-kit-memory not importable ({exc}); install with pip install -e \".[memory]\"")
    raise SystemExit(0)

with tempfile.TemporaryDirectory() as tmp:
    proj, bank = Path(tmp) / "proj", Path(tmp) / "bank"
    proj.mkdir()
    check(kit("init", str(proj), "--ide", "none").returncode == 0, "init exits 0")
    r = kit("memory", "link", str(bank), str(proj))
    check(r.returncode == 0 and "memory linked" in out(r), "memory link prints 'memory linked'")
    check(bank.is_dir(), "bank folder created")
    s = kit("memory", "status", str(proj))
    info = json.loads(s.stdout)
    check(info["enabled"] is True and info["layout"] == "flat", "status JSON: enabled, flat layout")
    check(info["index_exists"] is False, "index does not exist yet")
    d0 = kit("memory", "doctor", str(proj))
    check(d0.returncode == 1 and "missing  search index" in out(d0), "doctor flags the missing index")
    check(kit("memory", "index", str(proj)).returncode == 0, "memory index exits 0")
    d1 = kit("memory", "doctor", str(proj))
    check(d1.returncode == 0 and "ok  search index" in out(d1), "doctor passes after index")
    check(kit("memory", "unlink", str(proj)).returncode == 0, "memory unlink exits 0")
print("PASS")
