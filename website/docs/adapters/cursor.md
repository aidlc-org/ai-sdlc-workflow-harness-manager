---
title: Cursor
description: Project hooks and skills load from the workspace root. Open the repo that contains .cursor.
---

## Prerequisites

- `pipeline-kit` on PATH. See [Install the CLI](/docs/getting-started/install-cli).
- Python 3.11 or newer. `init` probes for a working interpreter and writes it into the hook config.
- Cursor with the repository root as the workspace folder.

## Install

```bash
pipeline-kit init --ide cursor
```

`cursor` is the default for `--ide`. Add `--agent-stubs` for named Task types. Use `pipeline-kit setup --ide cursor` to install the skill for every repo on this machine. See [Where you can install](/docs/getting-started/install-scopes).

## What gets written

| Path | Meaning |
|------|---------|
| `.pipeline/` | The pack, `config.json`, loader, hooks, install marker |
| `.cursor/skills/run-workflow/SKILL.md` | The skill that runs the loader |
| `.cursor/hooks.json` | Guardrail hooks, merged into any existing file |
| `.cursor/agents/*.md` | Thin Task stubs. Only with `--agent-stubs` |
| `~/.cursor/skills/run-workflow` | With `setup --ide cursor` (user scope) |

Without stubs, parent Tasks use `generalPurpose` and the prompt `Follow .pipeline/agents/{name}.md`.

## Hooks

`init --ide cursor` merges eight policy entries into `.cursor/hooks.json` and keeps existing entries.

| Event | Script |
|-------|--------|
| `subagentStart` | `subagent-start.py` |
| `subagentStop` | `subagent-stop.py` |
| `beforeShellExecution` | `before-shell.py` |
| `beforeMCPExecution` | `before-mcp.py` |
| `beforeReadFile` | `before-read.py` |
| `preToolUse` (Write, StrReplace) | `pre-write.py` |
| `afterFileEdit` | `after-file-edit.py` |
| `postToolUseFailure` | `post-tool-failure.py` |

What the guardrails deny is summarized in [Team best practices](/docs/guides/team-best-practices#set-guardrails). Cursor is the only host that gets the MCP gate and the after-edit `verify.rules` reminder.

Agent-run observability is separate and opt-in. `pipeline-kit obs install --ide cursor` appends its entries to the same file. It needs the `evidence` license area. See [observability](/docs/capabilities/observability).

## MCP

The kit does not write MCP config. The `beforeMCPExecution` hook allows MCP reads and searches and denies writes (create, edit, comment, push) unless `PIPELINE_ALLOW_MCP=1`.

- Jira over MCP uses a server you configure in Cursor. Set `intake.jira.mcp_namespaces` if discovery fails. See [adapt config.json](/docs/guides/config).
- The memory bank adds a stdio entry to `.cursor/mcp.json`. See [Memory bank](/docs/capabilities/memory).

## Verify

```bash
pipeline-kit doctor --ide cursor
```

The output should include `ok  cursor adapter`. Then open the repository root in Cursor, confirm the `run-workflow` skill is listed, and ask "How does X work?". It should run the `ask` workflow.

## Limits

- **Workspace root.** Cursor project hooks and skills load from the workspace root. Open the repository that contains `.cursor/hooks.json` and `.pipeline/`. A multi-root window whose first folder is another repo will not fire these hooks.
- **Hooks never fire.** Check the workspace root first. Then confirm `.cursor/hooks.json` has no `{{PYTHON}}` placeholder. If it does, run `init` again. See [hooks troubleshooting](/docs/troubleshooting/hooks).
- **After a clone or Python change.** Re-run `pipeline-kit init --ide cursor`. The interpreter path is written per machine.
- **External portal.** If an external agent portal owns approvals, pipeline hooks should not duplicate its policy. `failClosed` is off by default so a crashed hook does not freeze the IDE.
- **Observability.** Child Task traces can show zero tokens until Cursor sends usage for them.
- **Stubs.** Named Task types such as `developer-agent` exist only with `--agent-stubs`. The stubs are in Cursor format, and `init --agent-stubs` writes them for any `--ide` value.
