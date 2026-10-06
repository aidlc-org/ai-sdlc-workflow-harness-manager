---
name: epic-breakdown
description: >-
  Invoke when tracker intake resolves an issue to the epic workflow. Pull the
  epic’s child stories using the same tracker connection as intake
  (mcp, cli, or api; read-only), then write a plan-shaped
  features/{slug}/epic-plan.md whose proposed child specs are one per story, so
  the BA can specify the whole epic. Not for a single story or a bug. Does not
  write specifications, code, or tests.
---

# Epic breakdown

| Attribute | Value |
|-----------|--------|
| Type | Skill |
| Audience | The named agent, or the parent when this file is on the allowlist |
| Adapt | Change commands or paths only in deploy and testing skills. Planning skills stay product-neutral. |

An epic is a **plan source**, not a spec. This skill produces the same artifact shape the product manager would hand the BA — problem, direction, and a stable **one child spec per story** split — sourced from the tracker instead of from research.

Runs **inside the intake Task** (the tracker connection is already open). Extends [`../jira-intake/SKILL.md`](../jira-intake/SKILL.md) or [`../github-intake/SKILL.md`](../github-intake/SKILL.md) step I6.

**Success:** every in-scope child story has a row, a kebab slug, and enough scope for BA to write a spec against.
**Failure:** inventing stories the epic does not have, merging several stories into one child, or writing acceptance criteria the tracker never stated.

| When | Read |
|------|------|
| E4 (write the plan) | [assets/epic-plan-template.md](assets/epic-plan-template.md) |

---

## Steps

`E1 QUERY → E2 SELECT → E3 SPLIT → E4 PLAN → E5 SELF-GATE`

### E1 Query children

Cap results at `max_children`. Use the **same** tracker `connection` intake used — do not switch.

**Jira** (`JIRA_KEY` injected): use `intake.jira.epic_children_jql`, substituting `{KEY}` with the epic key.

- **mcp** — call the configured `tools.search`.
- **cli** — run `{cli.bin}` plus `cli.search` with `{JQL}` replaced. Parse stdout; do not call MCP.
- **api** — `python .pipeline/skills/jira-intake/scripts/jira_api.py search "{JQL}" --max {max_children}`. Parse JSON `issues`.

The JQL is config because trackers model epic links differently. Do not hardcode a link field, board, or project. If the configured JQL returns nothing, retry once with the epic key as parent link; if still nothing, treat the epic as childless (E5).

**GitHub** (`GITHUB_REF` injected): list sub-issues. There is no JQL.

- **mcp** — call the GitHub MCP tool that lists sub-issues or child issues for the number; if none exists, treat as childless (E5).
- **cli** — run `{cli.bin}` plus `cli.sub_issues` with `{N}` and `{REPO}` replaced. A 404 means no sub-issues.
- **api** — `python .pipeline/skills/github-intake/scripts/github_api.py sub-issues {REF} --max {max_children}`. Parse JSON `issues`. Empty or 404 is childless (E5).

For each child fetch the same fields intake collects for a single issue: key, type, status, summary, description, acceptance criteria, labels, components, links.

### E2 Select what is in scope

| Child | In this run? |
|-------|--------------|
| Open story / task | **Yes** |
| Already done / released | No — list under Out of scope with its status |
| Bug under the epic | No — list it; bugs run the bug workflow on their own key |
| Sub-task of another child | No — it is detail of its parent story |
| Beyond `max_children` | No — list the overflow keys so the user can split the run |

Never silently drop a story. Anything excluded is named with a reason.

### E3 Split into child specs

**One story → one child spec.** Do not merge two stories because they touch the same file, and do not split one story into two specs — that is the BA's call after reading the detail.

Child slug: `{story-key lowercased}-{short kebab summary}`. The key prefix keeps traceability from spec back to tracker.

Order the children into dependency groups the BA can turn into waves: stories sharing data, API, or a route are sequential; independent ones are parallel. Base this on stated links (`blocks`, `depends on`) and on the summaries — not on guesswork about implementation.

### E4 Write the plan

Load [assets/epic-plan-template.md](assets/epic-plan-template.md) and write `features/{slug}/epic-plan.md`.

- Problem, direction, and success criteria come from the **epic's own** description and acceptance criteria.
- Each child row carries its story key, one-line job, and the verbatim summary.
- Write each story's full description and acceptance criteria into `features/{slug}/stories/{child-slug}.md` so BA has the detail without re-querying the tracker.
- Gaps stay gaps: `Unknown — not in the epic`. Assumptions are labeled in the Assumptions table with why they were defaulted.
- Same redaction rules as intake: no secrets, no customer PII.

### E5 Self-gate

- [ ] `epic-plan.md` exists with at least one proposed child, or an explicit zero-story finding
- [ ] Every child row has a kebab slug prefixed with its story key
- [ ] Every in-scope story has a `stories/{child-slug}.md` detail file
- [ ] Every excluded child is listed with a reason
- [ ] Success criteria and non-goals come from the epic, not from you
- [ ] No spec, no code, no test written

Zero in-scope stories is a valid finding: write the plan with an empty child table, return `ASSUMPTIONS_USED`, and let the parent ask the user whether to specify the epic directly or wait for grooming.

---

## Outputs

```text
features/{slug}/epic-plan.md
features/{slug}/stories/{child-slug}.md
```

Handoff is the intake HANDOFF (`HANDOFF-intake.md`) with `EPIC_PLAN_PATH` and `CHILDREN` filled in — this skill does not emit its own.

## Anti-patterns

Inventing stories to “round out” the epic · merging stories into one spec for speed · writing acceptance criteria the tracker does not have · pulling done work back into scope · querying the tracker again from the BA Task · hardcoding a JQL, board, or project key outside the config.
