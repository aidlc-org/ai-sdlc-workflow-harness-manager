# Feature pipeline — PM gate and multi-spec waves

| Attribute | Value |
|-----------|--------|
| Type | Wiki |
| Audience | Parent or specialist when INDEX triggers match |
| Adapt | Add a new page after retro. Do not store secrets or customer identifiers. |

- **Layer:** pipeline
- **Load when:** product-manager-agent, prd.md, nested features/{slug}/{child}/, spec-order.md, waves, one feature-level tester

## Symptom

A feature-class ask starts at BA with one flat specification.md, or testers run between child specs, or devops ships without Playwright.

## Root cause

Feature class is now a parent folder: PM (or intake) plans first, the user signs requirements, Architect may run, BA splits children, parent fans out implementation waves, one tester signs off.

## Do not

- Spawn Architect or BA before `signoff-requirements.md`
- Ask what `decisions.md` or the repo already answers
- Put sibling slugs at features/ instead of features/{feature}/{child}/
- Run tester-agent per child or between waves
- Mark tester SUCCESS as TESTS: cases-only on feature class
- Start devops without FEATURE_SIGNOFF: passed
- Start waves without `signoff-ba.md`

## Convention

1. Parent writes features/{slug}/route.md and pipeline-state.json (change_class: feature).
2. product-manager-agent analyzes as-is in the repo, writes prd.md, research.md, decisions.md, and state/product-manager-agent.json. Clarify-first questions (max 20; UI designer checklist when surfaces exist).
3. Parent applies `ui-designer-policy.md` (or `RUN_UI_DESIGNER`). When not skipped, ui-designer-agent writes `ui-design.md`, `ui/` mockups, and `HANDOFF-ui.md`.
4. Parent `@signoff:requirements` (PRD **and** UI artifacts when UI ran). Then architect-policy; large stories run architect-agent.
5. ba-agent writes each features/{slug}/{child}/specification.md, spec-order.md (**children:** line), test-plan.md, and per-child test-strategy.md.
6. After BA critic approve and `@signoff:ba`, parent runs waves: per child developer then developer-critic (telemetry only if `RUN_TELEMETRY`). Parallel children share a wave.
7. One tester-agent at the parent slug runs Playwright/api/unit from the test plan.
8. Devops only after qa-signoff.md has FEATURE_SIGNOFF: passed.

Micro/minor unchanged (flat folder, no PM, no Architect, no tester unless policy on).

## Files

.pipeline/agents/product-manager-agent.md, .pipeline/skills/product-planning/SKILL.md, .pipeline/skills/spec-generation/SKILL.md, .pipeline/skills/feature-development/SKILL.md, .pipeline/wiki/feature-pipeline-architect-and-signoff.md, .pipeline/wiki/feature-pipeline-ui-designer.md

## Verify

features/{slug}/prd.md and signoff-requirements.md exist before Architect or BA. Child specs are subfolders. HANDOFF-tester.md is after every child critic. qa-signoff.md exists before devops.
