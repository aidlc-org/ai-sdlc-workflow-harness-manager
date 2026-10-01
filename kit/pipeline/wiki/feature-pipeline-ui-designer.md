# Feature pipeline — UI designer

| Attribute | Value |
|-----------|--------|
| Type | Wiki |
| Audience | Parent or specialist when INDEX triggers match |
| Adapt | Add a new page after retro. Do not store secrets or customer identifiers. |

- **Layer:** pipeline
- **Load when:** ui-designer-agent, ui-design.md, skip_ui_designer, RUN_UI_DESIGNER, CONSULT_UI, CONSULT_REQUESTED, features/{slug}/ui/, next_agent

## Symptom

Architect invents screens, Developer invents layout, or PM skips UX questions
on a naive “build this app” ask. UI designer is skipped on a new portal, or
every platform skill is loaded for an API-only job.

## Root cause

Feature-class text work now has an optional **UI designer** step after PM and
**before** `@signoff:requirements`. Parent applies `ui-designer-policy.md`.
Agents recommend the next legal step via `context.next_agent`; they never
spawn peers. Architect/BA may insert one consult.

## Do not

- Spawn UI designer on micro, minor, or jira-bug
- Auto-continue after PM SUCCESS without applying ui-designer-policy
- Sign off requirements without presenting mockups when UI ran
- Load every platform skill; U1 selects the pack
- Copy `features/{slug}/ui/` into the product tree
- Honor an illegal `next_agent` (developer, skip sign-off)
- Consult-loop past `gates.consult_cap` without `CONSULT_UI: true`

## Convention

1. PM asks surface/screen/theme/a11y questions (clarify-first UI rows) and writes `prd.md`.
2. Parent sets `skip_ui_designer` from policy + `RUN_UI_DESIGNER` + PM `next_agent`.
3. UI designer classifies surfaces, loads matching skills, writes `ui-design.md` + HTML mockups + state.
4. Parent `@signoff:requirements` presents PRD **and** UI artifacts together.
5. `recommend_after_signoff: architect-agent` is an extra architect-policy trigger.
6. Architect/BA read UI outputs. `CONSULT_REQUESTED` → one-shot UI designer → resume.

## Files

`.pipeline/agents/ui-designer-agent.md`, `.pipeline/skills/ui-design/SKILL.md`, `.pipeline/skills/feature-development/assets/ui-designer-policy.md`, `next-agent-policy.md`, `ui-design-template.md`

## Verify

User-facing feature-class runs have `HANDOFF-ui.md` or `skip_ui_designer: true`.
API-only jobs skip mockups. `ui/manifest.json` lists only skills U1 selected.
