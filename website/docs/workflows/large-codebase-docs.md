---
title: Large codebase docs
description: Module handbooks under wiki/codebase via Graphify extract and module-docs-agent.
---

`large-codebase-docs` documents a **monorepo by module**. It is not the feature ladder and not the pack lesson wiki at `.pipeline/wiki/`.

## When to use

In the IDE: **document the large codebase**, **monorepo docs**, or `WORKFLOW: large-codebase-docs`.

## Prerequisites

1. Graphify on PATH (official CLI; pipeline-kit never imports the Graphify package).
2. Human-owned inventory: `.pipeline/docs-modules.yaml`  
   `pipeline-kit docs init-modules` writes a template and `wiki/codebase/` skeleton.
3. Each module row: stable `id`, display `name`, repo-relative `path`, optional `tech`, `enabled`.

## Parent procedure

1. Loader `--workflow large-codebase-docs --step parent`.
2. Require `docs-modules.yaml` (stop if empty / missing paths).
3. **`pipeline-kit docs extract-modules`** — parallel official extract **inside the CLI** (not N graph agents). Graphs land at `wiki/codebase/modules/{id}/graph/graph.json`.
4. For each successful module, spawn **one** `module-docs-agent` → `wiki/codebase/modules/{id}/README.md`.
5. `pipeline-kit docs link-index` → `wiki/codebase/INDEX.md`.
6. On user approve: `pipeline-kit docs link-agents` (marked section in `AGENTS.md`).

Optional later: `docs merge-modules` and workflow [`system-architecture`](/docs/workflows/system-architecture). Security notes: [`module-security-review`](/docs/workflows/module-security-review).

## Anti-patterns

Inventing graphs · one LLM pass over the whole monorepo · writing under `.pipeline/wiki/` · parallel agents that each run Graphify.
