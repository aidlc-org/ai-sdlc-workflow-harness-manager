---
title: CLI reference
description: All pipeline-kit commands — pack, knowledge, plugins, features, observability.
---

Global: `pipeline-kit --version` (same number as `pipeline-kit version`).

The CLI is shared. The **project** is one of [two kits](/docs/capabilities/modes): **kit mode** (default markdown pack) or **orchestrator mode** (`--mode orchestrator`). Orchestrator-only commands are listed after the pack table.

## Pack

| Command | Purpose |
|---------|---------|
| `init [project]` | Install/update `<repo>/.pipeline` and its IDE adapter. `--ide`, `--mode kit\|orchestrator`, `--agent-stubs`, `--dry-run` |
| `setup` | Install/update `~/.pipeline` and a user IDE adapter |
| `update [project]` | Refresh managed files while retaining local `config.json` values. `--user` for the home pack |
| `uninstall [project]` | Remove managed project files. `--user` for the home pack |
| `doctor [project]` | Check Python, pack, config, loader, marker, and optional IDE adapter |
| `workflows [project]` | List workflows from the active project or user pack. `--scaffold NAME` is orchestrator-only |
| `scan [project]` | Assess the repo from `graphify-out/graph.json`. Requires the `assess` package (`uv tool install -e ".[assess]"`) and an `assess` license. Writes `features/assessment/` (report, plan, answers, `prompt.md`). Does not write rule, skill, or agent bodies. `--yes`, `--no-bootstrap`, `--json`, `--apply`, `--dry-run`. Does not call a model |

`--ide` is `cursor`, `claude-code`, `github`, or `none`. `--mode` is `kit` (default) or `orchestrator`.

## Orchestrator mode

Requires the `orchestrator` extra (`uv tool install -e ".[orchestrator]"`) and `CURSOR_API_KEY` for live runs.

| Command | Purpose |
|---------|---------|
| `run --slug S --workflow W` | Start or continue a code-owned run. `--request`, `--request-file`, `--runner fake`, `--dry-run` |
| `approve --slug S --gate G` | Pass a HITL gate |
| `resume --slug S` | Continue after a gate |
| `status --slug S` | Print orchestrator run state |
| `verify` | Report install mode and sealed graph |
| `export-briefs` | Write a non-executing brief reference copy |
| `workflows --scaffold NAME` | Write `pipeline_extensions/{name}.py` in the app |

Kit mode never loads `pipeline_extensions/`. Examples: [Extensions](/docs/capabilities/extensions).

## Knowledge

`knowledge init | extract | status | validate --run | promote --run | render --slug | playwright --slug | promote-feature --slug`

See [Knowledge base](/docs/capabilities/knowledge).

## Codebase docs (monorepo wiki)

Free open kit. Artifacts under `wiki/codebase/` (not `.pipeline/wiki/`). Inventory: `.pipeline/docs-modules.yaml`.

| Command | Purpose |
|---------|---------|
| `docs init-modules [project]` | Template `docs-modules.yaml` + `wiki/codebase/` skeleton |
| `docs extract-modules [project] [--workers N] [--module ID] [--force]` | Parallel official Graphify extract per module |
| `docs merge-modules [project]` | Merge module graphs → system graph |
| `docs status [project]` | Inventory, graphs, Graphify CLI |
| `docs link-index [project]` | Rebuild `wiki/codebase/INDEX.md` |
| `docs link-agents [project] [--dry-run]` | Marked monorepo map in `AGENTS.md` |

Workflows: [Large codebase docs](/docs/workflows/large-codebase-docs), [Module security](/docs/workflows/module-security-review), [System architecture](/docs/workflows/system-architecture).

## Memory

Needs the optional memory extra (`uv tool install -e ".[memory]"` from the kit checkout, same CLI as `pipeline-kit`). See [Memory bank and MCP](/docs/capabilities/memory).

| Command | Purpose |
|---------|---------|
| `memory link <bank-root> [project] [--project-id ID] [--layout flat\|namespaced]` | Link an external artifact bank |
| `memory unlink [project]` | Remove the link |
| `memory import-local [project]` | One-time copy of local `features/` into the bank |
| `memory index [project]` | Build or refresh the FTS index |
| `memory search <query> [project] [--limit N] [--json]` | Search without MCP |
| `memory status [project]` / `memory doctor [project]` | Inspect or diagnose the link |
| `memory mcp [project]` | Run the stdio MCP server in the foreground (IDEs normally run `pipeline-memory-mcp`) |

## Plugins

`plugins list | install graphify\|archify | status | uninstall` with `--ide`, `--scope project|user`. Graphify uninstall `--purge` deletes `graphify-out/`. Agent-run observability is a bundled add-on on the [Plugins](/docs/capabilities/plugins) page; install it with `obs`, not `plugins`.

## Features

`features list | status | enable \| disable` with ids `test-design`, `playwright`, `telemetry`, `tester`, `archify`, `jira-intake`, `github-intake`, `agent-observability`.

## Observability

`obs install --adapter langfuse\|datadog\|otlp | uninstall | status | flush | report`

See [Agent-run observability](/docs/capabilities/observability).

## Portal

Reports this project's local state to an [Enterprise portal](/docs/capabilities/portal).
Metadata only; see [what is sent](/docs/reference/portal-protocol).

| Command | Purpose |
|---------|---------|
| `portal connect --url URL --key KEY [project]` | Verify the project's ingest key, store the connection in `~/.pipeline/portal.json`, send the first report |
| `portal status [project]` | Show the portal, the project and organization it maps to, and when it last reported |
| `portal push [project]` | Send the current state now |
| `portal disconnect [project]` | Forget the connection on this machine |

Once connected, commands that change local state report automatically; a failure to
report prints one line and never changes the command's exit code. In CI, set
`PIPELINE_PORTAL_URL` and `PIPELINE_PORTAL_KEY` instead of running `connect`. The URL
must be `https://`, except for `localhost`.

## Maintainers

`version [show]` prints `VERSION`. `version bump patch|minor|major` and `version set X.Y.Z` update `VERSION` (and `website/package.json`) in the **kit git checkout** — resolved from `--repo`, then `$PIPELINE_KIT_REPO`, then upwards from the current directory — never in a customer project or the installed wheel. `--commit` commits there with `git -C`; `--tag` (requires `--commit`) adds `vX.Y.Z`. Also `--dry-run`. See [This repository](/docs/maintainers/repo).

## License

Paid areas are orchestrator mode, Jira intake, the governance workflows (`security-review`, `ci-audit`, `dependency-audit`, `accessibility-review`), agent-run observability / eval (`evidence`), and repository assessment (`pipeline-kit scan`, area `assess`). Kit mode, `ask`, and `feature-development` do not read the license. `obs report` stays local. Full detail: [Licensing](/docs/reference/licensing).

```bash
export PIPELINE_KIT_LICENSE='<token>'
pipeline-kit license activate
pipeline-kit license status
```

`activate` writes `~/.pipeline/license.json` (mode `0600`). `PIPELINE_KIT_LICENSE` in the environment wins over that file for one process. Maintainers sign a token from a kit checkout with `pipeline-kit license issue --org NAME --expires YYYY-MM-DD [--features a,b]`; without `--features` the token covers all five areas (`orchestrator`, `jira`, `governance`, `evidence`, `assess`). The signing key path is `PIPELINE_KIT_LICENSE_SIGNING_KEY`.

## Legacy

`python3 install.py` remains for compatibility and maintainer `--sync-kit`.
