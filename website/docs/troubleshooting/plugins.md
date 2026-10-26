---
title: Graphify and Archify
description: Missing CLI, skill not installed, unsupported or unpinned version, stale graph, and the Mermaid fallback.
---

Both plugins are external tools. The kit never vendors them. Start with:

```bash
pipeline-kit plugins status
pipeline-kit doctor
```

Both print the recovery step for what is wrong. Background: [Plugins](/docs/capabilities/plugins), [Graphify](/docs/capabilities/graphify), [Archify](/docs/capabilities/archify). Exact messages are in [Error messages](/docs/troubleshooting/errors#graphify-and-archify).

## Graphify

| Symptom | Cause | Fix |
|---------|-------|-----|
| `graphify: missing` in `plugins status` | The `graphify` command is not on `PATH` | `uv tool install graphifyy && graphify install`. Open a new terminal if the command is still not found, then see [Platforms](/docs/troubleshooting/platforms#installing-the-cli) |
| `supported: false` and `graphify <version> is older than 0.9.56` | The kit requires Graphify 0.9.56 or later | Upgrade Graphify with `uv tool` |
| `Graphify skill not registered. Install Graphify, then retry.` | `plugins install graphify` ran before the CLI was usable | Install Graphify first, then re-run `pipeline-kit plugins install graphify --ide cursor` |
| No `.cursor/rules/graphify.mdc` after install | Cursor project install writes it through `graphify cursor install`. It only runs when the CLI works | Fix the CLI first, then re-run the install |
| `graphify extract failed (exit <n>).` | The official command failed. The kit prints its output | Run `graphify extract . --code-only` in a terminal and read the output |
| `graph is empty — extraction produced no nodes` in that output | Graphify found nothing it could index. Seen on an empty folder (verified) | Run it inside a project that has source files |
| `graphify update failed` with a message about shrinking | Graphify refused to replace a larger graph with a smaller one | Run `graphify update . --force` if the smaller graph is expected |
| `freshness: stale` in status | More than a fifth of indexed files changed or went missing | `pipeline-kit knowledge extract --update`. It is incremental and does not call a model |
| `freshness: unknown` | No `graphify-out/manifest.json` yet | Run `pipeline-kit knowledge extract` once |
| Graph indexes the pack folders | `.graphifyignore` lacks the pack paths | The kit adds `.pipeline/`, `.cursor/`, `.claude/`, `.github/skills/`, `pipeline_extensions/`, `features/`, `graphify-out/` and `wiki/codebase/` on extract. Run `pipeline-kit knowledge extract` once |
| `graphify-out/` still there after uninstall | By design | Use `plugins uninstall graphify --purge` to delete it |

`pipeline-kit scan` and QA test design need `graphify-out/graph.json`. If extract keeps failing, follow the manual steps on the [Graphify page](/docs/capabilities/graphify), then continue with [knowledge bootstrap](/docs/capabilities/knowledge).

## Archify

Archify is a pinned skill: `tt-a1i/archify` at `v2.16.0`. The kit runs `gh skill install` with `--pin`, never the default branch.

| Symptom | Cause | Fix |
|---------|-------|-----|
| `archify: missing` with `GitHub CLI with gh skill is required (v2.90+).` | `gh` is absent or has no `skill` command | Install or upgrade GitHub CLI to 2.90 or later |
| `Node.js 18+ is required.` or `Node.js <n> is too old; need 18+.` | No `node`, or an old one | Install Node.js 18 or later |
| `archify: unpinned`, `Installed Archify is <x>, expected v2.16.0.` | A different version of the skill is on disk | Run the pinned install command shown below |
| `gh skill install failed (exit <n>).` | `gh` could not install, for example no network or not logged in. Its output is printed after the message | Run the pinned command below in a terminal and read the error |
| `gh skill install exited 0 but the pinned Archify skill is missing.` | The skill folder is not where the kit looks | See the table below. Use matching `--ide` and `--scope` |
| `no .pipeline/config.json — run pipeline-kit init first` (exit 64) | `plugins install archify` writes its config flag first | Run `pipeline-kit init` |
| `architecture_diagrams.enabled: false` in status | Archify was never installed or the flag was turned off | `pipeline-kit plugins install archify --ide cursor --scope project` |
| No HTML diagram, `manifest.json` says `mermaid-fallback` | Archify missing or deliver failed | Expected and safe. `architecture.md` keeps its Mermaid. Fix the cause above to get the HTML |
| Uninstall refuses to delete | The folder is not verified as the managed `tt-a1i/archify` skill | Check the folder. Delete `.agents/skills/archify` by hand only if it is yours |

The pinned command, for project scope with Cursor:

```bash
gh skill install tt-a1i/archify archify --pin v2.16.0 --agent cursor --scope project
```

Where the skill lands, from the code:

| `--ide` | `gh` agent | Folder under the project (or home with `--scope user`) |
|---------|------------|------------------------------------------------------|
| `cursor` | `cursor` | `.agents/skills/archify` |
| `claude-code` | `claude-code` | `.claude/skills/archify` |
| `github` | `github-copilot` | `.agents/skills/archify` |

`--ide none` cannot install the skill. The config flag is still turned on and Mermaid stays the baseline.

### Mermaid fallback

Mermaid in `architecture.md` is required. A missing `gh`, Node or skill, or a failed `deliver`, never blocks a valid Mermaid architecture. Architect records `mermaid-fallback` in `features/{slug}/diagrams/manifest.json`. A failed Archify install exits 1 but still leaves the flag on. That is why the message says Architect will use the fallback until Archify is ready.

### Unattended runs

Set `ARCHIFY_UPDATE_CHECK_DISABLED=1` so Archify does not fetch an update manifest. The kit sets this default for its own install call. Delivered HTML contains inline JavaScript, so treat it as active content before you publish it.

## Still stuck

Check the version in use against the page you are reading (`pipeline-kit --version`), then open an issue with the output of `pipeline-kit plugins status` and `pipeline-kit doctor`.
