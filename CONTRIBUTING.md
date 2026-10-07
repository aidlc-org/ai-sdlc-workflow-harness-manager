# Contributing to pipeline-kit

Thanks for helping improve the open kit. This repository is the **MIT-licensed**
harness: installer, pack, orchestrator engine, extensions, and optional packages.

**Package name:** `pipeline-kit` (install/import).  
**Repository:** [ai-sdlc-workflow-harness-manager](https://github.com/digitalneedstech/ai-sdlc-workflow-harness-manager).

## What belongs here

- Bug fixes and tests for the CLI, pack, hooks, plugins, knowledge, memory, and
  orchestrator engine
- Documentation and examples
- New workflows under `extensions/kit/` or `extensions/orchestrator/`
- Optional plugins under `capabilities/plugins/`

## What does not belong here

- The **Enterprise Pipeline Portal** server or UI (separate proprietary product)
- The private **`pipeline-kit-license`** package source (vendor-only)
- Signing keys, customer licenses, ingest keys, or production credentials
- Customer project overlays, private configs, or engagement-specific secrets

## Development

Requires Python 3.11+.

```bash
python -m pip install -e ".[dev]"
# Optional extras used by some tests:
# python -m pip install -e ".[dev,orchestrator,assess,memory]"
python -m pytest -q
```

Public CI runs without the private license package. Tests that need real
crypto are marked `requires_license_engine` and skip there. Maintainers with a
local sibling checkout can:

```bash
python -m pip install -e ../pipeline-kit-license
python -m pytest -q
```

To simulate public CI on a machine that has the private package:

```bash
# PowerShell
$env:PIPELINE_KIT_TEST_WITHOUT_LICENSE = "1"
python -m pytest -q
```

Optional docs site:

```bash
cd website
npm ci
npm start
```

## Pull requests

1. Keep changes focused and covered by tests where behavior changes.
2. Do not commit secrets, PEM keys, `.env`, or portal runtime data.
3. Match existing style: short modules, clear CLI exit codes, no drive-by refactors.
4. Update docs when you change commands, license behavior, or the portal report protocol.

## License

By contributing, you agree that your contributions are licensed under the MIT
License in `LICENSE`.
