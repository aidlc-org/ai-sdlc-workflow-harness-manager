---
title: This repository
description: Kit source layout, sync-kit, tests. Not a customer application.
---

This repository **is** the pipeline-kit source (installer + bundled pack). It is not a customer application. The source is **MIT** (`LICENSE`). The Enterprise Pipeline Portal lives in a separate proprietary repository.

- Pack body: `kit/pipeline/` (kit mode)
- Orchestrator engine: `orchestrator/` (import `pipeline_orchestrator`)
- Extensions: `extensions/kit/`, `extensions/orchestrator/`
- Capabilities: `capabilities/` (plugins, knowledge, observability, eval, flags)
- Installer: `install.py` / `pipeline-kit` CLI
- Customer handbook: `CUSTOMER-GUIDE.md`
- Docs site: `website/` (this Docusaurus app; not copied on `init`)
- Community: `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`

Folder map: [Repository layout](/docs/intro/repo-layout).

## Refresh the bundled pack

Maintainers who edit a live `.pipeline` in this repo can refresh the bundle:

```bash
python3 install.py --sync-kit
```

## Tests

```bash
python3 -m pip install -e ".[dev]"
python3 -m pytest -q tests
```

Public CI has no private `pipeline-kit-license`. Crypto and full entitlement
tests are marked `requires_license_engine` and skip there. Fail-closed paths use
`license_absent`. Maintainers with a sibling checkout can
`pip install -e ../pipeline-kit-license` to run the full suite.

## Release a new version

The kit version is a single file: `VERSION`. It drives `pipeline-kit --version`, the Python package version, and `.pipeline/install.json` after `init` / `update`. `website/package.json` is kept on the same number.

```bash
pipeline-kit version                 # current, e.g. 1.2.1
pipeline-kit version bump patch      # 1.2.1 → 1.2.2
pipeline-kit version bump minor      # 1.2.1 → 1.3.0
pipeline-kit version bump major      # 1.2.1 → 2.0.0
pipeline-kit version set 1.4.0       # exact
pipeline-kit version bump patch --dry-run
```

### Where the change lands

Bump and set always write to **this repository**, never to the project you happen to be standing in and never to the installed wheel. The checkout is resolved in this order:

1. `--repo PATH`
2. `$PIPELINE_KIT_REPO`
3. the first pipeline-kit git checkout at or above the current directory

If none of those resolve, the command fails rather than bumping the installed copy — a bump there would publish nothing. Export `PIPELINE_KIT_REPO=/path/to/pipeline-kit` to release from anywhere.

### Commit and tag

`--commit` commits `VERSION` (and `website/package.json`) **in the kit checkout**, using `git -C`, so a release never lands in a customer repo. Only those paths are committed; anything else staged in the kit repo is left alone. `--tag` adds the annotated `vX.Y.Z` tag and requires `--commit`.

```bash
pipeline-kit version bump patch --commit --tag
git -C /path/to/pipeline-kit push --follow-tags
```

Without `--commit` the files are written and the exact `git -C … commit` / `tag` commands are printed instead. Pushing is always yours to run.

Customers pick up the new wheel with `uv tool upgrade pipeline-kit` (or a reinstall), then `pipeline-kit update` in each project.

Do not start a nested feature pipeline against this repo unless the change is to the kit itself.
