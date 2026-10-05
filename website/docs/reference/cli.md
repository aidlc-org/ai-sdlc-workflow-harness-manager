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

## Plugins

`plugins list | install graphify\|archify | status | uninstall` with `--ide`, `--scope project|user`. Graphify uninstall `--purge` deletes `graphify-out/`. Agent-run observability is a bundled add-on on the [Plugins](/docs/capabilities/plugins) page; install it with `obs`, not `plugins`.

## Features

`features list | status | enable \| disable` with ids `test-design`, `playwright`, `telemetry`, `tester`, `archify`, `jira-intake`, `agent-observability`.

## Observability

`obs install --adapter langfuse\|datadog\|otlp | uninstall | status | flush | report`

See [Agent-run observability](/docs/capabilities/observability).

## Portal

Requires the `portal` extra (`pip install -e packages/pipeline-kit-portal -e .`, or `uv tool install -e ".[portal]"`).

| Command | Purpose |
|---------|---------|
| `portal serve [project]` | Start the dashboard. `--port`, `--host`, `--open`, `--read-only`, `--no-token`, `--allow-remote` |
| `portal add <path>` | Register a project in the fleet. `--team`, `--label` |
| `portal remove <path>` | Unregister a project |
| `portal list` | List registered projects |

Binds `127.0.0.1` with a per-launch token by default; writes go through the
same `features` / `plugins` / `obs` functions the CLI already uses, never a
second writer. See [Portal](/docs/capabilities/portal).

## Maintainers

`version [show]` prints `VERSION`. `version bump patch|minor|major` and `version set X.Y.Z` update `VERSION` (and `website/package.json`) in the **kit git checkout** — resolved from `--repo`, then `$PIPELINE_KIT_REPO`, then upwards from the current directory — never in a customer project or the installed wheel. `--commit` commits there with `git -C`; `--tag` (requires `--commit`) adds `vX.Y.Z`. Also `--dry-run`. See [This repository](/docs/maintainers/repo).

## License

Paid areas are orchestrator mode, Jira intake, the governance workflows (`security-review`, `ci-audit`, `dependency-audit`, `accessibility-review`), and agent-run observability / eval. Kit mode, `ask`, and `feature-development` do not read the license. `obs report` stays local.

```bash
export PIPELINE_KIT_LICENSE='<token>'
pipeline-kit license activate
pipeline-kit license status
```

`activate` writes `~/.pipeline/license.json` (mode `0600`). `PIPELINE_KIT_LICENSE` in the environment wins over that file for one process. Maintainers sign a token from a kit checkout with `pipeline-kit license issue --org NAME --expires YYYY-MM-DD`. The signing key path is `PIPELINE_KIT_LICENSE_SIGNING_KEY`.

## Legacy

`python3 install.py` remains for compatibility and maintainer `--sync-kit`.
