---
name: test-design
description: >-
  When test_design.enabled, turn reviewed overlay catalogs plus the Graphify
  graph into inventory.json and cases.json. Design only. No Playwright.
---

# Test design (structured cases)

| Attribute | Value |
|-----------|--------|
| Type | Skill |
| Audience | The named agent, or the parent when this file is on the allowlist |
| Adapt | Change catalog paths only if this project relocated `test-knowledge/`. Do not add a product name. |

**Phase 1 is design-only.** Do not create or edit product test trees, runners, or CI. Do not `import graphify`. Read `graphify-out/graph.json` and `test-knowledge/` only.

## When this skill runs

Parent checked [test-design-policy.md](../feature-development/assets/test-design-policy.md). You run only when `TEST_DESIGN_ENABLED: true`.

## Inputs

- Signed specs, `test-plan.md`, Architect `model-delta.json` (or `no_test_model_change`)
- `test-knowledge/` catalogs (promoted, reviewed)
- `graphify-out/graph.json` as structural substrate — never as a certified model

## Work

1. Read the overlay manifest. If `graphify-out/graph.json` is missing, `BLOCKED` and tell the parent to run `pipeline-kit knowledge extract`.
2. Write `features/{slug}/test-design/inventory.json` from [assets/inventory-template.json](assets/inventory-template.json): what, why, lowest effective level, technique. E2E needs a written reason.
3. Write `features/{slug}/test-design/cases.json` from [assets/cases-template.json](assets/cases-template.json).
   Overlay IDs (`actions` / `fixtures` / `oracles`) are traceability only.
   **`steps[].do` and `expected[].see` are the deliverable** — a numbered
   click-path a human (and later Playwright) can follow:
   open URL → sign in (env names, never secret values) → land on page →
   click the named nav/button → see the named heading or form.
   Vague slogans or ID-only steps (`ACT-submit` with no `do`) are not SUCCESS
   for `ui` / browser `e2e`. Every `ui` / browser `e2e` step must also set
   `verb` (allowlist: `goto`, `fill`, `click`, `expect_visible`, `expect_text`,
   `expect_disabled`, `expect_count`) and `control: { role, name }` except
   `goto`. `fill` uses `value_from_env` (env name only). Prefer
   `FIX-*-SIGNED-IN*` / `kind: auth` instead of repeating login. Name the
   control and the page. Never write a real password.
4. Write `traceability.json` (FR → AC → level → inventory → case →
   action/fixture/oracle → graph/source node). No executable test link.
5. Record new overlay nodes in `new-actions.json` as `planned` — do not promote them yourself.
6. Run `pipeline-kit knowledge render --slug {slug}` so `qa-test-cases.md` and `test-design/test-plan-view.md` match `cases.json`.
7. Do not invent a file/symbol graph if Graphify output is thin. Mark gaps `inferred` or `BLOCKED`.

## Techniques (use the lowest that can fail the AC)

boundary · partition · decision table · role/flag · state transition · negative/error · path coverage

## Outputs

```text
features/{slug}/test-design/inventory.json
features/{slug}/test-design/cases.json
features/{slug}/test-design/new-actions.json
features/{slug}/test-design/traceability.json
features/{slug}/qa-test-cases.md
features/{slug}/test-design/test-plan-view.md
```

## Anti-patterns

Importing Graphify · writing `graphify-out/` · generating Playwright specs ·
promoting overlay catalogs · **ID-only steps with no click-path prose** ·
pasting real passwords · treating Graphify confidence as `verified`.
