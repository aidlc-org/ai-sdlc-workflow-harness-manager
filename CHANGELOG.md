# Changelog

All notable changes to the public **pipeline-kit** package are recorded here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Version numbers come from `VERSION`.

## [Unreleased]

### Added

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
