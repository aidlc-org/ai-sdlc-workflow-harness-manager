---
title: Orchestrator mode first run
description: Install the orchestrator extra, init a project on the Python engine, dry-run a workflow, then inspect status.
---

**Goal:** Run the same first-party workflow names through the **Python engine** instead of the markdown pack loader.

**Components used:** [Two kits](/docs/capabilities/modes), [Workflows](/docs/capabilities/workflows), [CLI — orchestrator](/docs/reference/cli#orchestrator-mode).

:::warning Pick one kit per project
Do not layer orchestrator init on top of a kit-mode pack unless you intend to replace how work runs. Kit mode never loads `pipeline_extensions/`; orchestrator never runs the markdown loader chain.
:::

## Prerequisites

- Python **3.11+**
- Kit checkout or install that can take `.[orchestrator]`
- Optional: `CURSOR_API_KEY` for live Cursor SDK runs (fake runner needs none)

## Steps

### 1. Install the orchestrator extra

```bash
cd /path/to/pipeline-kit-checkout
uv tool install -e ".[orchestrator]"
pipeline-kit --help
```

### 2. Init the app in orchestrator mode

```bash
cd /path/to/your-app
pipeline-kit init --mode orchestrator --ide cursor
pipeline-kit doctor --ide cursor
pipeline-kit workflows
```

**Verify:** slim `.pipeline/` (config, docs, hooks, wiki) — **no** `agents/`, `skills/`, `loader/`, or `workflows/`. `install.json` shows `"mode": "orchestrator"`. First-party names still list from `workflows`.

### 3. Dry-run without the SDK

```bash
pipeline-kit run --slug label-tweak --workflow feature-development --runner fake \
  --request "Add a small label change on the homepage"
pipeline-kit status --slug label-tweak
```

**Verify:** state under `features/label-tweak/`. Fake runner does not call Cursor.

### 4. Live run (optional)

```bash
# export CURSOR_API_KEY=...
pipeline-kit run --slug checkout-redesign --workflow feature-development \
  --request "redesign checkout so guests can pay without an account"
```

Chat text in the IDE is **not** inherited. Pass `--request` or `--request-file`.

HITL: `pipeline-kit approve` / `resume` when gates require it — see [Planning gates](/docs/capabilities/planning-gates).

### 5. Add an associate graph (optional)

```bash
pipeline-kit workflows --scaffold my-review
# or copy examples from the kit clone:
# extensions/orchestrator/pipeline_extensions/
```

Do not reuse first-party workflow names. Details: [Extensions](/docs/capabilities/extensions), [Add a workflow cookbook](/docs/cookbooks/add-workflow).

## Done when

- [ ] `init --mode orchestrator` + `doctor` succeed  
- [ ] `run --runner fake` writes feature state  
- [ ] You know how live runs get `--request` and gates  

## Next

- [First feature](/docs/cookbooks/first-feature) (kit mode counterpart)
- [Enterprise governance](/docs/cookbooks/enterprise-governance) if license feature `orchestrator` applies
- [Modes deep dive](/docs/capabilities/modes)
