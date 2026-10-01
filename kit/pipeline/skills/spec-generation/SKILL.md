---
name: spec-generation
description: >-
  Invoke this skill when the user (or parent workflow) needs a detailed
  product/feature specification markdown document produced autonomously: vague
  feature requests, “write a spec”, “BA spec”, “requirements doc”,
  “specification.md”, or when the ba-agent must turn a plan source — a PRD,
  a tracker story, or an epic plan — into child specifications before critic
  review or implementation. Do not use for coding, test authoring, bug fixes
  (use bug-fix), or UI-only redesign (use ui-enhancement).
---

# Spec generation (autonomous BA loop)

| Attribute | Value |
|-----------|--------|
| Type | Skill |
| Audience | The named agent, or the parent when this file is on the allowlist |
| Adapt | Change commands or paths only in deploy and testing skills. Planning skills stay product-neutral. |

Turn a **plan source** into on-disk child specifications, a wave order, and a categorized test plan a critic can fail and developers can implement without inventing product decisions.

| `PLAN_SOURCE_KIND` | `PLAN_SOURCE_PATH` | Produced by |
|--------------------|--------------------|-------------|
| `pm-plan` | `features/{slug}/prd.md` | product-manager-agent |
| `jira-story` | `features/{slug}/intake.md` | intake-agent |
| `jira-epic` | `features/{slug}/epic-plan.md` + `features/{slug}/stories/{child}.md` | intake-agent via epic-breakdown |

Everything after S1 is identical across the three. A defect never reaches this skill — it is specified by `rca.md` in [bug-fix](../bug-fix/SKILL.md).

**Parent:** spawn BA as a separate `Task` after `@signoff:requirements` and, when Architect ran, after `@signoff:architect`. **BA:** write child specs + order + test plan + HANDOFF, then return. **Do not** implement code, spawn critic, spawn developer, or spawn UI designer.

**Success:** every child `specification.md` is complete, `spec-order.md` and `test-plan.md` exist, assumptions labeled, ACs testable.  
**Failure:** chat-only spec, silent invention, open Must questions, or no as-is evidence from the repo.

**Progressive loading:** follow S1–S6 in this file first. Templates are owned by **feature-development** — read them only at the step that names them.

| When | Read (feature-development) |
|------|------|
| S1 / S3 (clarify-first) | [../feature-development/assets/clarify-first.md](../feature-development/assets/clarify-first.md), [../feature-development/assets/decisions-template.md](../feature-development/assets/decisions-template.md) |
| S3 (interactive questions) | [../feature-development/assets/questions-format.md](../feature-development/assets/questions-format.md) |
| S4 (draft) | [../feature-development/assets/specification-template.md](../feature-development/assets/specification-template.md) |
| S4 (density check) | [../feature-development/assets/example-specification.md](../feature-development/assets/example-specification.md) |
| S4b (order) | [../feature-development/assets/spec-order-template.md](../feature-development/assets/spec-order-template.md) |
| S4c (tests) | [../feature-development/assets/test-plan-template.md](../feature-development/assets/test-plan-template.md), [../feature-development/assets/test-strategy-template.md](../feature-development/assets/test-strategy-template.md) |
| Every step (state) | [../feature-development/assets/pipeline-state.md](../feature-development/assets/pipeline-state.md) |
| S6 (handoff) | [../feature-development/assets/handoff-template.md](../feature-development/assets/handoff-template.md), [../feature-development/assets/agent-state-template.json](../feature-development/assets/agent-state-template.json) |
| Parent spawn | [../feature-development/assets/parent-task-prompt.md](../feature-development/assets/parent-task-prompt.md) |

---

## Roles and outputs

| Role | Allowed |
|------|---------|
| Parent | Create `features/{slug}/`, `Task` the plan-source step, Architect if required, then BA, then BA critic, then `@signoff:ba` |
| BA (this skill) | Read the plan source + architecture + decisions, explore repo, clarify-first questions, write child specs + order + test plan + HANDOFF |
| BA critic | Later `Task` only |

```text
features/{slug}/
  prd.md               # plan source (pm-plan)
  state/ba-agent.json
  pipeline-state.json
  intake.md            # plan source (jira-story)
  epic-plan.md         # plan source (jira-epic)
  stories/{child}.md   # jira-epic detail per story
  spec-order.md        # required
  test-plan.md         # required
  architecture.md      # when Architect ran
  implementation-plan.md
  ui-design.md         # when UI designer ran
  ui/manifest.json
  decisions.md
  questions.md         # if S3 ran
  HANDOFF.md           # required
  {child-slug}/
    specification.md   # required
    test-strategy.md   # required
```

Reuse `{slug}` if the folder exists. One child is valid. Disk is source of truth. Do not re-ask questions already answered in `decisions.md`, `questions.md`, the plan source, or signed-off architecture. Tracker-sourced runs must **not** call tracker MCP — intake already fetched everything. If Architect ran, do not contradict signed-off ADRs. If Architect revised the child split, that split **wins**.

---

## Steps (do not skip; no product code)

`S1 DISCOVER → S2 GAP → S3 CLARIFY? → S4 DRAFT → S4b ORDER → S4c TEST PLAN → S5 SELF-GATE → S6 HANDOFF`

**S1 Discover** — Read prior state JSON first, then only listed files: the plan source (`prd.md` / `intake.md` / `epic-plan.md`), `decisions.md`, signed-off `architecture.md` / `implementation-plan.md` / `architect-concerns.md` when present, then explore. Restate intent. Scan screens/routes/APIs/models. Record path + fact. Greenfield: say so. Load [clarify-first.md](../feature-development/assets/clarify-first.md). Append extracted facts to `decisions.md`.

| Kind | Read | Child-spec split |
|------|------|------------------|
| `pm-plan` | `prd.md`, `research.md`, architecture if present | Confirm or refine the Architect split when it exists; otherwise the PM split |
| `jira-story` | `intake.md` — description and ACs are **verbatim requirements**, section 7 lists the gaps | Split only if the story genuinely holds several independent jobs; one child is the normal answer |
| `jira-epic` | `epic-plan.md` child table, then each `stories/{child}.md` | **One child spec per story**, slugs taken from the plan's child table — do not merge or re-split without saying why in the HANDOFF |

Tracker-sourced: treat the issue text as the requirement, not as a suggestion. A gap in the issue is a gap (S2), never something you quietly fill. Each child spec records `**source:** {ISSUE-KEY}` under its title so the spec traces back to the tracker.

**S2 Gap** — Bucket every decision: **Given** (requirement / plan source / issue AC / architecture ADR / `decisions.md`) / **Inferred** (Assumption + rationale) / **Unknown**.

- Cosmetic Unknowns (copy, density) may be defaulted and labeled.
- Every other Unknown on the **BA** coverage checklist must be asked. Do not silently invent ACs, error states, or authz.

**S3 Clarify** — Follow clarify-first. Run the **BA** coverage checklist. One batch, **max 15**, multiple-choice with recommended default. Never ask what the repo, plan source, architecture, or `decisions.md` already answers. Interactive: write questions, **stop**, wait for answers or “proceed”. `ASSUMPTIONS_USED` only when the user said proceed or leftovers are cosmetic. Format: load questions asset.

**S4 Draft** — For each child slug, create `features/{slug}/{child}/` and write `specification.md` from the specification template (`N/A — reason` if needed). Load the example only to match density. Cite existing files as **constraints**, not as an implementation file list.

**S4b Order** — Load the spec-order template. Write `features/{slug}/spec-order.md`. Set `**children:**` to the comma-separated kebab list (hooks parse that line). Group waves: `parallel` when children do not share data/API/UI dependencies; `sequential` when they do. Dependencies must be real.

**S4c Test plan** — Load test-plan and test-strategy templates.

- Write `features/{slug}/{child}/test-strategy.md` per child (layer matrix + planned cases for that spec’s Must ACs).
- Write `features/{slug}/test-plan.md` rolling all cases up. Tag every case `ui` | `e2e` | `api` | `unit` | `telemetry` | `a11y`.
- Feature class: `e2e` cannot be `n/a`. `ui: n/a` only when there is no user-visible surface.
- `ui` = Playwright in the browser (unattended, feature-level tester). `api` = existing HTTP/RPC runner. `unit` = existing unit runner.
- Execution is **one tester after all child developer-critics**, not per spec and not between waves.
- When `TEST_DESIGN_ENABLED: true`: bind each Must AC to overlay action/fixture/oracle IDs and the lowest effective level. Do not write free-form automation steps. Login is an auth fixture unless login is under test. E2E needs a written reason. Test-designer writes `cases.json` after critic; you still write `test-plan.md` as the layer rollup.

**S5 Self-gate** — All **blockers** below must pass. Else fix or return to S3. Never HANDOFF `SUCCESS` on a failing pack.

**S6 Handoff** — Write `state/ba-agent.json` and update `pipeline-state.json`. Load handoff template. Write `HANDOFF.md`. Stop. Parent next: BA critic. Pass state JSON, not this HANDOFF body.

---

## Failure handling (mandatory)

| Situation | Action | HANDOFF |
|-----------|--------|---------|
| Interactive + blocking Unknown | Questions on disk + reply; do not draft a fake-complete spec | `BLOCKED`, `ready_for_ba_critic: false` |
| Non-interactive / user said proceed | Defaults in each spec §11 Assumptions; continue | `ASSUMPTIONS_USED` |
| S5 blocker fails | Fix or return to S3; do not call it SUCCESS | stay in S4/S5 or `BLOCKED` |
| Unsafe, illegal, or missing actor/scope that cannot be defaulted | Stop. No spec presented as Ready | `BLOCKED` + what parent should do |
| Repo exploration fails / no facts | Spec as-is = “unknown / greenfield”; do not invent APIs | continue with labeled assumptions or `BLOCKED` if Must scope is unknown |
| Parent or BA starts coding | Forbidden. Discard that work for this skill | N/A |
| Plan source missing | `BLOCKED` `INPUT_MISSING` — parent re-runs PM or intake | `BLOCKED` |
| Story has no description and no ACs | Do not invent them; list what is missing | `BLOCKED` or `ASSUMPTIONS_USED` per S3 |
| Epic plan lists zero in-scope stories | Nothing to specify | `BLOCKED` — parent asks the user |
| You want a tracker detail intake did not fetch | Ask the parent for it | `BLOCKED` — never call tracker MCP from this Task |

Must FRs still in Open questions ⇒ not Ready. Do not start `developer-agent`.

---

## S5 blockers (all required)

- [ ] The plan source for `PLAN_SOURCE_KIND` exists (`prd.md` | `intake.md` | `epic-plan.md`)
- [ ] `features/{slug}/state/ba-agent.json` on disk
- [ ] `pipeline-state.json` updated for this step
- [ ] `features/{slug}/decisions.md` updated this step
- [ ] Specs do not contradict signed-off `architecture.md` when that file exists
- [ ] `jira-epic`: one child spec per in-scope story, each carrying `**source:** {ISSUE-KEY}`
- [ ] Every child in `**children:**` has `features/{slug}/{child}/specification.md`
- [ ] `features/{slug}/spec-order.md` with a parseable `**children:**` line
- [ ] `features/{slug}/test-plan.md` and each child’s `test-strategy.md`
- [ ] Every Must FR (every child) has ≥1 AC and ≥1 planned test case
- [ ] Problem, goals, non-goals, actors, journeys, FRs, ACs present on each spec
- [ ] Assumptions labeled; no silent auth, payments, or retention invention
- [ ] As-is is factual (paths or explicit greenfield)
- [ ] Out of scope non-empty (or increment bounded with reason)
- [ ] Feature-class `e2e` is `required` on the test plan
- [ ] When `TEST_DESIGN_ENABLED`: every Must AC names a lowest level and overlay IDs, or an explicit gap
- [ ] No product file edits outside `features/{slug}/`

Cheap quality fixes before SUCCESS: atomic FRs, error paths, UI empty/loading/error, product language (not “edit file X”), implementable length (see example asset).

---

## Handoff statuses (mandatory)

| status | Meaning |
|--------|---------|
| `SUCCESS` | Blockers pass; critic may run |
| `ASSUMPTIONS_USED` | Defaults used; critic must test Assumptions |
| `BLOCKED` | Wait, unsafe, or incomplete; include recovery for parent |

Full file shape: [../feature-development/assets/handoff-template.md](../feature-development/assets/handoff-template.md).

---

## Anti-patterns

Chat-only spec · re-asking PM or Architect decisions · asking the repo · FR/AC as code tasks · Ready with blocking OQs · silent defaults on Must ACs · spawning developer from BA · copying the example spec · tester between waves · flat sibling slugs instead of `features/{slug}/{child}/` · calling tracker MCP instead of reading `intake.md` · paraphrasing an issue AC into something weaker · merging two epic stories into one spec · ignoring signed-off architecture.
