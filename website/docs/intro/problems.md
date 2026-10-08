---
title: Problems we solve
description: Operating-model failures Pipeline Kit removes — from context explosion to fleet governance — each linked to a component and cookbook.
---

Teams already use coding agents. What they lack is a **repeatable operating model** for those agents.

## 1. Context explosion

If every skill, agent brief, rule, and wiki page lives under `.cursor/` (or `.claude/`), the IDE auto-discovers them. Every turn loads far more than the current step needs. Cost and quality both degrade as the pack grows.

**Kit answer:** process files sit in `.pipeline/`. The IDE folder holds only `run-workflow`. The [loader](/docs/capabilities/loader) writes `allowed_reads` for the current specialist.

**Cookbook:** [First feature end-to-end](/docs/cookbooks/first-feature)

## 2. Pipeline glued to one IDE

Process (how you plan, specify, implement, test, deploy) was mixed with editor wiring. Moving from Cursor to Claude Code, or to a repo with no AI folder, meant copying and rewriting the whole tree.

**Kit answer:** thin [adapters](/docs/getting-started/ide-adapters). Cursor, Claude Code, GitHub, and `--ide none` get the same pack. Only the adapter path changes.

**Cookbook:** [First feature end-to-end](/docs/cookbooks/first-feature)

## 3. One customer's process baked into another's repo

Folder names, ports, tracker projects, verify commands, and deploy targets leaked into skills. The next customer on a different stack could not reuse the pack without a surgical rewrite.

**Kit answer:** engagement overlay in [`config.json`](/docs/guides/config). Skills stay free of customer folder names and site URLs.

**Cookbook:** [First feature](/docs/cookbooks/first-feature) · [Add a custom workflow](/docs/cookbooks/add-workflow)

## 4. No productized install

"Copy `.cursor` from last year's repo" does not scale. Architects need project install, user install, and a path to org-wide defaults — with a clear override order.

**Kit answer:** `pipeline-kit init` (project), `pipeline-kit setup` (user). Project pack wins at runtime. See [Where you can install](/docs/getting-started/install-scopes).

**Cookbook:** [First feature end-to-end](/docs/cookbooks/first-feature)

## 5. Every ask became the same ladder

A "how does tax work?" question should not start PM → BA → developer. A bug should not run a full feature plan. Without a **workflow** as a first-class object, the parent invents a new procedure each time.

**Kit answer:** named workflows (`ask`, `feature-development`, `jira-bug`, …) with a chain and a file allowlist.

**Component:** [Workflows](/docs/capabilities/workflows)  
**Cookbook:** [First feature](/docs/cookbooks/first-feature)

## 6. Hard to add a process

A new customer wants "architecture review" or "release checklist." That should be a new workflow JSON + skill + a config chain — not a new platform.

**Kit answer:** [add a workflow](/docs/cookbooks/add-workflow). Different customers can enable different workflows from the same pack.

**Component:** [Extensions](/docs/capabilities/extensions)

## 7. Cannot structure, reuse, and govern pipelines across projects

Enterprises have agent pipelines but struggle to standardize them, drop them into the next engagement quickly, and keep control of what is enabled where.

**Kit answer:** portable pack + config overlay + [planning gates](/docs/capabilities/planning-gates) + [enterprise portal](/docs/capabilities/portal) (pull-only fleet reports).

**Component:** [Governance](/docs/components/governance)  
**Cookbook:** [Enterprise governance and portal](/docs/cookbooks/enterprise-governance)

## 8. Weak telemetry and evals for agent work

Teams cannot tell whether a harness change improved agent output. Product analytics and agent-run traces get confused.

**Kit answer:** [agent-run observability](/docs/capabilities/observability) (ledger → Langfuse scores) separate from [app telemetry](/docs/capabilities/telemetry); product tests stay on [your runners](/docs/guides/tests).

**Component:** [Testing and evaluation](/docs/components/testing)  
**Cookbook:** [Observability, eval, and testing](/docs/cookbooks/observability-eval-testing)

## 9. Small teams need extend + memory without enterprise ceremony

Solo and small teams want custom harnesses and a searchable history of past feature artifacts, not only a wiki of short lessons.

**Kit answer:** extensions and workflows stay open; [memory package](/docs/components/packages) links an external artifact bank + MCP.

**Cookbook:** [Memory bank for small teams](/docs/cookbooks/memory-bank) · [Add a custom workflow](/docs/cookbooks/add-workflow)

## 10. QA and architecture tools stay bolted on

Code-graph extraction and interactive architecture HTML should not be mandatory on every `init`, but they should install cleanly when needed.

**Kit answer:** opt-in [knowledge](/docs/capabilities/knowledge) + [plugins](/docs/capabilities/plugins) (Graphify, Archify).

**Cookbook:** [Knowledge and plugins](/docs/cookbooks/knowledge-and-plugins)

## Scaling contract

What you take to the next customer: the **kit**. What you change per customer: `AGENTS.md`, `config.json`, deploy/test runbooks.

| Next step | Link |
|-----------|------|
| Component map | [Components overview](/docs/components/overview) |
| Tutorials | [Cookbooks](/docs/cookbooks/) |
| How the pieces fit | [How it works](/docs/intro/how-it-works) |