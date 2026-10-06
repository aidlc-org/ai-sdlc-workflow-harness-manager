# Packages

Optional extras. Each has its own `pyproject.toml`. `pipeline-kit init` does
**not** install them.

Install extras into the **same environment as the `pipeline-kit` CLI**. If the
CLI came from `uv tool` / `./install.sh`, use `uv tool install -e ".[extra]"`
from the kit checkout. `pip install` into another Python leaves
`pipeline-kit <extra> --help` working and real subcommands failing.

## Contents

1. [Assess](#assess) — paid repo assessment (`pipeline-kit scan`)
2. [Memory](#memory) — free artifact bank (`pipeline-kit memory`)

## Assess

| | |
|--|--|
| Package | [`pipeline-kit-assess/`](./pipeline-kit-assess/) |
| Extra | `.[assess]` |
| License | paid area `assess` |

```bash
cd /path/to/pipeline-kit-checkout
uv tool install -e ".[assess]"
pipeline-kit license status
pipeline-kit scan /path/to/product
```

## Memory

| | |
|--|--|
| Package | [`pipeline-kit-memory/`](./pipeline-kit-memory/README.md) |
| Extra | `.[memory]` |
| License | free |

```bash
cd /path/to/pipeline-kit-checkout
uv tool install -e ".[memory]"
pipeline-kit memory doctor /path/to/product
```

Then in the product repo: `memory link` → `import-local` (optional) →
`memory index` → `memory search`. MCP is a later step.

Full walkthrough: [pipeline-kit-memory/README.md](./pipeline-kit-memory/README.md).
