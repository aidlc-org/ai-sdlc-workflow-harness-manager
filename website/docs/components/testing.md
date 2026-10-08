---
title: Testing and evaluation
description: Point agent testers at your runners, keep test layers honest, and score coding-agent runs with observability.
---

**Testing** in Pipeline Kit has two layers that must not be mixed:

1. **Product tests** — unit, API, UI runners that belong to *your* application.
2. **Agent-run evaluation** — traces and deterministic scores for what the *coding agent* did.

## Product tests

Tester skills mention Playwright, API, and unit layers. Adapt them to this repository’s commands; do not invent a second framework tree.

| Topic | Doc |
|-------|-----|
| Point testers at Jest, pytest, Playwright, etc. | [Adapt tests](/docs/guides/tests) |
| Unit vs API vs UI layering mistakes | [Test layers troubleshooting](/docs/troubleshooting/test-layers) |
| QA overlay from a code graph | [Knowledge base](/docs/capabilities/knowledge) |
| One-time curator workflow | [Knowledge bootstrap](/docs/workflows/knowledge-bootstrap) |

Cookbook: [Observability, eval, and testing](/docs/cookbooks/observability-eval-testing).

## Agent-run evaluation

| Topic | Doc |
|-------|-----|
| Local ledger → Langfuse flush, scores | [Agent-run observability](/docs/capabilities/observability) |
| Install / flush issues | [Observability troubleshooting](/docs/troubleshooting/observability) |
| Not the same as product analytics | [App telemetry](/docs/capabilities/telemetry) |

```bash
pipeline-kit obs install --ide cursor --adapter langfuse
pipeline-kit obs report    # local scores; no network
pipeline-kit obs flush     # ship ledger rows when keys are set
```

## How this maps to components

| You want… | Use |
|-----------|-----|
| Cases derived from architecture graph | Knowledge + optional Graphify plugin |
| Playwright / API / unit in the feature ladder | Workflows + adapt tests |
| Measure agent quality over time | Observability (+ optional Langfuse) |
| Fleet view of who has obs on | [Governance / portal](/docs/components/governance) |

## Next

- [Cookbook: obs, eval, testing](/docs/cookbooks/observability-eval-testing)
- [Components overview](/docs/components/overview)
