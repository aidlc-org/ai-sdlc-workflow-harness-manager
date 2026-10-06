# Kit mode

Default `--mode kit`. The portable pack is [`pipeline/`](./pipeline/).
`pipeline-kit init` copies it to `<app>/.pipeline` (or `setup` to
`~/.pipeline`).

## Contents

1. [What this is](#what-this-is)
2. [Steps](#steps)

## What this is

Process lives here: skills, agent briefs, workflow allowlists, wiki,
rules, loader. The IDE adapter is a thin `run-workflow` skill.

To **add a workflow** in kit mode, see
[`extensions/kit/`](../extensions/kit/). To run the same first-party
graphs from Python instead of markdown, use
[`orchestrator/`](../orchestrator/) (`--mode orchestrator`).

## Steps

1. Install the CLI once (repo root [README](../README.md#quick-start)).
2. In the product: `pipeline-kit init --ide cursor` then `pipeline-kit doctor`.
3. Overlay `AGENTS.md` and `.pipeline/config.json` ([CUSTOMER-GUIDE](../CUSTOMER-GUIDE.md)).
4. Optional extras from the kit checkout, same CLI: `uv tool install -e ".[memory]"` / `.[assess]` / `.[orchestrator]`.
