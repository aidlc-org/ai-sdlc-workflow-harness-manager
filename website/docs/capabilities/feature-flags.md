---
title: Feature flags
description: Named on/off capabilities that mirror config.json. Chat overrides still win for a single run.
---

`pipeline-kit features` toggles the same keys as `.pipeline/config.json`. It does **not** replace `knowledge init`, `plugins install`, or `obs install`. Chat overrides (`RUN_TESTER`, `RUN_TELEMETRY`, `RUN_ARCHITECT`) still win for a single run.

```bash
pipeline-kit features list
pipeline-kit features status
pipeline-kit features enable telemetry
pipeline-kit features disable telemetry
```

## Flag ids

| Id | Effect |
|----|--------|
| `test-design` | Structured cases (`test_design.enabled`). Prefer `knowledge init` for the overlay. |
| `playwright` | Playwright projector path under test design |
| `telemetry` | Allow `telemetry-agent` on feature waves |
| `tester` | Tester policy / `run_tester` related switch |
| `archify` | `architecture_diagrams.enabled` |
| `jira-intake` | `intake.jira.enabled` |
| `github-intake` | `intake.github.enabled` (free; no Jira license) |
| `agent-observability` | `agent_observability.enabled` (still need `obs install` for hooks) |

Enable flags only when the matching install path is done (knowledge overlay, plugin skill, obs hooks, tracker MCP).
