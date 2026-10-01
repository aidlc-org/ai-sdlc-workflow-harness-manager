---
name: ui-design
description: >-
  Invoke when ui-designer-agent must turn a PRD into ui-design.md and static
  HTML mockups before requirements sign-off, or answer a CONSULT_REQUESTED
  insert. Classify surfaces first and load only matching platform skills.
  Do not use for micro/minor, coding, or a redesign of an existing screen
  (use ui-enhancement).
---

# UI design (autonomous designer loop)

| Attribute | Value |
|-----------|--------|
| Type | Skill |
| Audience | The named agent, or the parent when this file is on the allowlist |
| Adapt | Change commands or paths only in deploy and testing skills. Planning skills stay product-neutral. |

Turn a feature-class PRD into an on-disk **design contract** Architect, BA,
and Developer can use without inventing screens. A chat-only mood board is
a failed step.

**Parent:** spawn UI designer as a separate `Task` after PM when
`skip_ui_designer` is false. **Designer:** write ui-design + mockups + state
+ HANDOFF, then return. **Do not** write `specification.md`, implement
product code, or spawn Architect or BA.

**Success:** `ui-design.md` is complete (or `surfaces: none`), mockups match
the inventory when surfaces exist, leftover Unknowns are cosmetic or
user-approved.  
**Failure:** chat-only design, loading every platform skill, open Must UX
questions, or inventing a brand that contradicts the repo theme.

**Progressive loading:** follow U1–U6 first. After U1, Read **only** the
platform skills that table names. Templates are owned by
**feature-development** — read them only at the step that names them.

| When | Read |
|------|------|
| Every step (state) | [../feature-development/assets/pipeline-state.md](../feature-development/assets/pipeline-state.md) |
| U1 / U3 (clarify-first) | [../feature-development/assets/clarify-first.md](../feature-development/assets/clarify-first.md), [../feature-development/assets/decisions-template.md](../feature-development/assets/decisions-template.md) |
| U3 (questions) | [../feature-development/assets/questions-format.md](../feature-development/assets/questions-format.md) |
| U4 (spec) | [../feature-development/assets/ui-design-template.md](../feature-development/assets/ui-design-template.md) |
| U4 (mockups) | [../ui-html-mockups/SKILL.md](../ui-html-mockups/SKILL.md), [../feature-development/assets/ui-manifest-template.json](../feature-development/assets/ui-manifest-template.json) |
| U4 (a11y) | [../ui-accessibility/SKILL.md](../ui-accessibility/SKILL.md) when any visual surface |
| U6 (handoff) | [../feature-development/assets/handoff-ui-template.md](../feature-development/assets/handoff-ui-template.md), [../feature-development/assets/agent-state-template.json](../feature-development/assets/agent-state-template.json) |

---

## U1 surface map (load only these)

Read the PRD (and `decisions.md`). Pick **one or more** rows. Then Read that
skill. Do **not** Read the others.

| Surfaces in PRD | Read |
|-----------------|------|
| web, browser, SaaS, marketing, admin portal | [../ui-web-responsive/SKILL.md](../ui-web-responsive/SKILL.md) |
| mobile, phone, tablet, touch-first | [../ui-mobile/SKILL.md](../ui-mobile/SKILL.md) |
| desktop, workstation, IDE-like, multi-pane | [../ui-desktop/SKILL.md](../ui-desktop/SKILL.md) |
| ERP, enterprise density, master-detail, bulk tables | [../ui-erp-enterprise/SKILL.md](../ui-erp-enterprise/SKILL.md) |
| mixed | every matching row above |
| none (API, CLI, batch, job-only) | no platform skill; write `surfaces: none` and skip U4 mockups |

Always Read `ui-accessibility` and `ui-html-mockups` when any visual surface
exists. Never load `ui-enhancement` from this step.

---

## Roles and outputs

| Role | Allowed |
|------|---------|
| Parent | After PM, apply ui-designer-policy, `Task` this agent, then `@signoff:requirements` |
| UI designer (this skill) | Classify, mock, write ui-design + mockups + state + HANDOFF |
| Architect / BA / Developer | Later `Task` only |

```text
features/{slug}/
  ui-design.md
  ui/index.html
  ui/{screen}.html
  ui/manifest.json
  ui/consult-{n}.md          # consult job only
  decisions.md
  questions.md               # if U3 ran
  state/ui-designer-agent.json
  pipeline-state.json
  HANDOFF-ui.md
```

Reuse `{slug}` if the folder exists; update the design, do not fork.

---

## Jobs

| `UI_JOB` | What to do |
|----------|------------|
| `full` (default) | U1–U6 |
| `consult` | Answer `CONSULT_QUESTIONS`. Patch artifacts if needed. Write `ui/consult-{n}.md`. Set `next_agent` to `RESUME_AGENT`. Do not re-ask settled decisions. |

Consult numbering: next unused `n` under `features/{slug}/ui/consult-*.md`.

---

## Steps (full job; do not skip; no product code)

`U1 CLASSIFY → U2 SCAN → U3 CLARIFY → U4 DESIGN → U5 SELF-GATE → U6 HANDOFF`

**U1 Classify** — Restate who uses the UI and on which surfaces. Fill the
surface map. If `none`, write `ui-design.md` with `surfaces: none`, skip
mockups, continue to U5.

**U2 Scan** — Repo first: existing theme, CSS variables, layout shells,
component library, spacing scale. Cite paths in `ui-design.md` § Tokens.
Greenfield: say so. Do not invent a second design system when one exists.

**U3 Clarify** — Follow clarify-first. Run the **UI designer** coverage
checklist. One batch, **max 15**, multiple-choice with a recommended default.
Interactive + remaining Unknowns: write `questions.md`, HANDOFF `BLOCKED`,
**stop**. `ASSUMPTIONS_USED` only when the user said proceed or leftovers
are cosmetic.

**U4 Design** — Load the ui-design template and the platform skill(s) from
U1. Fill every section. Then follow `ui-html-mockups` and `ui-accessibility`.
Primary journeys get a mockup file. Empty / loading / error / denied are
sections on those files, not extra routes unless they are distinct screens.
Write `ui/manifest.json` from the template.

**U5 Self-gate** — All **blockers** below must pass. Else fix or return to U3.
Never HANDOFF `SUCCESS` on a failing design.

**U6 Handoff** — Write `state/ui-designer-agent.json` and update
`pipeline-state.json`. Load the UI handoff template. Write `HANDOFF-ui.md`.

- `context.next_agent`: `signoff-requirements` (full job) or `RESUME_AGENT` (consult)
- `context.recommend_after_signoff`: `architect-agent` if new persistence, API, authz, 2+ children, or NFRs that change structure; else `ba-agent`
- `context.next_must_read`: `prd.md`, `ui-design.md`, `ui/manifest.json`, `ui/index.html` (omit mockups when `surfaces: none`)

Stop. Parent next is sign-off, not Architect.

---

## P5-equivalent blockers (all required)

- [ ] `features/{slug}/ui-design.md` on disk
- [ ] Surface list matches the PRD (or explicit `none`)
- [ ] Only matching platform skills were used (named in `HANDOFF-ui.md`)
- [ ] `ui/manifest.json` on disk when any visual surface exists
- [ ] `ui/index.html` plus one HTML file per primary screen when surfaces exist
- [ ] Empty / loading / error / denied described per primary journey
- [ ] Tokens cite repo paths or explicit greenfield
- [ ] `features/{slug}/state/ui-designer-agent.json` on disk
- [ ] `pipeline-state.json` updated for this step
- [ ] Assumptions labeled; no silent brand or density invention
- [ ] No product file edits outside `features/{slug}/`

---

## Handoff statuses (mandatory)

| status | Meaning |
|--------|---------|
| `SUCCESS` | Blockers pass; parent may request requirements sign-off |
| `ASSUMPTIONS_USED` | Defaults used; Architect, BA, and Developer must test them |
| `BLOCKED` | Wait, unsafe, or incomplete; include recovery for parent |

---

## Anti-patterns

Chat-only mockups · loading every platform skill · Figma or binary assets ·
production React/Vue in `features/{slug}/ui/` · contradicting the PRD actors ·
spawning Architect from this agent · Ready with blocking UX Unknowns ·
copying mockup files into the product tree.
