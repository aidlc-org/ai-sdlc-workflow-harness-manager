# workflows

One example prompt and the expected artifacts for each workflow the kit ships. Run `pipeline-kit workflows` in an initialised project to see the same list. Run folders land under `features/{slug}/`; docs workflows write under `wiki/codebase/`.

You do not pick a workflow by name. The parent agent routes your ask. Longer explanations: the workflow tour in the website docs.

| Workflow | Example prompt | Expected artifacts |
|----------|----------------|--------------------|
| `ask` | `How does the order checkout flow reach the payment service?` | None. Read-only answer in chat. |
| `feature-development` | `Add a CSV export button to the invoices list. Keep the existing filters.` | `features/{slug}/route.md`, then for feature class `prd.md`, `architecture.md`, `{child}/specification.md`, `qa-test-cases.md`, `RETRO.md` |
| `jira-story` | `Work on PAY-1234` (story) | `features/{slug}/intake.md`, then the feature artifacts. Needs the `jira` license area. |
| `jira-epic` | `Work on PAY-100` (epic) | `intake.md`, `epic-plan.md`, one child spec per story. Needs the `jira` area. |
| `jira-bug` | `Work on PAY-1250` (bug) | `intake.md`, `rca.md`, `HANDOFF-bug-analyst.md`. Needs the `jira` area. |
| `github-story` | `Work on aidlc-org/shop#80` (story) | `intake.md`, then the feature artifacts |
| `github-epic` | `Work on aidlc-org/shop#81` (epic) | `intake.md`, `epic-plan.md`, one child spec per story |
| `github-bug` | `Fix aidlc-org/shop#87` | `intake.md`, `rca.md`, `HANDOFF-bug-analyst.md` |
| `test-knowledge-bootstrap` | `Bootstrap QA knowledge for this repo` | `test-knowledge/_candidates/{run}/` and `REVIEW.md` |
| `large-codebase-docs` | `Document the large codebase` | `wiki/codebase/modules/{id}/README.md`, `wiki/codebase/INDEX.md` |
| `system-architecture` | `System architecture for the monorepo` | `wiki/codebase/system/README.md` |
| `module-security-review` | `Module security review` | `wiki/codebase/modules/{id}/security.md` |
| `repo-assessment` | `Assess this repo` | `features/assessment/` (report, plan, answers, `prompt.md`), written by `pipeline-kit scan` |

GitHub intake is off by default: `pipeline-kit features enable github-intake`, then set `intake.github.repo`.

## Smoke test

```bash
python examples/workflows/smoke.py
```

Initialises a temp project, runs `workflows`, and checks that the workflows in the table above and the ones the command lists are the same set. Automated, offline. It does not run an agent.
