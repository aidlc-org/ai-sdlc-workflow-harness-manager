---
title: Packages
description: Installable extras — pipeline-kit-assess and pipeline-kit-memory — that extend the core CLI without forking the pack.
---

**Packages** are separate installable products under `packages/` in the kit repository. Each has its own `pyproject.toml`. The core `pipeline-kit` CLI grows a subcommand only when the extra is installed into the **same environment** as the CLI.

They are free of the enterprise license gate unless a specific command documents otherwise. See [Licensing](/docs/reference/licensing).

## Shipped packages

| Package | CLI surface | Extra | What it solves |
|---------|-------------|-------|----------------|
| **pipeline-kit-assess** | `pipeline-kit scan` | `.[assess]` | Licensed / structured repo assessment for intake and governance |
| **pipeline-kit-memory** | `pipeline-kit memory …` + `pipeline-memory-mcp` | `.[memory]` | External feature-artifact bank, FTS search, IDE MCP |

Layout detail: [Repository layout — Packages](/docs/intro/repo-layout#packages).

## Install pattern

Match how you installed the CLI (`uv tool`, editable checkout, etc.):

```bash
cd /path/to/pipeline-kit-checkout
uv tool install -e ".[memory]"    # or ".[assess]"
pipeline-kit memory doctor .      # or: pipeline-kit scan --help
```

`pipeline-kit init` does **not** install packages.

## When to use which

| Need | Package | Cookbook |
|------|---------|----------|
| Shared archive of `features/{slug}/` across repos; agent search | Memory | [Memory bank](/docs/cookbooks/memory-bank) |
| Structured assessment / scan of a codebase | Assess | [CLI reference](/docs/reference/cli) + package README |
| Short reusable lessons inside the project | Neither — use the [wiki](/docs/capabilities/wiki) | — |

## Deep dives

- [Memory bank and MCP](/docs/capabilities/memory)
- [Enterprise portal](/docs/capabilities/portal) reports whether assess/memory are installed (fleet visibility)
- Package READMEs in the kit clone: `packages/pipeline-kit-memory/`, `packages/pipeline-kit-assess/`

## Next

- [Components overview](/docs/components/overview)
- [Memory bank cookbook](/docs/cookbooks/memory-bank)
- [Capabilities overview](/docs/capabilities/overview)
