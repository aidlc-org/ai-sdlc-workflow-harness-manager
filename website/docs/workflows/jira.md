---
title: Jira story, epic, and bug
description: Tracker key first. Intake fetches once. Bugs skip PM/BA. Epics split children from the epic plan.
---

When `intake.jira.enabled` is true and the ask contains an issue key, the receptionist resolves **`jira-story`**, **`jira-epic`**, or **`jira-bug`** from the issue type — **before** change class.

## Shared rules

- `intake-agent` fetches **once**. Everyone else reads `intake.md`. Do not call the tracker from the parent or from BA.
- The configured `intake.jira.connection` (`mcp`, `cli`, or `api`) is the only fetch path. If it fails, intake returns `BLOCKED`. Switch `connection`, fix auth, or paste the description as plain text (`feature-development`). Do not guess.
- Do not hardcode a project key, JQL, MCP server name, CLI argv, or issue-type mapping in a skill. Those belong in `config.json`.

## Chains

| Workflow | Plan source | Chain |
|----------|-------------|-------|
| `jira-story` | `intake.md` | intake → sign-off requirements → architect? → BA → waves → tester → devops → retro (`skip_pm`) |
| `jira-epic` | `epic-plan.md` | Same shape; BA writes one child spec per in-scope story |
| `jira-bug` | `rca.md` | intake → bug-analyst → developer → critic → tester → devops → retro. No PM/BA/Architect |

`run_tester` is true on bugs. Do not let the developer start a fix before `HANDOFF-bug-analyst.md` is `SUCCESS`. `rca.md` is the defect’s specification.

Issue-type map (story, task, bug, defect, epic, …) is under `intake.jira.issue_type_map`. For `connection: mcp`, tool names default to `getJiraIssue` and `searchJiraIssuesUsingJql`.

Enable/disable: [config guide](/docs/guides/config). Failures: [intake troubleshooting](/docs/troubleshooting/jira-intake).
