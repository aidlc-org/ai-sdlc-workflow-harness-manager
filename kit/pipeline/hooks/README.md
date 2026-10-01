# Policy hooks

| Attribute | Value |
|-----------|--------|
| Type | Handbook |
| Audience | Developers running the pack in an IDE |
| Adapt | Do not add a customer app, host, or tracker URL here. Overlay verify rules in `config.json`. |

Command scripts for IDE tool gates. They sit next to `obs/` and ship with
every `pipeline-kit init`. They are **not** observability collectors.

`init --ide cursor` merges entries into `.cursor/hooks.json`.
`init --ide claude-code` merges mapped PreToolUse commands into
`.claude/settings.json`. `init --ide github` writes
`.github/hooks/pipeline-guardrails.json`, which Copilot CLI discovers on its
own. Existing entries stay. Observability still requires
`pipeline-kit obs install`.

## One payload, every host

A hook prints one JSON object carrying all three decision shapes. The key sets
do not collide, so each harness reads its own and ignores the rest:

| Host | Reads |
|------|-------|
| Cursor | `permission`, `user_message`, `agent_message` |
| Copilot CLI | top-level `permissionDecision`, `permissionDecisionReason` |
| Claude Code | `hookSpecificOutput.permissionDecision` / `.permissionDecisionReason` |

This is why no hook needs an environment variable to pick a format. The old
`PIPELINE_HOOK_FORMAT=claude` prefix is gone from the shipped configs: `VAR=x cmd`
is a parse error in cmd.exe and PowerShell, so it silently disabled every hook on
Windows.

## Interpreter

Hook configs are plain command strings, so they cannot resolve `sys.executable`
at runtime. `install.py` probes for a working interpreter (`detect_python`) and
writes it into the config. The shipped fragments carry a `{{PYTHON}}`
placeholder; an installed config that still contains it was not written by the
installer.

`python3` is not portable: on Windows it is usually absent, or an inert
Microsoft Store alias that prints "Python was not found" and exits non-zero.
Many Linux images have only `python3`. Probing settles it per machine — so
**re-run `init` after cloning a repo whose IDE config was committed**, or on a
machine where Python moved.

## Copilot CLI differences

- `preToolUse` is **fail-closed**: a crash or non-zero exit denies the tool call.
  Timeouts fail open. Every script here returns 0 on all paths, so the contract
  below still holds for the happy path — but an unhandled exception blocks rather
  than passes, which is the opposite of the other two hosts.
- `matcher` is a regex on `toolName`, which Copilot anchors as `^(?:PATTERN)$`.
  Writes arrive as the `create` and `edit` tools, shells as `bash` and
  `powershell`.
- Tool arguments arrive under `toolArgs`, which the official docs type as an
  object in one place and a JSON string in another. `lib._nested` accepts both.
- The `create` / `edit` argument key names are not in official docs, so
  `lib.tool_path` / `lib.tool_contents` probe several spellings. Copilot support
  is best-effort until verified against a real run.

## What is hooked

| Event | Script | Why |
|-------|--------|-----|
| `subagentStart` | `subagent-start.py` | Next specialist needs the previous artifact. UI designer skip/consult_cap; feature-class developer needs `signoff-ba.md` |
| `subagentStop` | `subagent-stop.py` | One HANDOFF nudge (`loop_limit: 1`) |
| `beforeShellExecution` | `before-shell.py` | Deny commit/push, remote script pipes, disk wipe, remote ssh, non-localhost net, and installs of packages the Architect did not declare |
| `beforeMCPExecution` | `before-mcp.py` | Allow MCP reads/search; deny create/edit/comment/PR/push unless `PIPELINE_ALLOW_MCP=1` |
| `beforeReadFile` | `before-read.py` | Secrets, then deny pack files not on the active allowlist |
| `preToolUse` Write | `pre-write.py` | No secret files, no generated/VCS dirs, analysis agents write artifacts only, no copy of `features/{slug}/ui/` into product source, no undeclared dependency in `package.json` / `requirements.txt` |
| `afterFileEdit` | `after-file-edit.py` | Inject the verify reminder from `config.json` |
| `postToolUseFailure` | `post-tool-failure.py` | Do not fix failures by dropping auth, hooks, or tests |

## Config

`subagent-start.py`, `pre-write.py`, and `after-file-edit.py` read
`.pipeline/config.json` (project pack, else `~/.pipeline/config.json`):

| Key | Used for |
|-----|----------|
| `workflows.{name}.chain` / `.skips` / `.plan_source` | Which gate applies |
| `product.artifact_dir` / `product.readonly_agents` | Who may write where |
| `verify.rules` | Path-substring reminders after an edit |
| `code_minimalism.require_declared_dependencies` / `.manifest_files` | Whether a new dependency needs an Architect declaration, and which manifests are checked |

Missing config falls back to built-in defaults. Hooks never hard-fail a run.
`failClosed` stays off.

## Overrides

`PIPELINE_ALLOW_GIT=1`, `PIPELINE_ALLOW_DEPS=1`, `PIPELINE_ALLOW_NET=1`,
`PIPELINE_ALLOW_MCP=1`, `PIPELINE_ALLOW_ALL=1`, `PIPELINE_HOOK_SKIP=1`.

`PIPELINE_HOOK_FORMAT` set to `cursor`, `claude`, or `copilot` emits only that
shape. Leave it unset unless a host rejects unknown keys; the default carries all
three.

`ALLOW_DEPENDENCY={name}` (comma-separated) allows those packages for one run
without a declaration. `FEATURE_SLUG` is what lets the dependency gates find
the declaration; without it they fall back to refusing every new install and
to allowing every manifest edit.

When `PIPELINE_HOOK_SKIP=1` (or an external portal already owns HITL),
scripts allow immediately so they do not double-gate.

## Pack allowlist

`before-read.py` uses `pack_gate.decide_read`. Active list:
`{pack}/state/active-context.json`. Missing pack means pack Reads are allowed.
Product source and `features/` are never gated.
