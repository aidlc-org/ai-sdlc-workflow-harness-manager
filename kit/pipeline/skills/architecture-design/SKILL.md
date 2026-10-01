---
name: architecture-design
description: >-
  Invoke when the architect-agent must turn signed-off requirements into
  architecture.md and an implementation plan before BA. Mine prior artifacts,
  challenge remaining technical decisions, then diagram. Do not use for
  micro/minor, bugs, coding, or UI-only redesign.
---

# Architecture design (autonomous Architect loop)

| Attribute | Value |
|-----------|--------|
| Type | Skill |
| Audience | The named agent, or the parent when this file is on the allowlist |
| Adapt | Change commands or paths only in deploy and testing skills. Planning skills stay product-neutral. |

Turn signed-off requirements into on-disk architecture and an ordered
implementation plan BA can specify against and developers can implement
without inventing structure.

**Parent:** spawn Architect as a separate `Task` after `@signoff:requirements`
when `skip_architect` is false. **Architect:** write architecture +
implementation plan + HANDOFF, then return. **Do not** write `specification.md`,
implement code, or spawn BA.

**Success:** `architecture.md` and `implementation-plan.md` are complete,
ADRs labeled, child split stable, `decisions.md` updated, concerns recorded
or raised as blocking.  
**Failure:** chat-only design, silent invention, or open Must technical questions.

**Progressive loading:** follow A1–A5 first. Templates are owned by
**feature-development** — read them only at the step that names them.

| When | Read (feature-development) |
|------|------|
| Every step (state) | [../feature-development/assets/pipeline-state.md](../feature-development/assets/pipeline-state.md) |
| A1 (decisions) | [../feature-development/assets/decisions-template.md](../feature-development/assets/decisions-template.md), [../feature-development/assets/clarify-first.md](../feature-development/assets/clarify-first.md) |
| A2 (questions) | [../feature-development/assets/questions-format.md](../feature-development/assets/questions-format.md) |
| A3 (design) | [../feature-development/assets/architecture-template.md](../feature-development/assets/architecture-template.md), [../feature-development/assets/implementation-plan-template.md](../feature-development/assets/implementation-plan-template.md), [../architecture-visualization/SKILL.md](../architecture-visualization/SKILL.md) (when `ARCHIFY_ENABLED`) |
| A5 (handoff) | [../feature-development/assets/handoff-architect-template.md](../feature-development/assets/handoff-architect-template.md), [../feature-development/assets/agent-state-template.json](../feature-development/assets/agent-state-template.json) |

---

## Roles and outputs

| Role | Allowed |
|------|---------|
| Parent | `@signoff:requirements`, then `Task` Architect, then `@signoff:architect` |
| Architect (this skill) | Read requirements + repo, challenge, write architecture + plan + HANDOFF |
| BA | Later `Task` only |

```text
features/{slug}/
  architecture.md
  implementation-plan.md
  architect-concerns.md     # if any concern was recorded
  decisions.md
  questions.md              # if A2 ran
  state/architect-agent.json
  pipeline-state.json
  HANDOFF-architect.md
  diagrams/manifest.json    # when ARCHIFY_ENABLED
```

Reuse `{slug}` if the folder exists; update the architecture, do not fork.

---

## Steps (do not skip; no product code)

`A1 DISCOVER → A2 CHALLENGE → A3 DESIGN → A4 SELF-GATE → A5 HANDOFF`

**A1 Discover** — Read prior **state JSON** first, then only the files it
lists. The signed-off requirements source is `prd.md` (PM) or `intake.md` /
`epic-plan.md`. Also read `ui-design.md`, `ui/manifest.json`, and
`ui/index.html` when they exist, then `research.md`, `decisions.md`,
`signoff-requirements.md`, then the repo. Restate the technical problem.
List 2–4 structural options and why one is preferred. Greenfield: say so.
Do not invent screens missing from `ui-design.md`. If IA/layout is blocking,
return `CONSULT_REQUESTED` per [next-agent-policy.md](../feature-development/assets/next-agent-policy.md).
Append extracted facts to `decisions.md`. Load [clarify-first.md](../feature-development/assets/clarify-first.md).

**A2 Challenge** — Follow clarify-first. Run the **Architect** coverage
checklist. Do **not** skip A2 because the PRD “looks clear.” Requirements
are often not fully solidified; record that instead of inventing product
direction.

**Concerns (required thinking, not optional):**

| Severity | When | What you do |
|----------|------|-------------|
| `blocking` | The design cannot be honest until the requirement changes | `audience: user` → `BLOCKED`. `audience: pm` on feature-development → `BLOCKED_CHALLENGE_PM`. |
| `recorded` | A risk, gap, or soft requirement the design can still proceed with | Write it in `architecture.md` §9, `architect-concerns.md`, and agent state. Continue. HITL reviews it at `@signoff:architect`. |

- One question batch, **max 15**. Format: questions asset. Set `audience: user | pm`.
- `audience: pm` on `jira-story` / `jira-epic` → treat as `user`.
- Never ask what the repo or a prior artifact already answers.
- Never hide a blocking concern as `recorded` to keep the pipeline moving.

**A3 Design** — Load the architecture and implementation-plan templates. Fill
every section. Use **mermaid** for the portable diagrams in `architecture.md`
(no ad-hoc images). Sequence diagram is required when a new API or
multi-step flow exists. If you revise the PM / intake child split for
technical reasons, that split **wins** for BA. Append ADRs to
`decisions.md`. Keep `recorded` concerns visible — do not drop them because
diagrams exist. When `TEST_DESIGN_ENABLED: true`, write
`features/{slug}/test-design/model-delta.json` (`planned` nodes) or set
`no_test_model_change: true`. When `ARCHIFY_ENABLED: true`, follow
[architecture-visualization/SKILL.md](../architecture-visualization/SKILL.md)
after mermaid is drafted: deliver JSON/HTML under
`features/{slug}/diagrams/` or record `mermaid-fallback`. Never remove the
mermaid blocks. Missing Archify is not `BLOCKED`.

**A4 Self-gate** — All **blockers** below must pass. Else fix or return to A2.
Never HANDOFF `SUCCESS` on a failing design.

**A5 Handoff** — Write `state/architect-agent.json` and update
`pipeline-state.json`. Load the Architect handoff template. Write
`HANDOFF-architect.md`. Stop. Parent next: `@signoff:architect` (present
concerns), then BA.

---

## Failure handling (mandatory)

| Situation | Action | HANDOFF |
|-----------|--------|---------|
| Interactive + Unknown on Architect checklist | Questions on disk; do not draft a fake-complete design | `BLOCKED` |
| Requirements are wrong / incomplete (text-sourced) | Challenge PM; do not invent a new product direction | `BLOCKED_CHALLENGE_PM` |
| Requirements are wrong (jira-story / jira-epic) | Ask the user | `BLOCKED` |
| User said proceed | Defaults labeled in ADRs | `ASSUMPTIONS_USED` |
| A4 blocker fails | Fix design or return to A2 | stay in A3/A4 or `BLOCKED` |
| Unsafe, illegal | Stop | `BLOCKED` + what parent should do |

---

## A4 blockers (all required)

- [ ] `features/{slug}/architecture.md` on disk
- [ ] `features/{slug}/implementation-plan.md` on disk
- [ ] `features/{slug}/state/architect-agent.json` on disk
- [ ] `pipeline-state.json` updated for this step
- [ ] Concerns section filled (`none` or listed); blocking concerns are not marked SUCCESS
- [ ] `features/{slug}/decisions.md` updated this step
- [ ] Context + module mermaid present; sequence present or explicitly `none`
- [ ] At least one ADR
- [ ] Child-spec split listed (at least one kebab slug)
- [ ] Constraints and do-not-invent non-empty
- [ ] New dependencies declared in `state/architect-agent.json` `context.new_dependencies` with the rung each failed, and mirrored in `HANDOFF-architect.md` (`none` when there are none)
- [ ] Assumptions labeled; no silent auth, persistence, or vendor invention
- [ ] When `TEST_DESIGN_ENABLED`: `test-design/model-delta.json` exists or `no_test_model_change` is true
- [ ] When `ARCHIFY_ENABLED`: `diagrams/manifest.json` exists with `delivered` or `mermaid-fallback`
- [ ] As-is is factual (paths or explicit greenfield)
- [ ] No product file edits outside `features/{slug}/`

---

## Handoff statuses (mandatory)

| status | Meaning |
|--------|---------|
| `SUCCESS` | Blockers pass; parent may request architect sign-off |
| `ASSUMPTIONS_USED` | Defaults used; BA and BA critic must test them |
| `BLOCKED` | Wait, unsafe, or incomplete |
| `BLOCKED_CHALLENGE_PM` | Parent must re-run PM (feature-development only) |

---

## Anti-patterns

Chat-only architecture · skipping A2 · asking the repo · re-asking PM
decisions · writing `specification.md` · spawning BA from Architect · Ready
with open Must technical questions · inventing a new product direction
instead of raising a concern · hiding blocking concerns as recorded.
