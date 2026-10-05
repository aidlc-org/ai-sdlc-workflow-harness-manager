# pipeline-kit-portal

Local admin web dashboard for pipeline-kit: which **features, plugins, and
extensions** are configured in each project, and the **health** of each
project's pipelines (runs, sign-off gates, observability-ledger scores) —
across several registered projects at once, grouped by team.

## Install

From the pipeline-kit checkout (recommended while developing):

```bash
pip install -e packages/pipeline-kit-portal -e .
```

> `uv tool install -e ".[portal]"` is the packaged-install path once the
> optional extra resolves in your environment; the direct path install above
> always works from a checkout.

Confirm:

```bash
pipeline-kit portal --help
```

## Usage

```bash
pipeline-kit portal add /abs/path/to/checkout-api --team payments --label "Checkout API"
pipeline-kit portal add /abs/path/to/payments-web --team payments
pipeline-kit portal list
pipeline-kit portal serve          # prints http://127.0.0.1:7171/?t=<token>
pipeline-kit portal remove /abs/path/to/payments-web
```

`serve` takes no project argument requirement beyond the registry — it shows
every project added with `portal add` (plus the one you launch from, which
is auto-registered). Useful flags:

| Flag | Effect |
|------|--------|
| `--port`, `--host` | Bind address (default `127.0.0.1:7171`) |
| `--read-only` | Disable every write endpoint |
| `--no-token` | Disable the per-launch token (same-machine trust only) |
| `--allow-remote` | Permit a non-loopback `--host` (token still required unless `--no-token`) |
| `--open` | Open the URL in a browser |
| `--home` | Registry location (default `~/.pipeline/portal/`) |

## What it reads, and what it never does

Every panel is backed by a documented, print-free read — `pipeline_portal`
never prints or parses CLI stdout:

| Panel | Source |
|-------|--------|
| Install / drift | `.pipeline/install.json` |
| Features | `pipeline_features.commands.snapshot` |
| Plugins | `pipeline_plugins.graphify` / `.archify`, `knowledge.overlay` |
| Observability | `pipeline_observability.export` (config + ledger size/offset) |
| Runs & gates | `.pipeline/state/runs/*.json` |
| Kit-mode boards | `features/{slug}/pipeline-state.json` (resolved via `pipeline_kit.paths`, so a linked memory bank still works) |
| Ledger scores | `pipeline_observability.scoring.score_ledger` |
| Doctor | the same three `*_doctor_checks(...)` functions `pipeline-kit doctor` calls |

**It never imports or executes a registered project's own Python** — no
`pipeline_extensions/*.py`, no copied `.pipeline/loader/*.py`. Those vary by
project and by version; a fleet server reading many repos cannot safely put
project-local code on `sys.path`. Everything project-specific is read as
plain JSON off disk instead.

**It never runs `init`/`update`** for a registered project. Those copy ~170
files and merge IDE hooks — too large a write to trigger from a browser. A
project that is missing or behind the installed kit version is flagged with
the exact command to run yourself.

**Writes are the existing CLI, not a second writer.** A feature/plugin/obs
toggle calls the same `cmd_enable` / `cmd_install` / `cmd_install` functions
`pipeline-kit features` / `plugins` / `obs` already call, so the dashboard
and the CLI can never disagree about how `config.json` gets written. Every
write is appended to `{project}/.pipeline/state/portal/audit.jsonl`.

## Security model

- Binds `127.0.0.1` by default. A non-loopback `--host` requires
  `--allow-remote` and is still gated by the token unless `--no-token` is
  also passed.
- A `secrets.token_urlsafe(32)` per launch, printed in the URL, required on
  every `/api/*` call (`?t=` or `X-Portal-Token`), compared with
  `secrets.compare_digest`.
- `Host`/`Origin` must match the bound loopback address and port, which
  blocks a stray browser tab or DNS-rebinding page from reaching the API.
- A write carries the `config_mtime` the UI rendered; a mismatch returns
  `409` instead of silently overwriting a concurrent CLI edit.
