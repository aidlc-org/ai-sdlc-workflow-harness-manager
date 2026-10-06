---
title: New-project checklist
description: The full customer surface after clone — AGENTS.md, config, deploy, tests, gitignore, smoke test.
---

Use this on every new engagement. The full customer surface is **AGENTS.md + config.json**, then deploy and test files if your runners are not the defaults.

1. Pick a kit, then install: `pipeline-kit init --ide cursor` (kit mode) or `pipeline-kit init --mode orchestrator --ide cursor`. See [Two kits](/docs/capabilities/modes).
2. Paste the `AGENTS.md` routing table and a short product blurb. See [Adapt AGENTS.md](/docs/guides/agents-md).
3. Edit `.pipeline/config.json`:
   - `verify.rules` for your folders (or leave `[]`)
   - `deploy.targets` for your apps
   - `intake.jira.enabled` (`false` unless you use Jira)
4. Rewrite the local-deploy runbook and `deploy-local.sh` for your stack. See [Adapt local deploy](/docs/guides/local-deploy).
5. Skim `.pipeline/docs/DOCUMENT-STANDARD.md` before editing any other pack markdown.
6. Add `features/` and `.pipeline/state/` to `.gitignore`.
7. Open the repo root in the IDE. Kit mode: confirm the `run-workflow` skill is visible. Orchestrator mode: confirm `CURSOR_API_KEY` and try `pipeline-kit run --dry-run`.
8. Smoke test. Kit mode: ask “How does X work?” (expect `ask`) and “Add a small label change” (expect `feature-development`). Orchestrator mode: `pipeline-kit run --slug try --workflow ask --request "How does X work?" --runner fake`.

Optional later: tracker MCP, wiki pages after retro, [knowledge](/docs/capabilities/knowledge), [memory bank](/docs/capabilities/memory) (`uv tool install -e ".[memory]"` then `memory link`), [plugins and observability](/docs/capabilities/plugins).
