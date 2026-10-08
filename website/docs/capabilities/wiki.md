---
title: Wiki / agent memory
description: Pack lesson wiki vs monorepo codebase wiki under wiki/codebase.
---

There are **two** wiki-style trees. Do not mix them.

## Pack lesson wiki (`.pipeline/wiki/`)

The pack wiki is **agent memory**: reusable lessons from past runs. It is not the QA knowledge overlay and not this documentation site.

After install it lives at `.pipeline/wiki/`. The parent or specialist matches **triggers** against the current request and reads **only** the linked page.

### Index (shipped)

| Triggers (any match) | Page |
|----------------------|------|
| Tracker issue key; which workflow; bug vs story vs epic | Orchestration and tracker intake |
| `CHANGE_CLASS`; micro vs minor vs feature | Change class |
| PM first gate; nested children; waves | PM and multi-spec |
| `pipeline-state.json`; slim handoff | Slim handoffs |
| Architect; planning `signoff-*.md` | Architect and sign-off |
| Telemetry contract; `EVENTS: none` | Telemetry extraction |
| `deploy-local.sh`; port in use | Reuse listeners |
| Hooks not loading; external portal HITL | IDE hooks |
| Agent-run traces; Langfuse | Agent observability |
| Skip retro; `NO_NEW_PAGE` | Retro after devops |
| Visible copy grep misses | UI copy split |
| test-strategy; FEATURE_SIGNOFF | Test layers |
| Interrupted Task; missing HANDOFF | Interrupted Task |

Human-oriented versions of those lessons are under [Troubleshooting](/docs/troubleshooting).

### After retro

Retro may add `.pipeline/wiki/{slug}.md` and one row on `INDEX.md`. Default is a wiki page, not a new always-on rule. `NO_NEW_PAGE` is still a successful retro. Do not store customer incidents with secrets.

## Codebase wiki (`wiki/codebase/`)

Monorepo **product knowledge** for agents and humans: per-module Graphify graphs and handbooks.

| Path | Role |
|------|------|
| `.pipeline/docs-modules.yaml` | Human-owned module inventory |
| `wiki/codebase/INDEX.md` | Module router table |
| `wiki/codebase/modules/{id}/` | `README.md`, optional `security.md`, `graph/graph.json` |
| `wiki/codebase/system/` | Cross-module architecture after merge |
| `wiki/codebase/runs/` | Extract manifests |

CLI: `pipeline-kit docs …`. Workflows: [large-codebase-docs](/docs/workflows/large-codebase-docs), [module-security-review](/docs/workflows/module-security-review), [system-architecture](/docs/workflows/system-architecture).
