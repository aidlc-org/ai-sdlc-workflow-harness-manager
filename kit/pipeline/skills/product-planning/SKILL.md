---
name: product-planning
description: >-
  Invoke when the feature-development parent (or product-manager-agent) must
  turn a feature-class ask into a signed PRD before UI designer, Architect, or BA.
  Analyze the existing product, mine prior artifacts, then ask remaining
  product decisions including surfaces and UX constraints. Do not use for
  micro/minor, coding, or UI-only redesign.
---

# Product planning (autonomous PM loop)

| Attribute | Value |
|-----------|--------|
| Type | Skill |
| Audience | The named agent, or the parent when this file is on the allowlist |
| Adapt | Change commands or paths only in deploy and testing skills. Planning skills stay product-neutral. |

Turn a feature-class request into one on-disk **PRD** UI designer, Architect, and BA can
use without inventing scope. A shallow restatement of the ask is a failed
step. If the PRD is thin, later stages cannot recover the missing analysis.

**Parent:** spawn PM as a separate `Task`. Pass pipeline state, not a long
chat. **PM:** write PRD + research + decisions + agent state + HANDOFF, then
return. **Do not** write `specification.md`, implement code, or spawn
UI designer, Architect, or BA.

**Success:** `features/{slug}/prd.md` is complete, as-is is grounded in the
repo or explicit greenfield, child-spec split is stable, `decisions.md` is
updated, leftover Unknowns are cosmetic or user-approved.  
**Failure:** chat-only PRD, silent invention, open Must questions, or
invented market facts with no citation.

**Progressive loading:** follow P1–P6 first. Templates are owned by
**feature-development** — read them only at the step that names them.

| When | Read (feature-development) |
|------|------|
| Every step (state) | [../feature-development/assets/pipeline-state.md](../feature-development/assets/pipeline-state.md) |
| P1 / P3 (clarify-first) | [../feature-development/assets/clarify-first.md](../feature-development/assets/clarify-first.md), [../feature-development/assets/decisions-template.md](../feature-development/assets/decisions-template.md) |
| P3 (interactive questions) | [../feature-development/assets/questions-format.md](../feature-development/assets/questions-format.md) |
| P2 (research) | [../feature-development/assets/research-template.md](../feature-development/assets/research-template.md) |
| P4 (PRD) | [../feature-development/assets/prd-template.md](../feature-development/assets/prd-template.md) |
| P6 (handoff + state) | [../feature-development/assets/handoff-pm-template.md](../feature-development/assets/handoff-pm-template.md), [../feature-development/assets/agent-state-template.json](../feature-development/assets/agent-state-template.json) |

---

## Roles and outputs

| Role | Allowed |
|------|---------|
| Parent | Create `features/{slug}/` and `pipeline-state.json`, `Task` PM, then `@signoff:requirements` |
| PM (this skill) | Explore repo, web search, clarify-first questions, write PRD + research + decisions + state + HANDOFF |
| Architect / BA | Later `Task` only |

```text
features/{slug}/
  prd.md
  research.md
  decisions.md
  questions.md                          # if P3 ran
  state/product-manager-agent.json
  pipeline-state.json                   # update this step
  HANDOFF-pm.md
```

Reuse `{slug}` if the folder exists; update the PRD, do not fork a second one.

---

## Steps (do not skip; no product code)

`P1 DISCOVER → P2 RESEARCH → P3 CLARIFY → P4 PRD → P5 SELF-GATE → P6 HANDOFF`

**P1 Discover + as-is** — Restate intent in business terms (who, goal,
timeline). Scan the repo until you can narrate how the **current** product
behaves in the area of change: screens, APIs, approval chains, jobs,
integrations. Typical shapes:

- An existing process (for example access review) that must change
  (approvals, roles, outcomes).
- An integration with an external system (what exists, what is missing).
- A net-new flow on top of an existing module.

List 2–4 product options and why one is preferred. Greenfield: say so with
evidence (no matching module). Load
[clarify-first.md](../feature-development/assets/clarify-first.md). Append
facts from `USER_REQUEST`, `route.md`, `intake.md` (if present), prior
state, and any existing PRD/questions to `decisions.md`.

**P2 Research** — Load the research template. Gather **cited** facts:

- Repo: path + fact (required unless greenfield). Cover the as-is flow, not
  a single file name.
- Web: comparable products, domain rules, or integration conventions that
  change the PRD. Use web search. Quote a URL per claim. If nothing useful
  is found, write `none — {why}` and continue.
- Do not invent market or competitor claims.

**P3 Clarify** — Follow clarify-first. Run the **PM** coverage checklist
(including surfaces, screens, theme, empty/error states, integrations,
persistence, authz). Ask every remaining decision. Do not prefer silent defaults.

- One batch, **max 20**, multiple-choice with a recommended default. Format:
  questions asset.
- Never ask what the repo or a prior artifact already answers.
- Interactive + remaining Unknowns: write `questions.md`, **stop**, wait
  for answers or “proceed”.
- `ASSUMPTIONS_USED` only when the user said proceed / use defaults, or
  leftovers are cosmetic.

**P4 PRD** — Load the PRD template. Fill every section including **§6.4
Surfaces and UX constraints**. As-is and to-be must be specific enough that
UI designer and Architect can challenge them. Propose child specs (kebab
slugs + one-line job). One child is valid. “Ready for sign-off” only when
the split is stable. Parent next is UI designer (when surfaces exist) or
**sign-off**, then Architect (or BA if `skip_architect`).

**P5 Self-gate** — All **blockers** below must pass. Else fix or return to P3.
Never HANDOFF `SUCCESS` on a failing PRD.

**P6 Handoff** — Write `state/product-manager-agent.json` and update
`pipeline-state.json` ([pipeline-state.md](../feature-development/assets/pipeline-state.md)).
Load the PM handoff template. Write `HANDOFF-pm.md`. Set
`context.next_agent` to `ui-designer-agent` or `signoff-requirements` per
[next-agent-policy.md](../feature-development/assets/next-agent-policy.md)
and [ui-designer-policy.md](../feature-development/assets/ui-designer-policy.md).
Stop. Parent applies UI policy; do not spawn the next agent.

---

## Failure handling (mandatory)

| Situation | Action | HANDOFF |
|-----------|--------|---------|
| Interactive + Unknown on PM checklist | Questions on disk; do not draft a fake-complete PRD | `BLOCKED`, `ready_for_ba: false` |
| User said proceed / leftovers cosmetic | Defaults labeled in the PRD | `ASSUMPTIONS_USED` |
| P5 blocker fails | Fix PRD or return to P3 | stay in P4/P5 or `BLOCKED` |
| Unsafe, illegal, or missing actor/scope that cannot be defaulted | Stop | `BLOCKED` + what parent should do |
| Web search fails | Continue with repo facts; label gaps | continue |

---

## P5 blockers (all required)

- [ ] `features/{slug}/prd.md` on disk
- [ ] `features/{slug}/research.md` on disk (may say no useful web facts)
- [ ] `features/{slug}/decisions.md` on disk
- [ ] `features/{slug}/state/product-manager-agent.json` on disk
- [ ] `pipeline-state.json` updated for this step
- [ ] Business context, problem, actors, as-is, to-be, success criteria, non-goals present
- [ ] Surfaces / UX constraints filled or explicit `none`
- [ ] As-is is factual (paths or explicit greenfield)
- [ ] Proposed child specs listed (at least one kebab slug)
- [ ] Assumptions labeled; no silent auth, payments, or retention invention
- [ ] No product file edits outside `features/{slug}/`

---

## Handoff statuses (mandatory)

| status | Meaning |
|--------|---------|
| `SUCCESS` | Blockers pass; parent may request requirements sign-off |
| `ASSUMPTIONS_USED` | Defaults used; Architect, BA, and BA critic must test them |
| `BLOCKED` | Wait, unsafe, or incomplete; include recovery for parent |

---

## Anti-patterns

Chat-only PRD · restating the ask without as-is · asking the repo · silent
defaults on Must decisions · inventing competitors · writing
`specification.md` · spawning UI designer, Architect, or BA from PM · Ready with blocking
open questions · pasting the PRD into chat instead of writing state JSON.
