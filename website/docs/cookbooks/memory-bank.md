---
title: Memory bank for small teams
description: Install the memory package, link an external artifact bank, index it, search past features, and optionally register MCP for the IDE.
---

**Goal:** Keep `features/{slug}/` artifacts in a **shared git bank**, search them from the CLI, and optionally expose them to the IDE via MCP.

**Components used:** [Packages](/docs/components/packages), [Memory bank and MCP](/docs/capabilities/memory).

:::note Not the wiki
[Wiki](/docs/capabilities/wiki) = short reusable lessons inside `.pipeline/wiki/`.  
**Memory bank** = full feature artifacts (requests, architecture, decisions, handoffs), usually outside the product repo.
:::

## Prerequisites

- Product repo with `.pipeline/`
- CLI environment where you can install `.[memory]` (same pattern as orchestrator/assess)
- A folder (often its own git repo) that will hold the bank

## Steps

### 1. Install the extra

```bash
cd /path/to/pipeline-kit-checkout
uv tool install -e ".[memory]"
pipeline-kit memory doctor .
```

**Verify:** `pipeline-kit-memory is not installed` is gone. `doctor` may still exit 1 until you `link`.

### 2. Link, import, index, search

From the **product** root:

```bash
pipeline-kit memory link ../pipeline-memory --project-id my-app
pipeline-kit memory import-local     # one-time copy of existing features/
pipeline-kit memory index
pipeline-kit memory search "oauth decision" --json
pipeline-kit memory doctor
```

**Verify:** `memory` block in `.pipeline/config.json`; search returns hits after index. Re-run `memory index` after artifacts change — MCP does not re-index alone.

### 3. Register MCP (optional)

Add a stdio MCP entry in the IDE. `--project` must be the **absolute path of the product repo** (with `.pipeline/config.json`), not the bank folder.

Example Cursor `.cursor/mcp.json` shape is documented in [Memory bank and MCP](/docs/capabilities/memory#register-the-mcp-server).

Restart the IDE client after editing MCP config.

## Layout reminder

| Mode | Path in the bank |
|------|------------------|
| Flat | `{root}/features/{slug}/...` |
| Namespaced (`--project-id`) | `{root}/projects/{id}/features/{slug}/...` |

Run state stays in the product project. Index: `{root}/.memory/index.sqlite` (gitignored in the bank).

## Done when

- [ ] Memory extra installed in the CLI env  
- [ ] Link + index + search work  
- [ ] MCP optional path documented for the team  

## Next

- [Packages hub](/docs/components/packages)
- [First feature](/docs/cookbooks/first-feature)
- [CLI — memory](/docs/reference/cli#memory)
