---
title: Components overview
description: The six product pillars — workflows, packages, plugins, capabilities, testing, and governance — and the problems each one addresses.
---

Pipeline Kit is one portable operating model made of **six components**. Use this page to pick the pillar you need, then drill into reference docs or a [cookbook](/docs/cookbooks/).

## Takeaways

- **Workflows** name the procedure (ask, feature ladder, tracker intake, custom graphs).
- **Packages** add installable extras (assess, memory) without bloating the core CLI.
- **Plugins** wrap open tools (Graphify, Archify) behind kit install commands.
- **Capabilities** are the always-on and opt-in surfaces: modes, knowledge, obs, wiki, loader, flags.
- **Testing & evaluation** point testers at your runners and score agent runs.
- **Governance** covers planning gates, licensing, and the enterprise portal fleet view.

## Component map

| Component | What it is | Problems it addresses | Start here |
|-----------|------------|------------------------|------------|
| [Workflows](/docs/capabilities/workflows) | Named procedures with chains, change classes, and file allowlists | One ladder for every ask; hard to reuse process across projects | [First feature cookbook](/docs/cookbooks/first-feature) |
| [Packages](/docs/components/packages) | Separate wheels: assess scan, memory bank + MCP | Enterprise extras without forking the kit; shared artifact archive | [Memory bank cookbook](/docs/cookbooks/memory-bank) |
| [Plugins](/docs/capabilities/plugins) | Graphify / Archify wrappers; install stays opt-in | Code-graph QA and architecture HTML without baking tools into init | [Knowledge and plugins](/docs/cookbooks/knowledge-and-plugins) |
| [Capabilities](/docs/capabilities/overview) | Two kits, extensions, knowledge, memory, obs, telemetry, flags, wiki, loader, gates | Context explosion; IDE lock-in; missing telemetry/evals; extend without fork | [Two kits](/docs/capabilities/modes) |
| [Testing & evaluation](/docs/components/testing) | Tester adaptation, test layers, agent-run scores | Measure success of agent work; keep product tests in *your* runners | [Obs, eval, testing](/docs/cookbooks/observability-eval-testing) |
| [Governance & portal](/docs/components/governance) | Planning sign-off, licenses, enterprise portal | Structure, reuse, and govern pipelines across a fleet | [Enterprise governance](/docs/cookbooks/enterprise-governance) |

## Always on vs opt-in

After `pipeline-kit init`, core delivery (workflows, loader, wiki, planning gates, feature flags) is available. Packages, plugins, knowledge, memory, observability, and the portal stay **off** until you turn them on.

Full catalog: [Capabilities overview](/docs/capabilities/overview).

## Two kits

Every component works with **kit mode** (markdown pack + IDE) or **orchestrator mode** (Python engine + CLI). Pick one per project at init.

→ [Two kits — pack and orchestrator](/docs/capabilities/modes)

## Next

1. [Problems we solve](/docs/intro/problems) — map pain → component → cookbook  
2. [Cookbooks](/docs/cookbooks/) — step-by-step use cases  
3. [Install the CLI](/docs/getting-started/install-cli)
