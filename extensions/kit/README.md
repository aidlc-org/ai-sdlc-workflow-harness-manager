# Kit-mode extensions

A new customer process is a **workflow** in the portable pack — not a
fork of this repository.

## After `pipeline-kit init` (customer repo)

1. Write `.pipeline/skills/{name}/SKILL.md` (plus `assets/` if needed).
2. Write `.pipeline/workflows/{name}.json` with `context.parent.files`
   and `context.steps.{agent}.files` (briefs and `SKILL.md`, not skill assets).
3. Add `workflows.{name}` in `.pipeline/config.json`.
4. Optional: add `.pipeline/agents/{role}.md` and allowlist it.
5. If the receptionist should auto-pick it, add a row to
   `.pipeline/skills/orchestration/SKILL.md`.
6. Smoke-test:

```bash
python3 .pipeline/loader/load_workflow.py --workflow {name} --step parent --slug try-{name}
```

Details: [kit/pipeline/README.md](../../kit/pipeline/README.md)
(“How to add a workflow”) and the customer guide.

## In this repository (ship a first-party workflow)

Edit the bundle, not a live `.pipeline`:

| Add | Path |
|-----|------|
| Skill | `kit/pipeline/skills/{name}/` |
| Allowlist | `kit/pipeline/workflows/{name}.json` |
| Default chain | `kit/pipeline/config.json` |
| Brief | `kit/pipeline/agents/{role}.md` |

Then `pipeline-kit update` in customer apps. Follow
`kit/pipeline/docs/DOCUMENT-STANDARD.md`.

Orchestrator-mode extensions are a different contract:
[`../orchestrator/`](../orchestrator/).
