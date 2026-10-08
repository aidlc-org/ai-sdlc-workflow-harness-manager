---
name: large-codebase-docs
description: >-
  Document monorepo modules under wiki/codebase using parallel Graphify extract
  (CLI) then module-docs-agent. Not the feature ladder.
---

# Large codebase documentation

| Attribute | Value |
|-----------|--------|
| Type | Skill |
| Audience | The named agent, or the parent when this file is on the allowlist |
| Adapt | Module inventory is `.pipeline/docs-modules.yaml`. Do not invent paths. |

This workflow is **not** feature-development. Do not write product specs or start PM/BA.

## Artifacts

| Path | Role |
|------|------|
| `.pipeline/docs-modules.yaml` | Human-owned module map |
| `wiki/codebase/modules/{id}/graph/graph.json` | Per-module Graphify graph |
| `wiki/codebase/modules/{id}/README.md` | Module handbook |
| `wiki/codebase/INDEX.md` | Router table |
| `wiki/codebase/runs/{run}/manifest.json` | Extract status |

Do **not** write into `.pipeline/wiki/` (pack lesson wiki).

## Parent (no specialist work inline)

1. Run the loader with `--workflow large-codebase-docs --step parent`.
2. Require `.pipeline/docs-modules.yaml`. If missing: stop with `pipeline-kit docs init-modules`, then ask the user to fill module `id` / `path` rows.
3. Run **`pipeline-kit docs extract-modules`** (optional `--workers N`). Graphs fan out **inside the CLI**, not via parallel graph agents. Wait for the process.
4. If extract reports failures, show the manifest summary. Continue only for modules with `status: ok` unless the user aborts.
5. For each successful module (sequential or batches of 2–3), spawn **one** `module-docs-agent` Task. Inject `MODULE_ID`, graph path, source `path`, and output dir `wiki/codebase/modules/{id}/`.
6. Run `pipeline-kit docs link-index`.
7. Present a short summary of modules documented. On user approve: `pipeline-kit docs link-agents`.
8. Optional later: `pipeline-kit docs merge-modules` and workflow `system-architecture`.

## Specialist work

See [module-docs-agent](../../agents/module-docs-agent.md) and [assets/module-readme-template.md](assets/module-readme-template.md).

## Anti-patterns

Importing Graphify · inventing a graph · one LLM pass over the whole monorepo · writing docs under `.pipeline/wiki/` · spawning N agents to run Graphify · promoting without human glance when the user asked for review.
