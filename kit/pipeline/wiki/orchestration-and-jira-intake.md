# Orchestration and tracker intake

| Attribute | Value |
|-----------|--------|
| Type | Wiki |
| Audience | Parent or specialist when INDEX triggers match |
| Adapt | Add a new page after retro. Do not store secrets or customer identifiers. |

- **Layer:** pipeline
- **Load when:** the ask contains a tracker issue key, or you are deciding which workflow runs before classifying micro / minor / feature

## Symptom

The parent runs the plain-text feature ladder for a pasted issue key, calls tracker MCP from the parent chat and floods its context, or sends a defect through PM → BA and gets a "spec" that is really a guess at the bug.

## Root cause

Class (`micro` | `minor` | `feature`) answers **how big**, not **where the work came from**. A tracker key changes the input contract and, for a defect, the whole chain. The workflow must be resolved before the class.

## Do not

- Call tracker MCP from the parent, or from BA. `intake-agent` fetches once; everyone else reads `intake.md`.
- Run PM or BA on a bug. `rca.md` is the defect's specification.
- Let the developer start a fix before `HANDOFF-bug-analyst.md` is `SUCCESS`.
- Write `route.md` before intake returns, on a tracker workflow — `issue_type` comes from the intake HANDOFF.
- Hardcode a project key, JQL, MCP server name, or issue-type mapping in a skill, agent, or hook.

## Convention

Entry point is `.cursor/skills/orchestration/SKILL.md` (O1 detect → O2 intake → O3 resolve → O4 route → O5 drive). Chains and skips come from `.pipeline/config.json`.

| Work source | Workflow | Chain |
|-------------|----------|-------|
| plain text | `feature-development` | class chain (micro / minor / feature) |
| story or task | `jira-story` | intake → sign-off requirements → architect? → sign-off → BA → BA critic → sign-off BA → waves → tester → devops → retro |
| epic | `jira-epic` | same, BA gets `epic-plan.md` and writes one child spec per story |
| bug | `jira-bug` | intake → bug analyst → developer → developer critic → tester → devops → retro |
| GitHub issue / PR | `github-story` / `github-bug` / `github-epic` | same ladders as the Jira rows; `connection` defaults to `cli` (`gh`) |

`route.md` gained `workflow`, `work_source`, `jira_key` or `github_ref`, `issue_type`. BA takes `PLAN_SOURCE_KIND` + `PLAN_SOURCE_PATH` instead of `PLAN_PATH`.

No tracker connection reachable is not a reason to guess: intake returns `BLOCKED` and the user either sets `intake.jira.connection` or `intake.github.connection` (`mcp`, `cli`, or `api`), fixes auth, or pastes the description as plain text.

Bare `#123` is GitHub only when `intake.github.enabled` is true and `repo` is set.

## Files

`.cursor/skills/orchestration/SKILL.md`, `.pipeline/skills/jira-intake/SKILL.md`, `.pipeline/skills/github-intake/SKILL.md`, `.pipeline/skills/epic-breakdown/SKILL.md`, `.pipeline/skills/bug-fix/SKILL.md`, `.pipeline/config.json`, `.cursor/hooks/subagent-start.py`

## Verify

`features/{slug}/route.md` names a `workflow`. Tracker runs have `intake.md`; epics also have `epic-plan.md` + `stories/`. Bug runs have `rca.md` and a regression test that was red before the fix. `subagent-start.py` denies a bug-workflow developer until the analyst HANDOFF is SUCCESS.
