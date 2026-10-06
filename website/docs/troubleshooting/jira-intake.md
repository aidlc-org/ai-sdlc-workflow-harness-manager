---
title: Tracker intake
description: Resolve workflow from the issue type before change class. Intake fetches once.
---

## Symptom

The parent runs the plain-text feature ladder for a pasted issue key, calls tracker MCP from the parent chat, or sends a defect through PM → BA.

## Cause

Class (`micro` | `minor` | `feature`) answers **how big**, not **where the work came from**. A tracker key changes the input contract. For a defect, the whole chain changes.

## Do not

- Call tracker MCP, the Jira/`gh` CLI, or `jira_api.py` / `github_api.py` from the parent or from BA
- Run PM or BA on a bug — `rca.md` is the spec
- Let the developer start before `HANDOFF-bug-analyst.md` is SUCCESS
- Write `route.md` before intake returns
- Hardcode project key, JQL, owner/repo, MCP name, or issue-type mapping in a skill
- Switch `intake.jira.connection` or `intake.github.connection` silently when the configured one fails
- Treat a bare `#123` as GitHub when `intake.github.enabled` is false or `repo` is empty

## Convention

O1 detect → O2 intake → O3 resolve → O4 route → O5 drive. See [Jira workflows](/docs/workflows/jira) and [GitHub workflows](/docs/workflows/github).
