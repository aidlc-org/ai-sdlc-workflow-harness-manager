---
title: Module security review
description: Per-module security.md from wiki/codebase graphs. Not a full AppSec product.
---

`module-security-review` writes **observed vs inferred** security notes per module under `wiki/codebase/modules/{id}/security.md`.

## When to use

**Module security review**, monorepo security notes, or `WORKFLOW: module-security-review`.

## Parent procedure

1. Require `.pipeline/docs-modules.yaml` and module graphs (run `docs extract-modules` if missing).
2. Spawn **one** `module-security-agent` per enabled module with a graph.
3. `pipeline-kit docs link-index` so INDEX shows the security column.

Not a penetration test. No secrets in output. Not feature-development Architect.
