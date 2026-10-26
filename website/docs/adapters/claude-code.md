---
title: Claude Code
description: Same pack. Skill under .claude/skills/run-workflow and guardrail hooks merged into .claude/settings.json.
---

## Prerequisites

- `pipeline-kit` on PATH. See [Install the CLI](/docs/getting-started/install-cli).
- Python 3.11 or newer. `init` probes for a working interpreter and writes it into the hook config.
- A Claude Code session started from the project directory that contains `.pipeline/`.

## Install

```bash
pipeline-kit init --ide claude-code
```

Use `pipeline-kit setup --ide claude-code` for a user-scope skill. See [Where you can install](/docs/getting-started/install-scopes).

## What gets written

| Path | Meaning |
|------|---------|
| `.pipeline/` | The pack, `config.json`, loader, hooks, install marker |
| `.claude/skills/run-workflow/SKILL.md` | The skill that runs the loader |
| `.claude/settings.json` | Guardrail hooks, merged into any existing file |

Archify may land under `.claude/skills/archify/`, depending on the `gh skill` scope. See [Archify](/docs/capabilities/archify).

## Hooks

`init --ide claude-code` merges six policy entries into `.claude/settings.json`. Existing hooks stay.

| Event | Matcher | Script |
|-------|---------|--------|
| `PreToolUse` | `Bash` | `before-shell.py` |
| `PreToolUse` | `Read` | `before-read.py` |
| `PreToolUse` | `Write\|Edit` | `pre-write.py` |
| `PostToolUseFailure` | none | `post-tool-failure.py` |
| `SubagentStart` | none | `subagent-start.py` |
| `SubagentStop` | none | `subagent-stop.py` |

There is no MCP gate and no after-edit `verify.rules` reminder on this host. `before-mcp.py` and `after-file-edit.py` are wired for Cursor only.

Observability is separate and opt-in. `pipeline-kit obs install --ide claude-code` merges fail-open collector entries and does not replace your hooks. It needs the `evidence` license area. See [observability](/docs/capabilities/observability).

## MCP

The kit does not write MCP config. Claude Code reads its own MCP settings. Add the memory bank as a stdio server the same way as other hosts. See [Memory bank](/docs/capabilities/memory). For Jira over MCP, set `intake.jira.mcp_namespaces` if discovery fails. See [adapt config.json](/docs/guides/config).

## Verify

```bash
pipeline-kit doctor --ide claude-code
```

The output should include `ok  claude-code adapter`. Then start Claude Code in the project directory and ask "How does X work?". It should run the `ask` workflow.

## Limits

- **Working directory.** Open the project directory that contains `.pipeline/`. Hook commands use paths relative to it.
- **Hooks never fire.** Confirm `.claude/settings.json` has no `{{PYTHON}}` placeholder. If it does, run `init` again. See [hooks troubleshooting](/docs/troubleshooting/hooks).
- **After a clone or Python change.** Re-run `pipeline-kit init --ide claude-code`. The interpreter path is written per machine.
- **Fewer gates than Cursor.** No MCP gate and no verify reminder. Treat MCP writes as ungated and review them yourself.
- **Stubs.** `--agent-stubs` writes Cursor-format files under `.cursor/agents/`. Claude Code does not use them.
