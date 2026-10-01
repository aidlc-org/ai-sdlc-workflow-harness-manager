# HANDOFF template (Architect step)

| Attribute | Value |
|-----------|--------|
| Type | Template |
| Audience | The specialist that writes the artifact |
| Adapt | Fill placeholders only. Do not add a product, host, or customer name. |

Owned by **feature-development**. Architect writes
`features/{slug}/HANDOFF-architect.md` and pastes this body in the final message.

```markdown
# HANDOFF — architect-agent

**status:** SUCCESS | BLOCKED | BLOCKED_CHALLENGE_PM | ASSUMPTIONS_USED | CONSULT_REQUESTED
**slug:** {slug}
**architecture_path:** features/{slug}/architecture.md | none
**implementation_plan_path:** features/{slug}/implementation-plan.md | none
**state_path:** features/{slug}/state/architect-agent.json
**concerns_path:** features/{slug}/architect-concerns.md | none
**questions_path:** features/{slug}/questions.md | none
**decisions_path:** features/{slug}/decisions.md
**ready_for_ba:** true | false
**child_split_changed:** true | false
**has_recorded_concerns:** true | false
**archify_status:** skipped | mermaid-fallback | delivered
**diagrams_manifest_path:** features/{slug}/diagrams/manifest.json | none

## Summary
{3–6 sentences: chosen shape, ADRs, child split, what was challenged}

## Evidence used
- {path}: {fact}

## Concerns
{none | C-1 recorded/blocking: one line each}

## Challenge audience
none | user | pm

## Assumptions used (if any)
- A-1: …

## Open questions left
- none | OQ-1: …

## Failure / recovery (if not SUCCESS)
- What failed:
- What the parent should do:

## Parent next step
Wait for @signoff:architect (present recorded concerns), then spawn ba-agent.
Do not start developer-agent. Pass state/architect-agent.json to BA — not this body.
If BLOCKED_CHALLENGE_PM: void signoff-requirements.md, re-spawn PM, user re-signs, then Architect again.
If BLOCKED with user questions: wait, then re-spawn Architect.
If CONSULT_REQUESTED: spawn ui-designer-agent (UI_JOB: consult) then re-spawn Architect.
```

### Status values (mandatory)

| status | When | `ready_for_ba` | Parent |
|--------|------|----------------|--------|
| `SUCCESS` | A4 blockers pass | `true` | `@signoff:architect`, then BA |
| `ASSUMPTIONS_USED` | User said proceed; defaults labeled in ADRs | `true` | Same; BA critic stress-tests defaults |
| `BLOCKED` | User questions or incomplete design | `false` | Wait; re-spawn Architect |
| `BLOCKED_CHALLENGE_PM` | Requirements must change (feature-development only) | `false` | Void requirements sign-off; re-spawn PM |
| `CONSULT_REQUESTED` | Layout/IA gap UI must settle | `false` | One-shot UI designer, then resume Architect |
