---
name: ask
description: >-
  Answer a question about this repository. No Task chain, no product edits
  unless the user asked for a change. Skip weather and other unrelated asks.
---

# Ask (read-only Q&A)

| Attribute | Value |
|-----------|--------|
| Type | Skill |
| Audience | The named agent, or the parent when this file is on the allowlist |
| Adapt | Change commands or paths only in deploy and testing skills. Planning skills stay product-neutral. |

The parent stays in this skill. Do **not** spawn specialists. Do **not** start feature-development.

## When this workflow runs

The receptionist already ran the loader with `--workflow ask --step parent`.

| Use `ask` | Do not use `ask` |
|-----------|------------------|
| How / what / why / where / explain about this repo | work on, fix, change, develop, implement, add, build |
| Point me at the file / function / flow | A tracker issue key (use the Jira workflow) |
| — | “Bootstrap QA knowledge” (workflow `test-knowledge-bootstrap`) |
| — | Document large codebase / monorepo docs (`large-codebase-docs`) |
| — | Module security review / system architecture workflows |
| Compare two approaches already in the tree | Architecture diagrams (out of scope for this skill) |

Weather, locations, and other asks unrelated to this repository: **stop**. Do not read pack files. Do not invent a pipeline.

## Steps

1. Answer from the repository. Prefer nearby code, tests, and docs over speculation.
2. Cite file paths. Do not dump large files.
3. Do not edit product source, tests, or config unless the user explicitly asked for a change. If they did, stop and tell them to re-ask as product work so `feature-development` can run.
4. Do not write `features/{slug}/route.md` and do not spawn a `Task`.

## Anti-patterns

Starting the feature ladder just in case. Loading every `.pipeline/skills` file. Editing code to illustrate an answer. Answering off-repo trivia with tools.
