---
title: First feature end-to-end
description: Install the CLI, init kit mode on an app repo, smoke-test ask, then run a small feature-development change.
---

**Goal:** Put Pipeline Kit on a real application repository and complete one small product change with the default **kit mode** pack.

**Components used:** [Workflows](/docs/capabilities/workflows), [loader](/docs/capabilities/loader), IDE [adapters](/docs/getting-started/ide-adapters).

## Prerequisites

- Python **3.11+**
- An application repo you can open in Cursor, Claude Code, or GitHub (or `--ide none` for pack-only)
- [CLI installed](/docs/getting-started/install-cli)

## Steps

### 1. Install the CLI (if needed)

```bash
uv tool install git+https://github.com/aidlc-org/ai-sdlc-workflow-harness-manager
# or from a local checkout: ./install.sh / uv tool install -e .
pipeline-kit --help
```

### 2. Initialize kit mode on the app

```bash
cd /path/to/your-app
pipeline-kit init --ide cursor
pipeline-kit doctor --ide cursor
pipeline-kit workflows
```

Use `--ide claude-code`, `--ide github`, or `--ide none` when that matches your setup.

**Verify:** `.pipeline/` exists with `config.json`, skills, workflows, loader; IDE folder has only `run-workflow` (for IDE adapters).

Details: [First project](/docs/getting-started/first-project).

### 3. Smoke-test `ask`

In the IDE, with the app root open:

> How does local deploy work in this repository?

**Expect:** workflow **`ask`**. No PM → BA → developer ladder.

Details: [Your first workflow](/docs/getting-started/first-workflow), [Ask](/docs/workflows/ask).

### 4. Run a small feature change

> Add a small label change on the homepage.

**Expect:** **`feature-development`**, usually classified **micro** (short chain: developer → tester if policy → devops → retro).

If the parent opens a full PRD for a label tweak, stop and read [change classes](/docs/capabilities/workflows).

Artifacts land under `features/{slug}/` in **this** app repo.

### 5. Engagement checklist (before real work)

- Adapt [AGENTS.md](/docs/guides/agents-md) and [config.json](/docs/guides/config)
- Point [tests](/docs/guides/tests) and [local deploy](/docs/guides/local-deploy) at your commands
- Confirm [gitignore](/docs/guides/gitignore) for `features/` / state if needed

Full list: [New-project checklist](/docs/getting-started/checklist).

## Done when

- [ ] `doctor` is clean for your IDE  
- [ ] `ask` answered from the repo without a Task chain  
- [ ] One micro `feature-development` run produced files under `features/`  

## Next

- [Add a custom workflow](/docs/cookbooks/add-workflow)
- [Orchestrator mode first run](/docs/cookbooks/orchestrator-first-run) if you prefer the Python engine
- [Components overview](/docs/components/overview)
