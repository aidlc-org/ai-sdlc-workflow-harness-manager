---
title: Troubleshooting FAQ
description: Short answers to the questions asked most often, each with a link to the detail.
---

Not here? Try the [flowchart](/docs/troubleshooting/flowchart) or search the [error messages](/docs/troubleshooting/errors).

## Install and setup

**1. `pipeline-kit` is not found after I installed it.**
The tool bin directory is not on `PATH`. Open a new terminal. `uv tool update-shell` adds the directory for uv. See [Platforms](/docs/troubleshooting/platforms#installing-the-cli).

**2. Which Python does it need?**
Python 3.11 or later. `pipeline-kit doctor` prints the version it sees. See [Prerequisites](/docs/getting-started/prerequisites).

**3. `doctor` ends with "pipeline-kit setup is incomplete".**
Each `missing` line names one thing. If the whole pack is missing, you are in a repo that has no `.pipeline`. Run `pipeline-kit init --ide <ide>` there. See [Error messages](/docs/troubleshooting/errors#install-and-project-setup).

**4. What is the difference between `init`, `update` and `uninstall`?**
`init` installs or refreshes the pack and the IDE adapter. `update` refreshes managed files and keeps your `config.json` values. `uninstall` removes managed files and leaves `features/` and your config edits. See the [CLI reference](/docs/reference/cli#pack).

**5. I installed an extra with `pip` and the CLI cannot see it.**
`pip` and `uv tool` use different environments. Install the extra the same way you installed the CLI, for example `uv tool install -e ".[memory]"`. See [Platforms](/docs/troubleshooting/platforms#uv-tool-and-pip-are-separate-environments).

**6. Can I use kit mode and orchestrator mode in one project?**
No. The project is one kit or the other. Read [Two kits](/docs/capabilities/modes) before you init.

## License

**7. A command exits 73 with "license: install the private pipeline-kit-license package".**
You used a paid area and the license engine is not installed. Install the vendor package, then run `pipeline-kit license activate`. See [Licensing](/docs/reference/licensing).

**8. Do I need a license for kit mode?**
No. Kit mode, `ask` and `feature-development` do not read the license. See the [CLI reference](/docs/reference/cli#license).

**9. `run` says "CURSOR_API_KEY is not set".**
Orchestrator mode needs the key for live runs. Export it, or use `--runner fake` or `--dry-run` to try the flow. See [Error messages](/docs/troubleshooting/errors#optional-packages-and-extras).

## Hooks and the IDE

**10. The hooks never fire in Cursor.**
Open the folder that contains `.cursor/hooks.json` as the only workspace root. See [IDE hooks](/docs/troubleshooting/hooks) and [Cursor](/docs/adapters/cursor).

**11. Hooks worked on my machine and fail on a teammate's.**
The committed IDE config holds the interpreter found on the machine that ran `init`. Re-run `pipeline-kit init --ide <ide>` on the other machine. See [Platforms](/docs/troubleshooting/platforms#hook-commands-and-the-interpreter).

**12. The agent says "Blocked commit/push/publish" (or a similar "Blocked" message).**
A policy hook denied the action. The message names the variable that allows it, such as `PIPELINE_ALLOW_GIT=1`. Set it only when you asked for that action. See [IDE hook blocks](/docs/troubleshooting/errors#ide-hook-blocks).

## Plugins

**13. Graphify is "missing" or extract fails.**
Run `uv tool install graphifyy && graphify install`, then `graphify extract . --code-only` yourself and read the output. See [Graphify and Archify](/docs/troubleshooting/plugins#graphify).

**14. Archify did not produce HTML diagrams.**
It needs GitHub CLI 2.90 or later and Node.js 18 or later. Without them Architect keeps the Mermaid diagram and records `mermaid-fallback`. That is expected. See [Archify](/docs/troubleshooting/plugins#archify).

## Runs

**15. The parent says a specialist "is not running" but I interrupted it.**
A missing HANDOFF does not prove the Task stopped. Confirm in the UI before you start another. See [Interrupted Task](/docs/troubleshooting/interrupted-task).

**16. I pasted a tracker key and the agent ran the plain-text ladder.**
The tracker key changes the input contract. Intake runs once and a bug skips PM and BA. See [Tracker intake](/docs/troubleshooting/jira-intake).

**17. The next Task prompt is huge.**
The previous HANDOFF was pasted in full. Handoffs should be slim. See [Slim handoffs](/docs/troubleshooting/slim-handoffs).

**18. Local deploy fails because the port is in use.**
Do not start a second copy. Health-check the process that already answers. See [Deploy listeners](/docs/troubleshooting/deploy-listeners).

**19. The ledger is empty or Langfuse shows no trace.**
Usual causes are the wrong workspace root, `obs` not enabled, hooks not merged, or missing keys. Run `pipeline-kit obs status`. See [Observability](/docs/troubleshooting/observability).

**20. The tester wrote only markdown, or devops ran before end-to-end.**
See [Test layers](/docs/troubleshooting/test-layers).
