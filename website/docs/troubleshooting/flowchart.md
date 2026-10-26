---
title: Troubleshooting flowchart
description: Start from what you see and follow the arrows to the page that fixes it.
---

Start from the symptom. Each end box names a page; the table under the diagram links them.

```mermaid
flowchart TD
    S{What do you see?}
    S --> C[A pipeline-kit command fails]
    S --> H[A tool call is blocked or hooks do nothing]
    S --> P[A Graphify or Archify step fails]
    S --> A[The agent behaves wrongly in a run]
    S --> O[Observability shows nothing]

    C --> C1{Which message?}
    C1 -->|command not found, wrong Python, path| PL[Platforms]
    C1 -->|exit 73 license| ER[Errors table]
    C1 -->|doctor says setup is incomplete| ER
    C1 -->|no .pipeline, not a directory| ER

    H --> H1{Blocked or silent?}
    H1 -->|a Blocked message| ER
    H1 -->|never fires| HK[IDE hooks]

    P --> PG[Plugins]

    A --> A1{What went wrong?}
    A1 -->|tracker key took the wrong path| JI[Tracker intake]
    A1 -->|prompt is huge, old HANDOFF pasted| SH[Slim handoffs]
    A1 -->|HANDOFF missing after interrupt| IT[Interrupted Task]
    A1 -->|port in use, secret in HANDOFF| DL[Deploy listeners]
    A1 -->|tests missing or wrong order| TL[Test layers]
    A1 -->|done too early, invented retro| RT[Retro]
    A1 -->|grep misses visible text| UC[UI copy]

    O --> OB[Observability]
```

| End box | Page |
|---------|------|
| Platforms | [Platforms](/docs/troubleshooting/platforms) |
| Errors table | [Error messages](/docs/troubleshooting/errors) |
| IDE hooks | [IDE hooks](/docs/troubleshooting/hooks) |
| Plugins | [Graphify and Archify](/docs/troubleshooting/plugins) |
| Tracker intake | [Tracker intake](/docs/troubleshooting/jira-intake) |
| Slim handoffs | [Slim handoffs](/docs/troubleshooting/slim-handoffs) |
| Interrupted Task | [Interrupted Task](/docs/troubleshooting/interrupted-task) |
| Deploy listeners | [Deploy listeners](/docs/troubleshooting/deploy-listeners) |
| Test layers | [Test layers](/docs/troubleshooting/test-layers) |
| Retro | [Retro](/docs/troubleshooting/retro) |
| UI copy | [UI copy split](/docs/troubleshooting/ui-copy) |
| Observability | [Observability](/docs/troubleshooting/observability) |

Nothing matches? Run `pipeline-kit doctor` first. Every `missing` line in its output names one thing to fix. Then read the [FAQ](/docs/troubleshooting/faq).
