---
title: What you should not edit
description: Loader, workflow JSON, planning skills, and secrets stay out of the engagement overlay.
---

After install, the contract is `.pipeline/docs/DOCUMENT-STANDARD.md`.

**Do not edit**

- `.pipeline/loader/` — allowlist CLI
- `.pipeline/workflows/*.json` — unless you [add a workflow](/docs/guides/add-workflow)
- `.pipeline/agents/*.md` and planning skills — process, not your stack
- Secrets, tokens, tracker site URLs — environment or IDE MCP settings only

**You should edit**

- Local-deploy runbook and `deploy-local.sh`
- `config.json` (`verify`, `deploy`, `intake.jira`, `intake.github`)
- Testing skills if the default runners are wrong
- Root `AGENTS.md` (installer does not write it)

Product source is in-bounds only when the user’s ask is about it.
