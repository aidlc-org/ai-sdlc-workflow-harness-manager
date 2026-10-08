---
title: Who it is for
description: Developers, architects, and enterprise delivery leads who need one kit across many engagements.
---

This documentation is for people who install, adapt, and run Pipeline Kit — not for the application the kit is dropped into.

## New users

Start here if you have never installed the pack:

1. [Prerequisites](/docs/getting-started/prerequisites)
2. [Install the CLI](/docs/getting-started/install-cli)
3. [Two kits](/docs/capabilities/modes) — pick kit mode or orchestrator mode
4. [First project](/docs/getting-started/first-project)
5. [Your first workflow](/docs/getting-started/first-workflow)

## Developers (regular users)

You already have `.pipeline/` in the repo. Use:

- [Two kits](/docs/capabilities/modes) — kit mode vs orchestrator mode
- [Capabilities](/docs/capabilities/overview) — workflows, knowledge, plugins, observability
- [CLI reference](/docs/reference/cli)
- [Troubleshooting](/docs/troubleshooting) when a run goes sideways

## Architects and delivery leads

You take the kit to a new engagement. You must overlay process without forking skills:

- [New-project checklist](/docs/getting-started/checklist)
- [Adapt AGENTS.md](/docs/guides/agents-md)
- [Adapt config.json](/docs/guides/config)
- [Adapt local deploy](/docs/guides/local-deploy)
- [What you should not edit](/docs/guides/what-not-to-edit)

## Kit maintainers

You change the installer or the bundled pack in this repository:

- [Repository layout](/docs/intro/repo-layout)
- [This repository](/docs/maintainers/repo)
- [Authoring pack markdown](/docs/maintainers/authoring)
- [Extensions](/docs/capabilities/extensions)

## What this is not

Pipeline Kit is **not** the customer application, not an IdentityIQ product, and not a hosted agent portal. It does not spawn daemons. The IDE (or `--ide none` plus the loader) runs the workflows.
