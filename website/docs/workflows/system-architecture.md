---
title: System architecture
description: Cross-module architecture under wiki/codebase/system.
---

`system-architecture` produces **cross-module** docs at `wiki/codebase/system/` from merged or per-module graphs plus module handbooks.

## When to use

**System architecture** for the monorepo, cross-module map, or `WORKFLOW: system-architecture`.

## Parent procedure

1. Require `docs-modules.yaml` and module graphs (extract if needed).
2. Prefer `pipeline-kit docs merge-modules` → `wiki/codebase/system/graph/graph.json`.
3. Spawn **one** `system-architect-agent` → `wiki/codebase/system/README.md` (optional `architecture.md`).
4. Refresh INDEX; optional `docs link-agents`.

This is **not** the feature-class `architect-agent` on the delivery ladder.
