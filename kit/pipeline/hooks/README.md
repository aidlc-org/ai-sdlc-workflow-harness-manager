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
`.claude/settings.json`. Existing entries stay. Observability still
requires `pipeline-kit obs install`.

## What is hooked

| Event | Script | Why |
|-------|--------|-----|
| `subagentStart` | `subagent-start.py` | Next specialist needs the previous artifact. UI designer skip/consult_cap; feature-class developer needs `signoff-ba.md` |
| `subagentStop` | `subagent-stop.py` | One HANDOFF nudge (`loop_limit: 1`) |
| `beforeShellExecution` | `before-shell.py` | Deny commit/push, remote script pipes, disk wipe, remote ssh, non-localhost net, new deps |
| `beforeMCPExecution` | `before-mcp.py` | Allow MCP reads/search; deny create/edit/comment/PR/push unless `PIPELINE_ALLOW_MCP=1` |
| `beforeReadFile` | `before-read.py` | Secrets, then deny pack files not on the active allowlist |
| `preToolUse` Write | `pre-write.py` | No secret files, no generated/VCS dirs, analysis agents write artifacts only, no copy of `features/{slug}/ui/` into product source |
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

Missing config falls back to built-in defaults. Hooks never hard-fail a run.
`failClosed` stays off.

## Overrides

`PIPELINE_ALLOW_GIT=1`, `PIPELINE_ALLOW_DEPS=1`, `PIPELINE_ALLOW_NET=1`,
`PIPELINE_ALLOW_MCP=1`, `PIPELINE_ALLOW_ALL=1`, `PIPELINE_HOOK_SKIP=1`.

When `PIPELINE_HOOK_SKIP=1` (or an external portal already owns HITL),
scripts allow immediately so they do not double-gate.

## Pack allowlist

`before-read.py` uses `pack_gate.decide_read`. Active list:
`{pack}/state/active-context.json`. Missing pack means pack Reads are allowed.
Product source and `features/` are never gated.
