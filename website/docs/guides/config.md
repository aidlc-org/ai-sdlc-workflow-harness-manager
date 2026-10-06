---
title: Adapt config.json
description: Overlay verify rules, deploy targets, and Jira on/off. Do not put secrets or site URLs here.
---

The installed `.pipeline/config.json` is a **generic template**. Edit the keys below. Do not put secrets, host URLs, or tracker site URLs in any other pack file.

## `verify.rules`

After a specialist edits a file, a hook (if present) injects a reminder. Match a **path substring** from *your* tree. Empty `[]` is valid.

```json
"verify": {
  "rules": [
    {
      "match": "/frontend/",
      "message": "You edited the UI. Run the frontend build and keep empty/error/loading states."
    }
  ]
}
```

Optional `expect` is a regex the observability scorer uses for integrity checks.

## `deploy.target` / `deploy.targets`

Devops receives `DEPLOY_TARGET` from the parent. Values must match **your** runbook and script.

```json
"deploy": {
  "target": "auto",
  "targets": ["auto", "web", "api", "both"]
}
```

The shipped `deploy-local.sh` writes `OVERALL=failed` until you implement build, serve, and health. See [local deploy](/docs/guides/local-deploy).

## `intake.jira`

| Situation | Setting |
|-----------|---------|
| No Jira | `"enabled": false` |
| Jira + IDE MCP | `"enabled": true`, `"connection": "mcp"`, fill `mcp_namespaces` if discovery fails |
| MCP banned, CLI allowed | `"connection": "cli"` |
| Token only | `"connection": "api"` plus `JIRA_BASE_URL` / `JIRA_API_TOKEN` in the environment |
| Types differ (`Defect`, `Incident`) | Edit `issue_type_map` |

Intake uses only the chosen `connection`. Do not put the Jira site URL or API token in this file.

## `intake.github`

| Situation | Setting |
|-----------|---------|
| No GitHub Issues | `"enabled": false` (pack default) |
| MCP banned, `gh` allowed | `"enabled": true`, `"connection": "cli"`, set `repo` to `owner/repo` if asks are only `#123` |
| Token only | `"connection": "api"` plus `GH_TOKEN` or `GITHUB_TOKEN` in the environment |
| GitHub MCP in the IDE | `"connection": "mcp"`, fill `mcp_namespaces` if discovery fails |

Default `connection` is `cli`. Intake uses only that path. Do not put a PAT in this file. Writes need `PIPELINE_ALLOW_GITHUB=1`.

## Leave as-is until you have a reason

| Key | Default meaning |
|-----|-----------------|
| `workflows.*` chains / `classes` | Delivery ladder. Change only if you drop or add a specialist. |
| `product.artifact_dir` | `features/` |
| `gates.retry_cap` | Critic retries (default 2) |
| `gates.require_planning_signoff_before_build` | User must approve planning artifacts before waves |
| `waves.child_chain` | Per-child developer → critic |

Full key list: [config reference](/docs/reference/config).
