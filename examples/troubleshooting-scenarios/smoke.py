"""Smoke: reproduce three offline problems and assert the real message text."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import check, env, kit, out  # noqa: E402

with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    home = tmp / "home"
    home.mkdir()

    # 1. doctor on an uninitialised folder (isolated home so no user pack exists)
    empty = tmp / "empty"
    empty.mkdir()
    d = kit("doctor", str(empty), "--ide", "none", home=home)
    text = out(d)
    check(d.returncode == 1, "doctor exits 1 on an uninitialised folder")
    check("missing  install marker" in text, "doctor: missing install marker")
    check("pipeline-kit setup is incomplete" in text, "doctor: setup is incomplete")

    # 2. init twice
    proj = tmp / "proj"
    proj.mkdir()
    first = kit("init", str(proj), "--ide", "none", home=home)
    check(first.returncode == 0 and "config.json: wrote" in out(first), "first init: config.json: wrote")
    cfg = proj / ".pipeline" / "config.json"
    data = json.loads(cfg.read_text(encoding="utf-8"))
    data["deploy"]["target"] = "staging"
    data["deploy"]["targets"] = ["staging"]
    cfg.write_text(json.dumps(data, indent=2), encoding="utf-8")
    second = kit("init", str(proj), "--ide", "none", home=home)
    check(second.returncode == 0 and "config.json: merged" in out(second), "second init: config.json: merged")
    check(json.loads(cfg.read_text(encoding="utf-8"))["deploy"]["target"] == "staging", "local config value kept")

    # 3. hook denial
    hook = proj / ".pipeline" / "hooks" / "before-shell.py"

    def run_hook(command: str, **extra: str) -> dict:
        e = env(home)
        for k in ("PIPELINE_ALLOW_ALL", "PIPELINE_ALLOW_GIT"):
            e.pop(k, None)
        e.update(extra)
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
        r = subprocess.run([sys.executable, str(hook)], input=payload, capture_output=True,
                           text=True, encoding="utf-8", env=e, cwd=str(proj), timeout=60)
        return json.loads(r.stdout)

    denied = run_hook("git push origin main")
    check(denied["permission"] == "deny", "git push is denied")
    check("Blocked commit/push/publish. Set PIPELINE_ALLOW_GIT=1" in denied["permissionDecisionReason"],
          "denial reason text matches")
    check(run_hook("git push origin main", PIPELINE_ALLOW_GIT="1")["permission"] == "allow",
          "PIPELINE_ALLOW_GIT=1 allows the push")
    check(run_hook("ls")["permission"] == "allow", "a harmless command is allowed")
print("PASS")
