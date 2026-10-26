---
title: Quick start
description: Install pipeline-kit, init one repo, edit two files, and run your first workflow in about 10 minutes (kit mode).
---

This page takes one application repository from nothing to a first workflow run. It uses **kit mode**, the default. Each step links to the longer page if you need more.

You need Python 3.11 or newer, `git`, an application repo, and one of Cursor, Claude Code, or GitHub Copilot. See [Prerequisites](/docs/getting-started/prerequisites).

## 1. Install the CLI (once per machine)

```bash
uv tool install git+https://github.com/aidlc-org/ai-sdlc-workflow-harness-manager
pipeline-kit --version
```

`pipx install git+<url>` and `./install.sh` from a clone also work. See [Install the CLI](/docs/getting-started/install-cli).

## 2. Initialize the repo

Run this at the root of your application repo. Pick the `--ide` that matches your editor: `cursor`, `claude-code`, `github`, or `none`.

```bash
cd /path/to/your-app
pipeline-kit init --ide claude-code
pipeline-kit doctor --ide claude-code
pipeline-kit workflows
```

Expected result:

- `.pipeline/` exists with `config.json`, `loader/`, `skills/`, `agents/`, `workflows/`, `hooks/` and `wiki/`.
- The IDE folder holds one skill, `run-workflow`. For Claude Code that is `.claude/skills/run-workflow/SKILL.md`. Other paths are in [IDE adapters](/docs/getting-started/ide-adapters).
- `doctor` ends with `pipeline-kit <version> is ready`. Lines that start with `info` (Graphify, Archify, observability, memory) are optional features that are off.
- `workflows` lists `ask`, `feature-development`, the Jira and GitHub workflows, and a few more.

`init` does not edit `AGENTS.md`, and it does not turn on knowledge, Graphify, Archify or observability. Details: [First project](/docs/getting-started/first-project).

## 3. Add a routing table to `AGENTS.md`

Create or edit `AGENTS.md` at the repo root. This is the smallest useful version. Replace the skill path with the one for your `--ide`.

```markdown
# My app: agent instructions

{One paragraph: what this repo is, its language, and how to run its tests.}

For product work or a question about this repo, follow the IDE
`.claude/skills/run-workflow/SKILL.md` skill. Run the loader and read only
`allowed_reads`.

Unrelated asks (weather, trivia): do not run the loader.

| User intent | What to do |
|-------------|------------|
| "work on", "fix", "change", "add", or a tracker issue key | Follow the `run-workflow` skill |
| A question about this repo | Same skill, workflow `ask`. No Task chain |
| Anything unrelated | Do not run the loader |
```

Without this file the agent may skip the pack entirely. The full table is in [Adapt AGENTS.md](/docs/guides/agents-md).

## 4. Edit `.pipeline/config.json`

`init` writes a complete template. You change only the keys that describe your repo.

```json
"intake": { "jira": { "enabled": false } },
"verify": {
  "rules": [
    { "match": "/src/", "message": "You edited source. Run the build and the tests." }
  ]
},
"deploy": { "target": "auto", "targets": ["auto"] }
```

- `intake.jira.enabled`: the shipped template has it `true`. Set it to `false` unless you use Jira.
- `verify.rules`: a path substring from your tree and a reminder shown after a file in that path is edited. `[]` is valid.
- `deploy`: leave as is until you have a [local deploy script](/docs/guides/local-deploy). The sample script reports `OVERALL=failed` until you fill it in, so expect the devops step of a first run to report a failed deploy.

The edit is explained in [Adapt config.json](/docs/guides/config); every key is in the [config reference](/docs/reference/config). `pipeline-kit update` keeps your local values.

## 5. Run the first workflow

Open the repository **root** in your IDE so it finds the `run-workflow` skill. Then:

1. Ask a question:

   > How does local deploy work in this repository?

   Expected: workflow `ask`. The agent answers from the repo and does not start a chain of specialists. See [Ask](/docs/workflows/ask).

2. Make a small change:

   > Add a small label change on the homepage.

   Expected: workflow `feature-development`, classified as `micro` in `features/<slug>/route.md` before any specialist runs. See [Feature development](/docs/workflows/feature-development) and [change classes](/docs/capabilities/workflows).

If nothing happens, see [If nothing happens](/docs/getting-started/first-workflow#if-nothing-happens).

## 6. Check the result

Each run writes to `features/<slug>/` in your repo. To check the install without the IDE, run the loader by hand:

```bash
python .pipeline/loader/load_workflow.py --workflow ask --step parent --slug smoke
ls features/smoke
```

It prints a JSON allowlist (`allowed_reads`) and creates `context-pack.json` and `step-context.md` in `features/smoke/`. That confirms the pack, config and loader work. Delete `features/smoke/` afterwards.

You are done when:

- [ ] `doctor` ends with `is ready`.
- [ ] `ask` answered from the repo with no specialist chain.
- [ ] A small change produced files under `features/<slug>/`.

## Next

- [New-project checklist](/docs/getting-started/checklist)
- [First feature end to end](/docs/cookbooks/first-feature)
- [Point tests at your runner](/docs/guides/tests) and [adapt local deploy](/docs/guides/local-deploy)
- [Keep `features/` out of git if you want to](/docs/guides/gitignore)
- [Architecture overview](/docs/intro/architecture)
- Prefer the Python engine with `pipeline-kit run`? See [Orchestrator mode first run](/docs/cookbooks/orchestrator-first-run).
- Something broke? [Troubleshooting](/docs/troubleshooting/)
