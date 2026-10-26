"""Smoke (manual example, static check): obs commands exist, README names env vars, no secrets."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import check, kit, out, validate_commands  # noqa: E402

readme = Path(__file__).resolve().parent / "README.md"
text = readme.read_text(encoding="utf-8")

obs = out(kit("obs", "--help"))
for sub in ("install", "uninstall", "status", "flush", "report"):
    check(sub in obs, f"obs --help lists {sub}")
validate_commands(readme)
check("langfuse" in out(kit("obs", "install", "--help")), "obs install lists the langfuse adapter")

for var in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL"):
    check(var in text, f"README names {var}")
check(not re.search(r"(pk|sk)-lf-[A-Za-z0-9]{6,}", text), "README contains no Langfuse key")
check(not re.search(r"(?i)(secret|public)_key\s*=\s*(?!<)\S", text), "env lines use placeholders only")
print("PASS")
