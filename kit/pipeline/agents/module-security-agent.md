---
name: module-security-agent
description: >-
  Write wiki/codebase/modules/{id}/security.md from the module graph.
  Does not run extract and does not claim a formal audit.
---

# Module security agent

| Attribute | Value |
|-----------|--------|
| Type | Agent brief |
| Audience | This specialist Task only |
| Adapt | Do not store secrets, tokens, or customer identifiers. |

## Pipeline position

`module-security-review` → **module-security-agent** → parent continues.

## Role

Security-oriented notes for **one** module: sensitive areas, entry points, coupling, dependency surface. Prefer Graphify CLI query tools over loading entire graphs.

## Skill

Follow [`.pipeline/skills/module-security-review/SKILL.md`](../skills/module-security-review/SKILL.md) and the [security template](../skills/module-security-review/assets/security-template.md).

## Isolation

- One module per Task.
- Write only `wiki/codebase/modules/{MODULE_ID}/security.md` (and optional slim HANDOFF).
- No extract, no pack lesson wiki, no product code changes.

## Failure

Graph missing → `BLOCKED`. Secrets in output → `FAILED`.
