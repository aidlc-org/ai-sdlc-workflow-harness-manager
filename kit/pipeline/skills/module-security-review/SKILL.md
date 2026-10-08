---
name: module-security-review
description: >-
  Security-oriented review per monorepo module using wiki/codebase graphs.
  Writes security.md. Not a full AppSec product and not the feature ladder.
---

# Module security review

| Attribute | Value |
|-----------|--------|
| Type | Skill |
| Audience | The named agent, or the parent when this file is on the allowlist |
| Adapt | Uses the same docs-modules.yaml inventory as large-codebase-docs. |

## Parent

1. Loader `--workflow module-security-review --step parent`.
2. Require `.pipeline/docs-modules.yaml`.
3. Ensure module graphs exist: if missing, run `pipeline-kit docs extract-modules` (CLI parallel extract).
4. For each enabled module with a graph, spawn **one** `module-security-agent` (sequential or small batches).
5. `pipeline-kit docs link-index` so INDEX shows security column.
6. Summarize findings; do not claim certified penetration test.

## Specialist

Write `wiki/codebase/modules/{id}/security.md` from [assets/security-template.md](assets/security-template.md). Use graph + lockfiles/manifests when present. Label **observed** vs **inferred**. No secrets in output.

## Anti-patterns

Parallel graph agents · inventing CVEs · writing under `.pipeline/wiki/` · editing production source to “fix” security.
