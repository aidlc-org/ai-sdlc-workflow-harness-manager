# Capabilities

Optional add-ons. `pipeline-kit init` does **not** turn these on.

## Contents

1. [What ships here](#what-ships-here)
2. [How to turn extras on](#how-to-turn-extras-on)

## What ships here

| Folder | Import name (unchanged) | CLI | What it is |
|--------|-------------------------|-----|------------|
| [`plugins/`](./plugins/) | `pipeline_plugins` | `pipeline-kit plugins` | External Graphify and Archify lifecycle |
| [`knowledge/`](./knowledge/) | `knowledge` | `pipeline-kit knowledge` | QA overlay that *consumes* a Graphify graph |
| [`observability/`](./observability/) | `pipeline_observability` | `pipeline-kit obs` | Agent-run traces, scores, Langfuse flush |
| [`eval/`](./eval/) | `pipeline_eval` | `pipeline-kit eval` | Judge catalog sync (Langfuse) |
| [`feature_flags/`](./feature_flags/) | `pipeline_features` | `pipeline-kit features` | Named on/off keys that mirror `config.json` |
| `packages/pipeline-kit-assess/` | `pipeline_assess` | `pipeline-kit scan` | Paid area (`assess` license). Install with `uv tool install -e ".[assess]"` |
| `packages/pipeline-kit-memory/` | `pipeline_memory` | `pipeline-kit memory` | External artifact bank, FTS search, MCP. Install with `uv tool install -e ".[memory]"` |

## How to turn extras on

Install extras into the **same** CLI as `pipeline-kit` (usually `uv tool`):

```bash
cd /path/to/pipeline-kit-checkout
uv tool install -e ".[orchestrator]"   # paid: pipeline-kit run
uv tool install -e ".[assess]"         # paid: pipeline-kit scan
uv tool install -e ".[memory]"         # free: pipeline-kit memory
```

Memory walkthrough: [`packages/pipeline-kit-memory/README.md`](../packages/pipeline-kit-memory/README.md).
Package map: [`packages/README.md`](../packages/README.md).

The web portal is not in this repository. It is the separate Enterprise Pipeline
Portal, which reads these capabilities' state and calls their commands.

Python import names stay `pipeline_*` / `knowledge` so hooks, associate
workflows, and the CLI do not change. Folders are grouped here so the
repo map matches the product: plugins, knowledge, observability, eval,
flags.

Observability is a **bundled add-on** (`obs install`), not an entry in
`plugins list`. Graphify and Archify are **external plugins** — the kit
never vendors them and never `import`s Graphify.
