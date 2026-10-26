---
title: No IDE
description: Pack only. Run the loader from the shell. No auto-discovered skill.
---

## Prerequisites

- `pipeline-kit` on PATH. See [Install the CLI](/docs/getting-started/install-cli).
- Python 3.11 or newer.
- A shell in the repository root.

## Install

```bash
pipeline-kit init --ide none
```

`--ide none` installs `.pipeline/` and skips the editor adapter. This is the right mode for CI experiments or editors the kit has no adapter for.

## What gets written

| Path | Meaning |
|------|---------|
| `.pipeline/` | The pack, `config.json`, loader, hooks, install marker |

Nothing is written under `.cursor/`, `.claude/` or `.github/`, and no hooks are merged.

## Hooks

None. Guardrail hooks are merged only for `cursor`, `claude-code` and `github`. The scripts still exist under `.pipeline/hooks/`, but nothing calls them.

Agent-run observability needs an IDE that fires hooks. `pipeline-kit obs install` accepts `--ide cursor`, `claude-code` or `github`, not `none`.

## MCP

None. The kit does not write MCP config, and without hooks there is no MCP gate. If your editor supports MCP, set it up in that editor.

## Verify

```bash
pipeline-kit doctor
python3 .pipeline/loader/load_workflow.py --workflow ask --step parent --slug try-ask
```

`doctor` should end with `is ready`. The loader prints the `allowed_reads` for the step. Read only those files. On Windows, use `python` if `python3` is not found.

## Limits

- **You drive each step.** Run the loader yourself, then read only the printed `allowed_reads`. Nothing enforces the allowlist.
- **No gates.** No write, shell or read hooks run. Rely on review.
- **No auto-discovery.** Overlay `AGENTS.md` if any agent in your editor reads it, and name the loader command there. See [AGENTS.md guide](/docs/guides/agents-md).
- **Stubs.** `--agent-stubs` still writes Cursor-format files under `.cursor/agents/`. They are unused here.
- **Moving to an IDE later.** Run `pipeline-kit init --ide <ide>` again. It adds the adapter and keeps your `config.json` values.
