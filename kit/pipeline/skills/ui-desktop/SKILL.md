---
name: ui-desktop
description: >-
  Load only when ui-designer-agent U1 classifies a desktop / workstation /
  multi-pane surface. Menus, keyboard, and dense tool layouts. Do not use
  for marketing landing pages or native installers.
---

# UI — desktop

| Attribute | Value |
|-----------|--------|
| Type | Skill |
| Audience | ui-designer-agent after U1 selects desktop |
| Adapt | Do not add a product, host, or OS chrome brand. |

Use this pack for **multi-pane tools** (workstations, consoles, editors).

## Decide

| Choice | Default unless PRD says otherwise |
|--------|-----------------------------------|
| Shell | App menu + toolbar + 2–3 panes |
| Keyboard | Document shortcuts for search, new, save, close pane |
| Selection | Multi-select in lists; inspector pane for the selection |
| Density | Comfortable (8px) unless ERP skill is also loaded |
| Windows | One primary window; modal only for destructive confirm |

## Must show in mockups

- Menu or command entry for the primary verb (not icon-only)
- Focus order across panes
- Split: list | detail (or nav | canvas | inspector)
- Empty inspector when nothing is selected

## Do not

Design a phone bottom-tab bar as the only nav · hide all actions in unlabeled
icons · require a pointing device with no keyboard path.
