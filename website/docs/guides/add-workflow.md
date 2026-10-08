---
title: Add a workflow
description: Skill, workflow JSON, config chain, optional agent brief, receptionist row, loader smoke test.
---

:::tip Prefer the cookbook
Step-by-step tutorial with done-when checks: [Add a custom workflow](/docs/cookbooks/add-workflow).
:::

A new customer process should be a **workflow**, not a fork of the kit. There are two contracts — pick the mode the project was initialized with.

## Kit mode (default)

1. Write `.pipeline/skills/{name}/SKILL.md` (plus `assets/` templates if needed).
2. Write `.pipeline/workflows/{name}.json` with `context.parent.files` and `context.steps.{agent}.files` (relative paths from the project root, `.pipeline/…` prefix).
3. Add `workflows.{name}` in `.pipeline/config.json` (`source`, `chain` or `classes`, `skips`). An empty `chain` means parent-only (see `ask`).
4. Optional: add `.pipeline/agents/{role}.md` and list it on that step’s allowlist.
5. If the receptionist should auto-pick it, add one row to `.pipeline/skills/orchestration/SKILL.md` (O1 / O3).
6. Activate and check the printed list:

```bash
python3 .pipeline/loader/load_workflow.py --workflow {name} --step parent --slug try-{name}
```

Confirm `allowed_reads` is the smallest set that step needs.

Follow [DOCUMENT-STANDARD](/docs/reference/document-standard) so the new markdown stays portable.

Kit-repo copy of this contract: `extensions/kit/`.

## Orchestrator mode

`--mode orchestrator` does not use the markdown loader. Add a Python graph:

```bash
pipeline-kit workflows --scaffold my-review
```

That writes `pipeline_extensions/my_review.py` and a brief. Copy-ready examples (security review, CI audit, dependency audit, accessibility review) live in the kit clone at `extensions/orchestrator/`.

```bash
cp -R extensions/orchestrator/pipeline_extensions /path/to/your-app/
```

Do not reuse a first-party name. Kit mode never loads `pipeline_extensions/`.

Full comparison: [Kit vs orchestrator](/docs/capabilities/modes), [Extensions](/docs/capabilities/extensions).
