---
title: Repository layout
description: How the pipeline-kit source tree is grouped — modes, extensions, capabilities.
---

This repository is the **kit source**, not a customer application. It contains **two kits**: the markdown pack (`kit/`) and the Python engine (`orchestrator/`). Customer-facing comparison: [Two kits](/docs/capabilities/modes).

```text
kit/                         kit mode — portable pack
orchestrator/                orchestrator mode — Python engine
extensions/
  kit/                       add a markdown workflow
  orchestrator/              associate Python workflows
capabilities/
  plugins/                   Graphify + Archify
  knowledge/                 QA overlay (consumes Graphify)
  observability/             agent-run traces
  eval/                      judges / Langfuse eval
  feature_flags/             named on/off keys
packages/                    separate installable extras, own pyproject.toml
  pipeline-kit-assess/       licensed repo assessment
  pipeline-kit-memory/       external artifact bank + MCP
website/                     this documentation site
tests/
```

## Modes

| Folder | CLI | What lands |
|--------|-----|------------|
| [`kit/`](/docs/capabilities/modes) | `pipeline-kit init` (default `--mode kit`) | `<app>/.pipeline` from `kit/pipeline/` |
| [`orchestrator/`](/docs/capabilities/modes) | `init --mode orchestrator` | Engine in the wheel. Import name stays `pipeline_orchestrator`. |

## Extensions

Add a process without forking the kit. [Full guide](/docs/capabilities/extensions).

| Mode | Contract |
|------|----------|
| Kit | Skill + `workflows/{name}.json` + `config.json` chain |
| Orchestrator | `pipeline_extensions/{name}.py` or a `pipeline_kit.workflows` entry point |

Kit mode never loads `pipeline_extensions/`. Orchestrator mode never runs the markdown loader chain.

## Capabilities

Optional. `init` does not turn them on. [Overview](/docs/capabilities/overview).

| Folder | CLI | Import name (stable) |
|--------|-----|----------------------|
| `capabilities/plugins/` | `pipeline-kit plugins` | `pipeline_plugins` |
| `capabilities/knowledge/` | `pipeline-kit knowledge` | `knowledge` |
| `capabilities/observability/` | `pipeline-kit obs` | `pipeline_observability` |
| `capabilities/eval/` | `pipeline-kit eval` | `pipeline_eval` |
| `capabilities/feature_flags/` | `pipeline-kit features` | `pipeline_features` |

Folder names are the product map. Import names stay the same so obs hooks (`from pipeline_observability.export import …`) and associate workflows (`from pipeline_orchestrator.graph import WorkflowSpec`) do not break.

## Packages

Also optional, but each is a **separate installable package** with its own
`pyproject.toml` — not imported until its extra is installed.

| Folder | CLI | Import name (stable) | Extra |
|--------|-----|----------------------|-------|
| `packages/pipeline-kit-assess/` | `pipeline-kit scan` | `pipeline_assess` | `.[assess]` |
| `packages/pipeline-kit-memory/` | `pipeline-kit memory` | `pipeline_memory` | `.[memory]` |
The [Enterprise portal](/docs/capabilities/portal) (sign-in, roles, analysis,
license management) is **not** in this repository. It is a separate product with
its own repository, installed alongside the kit.

## What stays at the repo root

`install.py`, `pyproject.toml`, `VERSION`, `CUSTOMER-GUIDE.md`, `OBSERVABILITY.md`, `website/`, `tests/`.

Maintainers: [This repository](/docs/maintainers/repo).
