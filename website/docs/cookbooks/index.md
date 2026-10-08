---
title: Cookbooks
description: Step-by-step tutorials that map real problems to Pipeline Kit components.
slug: /cookbooks/
---

Cookbooks are **use-case tutorials**. Each one starts from a problem, walks through commands and checks, and points at the components you used.

For product definitions and deep reference, use [Components](/docs/components/overview) and [Reference](/docs/reference/cli).

## Problem → cookbook

| Problem | Cookbook | Components |
|---------|----------|------------|
| Need a repeatable harness on a new app repo | [First feature end-to-end](/docs/cookbooks/first-feature) | Workflows, capabilities (loader, wiki) |
| Prefer CLI-driven sealed graphs over markdown pack | [Orchestrator mode first run](/docs/cookbooks/orchestrator-first-run) | Two kits, workflows |
| Customer wants a process the pack does not ship | [Add a custom workflow](/docs/cookbooks/add-workflow) | Workflows, extensions |
| QA needs a code graph and architecture HTML | [Knowledge and plugins](/docs/cookbooks/knowledge-and-plugins) | Knowledge, plugins |
| Cannot tell if agent runs are getting better | [Observability, eval, and testing](/docs/cookbooks/observability-eval-testing) | Observability, testing |
| Several repos; want one searchable artifact bank | [Memory bank for small teams](/docs/cookbooks/memory-bank) | Packages (memory) |
| Fleet control, licenses, planning sign-off | [Enterprise governance and portal](/docs/cookbooks/enterprise-governance) | Governance, portal, gates |

## Suggested order

1. [First feature](/docs/cookbooks/first-feature) — if you are new  
2. [Add a workflow](/docs/cookbooks/add-workflow) or [Orchestrator first run](/docs/cookbooks/orchestrator-first-run) — when you extend or switch kits  
3. Opt-ins: [Knowledge and plugins](/docs/cookbooks/knowledge-and-plugins), [Obs / testing](/docs/cookbooks/observability-eval-testing), [Memory](/docs/cookbooks/memory-bank)  
4. [Enterprise governance](/docs/cookbooks/enterprise-governance) — when you need fleet and license control  

## Also useful

Adaptation how-tos that are not full tutorials live under [Guides](/docs/guides/agents-md): `AGENTS.md`, `config.json`, local deploy, gitignore, what not to edit.
