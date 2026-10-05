# Capabilities

Optional add-ons. `pipeline-kit init` does **not** turn these on.

| Folder | Import name (unchanged) | CLI | What it is |
|--------|-------------------------|-----|------------|
| [`plugins/`](./plugins/) | `pipeline_plugins` | `pipeline-kit plugins` | External Graphify and Archify lifecycle |
| [`knowledge/`](./knowledge/) | `knowledge` | `pipeline-kit knowledge` | QA overlay that *consumes* a Graphify graph |
| [`observability/`](./observability/) | `pipeline_observability` | `pipeline-kit obs` | Agent-run traces, scores, Langfuse flush |
| [`eval/`](./eval/) | `pipeline_eval` | `pipeline-kit eval` | Judge catalog sync (Langfuse) |
| [`feature_flags/`](./feature_flags/) | `pipeline_features` | `pipeline-kit features` | Named on/off keys that mirror `config.json` |
| `packages/pipeline-kit-assess/` | `pipeline_assess` | `pipeline-kit scan` | Licensed assessment. Install with `uv tool install -e ".[assess]"` |
| `packages/pipeline-kit-memory/` | `pipeline_memory` | `pipeline-kit memory` | External artifact bank, FTS search, MCP server. Install with `.[memory]` |
| `packages/pipeline-kit-portal/` | `pipeline_portal` | `pipeline-kit portal` | Local fleet dashboard: features/plugins/extensions + health. Install with `.[portal]` |

Python import names stay `pipeline_*` / `knowledge` so hooks, associate
workflows, and the CLI do not change. Folders are grouped here so the
repo map matches the product: plugins, knowledge, observability, eval,
flags.

Observability is a **bundled add-on** (`obs install`), not an entry in
`plugins list`. Graphify and Archify are **external plugins** — the kit
never vendors them and never `import`s Graphify.
