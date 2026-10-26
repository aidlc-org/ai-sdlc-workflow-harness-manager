---
title: Docs workflow
description: How the documentation site is built, checked, deployed and measured, and how to add or change a page.
---

## What runs where

| Part | Where |
|------|-------|
| Source | `website/docs/` (Docusaurus 3.8). Sidebar: `website/sidebars.ts` |
| Checks | The Vercel build (links), and the drift tests you run locally |
| Deploy and PR previews, and the link check | Vercel's Git integration, configured by `website/vercel.json` |
| Search | Local index built at `npm run build`; no external service |

## The checks

| Check | What it catches |
|-------|-----------------|
| `npm run typecheck` and `npm run build` | Broken links and broken Markdown links (both set to `throw`), config type errors |
| `tests/test_docs_sync.py` | A CLI command in `install.py` missing from [CLI reference](/docs/reference/cli); `CUSTOMER-GUIDE.md` copies that differ; `VERSION` without a dated `CHANGELOG.md` heading; `llms.txt` links outside the configured site URL |

## Add a page

1. Create `website/docs/<section>/<name>.md` with `title` and `description` frontmatter.
2. Add its id to `website/sidebars.ts`.
3. If it is a key page, add a line to `website/static/llms.txt`.
4. Link to reference pages instead of copying flags and paths.
5. Run `npm run build` in `website/`. A broken link fails it.

New CLI commands need a row in the CLI reference; the drift test fails without one.

## Customer guide copies

Edit the root `CUSTOMER-GUIDE.md`, then copy it to `kit/pipeline/docs/CUSTOMER-GUIDE.md`. The copy under `kit/` ships to customers, so also run `python -m pytest tests/test_install.py`.

## Analytics

The site uses Vercel Web Analytics. It is cookieless, so there is no consent banner. It counts page views and referrers per page, and it has no session replay or heatmaps. To turn it on, enable Web Analytics for the project in the Vercel dashboard; the script in `docusaurus.config.ts` does nothing on other hosts. Do not add other trackers without updating this page.

## Review cadence

At each release, skim the pages for the features that changed, and update the "Last reviewed" line in `CUSTOMER-GUIDE.md`.

## Known gap

`.github/workflows/ci.yml` does not run the drift tests or the example tests, and the full suite has failures on `develop`. Run them locally (see [Contributing](https://github.com/aidlc-org/ai-sdlc-workflow-harness-manager/blob/main/CONTRIBUTING.md)) until CI is extended.
