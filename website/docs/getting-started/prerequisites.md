---
title: Prerequisites
description: Python 3.11+, uv or pipx, and an optional IDE.
---

## Required

| Tool | Why |
|------|-----|
| **Python 3.11+** | The `pipeline-kit` CLI and pack loader |
| **uv** or **pipx** | Install the CLI as a user tool |

The CLI requires **Python 3.11+** and the `cryptography` package (pulled in with
`pipeline-kit`). You do not need Node.js for the kit itself.

## Optional, by feature

| You want | Also install |
|----------|----------------|
| Cursor adapter | Cursor, and open the **project folder** as workspace root |
| Claude Code adapter | Claude Code CLI |
| GitHub adapter | Copilot / GitHub agent hooks as documented for that IDE |
| Graphify plugin | Graphify CLI (`uv tool install graphifyy`) |
| Archify plugin | GitHub CLI **v2.90+** (`gh skill`), **Node.js 18+**. Chrome is optional for visual-check |
| Agent-run observability | A Langfuse project and `LANGFUSE_*` keys in the environment |

## Documentation site (this folder)

To preview these docs locally you need **Node.js 18+**, only inside `website/`. That is independent of the kit CLI.

```bash
cd website
npm install
npm start
```

## Network

`uv tool install git+<repo-url>` needs access to the kit repository. A local clone can use `./install.sh` instead.
