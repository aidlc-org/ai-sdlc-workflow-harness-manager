---
title: Error messages
description: Messages the kit prints or an IDE hook returns, what causes each, and the fix.
---

Messages are quoted as the code prints them. Text in angle brackets is filled in at run time. Exit codes come from the code: `64` bad input or missing setup, `73` license, `1` general failure, `2` bad usage.

A message that is not listed here was not verified. Run `pipeline-kit doctor` first. If you are unsure where to look, use the [flowchart](/docs/troubleshooting/flowchart).

## Install and project setup

| Message | Cause | Fix |
|---------|-------|-----|
| `not a directory: <path>` (exit 64) | The `[project]` argument is not an existing folder | Pass the repo root, or run the command from it |
| `no pipeline-kit install at <pack> (install.json missing)` (exit 1) | `uninstall` found no managed pack at that path | Check the path. Use `--user` for the home pack |
| `pipeline-kit setup is incomplete` (exit 1) | `doctor` printed at least one `missing` line | Fix each `missing` line. `pipeline-kit init` or `update` restores most of them |
| `missing  install marker`, `missing  configuration`, `missing  workflow loader` | The repo has no pack, so `doctor` checked the home pack (`~/.pipeline`) and did not find one | Run `pipeline-kit init --ide <ide>` in the repo |
| `missing  <ide> adapter` | The IDE skill file is absent | Re-run `init --ide <ide>` |
| `missing  CURSOR_API_KEY` | The pack is in orchestrator mode and the variable is empty | Set `CURSOR_API_KEY` in the shell that runs the command |
| `no pipeline workflows found at <dir>` (exit 1) | The pack has no workflows or the folder is empty | Run `pipeline-kit update` |
| `invalid workflow <file>: <reason>` (exit 1) | A workflow file in the pack does not parse | Fix or restore the named file. `update` restores managed ones |
| `pipeline pack source is missing. Run: python3 install.py --sync-kit` | The kit checkout has no bundled pack | Reinstall the CLI. Maintainers: run the sync command in the kit checkout |
| `no .pipeline/config.json — run pipeline-kit init first` (exit 64) | A command that edits config ran in a repo without a pack | Run `pipeline-kit init` |
| `no .pipeline — run pipeline-kit init first` (exit 64 for `obs` and `security`, exit 1 for `memory`) | Same, for those commands | Run `pipeline-kit init` |

## License

| Message | Cause | Fix |
|---------|-------|-----|
| `license: install the private pipeline-kit-license package, then run: pipeline-kit license activate` (exit 73) | A paid area was used and the license engine is not installed. Paid areas are orchestrator mode, Jira intake, governance workflows, `evidence` and `assess` | Install the vendor-delivered package, then run `pipeline-kit license activate`. Kit mode and `ask` never need it. See [Licensing](/docs/reference/licensing) |
| `portal: license check failed (<reason>)` (exit 73) | `portal connect` or `portal push` needs the `portal` area | Activate a license that includes `portal` |

## Optional packages and extras

| Message | Cause | Fix |
|---------|-------|-----|
| `pipeline-kit-assess is not installed. Run: uv tool install -e ".[assess]"` (exit 1) | `scan` without the `assess` package | Run the install command from the kit checkout. A license is also needed |
| `pipeline-kit <version> does not match pipeline-kit-assess <compatible>. Run: uv tool install -e ".[assess]"` | The CLI and the assess package are different versions | Re-run that command |
| `pipeline-kit-memory is not installed. Run: pip install -e ".[memory]" or add packages/pipeline-kit-memory to PYTHONPATH` | A `memory` command without the extra | If the CLI came from `uv tool`, use `uv tool install -e ".[memory]"`. A `pip install` lands in a different environment |
| `cursor-sdk missing; install with: uv tool install -e ".[orchestrator]"` (exit 1) | `run` without the orchestrator extra | Install the extra into the same tool environment |
| `CURSOR_API_KEY is not set` (exit 1) | A live `run` without the key | Export `CURSOR_API_KEY`, or use `--runner fake` or `--dry-run` to try the flow |
| `no orchestrator run at <path>` | `resume`, `approve` or `status` with a slug that has no run | Check `--slug`, or start with `pipeline-kit run` |
| `unknown workflow: <name> (known: <list>)` | `--workflow` is not registered | Use a name from the list, or run `pipeline-kit workflows` |
| `request file not found: <path>` | The `--request-file` path is wrong | Fix the path |
| `Refusing to install Graphify without a terminal.` | `scan` needs Graphify and there is no interactive terminal (CI) | Install Graphify first: `uv tool install graphifyy && graphify install` |
| `Knowledge graph is missing.` (exit 1) | `scan` found no `graphify-out/graph.json` | Run `pipeline-kit knowledge extract` |
| `assessment.json is missing. Run pipeline-kit scan first.` | `scan --apply` before a scan | Run `pipeline-kit scan` |

## Graphify and Archify

Recovery steps are on [Graphify and Archify](/docs/troubleshooting/plugins).

| Message | Cause | Fix |
|---------|-------|-----|
| `graphify is not on PATH. Install Graphify officially, then retry.` | The CLI is not installed or not on `PATH` | `uv tool install graphifyy && graphify install` |
| `graphify extract failed (exit <n>).` | The official command failed; its output follows the message | Read the detail, then run `graphify extract . --code-only` yourself |
| `graphify extract exited 0 but graph.json is missing.` | Extract ran but wrote no graph | Run the same command and check the source tree is not empty |
| `graphify extract timed out. Run the official command locally.` | Extract ran for more than 900 seconds | Run `graphify extract . --code-only` in a terminal |
| `graphify update failed (exit <n>).` | `knowledge extract --update` failed | Run `graphify update .`. If the detail mentions shrinking, add `--force` |
| `Graphify skill not registered. Install Graphify, then retry.` (exit 1) | `plugins install graphify` found no usable CLI | Install Graphify, then re-run |
| `graphify hook: not installed. Run: graphify hook install` | The optional hook step failed | Run the printed command |
| `extract path escapes project root: <path>` | A `docs-modules.yaml` path points outside the repo | Use a path inside the project |
| `extract path is not a directory: <path>` | A module path does not exist | Fix the path in `docs-modules.yaml` |
| `gh is not on PATH. Install GitHub CLI v2.90+, then retry.` | No `gh` | Install GitHub CLI 2.90 or later |
| ``this GitHub CLI build has no `gh skill` command. Upgrade to v2.90+.`` | `gh` is too old | Upgrade `gh` |
| `node is not on PATH. Install Node.js 18+, then retry.` | No `node` | Install Node.js 18 or later |
| `Node.js <major> is too old. Archify needs Node.js 18+.` | Old Node | Upgrade Node.js |
| `gh skill install failed (exit <n>).` | The pinned install failed; its output follows | Run the pinned `gh skill install` command yourself (see the plugins page) |
| `gh skill install timed out. Run the pinned command locally.` | The install ran for more than 180 seconds | Run the pinned command in a terminal |
| `gh skill install exited 0 but the pinned Archify skill is missing.` | `gh` reported success but the skill folder is absent | Check that the `--agent` and `--scope` you used match your `--ide` and `--scope` |
| `Config is enabled; Architect will use mermaid-fallback until Archify is ready.` (exit 1) | The Archify install failed after the config flag was turned on | Not a blocker. Fix the line above it, or keep the Mermaid fallback |
| `refusing to delete <dir>: it is not a managed tt-a1i/archify skill.` | `uninstall` only deletes a skill it can verify as its own | Inspect the folder. Delete `.agents/skills/archify` by hand only if it is yours |
| `ide '<ide>' has no Archify skill mapping. Use cursor, claude-code, or github.` | An unsupported `--ide` value | Pick one of the three |
| `unknown plugin: <name>` (exit 64) | The name is not `graphify` or `archify` | Run `pipeline-kit plugins list` |

## Other commands

| Message | Cause | Fix |
|---------|-------|-----|
| `no ledger yet — run a pipeline with obs enabled` (exit 1) | `obs report` before any event was recorded | Run `obs install`, then a workflow. See [Observability](/docs/troubleshooting/observability) |
| `invalid mode: <mode>` (exit 64) | `security install --mode` is not `audit`, `warn` or `block` | Use one of the three |
| `enable test-design first (pipeline-kit features enable test-design)` | A flag that depends on the test-design flag | Run the printed command |
| `memory not linked` | A `memory` command with no link | `pipeline-kit memory link <bank-root> [project]` |
| `no index — run: pipeline-kit memory index` | `memory search` before an index exists | Run `pipeline-kit memory index` |
| `nothing to index: link a memory root or create features/` | There is nothing to index yet | Link a bank, or run a feature first |
| `portal: --key is required (create one in the portal under Projects)` (exit 64) | `portal connect` without `--key` | Create an ingest key in the portal |
| `the portal URL must start with https:// (or http:// for localhost)` | A bad `--url` | Use an `https://` URL |
| `the ingest key would travel unencrypted; use an https:// portal URL` | `http://` to a host that is not local | Use `https://` |
| `portal: could not report this change (<reason>). It will be included in the next report.` | The command worked but the report failed. The exit code does not change | Run `pipeline-kit portal status`, then `portal push` |

## IDE hook blocks

An IDE hook returns these as the reason for a denied tool call. They come from `.pipeline/hooks/`. The environment variable named in a message is a deliberate override. Set it only when the user asked for that action. See [IDE hooks](/docs/troubleshooting/hooks) and [Agent security](/docs/capabilities/agent-security).

| Message | Cause | Fix |
|---------|-------|-----|
| `Blocked write to secret/credential path: <path>` | The agent tried to write a secret-like file such as `.env` | Keep the value in your environment or secret store |
| `Blocked write into generated or VCS dir: <path>` | The target is a generated or version-control folder | Write to the source file instead |
| `Blocked write: payload looks like a hardcoded secret. Use env vars / secret stores.` | The content matched a secret pattern | Move the value out of the file |
| `<kind> may not edit product source (<path>). Write only under features/{slug}/.` | A planning specialist tried to edit product code | Let the developer step make the change |
| `Blocked undeclared dependency in <path>: <names>. Architect must declare it in features/<slug>/state/architect-agent.json context.new_dependencies ...` | A manifest gained a dependency Architect did not declare | Declare it as the message says, or drop it |
| `Blocked destructive or curl\|sh command. Autonomous agents must not wipe disks or pipe remote scripts to a shell.` | A destructive command or a piped remote script | Run it yourself if it is really needed. No override variable |
| `Blocked commit/push/publish. Set PIPELINE_ALLOW_GIT=1 only when the user asked to ship.` | A version-control write from the agent | Set `PIPELINE_ALLOW_GIT=1` for that session |
| `Blocked undeclared dependency: <names>. Architect must declare it in features/<slug>/state/architect-agent.json context.new_dependencies ...` | An install command for a package Architect did not declare | Declare it, or reuse an existing library |
| `Blocked new dependency install. Reuse existing libraries or set PIPELINE_ALLOW_DEPS=1 after a spec/security note.` | A dependency install outside a feature | Set `PIPELINE_ALLOW_DEPS=1` if approved |
| `Blocked ssh/scp/rsync to a remote host from the agent session.` | A remote shell or copy | Run it yourself. No override variable |
| `Blocked non-localhost network command (possible exfil). Use 127.0.0.1 or set PIPELINE_ALLOW_NET=1.` | A network call to a host that is not local | Use localhost, or set `PIPELINE_ALLOW_NET=1` |
| `Blocked Jira CLI/api-script mutation. Set PIPELINE_ALLOW_JIRA=1 only when the user asked to mutate Jira issues.` | A Jira write | Set `PIPELINE_ALLOW_JIRA=1` |
| `Blocked GitHub CLI/api-script mutation. Set PIPELINE_ALLOW_GITHUB=1 only when the user asked to mutate GitHub issues.` | A GitHub issue write | Set `PIPELINE_ALLOW_GITHUB=1` |
| `Blocked mutating MCP tool (<label>). Reads and search stay allowed. Set PIPELINE_ALLOW_MCP=1 only when the user asked to create/update remote data.` | The MCP tool name looks like a write | Set `PIPELINE_ALLOW_MCP=1` if the user asked for it |
| `Blocked unknown MCP tool (<label>). Treat as a write until it is classified. Set PIPELINE_ALLOW_MCP=1 if the user asked for this call.` | The tool name is not a known read | Same |
| `Blocked MCP call with no tool name. Set PIPELINE_ALLOW_MCP=1 only if you asked for a remote write.` | The hook payload had no tool name | Same |
| `Blocked read of secret file (<path>). Do not ingest credentials into the model.` | The agent tried to read a secret file | Pass the value by environment variable instead |
| `Blocked pack read (<path>); not on the active workflow allowlist.` | A pack file the active workflow does not list | The step should not need it. If the agent keeps asking, see [Slim handoffs](/docs/troubleshooting/slim-handoffs) |

`PIPELINE_HOOK_SKIP=1` makes every policy hook allow. `PIPELINE_ALLOW_ALL=1` does the same for the shell and MCP hooks and for the agent-security check. Use them for debugging only.
