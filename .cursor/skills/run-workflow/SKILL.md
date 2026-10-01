---
name: run-workflow
description: >-
  When the user wants product work (work on, fix, change, develop, or a
  tracker issue key) or a question about this repository, run the pipeline
  loader and read only the allowlist. Do not open other workflow skill files.
---

# Run workflow (harness)

| Attribute | Value |
|-----------|--------|
| Type | IDE adapter |
| Audience | Receptionist in this IDE |
| Adapt | Do not fork per product. Process lives in `.pipeline/`. |

You are the receptionist. Real workflow files live under `.pipeline/` (project, else `~/.pipeline`) so they are not auto-loaded.

## Steps

1. Detect the workflow the same way orchestration does:
   - Tracker issue key → `jira-story` / `jira-bug` / `jira-epic` after intake.
   - Product verbs (work on, fix, change, develop, implement, add, build) → `feature-development`.
   - A question about this repo (how / what / why / where / explain) → `ask`.
   - Weather, locations, Agency-desk assignments, and other unrelated asks: **do not** run the loader.
   You may Read `.pipeline/skills/orchestration/SKILL.md` **only after** the loader has listed it.
2. Choose a kebab `FEATURE_SLUG` and run (project pack first, else the user pack):

```bash
python3 .pipeline/loader/load_workflow.py --workflow {name} --step parent --slug {slug}
# if this repo has no .pipeline:
python3 ~/.pipeline/loader/load_workflow.py --workflow {name} --step parent --slug {slug}
```

3. Read **only** `allowed_reads` from the printed JSON (also at `features/{slug}/context-pack.json`). Do not Read other `.pipeline/skills/` files.
4. For `ask`: follow the ask skill and stop. No `route.md`, no Task chain.
5. For product workflows: classify and write `features/{slug}/route.md`. Spawn **one new Task** per chain step (`generalPurpose` plus `Follow .pipeline/agents/{name}.md`, or the named Cursor type if `--agent-stubs` was installed). Before each Task, run the loader again with `--step {agent}` and put `FEATURE_SLUG: {slug}` plus `CONTEXT_PACK: features/{slug}/context-pack.json` in the prompt.

Chains and skips: `.pipeline/config.json` (project, else `~/.pipeline/config.json`). Pack file lists: `{pack}/workflows/{name}.json`.
