---
title: Capabilities overview
description: What the kit ships, what is opt-in, and where to drill down.
---

Core delivery is on after `pipeline-kit init`. Everything in the second table is **opt-in**.

Pipeline Kit ships **two kits**. [Kit mode](/docs/capabilities/modes) is the markdown pack. [Orchestrator mode](/docs/capabilities/modes) is the Python engine. Same first-party workflow names. Adding a process is an [extension](/docs/capabilities/extensions), not a fork.

## The two kits

| Surface | What it is |
|---------|------------|
| [Two kits — pack and orchestrator](/docs/capabilities/modes) | Pick one per project at `init`. Do not mix. |
| [Extensions](/docs/capabilities/extensions) | Add a process in kit mode (JSON + skill) or orchestrator mode (`pipeline_extensions`) |
| [Repository layout](/docs/intro/repo-layout) | Where each kit lives in this repo |

## Always available after init

| Capability | What it is |
|------------|------------|
| [Workflows](/docs/capabilities/workflows) | Named procedures with chains and allowlists |
| [Planning gates](/docs/capabilities/planning-gates) | Human sign-off on requirements, architecture, BA |
| [Loader](/docs/capabilities/loader) | Per-step `allowed_reads` |
| [Wiki](/docs/capabilities/wiki) | Trigger-routed agent memory |
| [Feature flags](/docs/capabilities/feature-flags) | Named on/off keys that mirror `config.json` |

## Opt-in

| Capability | How you turn it on |
|------------|--------------------|
| [Knowledge base](/docs/capabilities/knowledge) | `pipeline-kit knowledge init` |
| [Memory bank and MCP](/docs/capabilities/memory) | `pip install -e packages/pipeline-kit-memory`, then `pipeline-kit memory link` |
| [Plugins](/docs/capabilities/plugins) | External Graphify/Archify (`plugins install`) and bundled observability (`obs install`) |
| [Graphify](/docs/capabilities/graphify) | Official CLI + skill registration |
| [Archify](/docs/capabilities/archify) | Pinned Agent Skill `v2.16.0` |
| [Agent-run observability](/docs/capabilities/observability) | Bundled add-on: `pipeline-kit obs install` (not `plugins install`) |
| [App telemetry](/docs/capabilities/telemetry) | `features enable telemetry` or `RUN_TELEMETRY` |
| [Enterprise portal](/docs/capabilities/portal) | Separate product and repository (enterprise plan): sign-in, roles, analysis, license management |

:::warning Two different “observability” words
**Agent-run observability** traces what the *coding agent* did (tools, steps, scores). **App telemetry** is a pipeline specialist that extracts *product* analytics events from a spec. Do not mix them.
:::

## Workflow names

`ask`, `feature-development`, `jira-story`, `jira-epic`, `jira-bug`, `test-knowledge-bootstrap`.

Deep dives: [Ask](/docs/workflows/ask), [Feature development](/docs/workflows/feature-development), [Jira](/docs/workflows/jira), [Knowledge bootstrap](/docs/workflows/knowledge-bootstrap).
