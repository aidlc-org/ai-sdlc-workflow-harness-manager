---
title: GitHub
description: Copilot CLI adapter. Same pack, skill under .github/skills/run-workflow and hooks in .github/hooks.
---

## Prerequisites

- `pipeline-kit` on PATH. See [Install the CLI](/docs/getting-started/install-cli).
- Python 3.11 or newer. `init` probes for a working interpreter and writes it into the hook config.
- GitHub Copilot CLI (or another GitHub agent that reads `.github/skills`) started from the repository root.

## Install

```bash
pipeline-kit init --ide github
```

## What gets written

| Path | Meaning |
|------|---------|
| `.pipeline/` | The pack, `config.json`, loader, hooks, install marker |
| `.github/skills/run-workflow/SKILL.md` | The skill that runs the loader |
| `.github/hooks/pipeline-guardrails.json` | Guardrail hooks. Copilot discovers `.github/hooks/*.json` on its own |

Project-scope Archify for GitHub-compatible agents typically lands under `.agents/skills/archify/`, the same as Cursor project scope.

## Hooks

`init --ide github` writes six policy entries. Other hook files in `.github/hooks/` are left alone.

| Event | Matcher | Script |
|-------|---------|--------|
| `preToolUse` | `bash\|powershell` | `before-shell.py` |
| `preToolUse` | `create\|edit` | `pre-write.py` |
| `preToolUse` | `view` | `before-read.py` |
| `postToolUseFailure` | none | `post-tool-failure.py` |
| `subagentStart` | none | `subagent-start.py` |
| `subagentStop` | none | `subagent-stop.py` |

There is no MCP gate and no after-edit `verify.rules` reminder on this host.

Observability is separate and opt-in. `pipeline-kit obs install --ide github` merges Copilot hook entries and keeps existing hooks. It needs the `evidence` license area. See [observability](/docs/capabilities/observability).

## MCP

The kit does not write MCP config. For GitHub issues you can avoid MCP: the default `intake.github.connection` is `cli` and uses `gh`. Set it to `mcp` only if your Copilot setup has a GitHub MCP server, and fill `mcp_namespaces` if discovery fails. See [adapt config.json](/docs/guides/config) and [GitHub workflows](/docs/workflows/github).

## Verify

```bash
pipeline-kit doctor --ide github
```

The output should include `ok  github adapter`. Then ask "How does X work?" from the repository root. It should run the `ask` workflow.

## Limits

- **`preToolUse` fails closed.** On Copilot CLI a hook crash or non-zero exit denies the tool call. The shipped scripts return 0 on every path, but an unhandled error blocks the call, which is the opposite of the other hosts. A timeout fails open.
- **Best-effort support.** The `create` and `edit` argument names are not in the official docs, so the hooks probe several spellings. Copilot support is best-effort until verified against a real run.
- **After a clone or Python change.** Re-run `pipeline-kit init --ide github`. The interpreter path is written per machine.
- **Hooks never fire.** Confirm the file has no `{{PYTHON}}` placeholder and sits under `.github/hooks/`. See [hooks troubleshooting](/docs/troubleshooting/hooks).
- **Fewer gates than Cursor.** No MCP gate and no verify reminder.
- **Stubs.** `--agent-stubs` writes Cursor-format files under `.cursor/agents/`. Copilot does not use them.
