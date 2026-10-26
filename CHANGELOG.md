# Changelog

All notable changes to the public **pipeline-kit** package are recorded here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Version numbers come from `VERSION`.

## [Unreleased]

### Added

- **Docs guardrails (issue #15):** broken links and broken Markdown links now fail the site build (Vercel runs it). `tests/test_docs_sync.py` fails when a CLI command in `install.py` is missing from `reference/cli.md`, when the two `CUSTOMER-GUIDE.md` copies differ, or when `VERSION` has no dated `CHANGELOG.md` heading
- **Docs content (issue #15):** quick start, architecture overview, enterprise readiness, workflow tour, team best practices, stack adaptation guide, and troubleshooting flowchart, FAQ, error-message table, platform and plugin pages; the four IDE adapter pages share one heading layout; maintainer pages for releases and the docs workflow
- **Examples (issue #19):** `examples/` with stack skeletons (Node, Python, Java, Go), workflows, plugins, observability, memory bank and troubleshooting scenarios, each with a `smoke.py` run by `tests/test_examples.py`
- **Release:** `pipeline-kit version bump|set` now moves `[Unreleased]` under the new dated heading (skip with `--no-changelog`); a `release` workflow builds the sdist and wheel on a `vX.Y.Z` tag and creates the GitHub release
- **Site:** production URL and Vercel Web Analytics configured, `website/vercel.json` added, `llms.txt` links point at the real host
- **Docs:** new `capabilities/agent-security` page; `security`, `eval` and `license` sections in the CLI reference; "Changing the docs" section in `CONTRIBUTING.md`
- **Kit model routing (advisory):** loader resolves `orchestrator.models` pins / `fallback_model` for specialist steps into `chosen_model` on the context pack and `features/{slug}/model-routing.json`. Agent CLIs may pass the id when Task spawn supports a model field. IDE chat does not enforce. Enforced routing stays orchestrator (`pipeline-kit run`). Opt out: `PIPELINE_KIT_MODEL_ROUTING=0`.
- **Documentation site (issue #11):** Tessl-style information architecture on Docusaurus
  - Components hubs: overview, packages, testing, governance
  - Cookbooks: first feature, orchestrator first run, add workflow, knowledge/plugins, obs/eval/testing, memory bank, enterprise governance
  - Navbar/footer: Components + Cookbooks; polished docs chrome CSS; updated `llms.txt`
- **Large codebase documentation platform** (`pipeline_docs`):
  - CLI: `pipeline-kit docs init-modules | extract-modules | merge-modules | status | link-index | link-agents`
  - Manual inventory `.pipeline/docs-modules.yaml`; artifacts under `wiki/codebase/` (not `.pipeline/wiki/`)
  - Parallel module Graphify extract via official CLI only (per-module cwd; no Graphify Python import)
- Kit workflows (free open pack):
  - `large-codebase-docs` — module handbooks via `module-docs-agent`
  - `module-security-review` — per-module `security.md` via `module-security-agent`
  - `system-architecture` — cross-module docs via `system-architect-agent`
- Graphify helpers: path-scoped `extract_graph_at`, `merge_graphs(..., out=)`; pack ignore for `wiki/codebase/`

### Changed

- Orchestration routes monorepo docs / module security / system architecture intents before the feature ladder

## [1.2.2] - 2026-10-08

### Added

- `.[dev]` optional extra (`pytest`, `cryptography`) for contributors and CI
- Project URLs in `pyproject.toml` (Homepage, Repository, Issues)
- Pytest markers `license_absent` and `requires_license_engine` so public CI
  runs without the private `pipeline-kit-license` package
- `CHANGELOG.md` and GitHub issue templates
- GitHub intake workflows in the assess catalog (`github-story`, `github-epic`,
  `github-bug`)
- DOCUMENT-STANDARD `Type` headers on eval judge handbooks

### Changed

- README quick start uses the public GitHub install URL
- SECURITY.md points at GitHub private vulnerability reporting
- Licensing docs: private license package is vendor-delivered (not public source)
- CONTRIBUTING matches the real `.[dev]` install path

### Fixed

- Observability scoring path normalization on Windows (`integrity_pass`)
- Public CI / contributor tests portable without bare `python3` or POSIX-only
  fake binaries
- Docs note Archify mermaid fallback when the tool is missing

### Notes

- Production CLI behaviour is unchanged: without `pipeline-kit-license`, paid
  areas still fail closed (exit 73)
- Enterprise portal and license packages remain separate private products
