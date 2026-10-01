# HANDOFF template (UI designer step)

| Attribute | Value |
|-----------|--------|
| Type | Template |
| Audience | The specialist that writes the artifact |
| Adapt | Fill placeholders only. Do not add a product, host, or customer name. |

Owned by **feature-development**. UI designer writes
`features/{slug}/HANDOFF-ui.md` and pastes this body in the final message.

```markdown
# HANDOFF — ui-designer-agent

**status:** SUCCESS | BLOCKED | ASSUMPTIONS_USED
**slug:** {slug}
**job:** full | consult
**ui_design_path:** features/{slug}/ui-design.md | none
**manifest_path:** features/{slug}/ui/manifest.json | none
**index_path:** features/{slug}/ui/index.html | none
**consult_path:** features/{slug}/ui/consult-{n}.md | none
**state_path:** features/{slug}/state/ui-designer-agent.json
**questions_path:** features/{slug}/questions.md | none
**decisions_path:** features/{slug}/decisions.md
**surfaces:** web | mobile | desktop | erp | mixed | none
**skills_loaded:** ui-design, {names} | none
**ready_for_signoff:** true | false
**recommend_after_signoff:** architect-agent | ba-agent | none

## Summary
{3–6 sentences: surfaces, IA, mockups, what was assumed}

## Screen inventory
- {S-1}: {one-line job} → `ui/{file}.html`

## Evidence used
- {path}: {fact}

## Assumptions used (if any)
- UA-1: …

## Open questions left
- none | OQ-1: …

## Failure / recovery (if not SUCCESS)
- What failed:
- What the parent should do:

## Parent next step
full: Wait for @signoff:requirements (PRD + UI). Then apply architect-policy.
consult: Re-spawn RESUME_AGENT. Pass this state JSON — not this body.
Do not start developer-agent.
```

### Status values (mandatory)

| status | When | `ready_for_signoff` | Parent |
|--------|------|---------------------|--------|
| `SUCCESS` | U5 blockers pass | `true` | `@signoff:requirements` (or resume consult) |
| `ASSUMPTIONS_USED` | User said proceed; defaults labeled | `true` | Same; later agents must stress-test Assumptions |
| `BLOCKED` | Interactive wait or incomplete | `false` | Wait for user then re-run UI designer, or stop |

Do not report `SUCCESS` when blockers fail or Must UX decisions are still open.
