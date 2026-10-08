---
title: Add a custom workflow
description: Extend the harness with a new process — kit mode skill + JSON + config, or orchestrator Python graph — without forking the kit.
---

**Goal:** Add a customer-specific procedure (for example architecture review or release checklist) as a **first-class workflow**.

**Components used:** [Workflows](/docs/capabilities/workflows), [Extensions](/docs/capabilities/extensions), [Document standard](/docs/reference/document-standard).

## Prerequisites

- A project already initialized (`pipeline-kit init`)
- Know which kit the project uses: kit mode vs orchestrator (`install.json` / how you inited)

## Kit mode

### Steps

1. Write `.pipeline/skills/{name}/SKILL.md` (and `assets/` templates if needed).
2. Write `.pipeline/workflows/{name}.json` with `context.parent.files` and `context.steps.{agent}.files` (paths relative to project root, `.pipeline/…` prefix).
3. Add `workflows.{name}` in `.pipeline/config.json` (`source`, `chain` or `classes`, `skips`). Empty `chain` = parent-only (see `ask`).
4. Optional: `.pipeline/agents/{role}.md` on that step’s allowlist.
5. Optional: one receptionist row in `.pipeline/skills/orchestration/SKILL.md` (O1 / O3).
6. Smoke-test the loader:

```bash
python3 .pipeline/loader/load_workflow.py --workflow {name} --step parent --slug try-{name}
```

**Verify:** `allowed_reads` is the smallest set that step needs.

Kit-repo contract copy: `extensions/kit/`.

Portable markdown: [DOCUMENT-STANDARD](/docs/reference/document-standard).

## Orchestrator mode

```bash
pipeline-kit workflows --scaffold my-review
```

That writes `pipeline_extensions/my_review.py` and a brief. Copy-ready associates (security review, CI audit, dependency audit, accessibility review):

```bash
cp -R /path/to/kit/extensions/orchestrator/pipeline_extensions /path/to/your-app/
```

**Rules:** do not reuse a first-party name; kit mode never loads `pipeline_extensions/`.

## Done when

- [ ] Workflow name appears in `pipeline-kit workflows` (or loader smoke passes in kit mode)  
- [ ] Chain / graph matches the customer process  
- [ ] Skills stay free of customer-specific ports and folder leaks ([config overlay](/docs/guides/config))  

## Reference

- Short form of this page: [Guides — Add a workflow](/docs/guides/add-workflow)
- [Two kits](/docs/capabilities/modes)
- [Extensions](/docs/capabilities/extensions)

## Next

- [First feature](/docs/cookbooks/first-feature)
- [What you should not edit](/docs/guides/what-not-to-edit)
