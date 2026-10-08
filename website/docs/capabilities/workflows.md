---
title: Workflows and change classes
description: Named procedures plus micro / minor / feature classification before any specialist Task.
---

A **workflow** answers *where the work came from* and *which chain to run*. A **change class** answers *how big* the work is. Resolve the workflow first, then classify.

## Shipped workflows

| Name | Source | Chain (summary) |
|------|--------|-----------------|
| `ask` | text | Empty — parent only |
| `feature-development` | text | Class chains (micro / minor / feature) |
| `jira-story` | jira | intake → sign-offs → architect? → BA → waves → tester → devops → retro |
| `jira-epic` | jira | Same; plan source is `epic-plan.md` |
| `jira-bug` | jira | intake → bug-analyst → developer → critic → tester → devops → retro |
| `test-knowledge-bootstrap` | text | `knowledge-curator-agent` only |
| `large-codebase-docs` | text | CLI extract-modules; `module-docs-agent` per module → `wiki/codebase/` |
| `module-security-review` | text | `module-security-agent` per module → `security.md` |
| `system-architecture` | text | optional merge; one `system-architect-agent` → `wiki/codebase/system/` |

Chains live in `.pipeline/config.json`. File allowlists live in `.pipeline/workflows/*.json`.

## Change class (feature-development)

Classify **before** any specialist `Task`. Unsure → **feature**. If the diff grows into a new screen mid-flight, rewrite `route.md` to `feature` and start **PM**.

| Class | Typical chain |
|-------|----------------|
| **micro** | developer → tester (policy) → devops → retro |
| **minor** | developer → developer-critic → tester (policy) → devops → retro |
| **feature** | PM → sign-off → Architect? → sign-off → BA → BA critic → sign-off → waves → one tester → devops → retro |

Do **not** classify micro if there is a new route, API, persistence, authz, money, or PII. Do **not** implement “because it’s small” in the parent chat.

Write `features/{slug}/route.md` from `.pipeline/skills/feature-development/assets/change-routing.md`.

## Tracker vs class

A tracker key changes the input contract. A defect uses `rca.md`, not a PRD. See [Jira workflows](/docs/workflows/jira) and [intake troubleshooting](/docs/troubleshooting/jira-intake).

## Waves

On feature class, `@waves` expands per child in `features/{slug}/spec-order.md` to `waves.child_chain` (developer → developer-critic). Parallel children share a wave. One tester runs **after** all children.
