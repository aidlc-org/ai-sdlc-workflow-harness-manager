"""Smoke: documented plugin commands exist; nothing is installed."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import check, kit, out, validate_commands  # noqa: E402

validate_commands(Path(__file__).resolve().parent / "README.md")
r = kit("plugins", "list")
check(r.returncode == 0 and "graphify" in out(r), "plugins list names graphify")
print("PASS")
