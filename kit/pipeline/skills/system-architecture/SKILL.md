---
name: system-architecture
description: >-
  Cross-module architecture under wiki/codebase/system using merged or
  per-module graphs and module handbooks. Not feature-development Architect.
---

# System architecture (monorepo)

| Attribute | Value |
|-----------|--------|
| Type | Skill |
| Audience | The named agent, or the parent when this file is on the allowlist |
| Adapt | Requires docs-modules.yaml and module graphs (and preferably module README docs). |

## Parent

1. Loader `--workflow system-architecture --step parent`.
2. Require `.pipeline/docs-modules.yaml` and at least two module graphs (or one system graph).
3. If module graphs missing: `pipeline-kit docs extract-modules`.
4. Prefer `pipeline-kit docs merge-modules` → `wiki/codebase/system/graph/graph.json`. If merge fails, continue with per-module graphs + INDEX only and note the gap.
5. Spawn **one** `system-architect-agent` Task.
6. `pipeline-kit docs link-index` (and optional `docs link-agents` after user approve).

## Specialist

Write `wiki/codebase/system/README.md` and optional `architecture.md` from the template. Cross-link module docs under `wiki/codebase/modules/`.

## Anti-patterns

Replacing module docs · inventing a merged graph by hand · writing into `.pipeline/wiki/` · full feature ladder.
