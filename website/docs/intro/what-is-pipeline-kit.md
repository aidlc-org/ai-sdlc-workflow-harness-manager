---
title: What is Pipeline Kit
description: A portable operating model for coding agents — six components, two kits, and cookbooks for real use cases.
---

Pipeline Kit is an **open platform for running coding agents as a repeatable factory**: named workflows, thin IDE adapters, opt-in extras, and an engagement overlay you take from customer to customer.

It ships **two kits**. You pick one per project at `init`.

| Kit | What you install | How work runs |
|-----|------------------|---------------|
| **Kit mode** (default) | The markdown pack → `.pipeline/` | IDE `run-workflow` + loader allowlist |
| **Orchestrator mode** | The Python engine in the wheel | `pipeline-kit run` / `approve` / `resume` |

Same first-party workflow names either way: `ask`, `feature-development`, Jira/GitHub intake, and more. The pack is not tied to a product, a language, or an editor.

:::info Handbook vs this site
This site is the guided product manual. After `pipeline-kit init`, the adaptation contract is copied to `.pipeline/docs/CUSTOMER-GUIDE.md` in the target repo. Keep that file as the in-repo handbook; use these pages to learn the product.
:::

## Takeaways

- What problems does Pipeline Kit remove from agentic delivery?
- What are the six components you can use and extend?
- When do you choose kit mode vs orchestrator mode?
- Where do tutorials (cookbooks) start?

## Six components

| Component | Role |
|-----------|------|
| [Workflows](/docs/capabilities/workflows) | Named procedures with chains, change classes, and allowlists |
| [Packages](/docs/components/packages) | Installable extras — assess scan, memory bank + MCP |
| [Plugins](/docs/capabilities/plugins) | Opt-in wrappers for Graphify, Archify, and related tools |
| [Capabilities](/docs/capabilities/overview) | Modes, extensions, knowledge, obs, wiki, loader, flags, gates |
| [Testing & evaluation](/docs/components/testing) | Your product runners + agent-run scores |
| [Governance](/docs/components/governance) | Planning gates, licensing, enterprise portal |

Full map: [Components overview](/docs/components/overview).

## What problems does it solve?

Teams already use coding agents. What they lack is a **portable operating model** — structure, reuse, telemetry, and governance across projects.

→ [Problems we solve](/docs/intro/problems) (each problem links to a cookbook)

## Why Pipeline Kit?

- **Process as files.** Skills, allowlists, and config are versioned with the same rigor as code — not trapped in one chat thread.
- **IDE-agnostic adapters.** Cursor, Claude Code, GitHub, or none; the pack stays the same.
- **Extend, don't fork.** New customer process = workflow or extension, not a copy of last year's `.cursor` tree.
- **Opt-in depth.** Knowledge, plugins, memory, observability, and portal stay off until you turn them on.
- **Two runtimes, one vocabulary.** Markdown pack or Python engine; same workflow names.
- **Enterprise-ready path.** Gates, licenses, and a pull-only portal for fleet visibility.

## What lands after install

**Kit mode** (default):

| Path | Role |
|------|------|
| `.pipeline/` | Workflows, skills, agent briefs, rules, wiki, loader, hooks |
| `.pipeline/config.json` | This engagement: chains, tracker, verify, deploy |
| `.pipeline/docs/CUSTOMER-GUIDE.md` | Copied handbook |
| `.pipeline/docs/OBSERVABILITY.md` | Agent-run observability handbook |
| IDE folder (`run-workflow` only) | Thin adapter skill |

**Orchestrator mode** does **not** copy `agents/`, `skills/`, `loader/`, or `workflows/`. The chain lives in the wheel. You still get `config.json`, docs, hooks, and `features/{slug}/`.

## Get started

1. [Install the CLI](/docs/getting-started/install-cli)
2. [First feature cookbook](/docs/cookbooks/first-feature) — init → ask → small change
3. Or jump to [Cookbooks](/docs/cookbooks/) for your use case

Also: [How it works](/docs/intro/how-it-works) · [Two kits](/docs/capabilities/modes) · [Repository layout](/docs/intro/repo-layout)