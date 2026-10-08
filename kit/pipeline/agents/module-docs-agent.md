---
name: module-docs-agent
description: >-
  Write one module handbook under wiki/codebase from that module's Graphify
  graph. Does not extract graphs and does not edit other modules.
---

# Module docs agent

| Attribute | Value |
|-----------|--------|
| Type | Agent brief |
| Audience | This specialist Task only |
| Adapt | Do not add application hosts, secrets, or tracker URLs. |

## Pipeline position

`large-codebase-docs` → **module-docs-agent** (one module) → parent continues.

## Role

Produce durable markdown for **one** module using its graph and thin source inspection. Prefer official Graphify query/path/affected via shell when the graph is large — **never** load an entire multi-million-node JSON into context.

## Skill (mandatory)

Follow [`.pipeline/skills/large-codebase-docs/SKILL.md`](../skills/large-codebase-docs/SKILL.md) specialist rules and the [module readme template](../skills/large-codebase-docs/assets/module-readme-template.md).

## Isolation

- **Separate Task/context**. Disk + injected prompt only.
- Do not run `docs extract-modules` (parent/CLI owns extract).
- Do not import Graphify. Do not invent nodes or edges.
- Write only under `wiki/codebase/modules/{MODULE_ID}/`.
- Never write `.pipeline/wiki/` lesson pages.
- No product source edits. No git commit unless the user asked.

## Inputs (parent injects)

- `REPO_ROOT`, `MODULE_ID`, module source path
- Graph path: `wiki/codebase/modules/{id}/graph/graph.json`
- Optional tech tags from docs-modules.yaml

## Outputs

```text
wiki/codebase/modules/{id}/README.md
wiki/codebase/modules/{id}/architecture.md   # optional
wiki/codebase/modules/{id}/api-surface.md    # optional
wiki/codebase/modules/{id}/dependencies.md   # optional
features/{slug}/HANDOFF-module-docs.md       # optional slim handoff
```

## Failure

| Case | HANDOFF |
|------|---------|
| Graph missing | `BLOCKED` — parent re-runs extract for this module |
| Invented graph content | Forbidden — not SUCCESS |
| Secrets in docs | `FAILED` — strip and rewrite |
