# HANDOFF template (PM step)

| Attribute | Value |
|-----------|--------|
| Type | Template |
| Audience | The specialist that writes the artifact |
| Adapt | Fill placeholders only. Do not add a product, host, or customer name. |

Owned by **feature-development**. PM writes `features/{slug}/HANDOFF-pm.md` and pastes this body in the final message.

```markdown
# HANDOFF — product-manager-agent

**status:** SUCCESS | BLOCKED | ASSUMPTIONS_USED
**slug:** {slug}
**prd_path:** features/{slug}/prd.md
**research_path:** features/{slug}/research.md
**state_path:** features/{slug}/state/product-manager-agent.json
**questions_path:** features/{slug}/questions.md | none
**decisions_path:** features/{slug}/decisions.md
**ready_for_signoff:** true | false
**ready_for_ba:** true | false
**next_agent:** ui-designer-agent | signoff-requirements

## Summary
{3–6 sentences: direction, proposed child specs, surfaces, what was assumed}

## Proposed children
- {child-slug}: {one-line job}

## Evidence used
- {path or URL}: {fact}

## Assumptions used (if any)
- A-1: …

## Open questions left
- none | OQ-1: …

## Failure / recovery (if not SUCCESS)
- What failed:
- What the parent should do:

## Parent next step
Parent applies ui-designer-policy. Then spawn ui-designer-agent unless skip_ui_designer.
Else wait for @signoff:requirements. Then spawn architect-agent unless skip_architect.
Do not start developer-agent. Pass state/product-manager-agent.json — not this body.
```

### Status values (mandatory)

| status | When | `ready_for_ba` | Parent |
|--------|------|----------------|--------|
| `SUCCESS` | P5 blockers pass | `true` | UI designer or `@signoff:requirements`, then Architect or BA |
| `ASSUMPTIONS_USED` | User said proceed; defaults labeled | `true` | Same; later agents must stress-test Assumptions |
| `BLOCKED` | Interactive wait, unsafe ask, or missing scope | `false` | Wait for user then re-run PM, or stop |

Do not report `SUCCESS` when blockers fail or Must decisions are still open.
