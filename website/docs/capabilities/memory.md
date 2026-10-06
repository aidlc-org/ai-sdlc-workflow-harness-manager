---
title: Memory bank and MCP
description: Keep feature artifacts in a separate git repo, search them from the CLI, and expose them to your IDE through a stdio MCP server.
---

The memory bank is an **external archive of feature artifacts**. Instead of leaving `features/{slug}/` inside each product repo, you link a separate git folder, index it with SQLite FTS5, and let the agent search past requests, decisions and handoffs.

:::note Not the wiki
The [Wiki](/docs/capabilities/wiki) holds short reusable *lessons* inside `.pipeline/wiki/`. The memory bank holds the *artifacts of every feature* (requests, architecture, decisions, handoffs), usually in a shared repo. They are separate and do not overlap.
:::

## When to use it

- A product line spans several repos and you want one shared archive.
- You want an org-wide record of past decisions that agents can query.
- You do not want artifacts committed to the product repo.

If you have a single repo and are happy with `features/{slug}/` in it, you do not need this.

## Install

It is an optional package. From the kit checkout:

```bash
pip install -e packages/pipeline-kit-memory -e .
```

This adds `pipeline-kit memory ...` and the `pipeline-memory-mcp` server binary. Using it is part of the free tier, see [Licensing](/docs/reference/licensing).

## Set up a product

Run from the product root (it must already have `.pipeline/`):

```bash
pipeline-kit memory link ../pipeline-memory --project-id my-app
pipeline-kit memory import-local     # one-time copy of existing features/
pipeline-kit memory index
pipeline-kit memory search "oauth decision" --json
pipeline-kit memory doctor
```

`link` writes a `memory` block into `.pipeline/config.json`. **Indexing is required** before search returns anything, and you must re-run `memory index` after artifacts change. The MCP server does not re-index on its own.

### Layout

| Mode | Path in the bank |
|------|------------------|
| Flat (one product, one bank) | `{root}/features/{slug}/...` |
| Namespaced (`--project-id`) | `{root}/projects/{id}/features/{slug}/...` |

Run state (`.pipeline/state/`) always stays in the product project. The index lives at `{root}/.memory/index.sqlite` and is gitignored in the bank.

## Register the MCP server

The kit does **not** wire memory into your IDE. Each developer (or a team template) adds a stdio MCP entry, then restarts the client. The client spawns the server when a tool is called, so you never keep it running in a terminal.

`--project` must be the **absolute path of the product repo** you linked (the one containing `.pipeline/config.json`), not the bank folder.

**Cursor** (`.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "pipeline-memory": {
      "command": "pipeline-memory-mcp",
      "args": ["--project", "C:/path/to/your-product-repo"]
    }
  }
}
```

**VS Code / Copilot** (`mcp.json`; the key may be `servers`):

```json
{
  "servers": {
    "pipeline-memory": {
      "type": "stdio",
      "command": "pipeline-memory-mcp",
      "args": ["--project", "C:/path/to/your-product-repo"]
    }
  }
}
```

**Claude Desktop** (`claude_desktop_config.json`) uses the same shape as Cursor. Claude Code and other stdio hosts work the same way.

If `pipeline-memory-mcp` is not on PATH, set `command` to your full `python.exe` path and use args `-m`, `pipeline_memory.mcp_server`, `--project`, `<product path>`.

## Tools

| Tool | Arguments | Purpose |
|------|-----------|---------|
| `memory_search` | `query`, optional `slug`, `kind`, `limit` | Full-text search over indexed chunks |
| `memory_why` | `query`, optional `slug`, `limit` | Prefers decision, request, handoff and architecture docs |
| `memory_get` | `path`, or `slug` + `rel` | Read one artifact file |
| `memory_list_slugs` | none | List feature slugs in the bank |
| `memory_list_files` | `slug` | List files under one feature |

The server is **read-only**. Changes to the bank go through normal git plus `memory index`.

To verify, restart the IDE, call `memory_list_slugs`, then `memory_search` with `{ "query": "architecture", "limit": 5 }`.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Command not found | Use the full path to `pipeline-memory-mcp` or `python.exe`, from the env where you ran `pip install` |
| Tools missing in the IDE | Invalid JSON or wrong file location. Restart the client and check MCP logs |
| `memory not enabled` | Run `memory link` and check `memory.enabled` and `memory.root` in `.pipeline/config.json` |
| Search always empty | Run `pipeline-kit memory index .`, then try `memory_list_slugs` first |
| Results from the wrong project | `--project` points at another repo. Fix the absolute path |

CLI commands are listed in the [CLI reference](/docs/reference/cli#memory). The package README at `packages/pipeline-kit-memory/README.md` has the full detail.
