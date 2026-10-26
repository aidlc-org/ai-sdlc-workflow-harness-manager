---
title: Workflow tour
description: The kit workflows in the order a customer meets them, with when to use each, an example prompt, and the files it writes.
---

This page walks through the workflows in the order most teams adopt them. Each stop says when to use it, gives one example prompt, and lists what lands on disk. Details live on the linked workflow pages.

You do not pick a workflow by name. The parent agent reads your ask and the table in `AGENTS.md` ([guide](/docs/guides/agents-md)) and runs the loader for the right one. Run `pipeline-kit workflows` to list what your install has.

Run artifacts go under `features/{slug}/` in your project. Docs workflows write under `wiki/codebase/`. Both are described in [git ignore](/docs/guides/gitignore).

## Which areas are paid

Kit mode, `ask`, `feature-development`, the GitHub workflows, `knowledge`, and the codebase docs workflows need no license. The Jira workflows need the `jira` area. Orchestrator mode needs the `orchestrator` area. Full list and exit codes: [Licensing](/docs/reference/licensing).

| Stop | Workflow | License |
|------|----------|---------|
| 1 | `ask` | None |
| 2 | `feature-development` | None |
| 3 | `jira-story`, `jira-epic`, `jira-bug` | `jira` area |
| 3 | `github-story`, `github-epic`, `github-bug` | None |
| 4 | `test-knowledge-bootstrap` | None |
| 5 | `large-codebase-docs`, `system-architecture`, `module-security-review` | None |

## Stop 1: ask

**Use it when** you want to understand the repo: how, what, why, where. It is read-only and spawns no specialists.

**Example prompt**

```text
How does the order checkout flow reach the payment service?
```

**Artifacts:** none. The answer comes back in chat with file paths. It does not write `route.md` or edit product code.

If the question turns into a change request, re-ask it as product work so stop 2 runs. See [Ask](/docs/workflows/ask).

## Stop 2: feature-development

**Use it when** you ask to add, fix, change or implement something from chat. The parent first classifies the work as micro, minor or feature. Feature class stops at three sign-offs before any code is written.

**Example prompt**

```text
Add a CSV export button to the invoices list. Keep the existing filters.
```

**Artifacts** under `features/{slug}/`:

| File | Written by | When |
|------|-----------|------|
| `route.md` | Parent | Always, before any specialist |
| `prd.md`, `research.md`, `decisions.md` | Product manager | Feature class |
| `signoff-requirements.md` | You | Feature class gate |
| `architecture.md`, `HANDOFF-architect.md` | Architect | Feature class, when the size policy asks for it |
| `{child}/specification.md`, `spec-order.md` | BA | Feature class |
| `signoff-ba.md` | You | Feature class gate |
| `qa-test-cases.md`, `qa-signoff.md` | Tester | After the developer waves |
| `deploy-result.env` | Devops | After `FEATURE_SIGNOFF: passed` |
| `RETRO.md` | Retro | Last step |

Micro and minor class skip the product manager and architect and keep a flat folder. Chains: [Feature development](/docs/workflows/feature-development). Gates: [Planning gates](/docs/capabilities/planning-gates).

Before this works end to end, fill in your deploy script and test runners: [Adapt to your stack](/docs/guides/adapt-to-your-stack).

## Stop 3: Jira and GitHub intake

**Use it when** the ask contains a tracker reference. Intake fetches the issue once and writes it to disk. Every later specialist reads the file, not the tracker. The issue type picks the workflow: story, epic or bug.

**Example prompts**

```text
Work on PAY-1234
```

```text
Fix aidlc-org/shop#87
```

**Artifacts** under `features/{slug}/`:

| Workflow | Plan file | Notes |
|----------|-----------|-------|
| `jira-story`, `github-story` | `intake.md` | Then the same sign-offs as a feature |
| `jira-epic`, `github-epic` | `intake.md`, `epic-plan.md` | BA writes one child spec per in-scope story |
| `jira-bug`, `github-bug` | `intake.md`, `rca.md`, `HANDOFF-bug-analyst.md` | No product manager, BA or architect. `rca.md` is the requirement |

Turn intake on first. Jira is enabled by default in the shipped `config.json` but needs the `jira` license area. GitHub is off by default; enable it with `pipeline-kit features enable github-intake` and set `intake.github.repo`. Settings: [config guide](/docs/guides/config). Pages: [Jira](/docs/workflows/jira), [GitHub](/docs/workflows/github). Failures: [intake troubleshooting](/docs/troubleshooting/jira-intake).

## Stop 4: knowledge-bootstrap

**Use it when** you want a reviewed QA knowledge catalog so later features can bind acceptance criteria to known nodes. It is a one-off setup, not a delivery workflow. The workflow name is `test-knowledge-bootstrap`.

**Before you start**, run `pipeline-kit knowledge init` and `pipeline-kit knowledge extract`. Extract needs the official Graphify CLI. See [Knowledge base](/docs/capabilities/knowledge).

**Example prompt**

```text
Bootstrap QA knowledge for this repo
```

**Artifacts**

| Path | Meaning |
|------|---------|
| `test-knowledge/_candidates/{run}/` | Candidate catalog entries |
| `test-knowledge/_candidates/{run}/REVIEW.md` | The one report a human approves |

After you approve, run `pipeline-kit knowledge promote --run <run>`. Reviewed catalogs under `test-knowledge/` are usually committed. Page: [Knowledge bootstrap](/docs/workflows/knowledge-bootstrap).

## Stop 5: codebase docs for monorepos

Three workflows build on each other. They all read Graphify graphs and write under `wiki/codebase/`, not `.pipeline/wiki/`. None needs a license.

### large-codebase-docs

**Use it when** you have a monorepo and want a handbook per module. Fill in `.pipeline/docs-modules.yaml` first. `pipeline-kit docs init-modules` writes a template.

**Example prompt**

```text
Document the large codebase
```

**Artifacts**

| Path | Meaning |
|------|---------|
| `wiki/codebase/modules/{id}/graph/graph.json` | Per-module graph, from `pipeline-kit docs extract-modules` |
| `wiki/codebase/modules/{id}/README.md` | Module handbook |
| `wiki/codebase/INDEX.md` | Router table, from `pipeline-kit docs link-index` |

Page: [Large codebase docs](/docs/workflows/large-codebase-docs).

### system-architecture

**Use it when** the module handbooks exist and you want the cross-module picture. It is not the feature-class architect on the delivery ladder.

**Example prompt**

```text
System architecture for the monorepo
```

**Artifacts:** `wiki/codebase/system/graph/graph.json` (from `pipeline-kit docs merge-modules`), `wiki/codebase/system/README.md`, and optionally `architecture.md` in the same folder. Page: [System architecture](/docs/workflows/system-architecture).

### module-security-review

**Use it when** you want per-module security notes. It labels what it observed and what it inferred. It is not a penetration test.

**Example prompt**

```text
Module security review
```

**Artifacts:** `wiki/codebase/modules/{id}/security.md` for each enabled module with a graph, plus a security column in `INDEX.md`. Page: [Module security review](/docs/workflows/module-security-review).

## Where to go next

- Add your own workflow: [Add a workflow](/docs/guides/add-workflow).
- Share one setup across a team: [Team best practices](/docs/guides/team-best-practices).
- The change classes and chains in one place: [Workflows](/docs/capabilities/workflows).
