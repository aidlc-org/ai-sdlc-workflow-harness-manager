---
name: ui-enhancement
description: >-
  Invoke for a UI redesign of a screen or component. Copy/label/single-button
  without new behavior is NOT this skill — use feature-development CHANGE_CLASS
  micro. New UI flows use feature-development CHANGE_CLASS feature.
---

# UI enhancement (redesign only)

| Attribute | Value |
|-----------|--------|
| Type | Skill |
| Audience | The named agent, or the parent when this file is on the allowlist |
| Adapt | Change commands or paths only in deploy and testing skills. Planning skills stay product-neutral. |

Use this skill when the user wants a **redesign** (layout, visual system, multiple components) of an **existing** screen.

**New screens or a naive app build** belong in **feature-development** `feature`: PM then `ui-designer-agent` (`ui-design` skill), not this file.

**Do not use** for “add a label”, “rename a button”, or “wire this existing control” — those are **feature-development** `micro` / `minor` ([change-routing.md](../feature-development/assets/change-routing.md)).

## Workflow

1. Confirm it is a redesign (not a micro patch). If not, stop and tell the parent to route `micro`/`minor`/`feature`.
2. Locate the UI from `REPO_ROOT` (the package the user named). Ask at most 7 clarifying questions if scope is unclear.
3. Plan: files, no new libraries unless security-reviewed. Get user approval of the plan.
4. After approval, parent still spawns **developer-agent** in a **separate Task** (do not implement in the parent). Treat as **minor** or **feature** per change-routing hard-upgrade triggers.
