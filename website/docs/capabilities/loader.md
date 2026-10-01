---
title: Loader and allowlists
description: The receptionist runs load_workflow.py so each specialist reads only the current step’s files.
---

The loader is how a large pack stays cheap. `run-workflow` runs:

```bash
python3 .pipeline/loader/load_workflow.py --workflow {name} --step {step} --slug {slug}
```

It writes `allowed_reads`, `seed_reads`, and `seed_bundle` (`features/{slug}/step-context.md`) under `{pack}/state/active-context.json`. The specialist **must not** open other `.pipeline/skills/` files.

## What is allowlisted

Each `.pipeline/workflows/{name}.json` lists `context.parent.files` and `context.steps.{agent}.files` — agent briefs, `SKILL.md`, config, wiki. Do **not** list skill `assets/` there.

The loader expands `allowed_reads` from those skills (the skill's `assets/` folder plus markdown links to other skill assets) so specialists may Read a template **when the skill names it**. `seed_reads` is the preload set: briefs, skills, and config. Pipeline-state and other skill assets stay on `allowed_reads` only. The loader concatenates `seed_reads` into `seed_bundle` so the specialist Reads **once**, not one tool call per file.

BA does not ingest the deploy runbook. The developer does not ingest Jira intake. Wiki pages are loaded only when INDEX triggers match — not as a folder.

## Receptionist

`AGENTS.md` is a routing table. The agent does not load the pack until `run-workflow` runs the loader. Weather, locations, and other unrelated asks skip the pipeline entirely.

## Do not edit

`.pipeline/loader/` is kit machinery. Add files by listing them on a workflow allowlist, not by teaching the parent to glob `.pipeline/`.
