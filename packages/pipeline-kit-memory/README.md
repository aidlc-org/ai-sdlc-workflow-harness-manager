# pipeline-kit-memory

External **artifact memory bank** for pipeline-kit: keep `features/{slug}/`
artifacts in a separate git repo, index them with SQLite FTS5, and expose
search over a **stdio MCP server** that you register in your IDE/agent client.

## Contents

1. [When to use this](#when-to-use-this)
2. [Step 1 — Install into the same CLI](#step-1--install-into-the-same-cli)
3. [Step 2 — Product already has `.pipeline/`](#step-2--product-already-has-pipeline)
4. [Step 3 — Link a memory bank](#step-3--link-a-memory-bank)
5. [Step 4 — Import, index, smoke-test](#step-4--import-index-smoke-test)
6. [Step 5 — MCP (optional)](#mcp-server--what-the-user-must-do)
7. [Layout](#layout)
8. [Config](#config-pipelineconfigjson)
9. [CLI reference](#cli-reference-non-mcp)
10. [Troubleshooting](#troubleshooting)

## When to use this

Skip this package if a single product repo and local `features/{slug}/` is enough.

Use it when:

- several product repos should share one artifact archive
- agents need FTS over past requests, decisions, and handoffs
- you do not want those artifacts committed in the product repo

`pipeline-kit init` does **not** install memory. It is an optional extra.

## Step 1 — Install into the same CLI

`pipeline-kit memory --help` only parses flags. Real commands (`status`,
`doctor`, `link`, …) import `pipeline_memory` from the **same environment as
`pipeline-kit`**. If the CLI is a `uv tool` binary (`~/.local/bin/pipeline-kit`
on Windows too), install the extra with `uv tool`, not `pip` into system Python.

From the **pipeline-kit checkout** (this repo, not the product):

```bash
cd /path/to/pipeline-kit-checkout
uv tool install -e ".[memory]"
```

That is the same pattern as `.[orchestrator]` and `.[assess]`.

Confirm the extra is in the CLI you actually run:

```bash
command -v pipeline-kit        # Windows: Get-Command pipeline-kit
pipeline-kit memory --help
pipeline-kit memory doctor .
```

`doctor` / `status` may still exit 1 until you link a bank. The line
`pipeline-kit-memory is not installed` must be gone.

| How `pipeline-kit` was installed | How to add memory |
|----------------------------------|-------------------|
| `uv tool install …` or `./install.sh` | `uv tool install -e ".[memory]"` from this checkout |
| Same venv as an editable kit install | `pip install -e packages/pipeline-kit-memory -e .` |

`pip install -e ".[memory]"` can fail until the extra resolves as a path
dependency. Prefer `uv tool install -e ".[memory]"` when the CLI is a uv tool.

This adds:

| Entry point | Purpose |
|-------------|---------|
| `pipeline-kit memory …` | CLI (link, index, search, mcp, …) |
| `pipeline-memory-mcp` | Stdio MCP server binary (for IDE MCP config) |

## Step 2 — Product already has `.pipeline/`

From the **product** root (customer app), not the kit checkout:

```bash
cd /path/to/your-product
pipeline-kit init --ide cursor    # skip if already initialized
pipeline-kit doctor --ide cursor
```

## Step 3 — Link a memory bank

Still in the product root. The bank path is a separate git folder (created
if missing):

```bash
pipeline-kit memory link /abs/path/to/my-memory-bank .
# multi-product shared bank:
# pipeline-kit memory link /abs/path/to/org-bank . --project-id my-app --layout namespaced
```

Link writes `memory` into `.pipeline/config.json`. The MCP server reads that
config via `--project` (the product path, not the bank).

## Step 4 — Import, index, smoke-test

```bash
# Optional: copy existing local features/ into the bank
pipeline-kit memory import-local .

# Required before search returns hits (re-run after artifact changes)
pipeline-kit memory index .

pipeline-kit memory search "architecture" . --limit 5
pipeline-kit memory status .
pipeline-kit memory doctor .
```

**Indexing is required** before search tools return hits. MCP does not
re-index on its own.

## Layout

| Mode | Path |
|------|------|
| Flat (default) | `{memory.root}/features/{slug}/…` |
| Namespaced (`--project-id`) | `{memory.root}/projects/{id}/features/{slug}/…` |

Run state stays in the product project under `.pipeline/state/`.
The FTS index lives at `{memory.root}/.memory/index.sqlite` (gitignored in the bank).

## Config (`.pipeline/config.json`)

Written/updated by `memory link`:

```json
{
  "memory": {
    "enabled": true,
    "root": "/abs/path/to/memory-bank",
    "project_id": "my-app",
    "layout": "namespaced",
    "index": { "engine": "fts5", "path": ".memory/index.sqlite" },
    "mcp": { "name": "pipeline-memory", "allow_writes": false }
  }
}
```

| Field | Role |
|-------|------|
| `enabled` | Must be `true` for CLI/MCP to use the bank |
| `root` | Absolute path to the memory-bank git root |
| `layout` / `project_id` | Flat vs namespaced feature paths |
| `mcp.name` | Logical server name (documentation / discovery) |
| `mcp.allow_writes` | Reserved; server is read-oriented today |

---

## MCP server — what the user must do

The memory package does **not** auto-register with Cursor, VS Code, Claude, or
Copilot. **Each user (or team template) adds an MCP server entry** in their
client config, then restarts/reloads the client so the tools appear.

### What to put in the MCP config

| Setting | Value | Notes |
|---------|--------|--------|
| Transport | **stdio** | One process per session; no HTTP URL |
| Command | `pipeline-memory-mcp` | Or `python` / `pipeline-kit` alternatives below |
| Args | `--project`, `<absolute path to product repo>` | Repo that contains `.pipeline/config.json` with `memory` |
| Optional arg | `--root`, `<memory bank path>` | Overrides `memory.root` from config |
| Working directory | Product repo (optional) | Helpful if you use relative `--project .` |

The server resolves the bank from:

1. `--root` if passed, else  
2. `memory.root` in `<project>/.pipeline/config.json`

So **`--project` must point at the product checkout you linked**, not at the
memory-bank folder alone.

### Recommended command (after install on PATH)

```text
command: pipeline-memory-mcp
args:    --project  C:/path/to/your-product-repo
```

Equivalent launches (pick one style and stick to it):

```bash
# A) Console script (best for IDE config)
pipeline-memory-mcp --project /abs/path/to/product

# B) Via pipeline-kit CLI
pipeline-kit memory mcp /abs/path/to/product

# C) Module form (package installed in that Python)
python -m pipeline_memory.mcp_server --project /abs/path/to/product
```

Prefer (A) after `pip install -e …`. Use (C) in IDE config if the console
script is not on PATH — set `command` to the full `python.exe` path and put
`-m`, `pipeline_memory.mcp_server`, `--project`, and the product path in `args`.

### Cursor

Create or edit **`.cursor/mcp.json`** in the product project (or your global
Cursor MCP settings):

```json
{
  "mcpServers": {
    "pipeline-memory": {
      "command": "pipeline-memory-mcp",
      "args": [
        "--project",
        "C:/path/to/your-product-repo"
      ]
    }
  }
}
```

Use a **full absolute path** for `--project`. Restart Cursor (or reload MCP).
You should see server `pipeline-memory` and tools listed below.

If `pipeline-memory-mcp` is not on PATH, use the Python executable explicitly:

```json
{
  "mcpServers": {
    "pipeline-memory": {
      "command": "C:/Users/YOU/AppData/Local/Programs/Python/Python312/python.exe",
      "args": [
        "-m",
        "pipeline_memory.mcp_server",
        "--project",
        "C:/path/to/your-product-repo"
      ]
    }
  }
}
```

(`python -m pipeline_memory.mcp_server` works when the package is installed in
that interpreter.)

### VS Code / GitHub Copilot Chat (MCP)

Add a stdio server in your MCP configuration (User or Workspace
`mcp.json`, depending on your VS Code MCP support):

```json
{
  "servers": {
    "pipeline-memory": {
      "type": "stdio",
      "command": "pipeline-memory-mcp",
      "args": [
        "--project",
        "C:/path/to/your-product-repo"
      ]
    }
  }
}
```

Schema keys can vary slightly by VS Code version (`mcpServers` vs `servers`).
Keep **command + args + absolute `--project`** the same.

### Claude Desktop

Edit the Claude Desktop config file (e.g. `%APPDATA%\Claude\claude_desktop_config.json`
on Windows) and add:

```json
{
  "mcpServers": {
    "pipeline-memory": {
      "command": "pipeline-memory-mcp",
      "args": [
        "--project",
        "C:/path/to/your-product-repo"
      ]
    }
  }
}
```

Restart Claude Desktop after saving.

### Claude Code / other stdio hosts

Same pattern: register a stdio MCP server whose command is
`pipeline-memory-mcp` (or `pipeline-kit memory mcp`) with
`--project <product-root>`.

### After configuration — run / verify

1. **Restart** the IDE or MCP host so it spawns the server.  
2. Confirm tools are listed: `memory_search`, `memory_why`, `memory_get`,
   `memory_list_slugs`, `memory_list_files`.  
3. Call `memory_list_slugs` (no args) — should return feature slugs from the bank.  
4. Call `memory_search` with `{ "query": "architecture", "limit": 5 }`.  
5. If empty: run `pipeline-kit memory index .` in the product repo, then retry.  
6. Optional CLI parity (no IDE):  
   `pipeline-kit memory search "architecture" .`  
   or foreground server (stdio; usually only for debugging):  
   `pipeline-kit memory mcp .`

You do **not** normally “run MCP” in a terminal for daily use — the **IDE
starts the process** when chat needs a tool. Use the terminal only to
link/index/search or to debug the stdio process.

### MCP tools (API)

| Tool | Arguments | Purpose |
|------|-----------|---------|
| `memory_search` | `query` (required), optional `slug`, `kind`, `limit` | FTS over indexed chunks |
| `memory_why` | `query`, optional `slug`, `limit` | Prefer decision / request / handoff / architecture docs |
| `memory_get` | `path` **or** `slug` + `rel` | Read one artifact file |
| `memory_list_slugs` | _(none)_ | List feature slugs in the bank |
| `memory_list_files` | `slug` | List files under one feature |

Writes from MCP are not exposed; bank updates go through normal git +
`memory index`.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Server won’t start / command not found | Install with `uv tool install -e ".[memory]"`; use full path to `pipeline-memory-mcp` or `python.exe` from **that** env |
| `pipeline-kit memory --help` works, `status`/`doctor` say not installed | Extra is in a different Python than the CLI. Re-run `uv tool install -e ".[memory]"` from the kit checkout; do not `pip install` into system Python |
| Tools missing in IDE | Config JSON invalid; wrong file location; restart client; check MCP logs |
| `memory not enabled` / empty bank | Run `memory link` and check `.pipeline/config.json` → `memory.enabled` + `root` |
| Search always `[]` | Run `memory index .`; query terms must appear in artifacts; try `memory_list_slugs` first |
| Wrong project’s features | `--project` points at another repo; fix absolute path in MCP config |
| PATH has old `pipeline-kit` | Prefer `pipeline-memory-mcp` from the env where you installed this extra, or call via that Python |

### Team checklist (copy into onboarding)

1. From the kit checkout: `uv tool install -e ".[memory]"` (same CLI as `pipeline-kit`).
2. In the product repo: `memory link`, `import-local` (if needed), `memory index`.
3. Add **stdio MCP** entry with `pipeline-memory-mcp` and `--project <abs product path>`.
4. Restart IDE → verify `memory_list_slugs` / `memory_search`.
5. After large artifact changes: re-run `memory index` (MCP does not auto-reindex).

---

## CLI reference (non-MCP)

```bash
pipeline-kit memory link <bank-root> [project] [--project-id ID] [--layout flat|namespaced]
pipeline-kit memory unlink [project]
pipeline-kit memory import-local [project]
pipeline-kit memory index [project]
pipeline-kit memory search <query> [project] [--limit N] [--json]
pipeline-kit memory status [project]
pipeline-kit memory doctor [project]
pipeline-kit memory mcp [project]          # stdio server (IDE usually runs pipeline-memory-mcp instead)
```

## Package API

```python
from pipeline_memory.commands import cmd_link, cmd_index, cmd_search
from pipeline_memory.index import get_backend
from pipeline_memory.mcp_server import MemoryContext, call_tool, main
```
