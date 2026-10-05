---
title: Portal
description: Local admin web dashboard across several projects — features, plugins, extensions, and pipeline health. Separate package, needs the .[portal] extra.
---

`pipeline-kit portal` is a **local, loopback-only web dashboard** over
several registered projects at once, grouped by team: which
[features](/docs/capabilities/feature-flags), [plugins](/docs/capabilities/plugins),
and [extensions](/docs/capabilities/extensions) are configured where, and the
health of each project's pipelines (runs, [planning gates](/docs/capabilities/planning-gates),
[agent-run observability](/docs/capabilities/observability) scores). It does
**not** run workflows, does **not** run `init`/`update` for you, and does
**not** add a second way to write `config.json` — every toggle calls the same
CLI functions `features` / `plugins` / `obs` already call.

Like [repo assessment](/docs/capabilities/overview), this is a **separate
package**, not a bundled capability: install it with the `portal` extra
before `pipeline-kit portal` exists as a command.

## What you get

| Piece | Location | Role |
|-------|----------|------|
| Registry | `~/.pipeline/portal/projects.json` (`--home` to override) | Which projects this portal instance shows, with a team label |
| Server | stdlib `http.server`, no new runtime dependency | Loopback bind, per-launch token, POST-only writes |
| Fleet view | `/` | One card per registered project, grouped by team, severity-sorted |
| Project view | Setup / Health / Config tabs | Toggles, run & gate state, ledger scores, read-only `config.json` |
| Audit log | `{project}/.pipeline/state/portal/audit.jsonl` | One line per write, same shape as the orchestrator's own event log |

## Install

```bash
pip install -e packages/pipeline-kit-portal -e .
# packaged path once the extra resolves in your environment:
# uv tool install -e ".[portal]"
```

```bash
pipeline-kit portal add /abs/path/to/checkout-api --team payments --label "Checkout API"
pipeline-kit portal add /abs/path/to/payments-web --team payments
pipeline-kit portal list
pipeline-kit portal serve --open
pipeline-kit portal remove /abs/path/to/payments-web
```

`serve` prints a URL with a per-launch token, e.g.
`http://127.0.0.1:7171/?t=<token>`. Useful flags: `--port`, `--host`,
`--read-only` (disables every write route), `--no-token` (same-machine trust
only), `--allow-remote` (permits a non-loopback `--host`; the token
requirement never relaxes).

## What it never does

- **Never imports or executes a registered project's own Python** — no
  `pipeline_extensions/*.py`, no copied `.pipeline/loader/*.py`. Those vary
  by project and by version; a fleet server reading many repos reads them as
  plain JSON off disk instead, never as code on `sys.path`.
- **Never runs `init`/`update`.** A project that is missing the pack, or
  behind the kit version this portal ships with, is flagged with the exact
  command to copy — a drift *report*, not a trigger.
- **Never triggers a workflow run.** Reading `.pipeline/state/runs/*.json`
  and `features/{slug}/pipeline-state.json` is how it shows progress; starting
  one still needs the IDE/agent session.

## Security model

- Binds `127.0.0.1` by default.
- A `secrets.token_urlsafe(32)` per launch, required on every `/api/*` call,
  compared with `secrets.compare_digest`.
- `Host`/`Origin` must match the bound loopback address and port — blocks a
  stray browser tab or a DNS-rebinding page from reaching the API.
- A write carries the `config_mtime` the UI rendered; a stale value returns
  `409` instead of silently overwriting a concurrent CLI edit.

Full detail: kit repo `packages/pipeline-kit-portal/README.md`.
