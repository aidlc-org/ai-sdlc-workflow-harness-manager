---
title: Release process
description: How to cut a pipeline-kit release, from changelog to tag, GitHub release and docs version.
---

A release is one commit and one tag. The version lives in `VERSION`; the history lives in `CHANGELOG.md`.

## Before you start

1. Make sure everything user-visible has a line under `## [Unreleased]` in `CHANGELOG.md`.
2. Run the checks locally:

```bash
python -m pytest tests/test_docs_sync.py -q
cd website && npm run typecheck && npm run build
```

## Cut the release

Use a dry run first. It prints the version change and says whether the changelog will move.

```bash
pipeline-kit version bump minor --dry-run
pipeline-kit version bump minor --commit --tag
```

`version bump` and `version set` do three things in the kit checkout:

- write the new number to `VERSION` and `website/package.json`;
- move the `[Unreleased]` entries under `## [X.Y.Z] - date` and leave a fresh empty `[Unreleased]` (skip with `--no-changelog`);
- with `--commit --tag`, commit those files as `Release X.Y.Z` and create the annotated tag `vX.Y.Z`.

Details of repository resolution and flags are in [This repository](/docs/maintainers/repo#release-a-new-version).

## Snapshot the docs version

Docusaurus versioning keeps a frozen copy of the docs for each release. Take the snapshot before you tag, so the tagged commit contains it:

```bash
cd website
npx docusaurus docs:version X.Y.Z
```

This creates `versioned_docs/`, `versioned_sidebars/` and `versions.json`. Do not backfill old releases. Commit the snapshot, then tag. When the first version exists, check on the Vercel preview that old versions keep stable URLs (`/docs/X.Y.Z/...`).

## Publish

```bash
git push --follow-tags
```

The tag starts the `release` workflow. It checks that the tag equals `VERSION`, runs the docs drift tests, builds the sdist and wheel, and creates a GitHub release with the changelog section as notes. Vercel deploys the site from the same push. Nothing is published to PyPI; the `assess` and `memory` packages are not on PyPI yet.

## After the release

Customers upgrade with `uv tool upgrade pipeline-kit`, then `pipeline-kit update` in each project.
