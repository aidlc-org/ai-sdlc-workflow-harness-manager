"""Policy guardrails ship with the pack and merge on IDE init."""

from __future__ import annotations

import json
import os
import runpy
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INSTALL = REPO / "install.py"


def _run(argv: list[str]) -> int:
    ns = runpy.run_path(str(INSTALL))
    return int(ns["main"](argv))


def _run_cli(argv: list[str]) -> int:
    ns = runpy.run_path(str(INSTALL))
    return int(ns["cli_main"](argv))


def test_init_copies_guardrails_beside_obs(tmp_path: Path):
    app = tmp_path / "app"
    app.mkdir()
    assert _run(["--project", str(app), "--ide", "none"]) == 0
    hooks = app / ".pipeline" / "hooks"
    assert (hooks / "before-shell.py").is_file()
    assert (hooks / "before-mcp.py").is_file()
    assert (hooks / "before-read.py").is_file()
    assert (hooks / "after-file-edit.py").is_file()
    assert (hooks / "pre-write.py").is_file()
    assert (hooks / "subagent-start.py").is_file()
    assert (hooks / "lib.py").is_file()
    assert (hooks / "pack_gate.py").is_file()
    assert (hooks / "obs" / "obs_collect.py").is_file()
    assert not (hooks / "obs" / "before-shell.py").exists()


def test_cursor_init_merges_guardrails_not_obs(tmp_path: Path):
    app = tmp_path / "app"
    app.mkdir()
    assert _run(["--project", str(app), "--ide", "cursor"]) == 0
    data = json.loads((app / ".cursor" / "hooks.json").read_text(encoding="utf-8"))
    hooks = data["hooks"]
    assert any("before-shell.py" in item["command"] for item in hooks["beforeShellExecution"])
    assert any("before-mcp.py" in item["command"] for item in hooks["beforeMCPExecution"])
    assert any("after-file-edit.py" in item["command"] for item in hooks["afterFileEdit"])
    flat = [item.get("command", "") for entries in hooks.values() for item in entries]
    assert not any("obs_collect.py" in cmd for cmd in flat)


def test_cursor_merge_keeps_existing_and_survives_obs(tmp_path: Path):
    app = tmp_path / "app"
    app.mkdir()
    hooks = app / ".cursor" / "hooks.json"
    hooks.parent.mkdir(parents=True)
    hooks.write_text(
        json.dumps(
            {
                "version": 1,
                "hooks": {"afterFileEdit": [{"command": "node .cursor/hooks/hook-handler.js"}]},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    assert _run(["--project", str(app), "--ide", "cursor"]) == 0
    assert _run_cli(["obs", "install", str(app), "--ide", "cursor"]) == 0
    data = json.loads(hooks.read_text(encoding="utf-8"))
    after = data["hooks"]["afterFileEdit"]
    cmds = [item.get("command", "") for item in after]
    assert cmds[0] == "node .cursor/hooks/hook-handler.js"
    assert any("after-file-edit.py" in cmd for cmd in cmds)
    assert any("obs_collect.py" in cmd for cmd in cmds)


def test_uninstall_strips_guardrails_keeps_foreign(tmp_path: Path):
    app = tmp_path / "app"
    app.mkdir()
    hooks = app / ".cursor" / "hooks.json"
    hooks.parent.mkdir(parents=True)
    hooks.write_text(
        json.dumps(
            {
                "version": 1,
                "hooks": {"stop": [{"command": "node .cursor/hooks/hook-handler.js"}]},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    assert _run(["--project", str(app), "--ide", "cursor"]) == 0
    assert _run(["--uninstall", "--project", str(app)]) == 0
    data = json.loads(hooks.read_text(encoding="utf-8"))
    assert data["hooks"]["stop"] == [{"command": "node .cursor/hooks/hook-handler.js"}]
    assert "beforeShellExecution" not in data["hooks"]


def test_before_shell_denies_publish():
    script = REPO / "kit" / "pipeline" / "hooks" / "before-shell.py"
    verb = "com" + "mit"
    proc = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps({"command": "git %s -am x" % verb}),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    out = json.loads(proc.stdout)
    assert out["permission"] == "deny"


def test_before_mcp_allows_read_denies_write():
    script = REPO / "kit" / "pipeline" / "hooks" / "before-mcp.py"
    read = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps({"tool_name": "getJiraIssue"}),
        capture_output=True,
        text=True,
        check=False,
    )
    write = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps({"tool_name": "createJiraIssue"}),
        capture_output=True,
        text=True,
        check=False,
    )
    assert json.loads(read.stdout)["permission"] == "allow"
    assert json.loads(write.stdout)["permission"] == "deny"

DECLARED_AXIOS = {
    "context": {
        "new_dependencies": [
            {"name": "axios", "why_nothing_existing_works": "fetch has no retry or interceptors"}
        ]
    }
}


def _hook_install(tmp_path: Path, *scripts: str) -> Path:
    """Minimal installed layout so the hooks resolve `features/` from their own path."""
    hooks = tmp_path / ".pipeline" / "hooks"
    hooks.mkdir(parents=True)
    src = REPO / "kit" / "pipeline" / "hooks"
    for name in scripts + ("lib.py",):
        (hooks / name).write_bytes((src / name).read_bytes())
    return hooks


def _declare(root: Path, slug: str, state: dict) -> None:
    path = root / "features" / slug / "state"
    path.mkdir(parents=True, exist_ok=True)
    (path / "architect-agent.json").write_text(json.dumps(state), encoding="utf-8")


def _fire(script: Path, payload: dict, env_extra: dict) -> dict:
    env = dict(os.environ)
    for key in ("PIPELINE_ALLOW_DEPS", "PIPELINE_ALLOW_ALL", "FEATURE_SLUG", "ALLOW_DEPENDENCY"):
        env.pop(key, None)
    env.update(env_extra)
    proc = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def test_before_shell_allows_manifest_restore(tmp_path: Path):
    """A bare install adds nothing the manifest does not already pin."""
    hooks = _hook_install(tmp_path, "before-shell.py")
    out = _fire(hooks / "before-shell.py", {"command": "npm install"}, {})
    assert out["permission"] == "allow"


def test_before_shell_denies_undeclared_dependency(tmp_path: Path):
    hooks = _hook_install(tmp_path, "before-shell.py")
    _declare(tmp_path, "dark-mode", DECLARED_AXIOS)
    out = _fire(
        hooks / "before-shell.py",
        {"command": "npm install react-datepicker"},
        {"FEATURE_SLUG": "dark-mode"},
    )
    assert out["permission"] == "deny"
    assert "react-datepicker" in out["user_message"]


def test_before_shell_allows_declared_dependency(tmp_path: Path):
    hooks = _hook_install(tmp_path, "before-shell.py")
    _declare(tmp_path, "dark-mode", DECLARED_AXIOS)
    out = _fire(
        hooks / "before-shell.py",
        {"command": "npm install axios@1.6.0"},
        {"FEATURE_SLUG": "dark-mode"},
    )
    assert out["permission"] == "allow"


def test_before_shell_child_slug_reads_parent_declaration(tmp_path: Path):
    hooks = _hook_install(tmp_path, "before-shell.py")
    _declare(tmp_path, "dark-mode", DECLARED_AXIOS)
    out = _fire(
        hooks / "before-shell.py",
        {"command": "pnpm add axios"},
        {"FEATURE_SLUG": "dark-mode/toggle"},
    )
    assert out["permission"] == "allow"


def test_before_shell_keeps_legacy_message_without_slug(tmp_path: Path):
    """No slug means no declaration to read, so the pre-existing refusal stands."""
    hooks = _hook_install(tmp_path, "before-shell.py")
    out = _fire(hooks / "before-shell.py", {"command": "npm install axios"}, {})
    assert out["permission"] == "deny"
    assert "PIPELINE_ALLOW_DEPS=1" in out["user_message"]


def test_before_shell_deps_break_glass(tmp_path: Path):
    hooks = _hook_install(tmp_path, "before-shell.py")
    out = _fire(
        hooks / "before-shell.py",
        {"command": "npm install react-datepicker"},
        {"PIPELINE_ALLOW_DEPS": "1"},
    )
    assert out["permission"] == "allow"


def test_pre_write_denies_undeclared_manifest_dependency(tmp_path: Path):
    hooks = _hook_install(tmp_path, "pre-write.py")
    _declare(tmp_path, "dark-mode", DECLARED_AXIOS)
    manifest = tmp_path / "app" / "package.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"dependencies": {"react": "^18.0.0"}}), encoding="utf-8")
    out = _fire(
        hooks / "pre-write.py",
        {
            "file_path": "app/package.json",
            "contents": json.dumps({"dependencies": {"react": "^18.0.0", "react-datepicker": "^4.0.0"}}),
        },
        {"FEATURE_SLUG": "dark-mode"},
    )
    assert out["permission"] == "deny"
    assert "react-datepicker" in out["user_message"]


def test_pre_write_allows_declared_and_unchanged_manifest(tmp_path: Path):
    hooks = _hook_install(tmp_path, "pre-write.py")
    _declare(tmp_path, "dark-mode", DECLARED_AXIOS)
    manifest = tmp_path / "app" / "package.json"
    manifest.parent.mkdir(parents=True)
    base = {"dependencies": {"react": "^18.0.0"}}
    manifest.write_text(json.dumps(base), encoding="utf-8")
    declared = _fire(
        hooks / "pre-write.py",
        {
            "file_path": "app/package.json",
            "contents": json.dumps({"dependencies": {"react": "^18.0.0", "axios": "^1.6.0"}}),
        },
        {"FEATURE_SLUG": "dark-mode"},
    )
    untouched = _fire(
        hooks / "pre-write.py",
        {"file_path": "app/package.json", "contents": json.dumps(base)},
        {"FEATURE_SLUG": "dark-mode"},
    )
    assert declared["permission"] == "allow"
    assert untouched["permission"] == "allow"


def test_pre_write_manifest_gate_fails_open_without_slug(tmp_path: Path):
    hooks = _hook_install(tmp_path, "pre-write.py")
    manifest = tmp_path / "app" / "package.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"dependencies": {}}), encoding="utf-8")
    out = _fire(
        hooks / "pre-write.py",
        {
            "file_path": "app/package.json",
            "contents": json.dumps({"dependencies": {"react-datepicker": "^4.0.0"}}),
        },
        {},
    )
    assert out["permission"] == "allow"

COPILOT_TOOL_NAMES = {"bash", "powershell", "create", "edit", "view"}


def _verdicts(out: dict) -> tuple:
    """The same decision as each host reads it: Cursor, Copilot, Claude Code."""
    return (
        out.get("permission"),
        out.get("permissionDecision"),
        (out.get("hookSpecificOutput") or {}).get("permissionDecision"),
    )


def test_one_payload_answers_every_host(tmp_path: Path):
    """Cursor, Copilot, and Claude key sets do not collide, so all three ship together."""
    hooks = _hook_install(tmp_path, "before-shell.py")
    out = _fire(hooks / "before-shell.py", {"command": "git %s -am x" % ("com" + "mit")}, {})
    assert _verdicts(out) == ("deny", "deny", "deny")
    assert out["hookSpecificOutput"]["permissionDecisionReason"] == out["user_message"]


def test_hook_format_can_force_a_single_shape(tmp_path: Path):
    hooks = _hook_install(tmp_path, "before-shell.py")
    payload = {"command": "git %s -am x" % ("com" + "mit")}
    cursor = _fire(hooks / "before-shell.py", payload, {"PIPELINE_HOOK_FORMAT": "cursor"})
    claude = _fire(hooks / "before-shell.py", payload, {"PIPELINE_HOOK_FORMAT": "claude"})
    copilot = _fire(hooks / "before-shell.py", payload, {"PIPELINE_HOOK_FORMAT": "copilot"})
    assert set(cursor) == {"permission", "user_message", "agent_message"}
    assert set(claude) == {"hookSpecificOutput"}
    assert set(copilot) == {"permissionDecision", "permissionDecisionReason"}


def test_copilot_tool_args_object_and_json_string(tmp_path: Path):
    """Copilot documents `toolArgs` as an object in one place and a JSON string in another."""
    hooks = _hook_install(tmp_path, "before-shell.py")
    _declare(tmp_path, "dark-mode", DECLARED_AXIOS)
    as_object = _fire(
        hooks / "before-shell.py",
        {"toolName": "bash", "cwd": "/repo", "toolArgs": {"command": "npm install react-datepicker"}},
        {"FEATURE_SLUG": "dark-mode"},
    )
    as_string = _fire(
        hooks / "before-shell.py",
        {
            "toolName": "bash",
            "cwd": "/repo",
            "toolArgs": json.dumps({"command": "npm install react-datepicker"}),
        },
        {"FEATURE_SLUG": "dark-mode"},
    )
    declared = _fire(
        hooks / "before-shell.py",
        {"toolName": "bash", "toolArgs": {"command": "npm install axios"}},
        {"FEATURE_SLUG": "dark-mode"},
    )
    assert _verdicts(as_object) == ("deny", "deny", "deny")
    assert _verdicts(as_string) == ("deny", "deny", "deny")
    assert "react-datepicker" in as_string["permissionDecisionReason"]
    assert _verdicts(declared) == ("allow", "allow", "allow")


def test_copilot_write_payload_reaches_pre_write(tmp_path: Path):
    hooks = _hook_install(tmp_path, "pre-write.py")
    _declare(tmp_path, "dark-mode", DECLARED_AXIOS)
    manifest = tmp_path / "app" / "package.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"dependencies": {"react": "^18.0.0"}}), encoding="utf-8")
    out = _fire(
        hooks / "pre-write.py",
        {
            "toolName": "create",
            "toolArgs": {
                "path": "app/package.json",
                "file_text": json.dumps({"dependencies": {"react": "^18.0.0", "left-pad": "^1.0.0"}}),
            },
        },
        {"FEATURE_SLUG": "dark-mode"},
    )
    assert _verdicts(out) == ("deny", "deny", "deny")
    assert "left-pad" in out["user_message"]


def test_detect_python_returns_a_working_interpreter():
    ns = runpy.run_path(str(INSTALL))
    token = ns["detect_python"]()
    assert token
    proc = subprocess.run(
        token.strip('"').split() + ["-c", "print('ok')"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0 and "ok" in proc.stdout


def test_every_ide_gets_substituted_hook_commands(tmp_path: Path):
    """No harness sets env vars or resolves `python3` portably, so neither may ship."""
    targets = {
        "cursor": Path(".cursor") / "hooks.json",
        "claude-code": Path(".claude") / "settings.json",
        "github": Path(".github") / "hooks" / "pipeline-guardrails.json",
    }
    for ide, rel in targets.items():
        app = tmp_path / ide
        app.mkdir()
        assert _run(["--project", str(app), "--ide", ide]) == 0
        raw = (app / rel).read_text(encoding="utf-8")
        assert "{{PYTHON}}" not in raw, "%s: placeholder not substituted" % ide
        assert "python3 " not in raw, "%s: ships a bare python3" % ide
        assert "PIPELINE_HOOK_FORMAT=" not in raw, "%s: ships a POSIX env prefix" % ide
        assert ".pipeline/hooks/" in raw


def test_copilot_fragment_matchers_name_real_tools():
    fragment = json.loads(
        (REPO / "kit" / "pipeline" / "hooks" / "copilot.hooks.json").read_text(encoding="utf-8")
    )
    pre = fragment["hooks"]["preToolUse"]
    assert pre, "no preToolUse entries"
    for entry in pre:
        assert entry["bash"] == entry["powershell"]
        for name in entry["matcher"].split("|"):
            assert name in COPILOT_TOOL_NAMES, "unknown Copilot tool: %s" % name


def test_github_uninstall_removes_the_owned_hook_file(tmp_path: Path):
    app = tmp_path / "app"
    app.mkdir()
    owned = app / ".github" / "hooks" / "pipeline-guardrails.json"
    assert _run(["--project", str(app), "--ide", "github"]) == 0
    assert owned.is_file()
    assert _run(["--uninstall", "--project", str(app)]) == 0
    assert not owned.exists()

def _all_hook_commands(cfg: dict) -> list[tuple[str, str]]:
    rows = []
    for event, entries in (cfg.get("hooks") or {}).items():
        for entry in entries:
            for hook in entry.get("hooks") or [entry]:
                rows.append((event, hook.get("command") or hook.get("bash") or ""))
    return rows


def test_upgrade_replaces_stale_guardrails_and_keeps_foreign_hooks(tmp_path: Path):
    """A pre-change install registered `python3` and a POSIX env prefix.

    Appending beside those would run each hook twice with one invocation failing,
    and Copilot's fail-closed preToolUse turns that failure into a blanket deny.
    """
    app = tmp_path / "app"
    app.mkdir()
    cfg = app / ".claude" / "settings.json"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(
        json.dumps(
            {
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": "Bash",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "PIPELINE_HOOK_FORMAT=claude python3 .pipeline/hooks/before-shell.py",
                                }
                            ],
                        }
                    ],
                    "Stop": [{"hooks": [{"type": "command", "command": "node my-own-hook.js"}]}],
                    "PostToolUse": [
                        {
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "python3 .pipeline/hooks/obs/obs_collect.py",
                                }
                            ]
                        }
                    ],
                }
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    assert _run(["--project", str(app), "--ide", "claude-code"]) == 0
    first = _all_hook_commands(json.loads(cfg.read_text(encoding="utf-8")))

    commands = [cmd for _, cmd in first]
    assert not [c for c in commands if "PIPELINE_HOOK_FORMAT=" in c], "stale env prefix survived"
    assert not [c for c in commands if "python3 .pipeline/hooks/before" in c], "stale python3 survived"
    assert sum("before-shell.py" in c for c in commands) == 1, "hook registered twice"
    assert ("Stop", "node my-own-hook.js") in first, "dropped a hook we do not own"
    assert any("obs_collect" in c for c in commands), "dropped the obs collector"

    # re-running must not accumulate
    assert _run(["--project", str(app), "--ide", "claude-code"]) == 0
    second = _all_hook_commands(json.loads(cfg.read_text(encoding="utf-8")))
    assert first == second, "merge is not idempotent"
