---
title: Agent security
description: Opt-in detection and response for coding-agent actions. Audit, warn or block, with local rules and offline session scans.
---

Agent security looks at what a coding agent is about to do (read a file, run a shell command, call an MCP tool, write a file) and records whether it looks risky. In `warn` or `block` mode it can also surface a warning or stop the call.

It is **off by default** and **adds to** the pack's existing guardrails; it never replaces them. If a guardrail denies an action, the result stays blocked in every mode.

## Two ways it runs

| | Live hooks | Offline scan |
|--|-----------|--------------|
| When | The IDE fires a pre-tool hook (`before-read`, `before-shell`, `before-mcp`, `pre-write`) | You run `pipeline-kit security scan` |
| Writes | `findings.jsonl`, `decisions.jsonl` | `session-events.jsonl`, checkpoints, provider health |
| Changes agent behaviour | Only in `warn` or `block` mode, when a rule matches | Never |

A chat reply that never calls a tool does not trigger the live path. To test it, make the agent use a real tool.

## Modes

Set the mode with `pipeline-kit security install . --mode audit|warn|block`. It decides what a rule's recommendation turns into.

| Mode | Rule says allow | Rule says warn | Rule says block |
|------|-----------------|----------------|-----------------|
| `audit` (default) | allow | allow, recorded | allow, recorded |
| `warn` | allow | warn | warn |
| `block` | allow | warn | block if severity and confidence meet the thresholds, else warn |

Defaults for the block thresholds are severity `high` and confidence `0.9`. Start in `audit`, review the findings for false positives, then move up.

## What the built-in rules catch

The `local-policy` provider runs inline, with a 100 ms default budget.

| Rule | Looks for | Recommends |
|------|-----------|------------|
| `shell.destructive` | commands like `rm -rf /` | block |
| `shell.credential_exfil` | shell commands that send credential files out | block |
| `shell.force_push` | `git push --force` | warn |
| `shell.remote_transfer` | remote-access commands | block |
| `shell.outbound_network` | non-localhost network commands such as `curl` | warn |
| `shell.secret_keys_with_network` | secret-named argument keys on a network command | warn |
| `path.credential` | reads or writes of `.env`, `*.pem`, `id_rsa`, cloud credential files | block |
| `write.secret_named_file` | writes to secret-named files | warn |
| `mcp.risky_tool` | risky MCP tool names | block |
| `mcp.path_argument` | MCP calls with credential path arguments | warn |

## Set it up

```bash
pipeline-kit security install . --mode audit
pipeline-kit security doctor .
pipeline-kit security scan .
pipeline-kit security status .
```

Use `pipeline-kit security flush .` to copy findings into the [observability](/docs/capabilities/observability) ledger, and `pipeline-kit security uninstall .` to turn it off while keeping the history. Every command is listed in the [CLI reference](/docs/reference/cli#agent-security).

State lives under `.pipeline/state/security/`. Configuration is the `agent_security` block of `.pipeline/config.json`; the template with every field is `kit/pipeline/config.json`.

## Privacy

- Ledgers hold rule ids, field names and generic detail. They never hold prompts, tool argument values or tool results (`capture.prompts` and `capture.tool_results` default to `false`).
- Session scans record tool names and argument keys only.
- The observability projection drops evidence detail.

## Limits

- Live checks need the IDE to register the pack's hooks and the agent to call a hooked tool.
- `PIPELINE_ALLOW_ALL=1`, or a session owned by the portal, skips live evaluation by design.
- Cursor session collection uses the optional `adr-sensor` package. It is strongest on macOS and Linux; on Windows the path may be found but the parser can still miss the database.
- VS Code Copilot Chat is not scanned (by design). Copilot CLI sessions are.
- Correlating actions across turns (read `.env` in one turn, send it in the next) is minimal today.
- Default failure mode is open: if a provider crashes or times out, the action is allowed. Set `fail_mode: closed` to change that.

## Extending

Third parties can add providers through the `pipeline_kit.agent_security.providers` entry-point group. Design background: `features/agentic-detection-response/adr-integration-plan.md` in the kit repository. The package's own `capabilities/agent_security/README.md` has worked examples for every mode.

Related: [Governance](/docs/components/governance), [Feature flags](/docs/capabilities/feature-flags).
