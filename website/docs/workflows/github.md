---
title: GitHub story, epic, and bug
description: GitHub issue or PR first. Intake fetches once via gh, REST, or MCP. Same ladders as Jira without a Jira license.
---

When `intake.github.enabled` is true and the ask contains a GitHub issue/PR URL, `owner/repo#N`, or `#N` with `intake.github.repo` set, the receptionist resolves **`github-story`**, **`github-epic`**, or **`github-bug`** from the issue type — **before** change class.

Default `connection` is `cli` (`gh`). Missing `connection` means `cli`. Intake uses **only** that path.

## Shared rules

- `intake-agent` fetches **once**. Everyone else reads `intake.md`. Do not call GitHub from the parent or from BA.
- The configured `intake.github.connection` (`mcp`, `cli`, or `api`) is the only fetch path. If it fails, intake returns `BLOCKED`. Switch `connection`, fix auth, or paste the body as plain text (`feature-development`). Do not guess. Do not fall back silently.
- Do not hardcode owner/repo, host, CLI argv, or issue-type mapping in a skill. Those belong in `config.json`. Tokens stay in `GH_TOKEN` / `GITHUB_TOKEN`.
- Bare `#123` is **not** GitHub unless `enabled` is true **and** `repo` is `owner/repo`.
- `github-*` workflows do **not** need the Jira license area. Enable with `pipeline-kit features enable github-intake`.

## Chains

| Workflow | Plan source | Chain |
|----------|-------------|-------|
| `github-story` | `intake.md` | Same as `jira-story` (`skip_pm`) |
| `github-epic` | `epic-plan.md` | Same as `jira-epic`; children come from GitHub sub-issues |
| `github-bug` | `rca.md` | Same as `jira-bug` |

Issue-type map (issue, bug, pull_request, epic, …) is under `intake.github.issue_type_map`. A `bug` / `defect` / `incident` label maps to `github-bug`.

Enable/disable: [config guide](/docs/guides/config). Failures: [intake troubleshooting](/docs/troubleshooting/jira-intake).
