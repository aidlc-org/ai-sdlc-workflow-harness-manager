---
title: config.json reference
description: Workflows, waves, intake, product, test_design, architecture_diagrams, agent_observability, verify, gates, deploy.
---

Path: `.pipeline/config.json`. Do not put secrets or tracker site URLs in this file.

## `workflows`

Each key is a workflow name. Fields you will see:

| Field | Meaning |
|-------|---------|
| `source` | `text`, `jira`, or `github` |
| `plan_source` | Artifact the planner reads (`prd.md`, `intake.md`, `epic-plan.md`, `rca.md`) |
| `chain` | Ordered specialist tokens and `@signoff:*` / `@waves` |
| `classes` | micro / minor / feature chains (`feature-development` only) |
| `skips` | `skip_pm`, `skip_ba`, `skip_architect`, `skip_telemetry`, … |
| `run_tester` | Force tester on (bugs) |
| `default_change_class` | Starting class for tracker workflows |

## `waves.child_chain`

Expanded per child listed in `features/{slug}/spec-order.md`. Default: developer → developer-critic.

## `intake.jira`

`enabled`, `connection` (`mcp` | `cli` | `api`; missing means `mcp`), `key_pattern`, `mcp_namespaces`, `tools.issue` / `tools.search`, `cli.bin` / `cli.issue_view` / `cli.search`, `api` (env-only note), `epic_children_jql`, `max_children`, `issue_type_map`, `include_comments`, `write_back`.

Site URL and token stay in the environment (`JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`), never in this file.

## `intake.github`

`enabled` (default false), `connection` (`mcp` | `cli` | `api`; missing means `cli`), `repo` (`owner/repo`, required for bare `#N`), `mcp_namespaces`, `tools.issue` / `tools.search`, `cli.bin` / `cli.issue_view` / `cli.pr_view` / `cli.sub_issues`, `api` (env-only note), `max_children`, `issue_type_map`, `include_comments`, `write_back`.

Token stays in the environment (`GH_TOKEN` or `GITHUB_TOKEN`). Optional `GITHUB_API_URL` for GitHub Enterprise. Optional `GITHUB_REPO` when the ask is only `#123`.

## `product`

`artifact_dir` (default `features/`). `readonly_agents` may write only there.

## Opt-in blocks

| Block | Set by |
|-------|--------|
| `test_design` | `knowledge init` (`enabled`, `graph_path`, `playwright`, …) |
| `architecture_diagrams` | `plugins install archify` (`version` `v2.16.0`, `fallback` mermaid) |
| `agent_observability` | `obs install` (adapter, redact, dataset, retention) |

## `verify.rules`

Path substring + message. Optional `expect` regex for obs integrity.

## `gates`

`retry_cap` (default 2), `require_signoff_before_deploy`, `require_planning_signoff_before_build`, `complete_after` (`retro-agent`).

## `deploy`

`target` and `targets` list. Must match the local-deploy script.
