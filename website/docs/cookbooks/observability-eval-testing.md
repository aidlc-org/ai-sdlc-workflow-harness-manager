---
title: Observability, eval, and testing
description: Install agent-run observability, read local scores, flush to Langfuse, and point product testers at your real runners.
---

**Goal:** Measure what the **coding agent** did, and keep **product** tests on your own frameworks.

**Components used:** [Observability](/docs/capabilities/observability), [Testing hub](/docs/components/testing), [Adapt tests](/docs/guides/tests).

:::info Two different words
**Agent-run observability** = traces/scores for the IDE agent. **App telemetry** = product analytics events from a spec ([telemetry](/docs/capabilities/telemetry)). Do not mix them.
:::

## Prerequisites

- `.pipeline/` from `init` (obs needs hooks + config)
- Optional: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL` for flush

## Part A — Agent-run observability

### 1. Install

```bash
cd /path/to/your-app
pipeline-kit obs install --ide cursor --adapter langfuse
```

`--ide` may be `cursor`, `claude-code`, or `github`.

Keys go in `.env` or the shell — **never** in `config.json`.

### 2. Work in the right workspace

Open **this** project folder as the workspace root so IDE hooks fire.

### 3. Report and flush

```bash
pipeline-kit obs status
pipeline-kit obs report    # local deterministic scores; no network
pipeline-kit obs flush     # ship new ledger rows when keys are set
```

Ledger: `.pipeline/state/obs/events.jsonl`. Fail-open collectors must not break the agent.

Deep dive: [Agent-run observability](/docs/capabilities/observability). Troubleshoot: [Observability troubleshooting](/docs/troubleshooting/observability).

## Part B — Product tests

### 1. Point tester skills at your commands

| Your stack | Tell the tester |
|------------|-----------------|
| Jest / Vitest | `npm test` in the UI package |
| Existing Playwright | Use that project; no second tree |
| pytest | `pytest path/to/module` |
| No UI | Skip Playwright; keep unit + API |

→ [Adapt tests](/docs/guides/tests)

### 2. Keep layers honest

Playwright implements `qa-test-cases.md` 1:1. Do not invent a second scenario list.

→ [Test layers](/docs/troubleshooting/test-layers)

### 3. Optional knowledge-driven cases

Graph-informed cases: [Knowledge and plugins cookbook](/docs/cookbooks/knowledge-and-plugins).

## Done when

- [ ] `obs status` shows install healthy (or you skipped obs intentionally)  
- [ ] `obs report` runs locally  
- [ ] Tester briefs match this repo’s runners  
- [ ] You can explain agent scores vs product test results  

## Next

- [Testing component hub](/docs/components/testing)
- [Enterprise governance](/docs/cookbooks/enterprise-governance) for fleet visibility of obs
