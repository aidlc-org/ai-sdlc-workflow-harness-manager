# Contributing to pipeline-kit

Thanks for helping improve the open kit. This repository is the **MIT-licensed**
harness: installer, pack, orchestrator engine, extensions, and optional packages.

**Package name:** `pipeline-kit` (install/import).  
**Repository:** [ai-sdlc-workflow-harness-manager](https://github.com/aidlc-org/ai-sdlc-workflow-harness-manager).

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
# Optional extras used by some tests (assess/memory are path packages, not PyPI yet):
# python -m pip install -e ./packages/pipeline-kit-assess -e ./packages/pipeline-kit-memory -e ".[dev,orchestrator]"
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

## Changing the docs

The site lives in `website/` (Docusaurus). Run it locally:

```bash
cd website
npm ci
npm start
```

Vercel builds the site on every push and PR. Run these yourself before pushing; CI does not run them yet:

| Check | Command | Fails when |
|-------|---------|------------|
| Site build | `cd website && npm run build && npm run typecheck` | a link or Markdown link is broken, or the config does not type-check |
| Drift tests | `python -m pytest tests/test_docs_sync.py -q` | a CLI command in `install.py` is missing from `website/docs/reference/cli.md`, the two guide copies differ, or `VERSION` has no `CHANGELOG.md` heading |
| Full tests (local only for now) | `python -m pytest -q` | any behaviour change; the suite has known failures on `develop` |

`CUSTOMER-GUIDE.md` exists in several places. **Edit the root file**, then copy it over
`kit/pipeline/docs/CUSTOMER-GUIDE.md` (the copy `init` ships to customers). The copies under
`.pipeline/docs/` and `website/.pipeline/docs/` are install output and are git-ignored; do not edit them.
Anything under `kit/pipeline/docs/` reaches customer projects, so run `python -m pytest tests/test_install.py` after changing it.

## Pull requests

1. Keep changes focused and covered by tests where behavior changes.
2. Do not commit secrets, PEM keys, `.env`, or portal runtime data.
3. Match existing style: short modules, clear CLI exit codes, no drive-by refactors.
4. Update docs when you change commands, license behavior, or the portal report protocol.
   A new CLI command needs a row in `website/docs/reference/cli.md`; the drift test fails without it.
5. Add a line under `[Unreleased]` in `CHANGELOG.md` for any user-visible change.

## License

By contributing, you agree that your contributions are licensed under the MIT
License in `LICENSE`.
