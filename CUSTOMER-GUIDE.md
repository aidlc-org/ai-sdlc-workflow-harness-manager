# Pipeline kit — customer guide

| Attribute | Value |
|-----------|--------|
| Type | Handbook |
| Audience | Developers and architects installing this pack on a customer engagement |
| Adapt | Do not add a customer app, host, or tracker URL here. Overlay those in the project `config.json` and local-deploy files. |

Audience: **developers and senior architects** who need a delivery pipeline
they can install, adapt, and scale across many customer engagements — each
with a different process, stack, and IDE — without forking a new agent
framework every time.

The rest of this file is the adaptation handbook (install, `AGENTS.md`,
config, deploy, tests). Read the problem and architecture first.

---

## Problem statement

Teams already use coding agents. What they lack is a **repeatable operating
model** for those agents:

1. **Context explosion.** If every skill, agent brief, rule, and wiki page
   lives under `.cursor/` (or `.claude/`), the IDE auto-discovers them. Every
   turn loads far more than the current step needs. Cost and quality both
   degrade as the pack grows.

2. **Pipeline glued to one IDE.** Process (how you plan, specify, implement,
   test, deploy) was mixed with editor wiring. Moving from Cursor to Claude
   Code, or to a repo with no AI folder, meant copying and rewriting the
   whole tree.

3. **One customer’s process baked into another’s repo.** Folder names, ports,
   tracker projects, verify commands, and deploy targets leaked into skills.
   The next customer on Spring + Jira could not reuse the pack without a
   surgical rewrite.

4. **No productized install.** “Copy `.cursor` from last year’s repo” does
   not scale. Architects need project install, user install, and a path to
   org-wide defaults — with a clear override order.

5. **Every ask became the same ladder.** A “how does tax work?” question
   should not start PM → BA → developer. A bug should not run a full feature
   plan. Without a **workflow** as a first-class object, the parent invents
   a new procedure each time.

6. **Hard to add a process.** A new customer wants “architecture review”
   or “release checklist.” That should be a new workflow JSON + skill + a
   config chain — not a new platform.

The requirement: **one kit, many customers, many processes.** Process lives
in a portable pack. The IDE is a thin adapter. Each engagement customizes
config and a few runbooks, not the engine.

---

## How this architecture solves it

```text
IDE adapter (one skill)     .cursor | .claude | .github | none
        │
        ▼
   run-workflow             receptionist: pick workflow, run loader
        │
        ▼
   .pipeline pack           skills, agents, workflows, wiki, rules
        │
        ├── config.json     THIS engagement (verify, deploy, tracker)
        └── loader          allowlist for the current step only
        │
        ▼
   features/{slug}/         artifacts for this run (not product source)
```

**Portable pack, thin IDE.** All process files sit in `.pipeline/`. The IDE
folder holds **only** `run-workflow` (and optional hooks). Cursor, Claude
Code, and GitHub each get the same pack; only the adapter path changes
(`--ide cursor` | `claude-code` | `github` | `none`).

**Workflow as the unit of scale.** A workflow is a named procedure
(`ask`, `feature-development`, `jira-bug`, …) with a chain and a file
allowlist. Adding a customer-specific process means adding a workflow —
not cloning the kit. Different customers can enable different workflows
from the same pack.

**Allowlist per step.** The loader writes `allowed_reads` for the current
specialist. BA does not ingest the deploy runbook; the developer does not
ingest Jira intake. That is what keeps a large pack cheap enough to reuse
across accounts.

**Config is the engagement overlay.** Chains, tracker on/off, path-based
verify reminders, and deploy target names live in `.pipeline/config.json`.
Skills stay free of customer folder names and site URLs. The next account
changes config (and the local-deploy script), not the orchestration skill.

**Install scopes.** `--project` materializes `<repo>/.pipeline`. `--user`
materializes `~/.pipeline`. At runtime the project pack wins; otherwise
the user pack is used. Artifacts always land in the **current** repo’s
`features/`. Architects can later layer org template → user → project
without changing the runtime model.

**Receptionist, not a monolith.** `AGENTS.md` stays a routing table. The
agent does not load the pack until `run-workflow` runs the loader. Trivia
and off-repo asks skip the pipeline entirely.

What you take to the next customer: the **kit** (installer + bundled pack).
What you change per customer: `AGENTS.md`, `config.json`, deploy/test
runbooks. That is the scaling contract.

---

## Two kits (pick one at init)

This product ships **two kits**. Same first-party workflow names
(`ask`, `feature-development`, Jira). Different how a step runs. Pick
one per project. Do not mix.

| | **Kit mode** (default) | **Orchestrator mode** |
|--|------------------------|------------------------|
| Flag | `pipeline-kit init --ide cursor` | `pipeline-kit init --mode orchestrator --ide cursor` |
| What it is | Markdown pack in `.pipeline/` | Python engine in the wheel |
| How work runs | IDE `run-workflow` + loader | `pipeline-kit run` / `approve` / `resume` |
| What `init` copies | Skills, agents, loader, workflows, wiki, hooks, docs | Slim `.pipeline/` (config, hooks, wiki, docs). No skills/loader/workflows |
| Extra workflows | Skill + JSON + `config.json` | `pipeline_extensions/*.py` |
| Extra install | None | `uv tool install -e ".[orchestrator]"` and `CURSOR_API_KEY` |

If you are unsure, use **kit mode**. Orchestrator mode does not inherit
chat text — pass `--request` or `features/<slug>/request.md`.

Add a process with [`extensions/`](./extensions/). Optional add-ons live
under [`capabilities/`](./capabilities/) (plugins, knowledge, observability,
eval, feature flags). Commands for both kits are in §2.

---

## 1. What you get

| Path | Role |
|------|------|
| `.pipeline/` | Workflows, skills, agent briefs, rules, wiki, loader |
| `.pipeline/config.json` | **Your** chains, tracker, verify reminders, deploy targets |
| `.pipeline/docs/CUSTOMER-GUIDE.md` | This guide (copied into the project on install) |
| `.pipeline/docs/DOCUMENT-STANDARD.md` | How pack markdown is structured and what a project may change |
| `.cursor/skills/run-workflow/` or `.claude/skills/run-workflow/` | The only IDE-discovered skill |

Specialist briefs and skill bodies stay under `.pipeline/` so the IDE does
not auto-load them. The parent reads only the allowlist from the loader.

**Workflows shipped today**

| Name | When it runs |
|------|----------------|
| `ask` | Question about this repo (how / what / why / explain). No Task chain. |
| `feature-development` | Product work from chat (“add”, “fix”, “change”, “implement”). Feature class: PM → user sign-off → Architect (large stories) → user sign-off → BA → critic → user sign-off → developers. |
| `jira-story` / `jira-epic` / `jira-bug` | Tracker issue key, if Jira intake is enabled. Stories/epics use intake as the requirements pack (same Architect + sign-off gates). Bugs skip planning. |

---

## 2. Install

Install the command once on each developer machine:

```bash
# Directly from the repository
uv tool install git+<pipeline-kit-repo-url>

# Alternative
pipx install git+<pipeline-kit-repo-url>
```

From a local clone, `./install.sh` selects `uv` or `pipx` and installs the
same command.

Then initialize a customer project:

```bash
cd /path/to/your-app
pipeline-kit init --ide cursor
pipeline-kit doctor --ide cursor
pipeline-kit workflows
```

Default `--mode kit` copies the markdown pack. See [Two kits](#two-kits-pick-one-at-init)
if you have not chosen yet.

### Choosing an IDE (`--ide`)

The kit works with **Cursor**, **Claude Code**, and **GitHub Copilot CLI**. Pick one per project:

| IDE | Flag | Setup | Use case |
|-----|------|-------|----------|
| **Cursor** | `--ide cursor` | GUI editor (VSCode fork). Open repo root. | Most common; full context control. |
| **Claude Code** | `--ide claude-code` | CLI or desktop app. Works anywhere Python runs. | Remote dev, no VSCode. Lightweight. |
| **GitHub Copilot CLI** | `--ide github` | Terminal tool. Runs `copilot_cli` command. | Shell-first workflows, zero-UI. |
| `none` | `--ide none` | No IDE adapter. Run workflows from orchestrator only. | CI/CD, test harnesses. |

All options ship the same `.pipeline/` pack. Only the IDE folder location changes (`.cursor/`, `.claude/`, `.github/`).

**Portable across IDEs:** If you commit the IDE config to git, teammates can use it on their own IDE by re-running `init`. The interpreter is detected per machine, so:

```bash
# On machine A (Windows): detected python
# You commit the config to git
# On machine B (Linux): run init again to pick up python3
git clone …
pipeline-kit init --ide cursor  # auto-detects the right interpreter
```

If you skip the re-run, hooks may fail silently on the second machine (wrong interpreter). Re-running `init` or `update` is safe — it replaces stale hook entries and keeps everything else intact.

### Orchestrator mode (optional, parallel)

`--mode orchestrator` does **not** copy `agents/`, `skills/`, `loader/`, or
`workflows/`. The chain lives in the installed wheel. Associates add their
own workflows in `pipeline_extensions/`; kit mode never loads those files.

```bash
# install the Cursor SDK extra once (kit mode does not need this)
uv tool install -e ".[orchestrator]"
cd /path/to/your-app
pipeline-kit init --mode orchestrator --ide cursor
# set CURSOR_API_KEY from Cursor Dashboard -> Integrations
# chat text is not inherited; pass it or write features/<slug>/request.md
pipeline-kit run --slug checkout-redesign --workflow feature-development \
  --request "redesign checkout so guests can pay without an account"
pipeline-kit approve --slug checkout-redesign --gate requirements
pipeline-kit resume --slug checkout-redesign
pipeline-kit workflows --scaffold security-review
pipeline-kit run --slug pci-gap --workflow security-review --runner fake \
  --request-file features/pci-gap/request.md
```

Copy-ready examples live in the kit repo at
[`extensions/orchestrator/`](./extensions/orchestrator/)
(`security-review`, `ci-audit`, `dependency-audit`,
`accessibility-review`). Copy `pipeline_extensions/` into the customer
app; they are not installed by `init`.

Custom workflows are orchestrator-only. They do not appear in kit-mode
`pipeline-kit workflows` listings and do not change `.pipeline/workflows/`.

The wheel is version-pinned, not a hard sandbox: a developer can still
edit their own `site-packages`. Every run records `workflow_provider` and
`kit_version`.

#### Model choice

The sealed graph still picks the next agent. Before each agent, the engine
asks a decider which Cursor model should run that step. Configure it under
`orchestrator` in `.pipeline/config.json`.

| Key | Meaning |
|-----|---------|
| `decider` | `jev` (default, TypeSafe Choice, needs `TYPESAFE_API_KEY`) or `fixed` (no network) |
| `fallback_model` | Used when Jev is off, the call fails, or confidence is below `jev.min_confidence` |
| `models.candidates` | Shortlist Jev may pick from, intersected with this account’s live Cursor list. Empty `[]` sends every catalog id. |
| `models.cards` | Optional overlay: `kind`, `fit`, `display_name`, `description` for an id already in `candidates` |
| `models.steps` | Pin one agent to an id. That step skips Jev. |
| `jev.min_confidence` | Floor (kit default `0.5`). Below it, `fallback_model` runs and stdout still shows `jev_choice` |

Do **not** put the same details in both `candidates` and `cards`. Use one form:

- **One list:** `{ "id": "glm-5.2", "kind": "reasoning", "fit": "…" }` inside `candidates`
- **Id + overlay:** `"glm-5.2"` in `candidates`, details under `models.cards.glm-5.2`

`kind` is `coding`, `reasoning`, `general`, or `writing`. That value drives
`for_this_agent` (planning/review mark Composer poor fit; implementation
marks it good). The id must already appear in `Cursor.models.list()`. A
name that exists only in config is skipped.

`--dry-run` asks the decider and prints `need`, `basis`, `sent`, scores,
then a `summary` table. It does not start Cursor agents. Without
`CURSOR_API_KEY` it prints `reason=catalog_unavailable` and exits 0.
`--change-class micro` only runs coding steps, so Composer is the expected
pick. Use `feature` to see planning and review.

Sign-off gates do not ask the decider. Full examples:
[`orchestrator/README.md`](./orchestrator/README.md#model-choice).


| Command | Purpose |
|---------|---------|
| `pipeline-kit init [project]` | Install/update `<repo>/.pipeline` and its IDE adapter |
| `pipeline-kit setup` | Install/update `~/.pipeline` and a user IDE adapter |
| `pipeline-kit update [project]` | Refresh managed files while retaining local `config.json` values |
| `pipeline-kit update --user` | Refresh the user pack |
| `pipeline-kit doctor [project]` | Check Python, pack, config, loader, marker, and optional IDE adapter |
| `pipeline-kit workflows [project]` | List workflows from the active project or user pack |
| `pipeline-kit uninstall [project]` | Remove managed project files |
| `pipeline-kit uninstall --user` | Remove managed user files |
| `pipeline-kit knowledge init [project]` | Opt-in: create `test-knowledge/` and set `test_design.enabled` |
| `pipeline-kit knowledge extract [project]` | Run official `graphify extract . --code-only` (no homemade graph) |
| `pipeline-kit scan [project]` | Assess the repo. Requires the `assess` package and an `assess` license. See Assessment below. |
| `pipeline-kit knowledge status [project]` | Graphify CLI and `graphify-out/graph.json` |
| `pipeline-kit plugins list` | List Graphify / Archify (observability uses `obs status`) |
| `pipeline-kit plugins install graphify [project]` | Register the official Graphify IDE skill |
| `pipeline-kit plugins install archify [project]` | Pin Archify `v2.16.0` and set `architecture_diagrams.enabled` |
| `pipeline-kit plugins status [project]` | Graphify CLI and Archify skill status |
| `pipeline-kit plugins uninstall graphify [project]` | Remove the Graphify IDE skill (`--purge` deletes `graphify-out/`) |
| `pipeline-kit plugins uninstall archify [project]` | Remove the managed Archify skill; keep `features/*/diagrams/` |
| `pipeline-kit obs install [project]` | Merge fail-open agent-run hooks (Langfuse first). Does not replace existing hooks. |
| `pipeline-kit obs report [project]` | Local scores from the ledger. No network. |
| `pipeline-kit obs flush [project]` | Ship new ledger rows to the configured adapter. |
| `pipeline-kit memory link <root> [project]` | Link external artifact bank (needs `.[memory]`) |
| `pipeline-kit memory index / search / mcp` | Index, query, or run the memory MCP server |
| `pipeline-kit portal add <path> [--team] [--label]` | Register a project in the portal's fleet (needs `.[portal]`) |
| `pipeline-kit portal serve [project]` | Start the local admin dashboard (loopback + per-launch token by default) |
| `pipeline-kit portal list` / `remove <path>` | List or unregister fleet projects |

Full agent-run observability handbook (install, Langfuse identity, scores, ideal values, troubleshooting): **[OBSERVABILITY.md](./OBSERVABILITY.md)** (copied to `.pipeline/docs/OBSERVABILITY.md` on `init`).

Flush traces use Cursor `conversation_id` as the Langfuse trace/session (not the feature slug). User prompt comes from `beforeSubmitPrompt` or the transcript on flush.

Install/update commands accept `--ide cursor`, `claude-code`, `github`, or
`none`. Add `--agent-stubs` to create thin `.cursor/agents/*.md` files.

Resolution at run time: project `.pipeline` wins; otherwise `~/.pipeline`.
Run artifacts default to **this project’s** `features/{slug}/`. Optionally link an
**external memory bank** so artifacts live in a separate git repo (see Memory bank below).

Open the repository root in the IDE so the skill folder is discovered.

The old `python3 install.py` flags remain available for compatibility and
for the maintainer-only `--sync-kit` operation.

### 2.0.1 Guardrail hooks (code minimalism and dependencies)

The kit includes optional **guardrail hooks** that fire before tool use to
enforce code minimalism:

- **Dependency gate**: Blocks undeclared `npm install`, `pip install`, etc.
  and direct edits to `package.json`, `requirements.txt`, etc.
  Architect declares dependencies with a reason; gate reads that declaration.
  Break-glass: `PIPELINE_ALLOW_DEPS=1`.

- **Code minimalism policy**: A decision ladder (reuse → stdlib → platform →
  install → one-liner → minimum) shipped with the kit in `.pipeline/`. Agent
  briefs link to it. See [`minimalism-policy.md`](./.pipeline/skills/feature-development/assets/minimalism-policy.md).

Hooks are **not required** and do not turn on by default. To enable:

```bash
# The hooks are already in place; they fire on all IDEs (Cursor, Claude Code, Copilot).
# Just write a declaration when the gate fires, or set PIPELINE_ALLOW_DEPS=1 to override.
```

Full hook reference: [`.pipeline/hooks/README.md`](./.pipeline/hooks/README.md)

### 2.0.2 Memory bank (optional external artifacts)

By default, feature artifacts stay in the product repo under `features/{slug}/`.
For multi-repo product lines or a shared org archive, install the optional
memory package and link an external git folder:

```bash
pip install -e packages/pipeline-kit-memory -e .
pipeline-kit memory link ../pipeline-memory --project-id my-app
pipeline-kit memory import-local    # one-time copy of existing features/
pipeline-kit memory index
pipeline-kit memory search "oauth decision" --json
pipeline-kit memory doctor
```

- **Flat layout** (one product ↔ one bank): `{root}/features/{slug}/…`
- **Namespaced** (`--project-id`): `{root}/projects/{id}/features/{slug}/…`
- Run cursor under `.pipeline/state/` always stays in the product project.
- Search works from the CLI without MCP (`memory search`). Re-run `memory index`
  after artifact changes.

#### MCP (optional — user must register the server)

Memory does **not** auto-wire into the IDE. Each developer adds a **stdio MCP
server** entry in their client config, then restarts the client.

1. Install so `pipeline-memory-mcp` is on PATH (same env as above).
2. Ensure the product is linked and indexed (`memory link` / `memory index`).
3. Add MCP config (absolute `--project` = product repo with `.pipeline/config.json`):

**Cursor** (`.cursor/mcp.json` or global MCP settings):

```json
{
  "mcpServers": {
    "pipeline-memory": {
      "command": "pipeline-memory-mcp",
      "args": ["--project", "C:/path/to/your-product-repo"]
    }
  }
}
```

**VS Code / Copilot MCP** (workspace or user MCP JSON; key name may be `servers`):

```json
{
  "servers": {
    "pipeline-memory": {
      "type": "stdio",
      "command": "pipeline-memory-mcp",
      "args": ["--project", "C:/path/to/your-product-repo"]
    }
  }
}
```

**Claude Desktop** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "pipeline-memory": {
      "command": "pipeline-memory-mcp",
      "args": ["--project", "C:/path/to/your-product-repo"]
    }
  }
}
```

If the console script is missing from PATH, point `command` at your `python.exe`
and use args: `-m`, `pipeline_memory.mcp_server`, `--project`, `<product path>`.

4. Restart the IDE. Tools: `memory_search`, `memory_why`, `memory_get`,
   `memory_list_slugs`, `memory_list_files`.
5. You do not keep `memory mcp` running in a terminal for daily use — the client
   spawns stdio when a tool is called. Use the terminal for link/index/search/debug.

Full detail, troubleshooting, and checklist:
[`packages/pipeline-kit-memory/README.md`](./packages/pipeline-kit-memory/README.md).

### 2.0.3 Portal (optional local admin dashboard)

A read-mostly local web dashboard across several projects: which features,
plugins, and extensions are on where, and the health of their pipelines
(runs, sign-off gates, observability-ledger scores). It is a separate
package, installed and run the same way as assess/memory:

```bash
pip install -e packages/pipeline-kit-portal -e .
pipeline-kit portal add ../checkout-api --team payments --label "Checkout API"
pipeline-kit portal add ../payments-web --team payments
pipeline-kit portal serve
```

- One registry (`~/.pipeline/portal/projects.json`, override with `--home`)
  lists every project the portal shows — not just the one you launch from.
- Binds `127.0.0.1` and prints a per-launch token in the URL; writes are
  POST-only and refused entirely with `--read-only`. A non-loopback `--host`
  needs `--allow-remote` and keeps the token requirement.
- Never imports or runs a registered project's own code (no
  `pipeline_extensions/*.py`, no copied `.pipeline/loader/*.py`) — every
  project is read through its own JSON state files on disk.
- Toggles call the exact same functions as `pipeline-kit features` /
  `plugins` / `obs` — the dashboard is a view over those commands, not a
  second way to write `config.json`.
- The portal never runs `init`/`update` for you; a project that is missing
  or behind the installed kit version is flagged with the exact command to
  copy.

Full detail and the security model:
[`packages/pipeline-kit-portal/README.md`](./packages/pipeline-kit-portal/README.md).

### 2.1 Optional QA knowledge (opt-in)

`pipeline-kit init` / `update` do **not** turn this on. Absent
`test_design.enabled` keeps today’s planning ladder.

```bash
pipeline-kit init --ide cursor
pipeline-kit knowledge init --register-skill
# If graphify is missing, install it the official way, then:
pipeline-kit knowledge extract
```

Official Graphify (not a kit extra):

```text
uv tool install graphifyy
graphify install
graphify extract . --code-only
```

That writes `graphify-out/graph.json`. Pipeline-kit never imports Graphify
and never invents a substitute graph. If extract fails, stop and run those
commands. Then in the IDE: **Bootstrap QA knowledge for this repo**. Approve
one Markdown report. After that, “work on …” writes stepwise click-path
cases in `features/{slug}/qa-test-cases.md` when `test_design.enabled` is
true (open → sign-in from env names → navigate → click → assert).

Per feature when the flag is on: Architect writes a model delta (or
`no_test_model_change`) → BA binds ACs to overlay nodes → test-designer
writes `cases.json` and `qa-test-cases.md` → you sign off BA → developers
→ tester wave (unit / api / ui in parallel).

`pipeline-kit knowledge playwright --slug {slug}` is a projector of
`cases.json` + `locators.json` into the existing `automation-tests/` tree.
It is not Graphify and not `pipeline-kit plugins`.

`graphify-out/` is Graphify-owned. The team chooses whether to commit it or
ignore it. Do not create a second graph store.

### 2.2 Optional plugins

`pipeline-kit init` does not turn these on. Two kinds:

| Kind | What it is | Command |
|------|------------|---------|
| **External plugins** | Graphify and Archify. The kit never vendors them. | `pipeline-kit plugins …` |
| **Bundled add-on** | Agent-run observability (collector, ledger, scores, flush). Langfuse is an adapter, not a plugin. | `pipeline-kit obs install` — not `plugins install` |

```bash
pipeline-kit plugins list
pipeline-kit plugins status
pipeline-kit obs status
```

Graphify (QA graph) and Archify (Architect diagrams) are the **external**
plugins. Pipeline-kit never vendors them.

**Graphify** — official CLI. Compatibility path:
`pipeline-kit knowledge init --register-skill` still registers the Graphify
skill. Equivalent: `pipeline-kit plugins install graphify --ide cursor`.

```bash
uv tool install graphifyy
pipeline-kit plugins install graphify --ide cursor
pipeline-kit knowledge extract
pipeline-kit plugins uninstall graphify --ide cursor
pipeline-kit plugins uninstall graphify --ide cursor --purge   # also deletes graphify-out/
```

**Archify** — pinned Agent Skill `tt-a1i/archify` `v2.16.0`. Needs GitHub CLI
v2.90+ (`gh skill`) and Node.js 18+. Chrome is optional for `visual-check`.
Cursor project scope installs to `.agents/skills/archify/`. `--scope user`
installs under the home directory instead.

```bash
pipeline-kit plugins install archify --ide cursor --scope project
pipeline-kit plugins status --plugin archify
pipeline-kit plugins uninstall archify --ide cursor
```

The kit runs:

```text
gh skill install tt-a1i/archify archify --pin v2.16.0 --agent cursor --scope project
```

It never tracks the default branch. Uninstall deletes only a managed Archify
skill directory after verifying the source and path. Generated
`features/{slug}/diagrams/` files stay. `gh skill` has no remove command.

Architect mermaid in `architecture.md` remains required. When
`architecture_diagrams.enabled` is true, Architect also writes
`features/{slug}/diagrams/manifest.json` (`delivered` or `mermaid-fallback`).
Missing GitHub CLI, Node, Chrome, or a failed `deliver` must not block a
valid mermaid architecture.

Delivered HTML is self-contained interactive HTML (inline JavaScript). Treat
it as active content when publishing. Unattended runs should set
`ARCHIFY_UPDATE_CHECK_DISABLED=1` so Archify does not fetch an update
manifest. Archify does not send repository contents on that check.

**Agent-run observability** is first-party kit code copied into
`.pipeline/hooks/obs/` on `init` (off until you install). It records what
the coding agent did, not product analytics (`telemetry-agent`).

```bash
pipeline-kit obs install --ide cursor --adapter langfuse
# LANGFUSE_* in .env, never in config.json
pipeline-kit obs report
pipeline-kit obs flush
pipeline-kit obs uninstall
```

`features enable agent-observability` only sets
`agent_observability.enabled`. You still need `obs install` to merge IDE
hooks. Handbook: **[OBSERVABILITY.md](./OBSERVABILITY.md)** (also
`.pipeline/docs/OBSERVABILITY.md` after `init`).

---

## 3. What you must configure (every new project)

Two files. Nothing else is required for the first run.

### 3.1 `AGENTS.md` (create or edit)

Keep a short product blurb (what this repo is, how to build/test). Then add
the routing table. Do **not** paste specialist briefs or skill bodies here.

```markdown
# {Project name} — agent instructions

{One paragraph: what this repo is. Language, how to test.}

**Default read.** For product work or a question about this repo, follow the
IDE `run-workflow` skill. Run the loader and read only `allowed_reads`.
Do not open every file under `.pipeline/skills/`.

Unrelated asks (weather, locations, trivia): do not run the loader.

## Which workflow to use

| User intent | What to do |
|-------------|------------|
| Product work (“work on …”, “fix …”, “change …”, “develop …”, “implement …”, “add …”, or a tracker issue key) | Follow `.cursor/skills/run-workflow/SKILL.md` (or `.claude/skills/run-workflow/SKILL.md`). Run `.pipeline/loader/load_workflow.py` (or `~/.pipeline/loader/load_workflow.py`). Read **only** `allowed_reads`. |
| Question about this repo (how / what / why / where / explain) | Same skill, workflow `ask`. No Task chain. |
| Bootstrap QA knowledge for this repo | Workflow `test-knowledge-bootstrap`. Not the feature ladder. |
| Unrelated asks | Do not run the loader. |

Chains and skips: `.pipeline/config.json`.
File lists: `.pipeline/workflows/`.
Specialist briefs: `.pipeline/agents/`.
Specialist Tasks: `generalPurpose` plus `Follow .pipeline/agents/{name}.md`
(or the named Cursor type if you installed `--agent-stubs`).
```

Use the skill path that matches `--ide`.

**Why this file:** it is the first thing the agent reads. Without the table,
it may start a full delivery ladder for a question, or implement a feature
without the harness.

### 3.2 `.pipeline/config.json`

The installed file is a **generic template**. Edit the keys below. Do not put
secrets, host URLs, or tracker site URLs in any other pack file.

---

## 4. `config.json` — what each area is for

### 4.1 `verify.rules` — remind after edits

After a specialist edits a file, a hook (if present) injects a reminder.
Match a **path substring** from *your* tree.

```json
"verify": {
  "rules": [
    {
      "match": "/frontend/",
      "message": "You edited the UI. Run the frontend build and keep empty/error/loading states."
    },
    {
      "match": "/backend/",
      "message": "You edited the API. Run the unit tests for the module you changed."
    }
  ]
}
```

| Your stack | Typical `match` | Reminder |
|------------|-----------------|----------|
| React / Vue / Angular app in `web/` or `ui/` | `"/web/"` or `"/ui/"` | `npm run build` (or `ng build`) in that folder |
| Spring / Maven | `"/src/main/java/"` | `mvn -pl <module> test` |
| .NET | `"/src/"` | `dotnet test` |
| Python / Django / FastAPI | `"/app/"` or `"/src/"` | `pytest` for the module you touched |
| Go | `"/internal/"` | `go test ./...` |
| Mobile (`ios/`, `android/`) | `"/ios/"` / `"/android/"` | The existing unit/UI test command |
| Docs-only or unknown | `[]` | No reminder; add rules when folders are stable |

**Use case:** Developer changes `frontend/src/Cart.tsx`. The reminder fires.
They should not claim SUCCESS without a build.

Empty `[]` is valid. The pipeline still runs.

### 4.2 `deploy.target` / `deploy.targets` — which process to start

Devops receives `DEPLOY_TARGET` from the parent. Values must match **your**
runbook and script (section 5), not leftover names from another engagement.

```json
"deploy": {
  "target": "auto",
  "targets": ["auto", "web", "api", "both"]
}
```

| Ask | Target you would inject |
|-----|-------------------------|
| Copy change on the homepage | `web` |
| API-only bug | `api` |
| New field on UI + new endpoint | `both` or `auto` |

The shipped `deploy-local.sh` is a **placeholder**. It writes
`OVERALL=failed` until you implement build, serve, and health for this
repository (section 5). Set `targets` to the names you will implement.

### 4.3 `intake.jira` — tracker or not

| Situation | What to set |
|-----------|-------------|
| No Jira (or Azure Boards, GitHub Issues only) | `"enabled": false` |
| Jira + IDE MCP connected | `"enabled": true`, fill `mcp_namespaces` if the server name is not discovered |
| Jira types differ (`Defect`, `Incident`, `Spike`) | Edit `issue_type_map` |

```json
"intake": {
  "jira": {
    "enabled": false,
    "key_pattern": "\\b[A-Z][A-Z0-9_]+-[0-9]+\\b",
    "mcp_namespaces": [],
    "issue_type_map": {
      "story": "jira-story",
      "bug": "jira-bug",
      "defect": "jira-bug",
      "epic": "jira-epic",
      "default": "jira-story"
    }
  }
}
```

**Use case, enabled:** “Work on ISSUE-1842” → intake fetches the issue →
story, bug, or epic workflow. No one pastes the ticket by hand.

**Use case, disabled:** The same sentence is treated as text
(`feature-development` or `ask`). Correct for repos with no tracker.

Connect the tracker MCP in the IDE. Tool names in config default to
`getJiraIssue` and `searchJiraIssuesUsingJql`. Change `tools` if your MCP
uses different names. Do not put the Jira site URL or API token in this file.

### 4.4 Leave as-is until you have a reason

| Key | Default meaning |
|-----|-----------------|
| `workflows.*` chains / `classes` | Delivery ladder (micro / minor / feature). Change only if you drop or add a specialist. Feature class includes `@signoff:*`, optional `ui-designer-agent`, and `architect-agent`. Drop `ui-designer-agent` from the feature chain to disable the seat for this engagement. |
| `product.artifact_dir` | `features/` — analysis agents write here only. |
| `gates.retry_cap` | Critic `changes-required` retries (default 2). |
| `gates.consult_cap` | Architect/BA UI-designer consult inserts (default 1). Override one run with `CONSULT_UI: true`. |
| `gates.require_planning_signoff_before_build` | User must approve PM / Architect / BA artifacts before waves (default true). |
| `waves.child_chain` | Per-child developer → critic. Telemetry only if `RUN_TELEMETRY`. |
| `orchestrator.decider` | Orchestrator mode only. `jev` or `fixed`. Kit mode ignores this block. |
| `orchestrator.models.candidates` | Shortlist sent to Jev. See [Model choice](#model-choice). |
| `orchestrator.models.cards` | Optional fit/kind overlay. Do not duplicate an object already in `candidates`. |
| `orchestrator.models.steps` | Pin one step. That agent skips Jev. |
| `orchestrator.jev.min_confidence` | Confidence floor before `fallback_model` is used. |

PM, Architect, and BA follow **clarify-first**: they read prior `features/{slug}/`
artifacts (`decisions.md`, plan, architecture) before asking, then ask remaining
checklist items instead of silent defaults. Override UI designer with
`RUN_UI_DESIGNER: true|false` (policy in
`.pipeline/skills/feature-development/assets/ui-designer-policy.md`). Override
Architect with `RUN_ARCHITECT: true|false`. Size policy lives in
`.pipeline/skills/feature-development/assets/architect-policy.md`.

**New dependencies.** Architect declares each one in
`features/{slug}/state/architect-agent.json` `context.new_dependencies`
(`name` + `why_nothing_existing_works`) and mirrors it in
`HANDOFF-architect.md`. Developer cannot install or add to a manifest what was
not declared — the refusal names the package. Micro, minor, and bug work take
no new dependencies at all. Ladder and table in
`.pipeline/skills/feature-development/assets/minimalism-policy.md`; one-run
escape is `ALLOW_DEPENDENCY={name}`.

---

## Operator guardrails (do not skip)

These are **process and tool policy**, not a security certification. Read them
before anyone else runs the pack.

- Do **not** set `PIPELINE_ALLOW_ALL=1` or `PIPELINE_HOOK_SKIP=1` on a shared
  or customer machine. Those disable commit, network, MCP, and artifact gates.
- Do **not** copy `features/{slug}/ui/` into application source. Mockups are the
  visual contract. Developer translates them into the product stack. The write
  hook denies HTML/CSS that look like those mockups outside `features/`.
- Treat `ui-design.md` and `ui/*.html` as a **design contract**, not production UI.
- Pilots and demos: no production secrets and no real PII in PRDs or mockups.
- Honor HITL files (`signoff-requirements.md`, `signoff-ba.md`). Do not spawn
  `developer-agent` because a specialist wrote `next_agent: developer-agent`.
- `CONSULT_UI: true` overrides `gates.consult_cap` for one run. It is not a
  license to skip UI policy or requirements sign-off.

---

## 5. Adapt local deploy (different tech)

The shipped runbook and script are **empty overlays**. They do not start
an application until you fill them in. For any stack, edit these three:

| File | What to change |
|------|----------------|
| `.pipeline/config.json` → `deploy.targets` | Names you will pass as `DEPLOY_TARGET` |
| `.pipeline/skills/local-deployment/assets/local-deploy-runbook.md` | How a human (and devops) starts **your** apps |
| `.pipeline/skills/local-deployment/scripts/deploy-local.sh` | Build, start, and health-check **your** folders and ports |

**Do not** leave another product’s folder names, ports, or process names
in the script. Until the script matches this repository, devops must not
report SUCCESS.

### Examples

**React (Vite) + Node API**

- Targets: `web`, `api`, `both`, `auto`
- Web: `npm run build` then Vite preview bound to `127.0.0.1` on the team’s preview port
- API: the existing start command on the team’s API port
- Health: GET the UI origin and `GET /health` on the API

**Spring Boot + Angular**

- Targets: `ui`, `service`, `both`
- UI: `npm ci && npm run build` in `ui/`
- Service: `mvn -DskipTests package` then `java -jar` on 8080
- Health: `GET http://127.0.0.1:8080/actuator/health`

**Python API only**

- Targets: `api`, `auto`
- `pytest` (optional) then `uvicorn app:app --host 127.0.0.1 --port 8000`
- Health: `GET http://127.0.0.1:8000/health`

**Do not start a second copy** if the port is already listening. Check
health on the existing process instead.

Until the script matches the repo, you can set devops to a dry-run
(document “build only, no preview”) in the runbook so the pipeline can
still complete.

---

## 6. Adapt tests (different runners)

Tester skills mention Playwright, API, and unit layers. Point them at
**your** commands by editing the tester brief and the testing skills only
if the defaults do not match.

| Your tests | What to tell the tester (runbook or skill) |
|------------|--------------------------------------------|
| Jest / Vitest | `npm test` in the UI package |
| Playwright already in-repo | Use that project; do not add a second Playwright tree |
| JUnit / TestNG | `mvn test` or `gradle test` |
| pytest | `pytest path/to/module` |
| xUnit / NUnit | `dotnet test` |
| No UI | Skip Playwright; keep unit + API. Feature class may still need a sign-off file. |

Do not add new test frameworks unless a requirement says so.

---

## 7. IDE and editor differences

| Team uses | Install | `AGENTS.md` skill path |
|-----------|---------|------------------------|
| Cursor | `--ide cursor` | `.cursor/skills/run-workflow/SKILL.md` |
| Claude Code | `--ide claude-code` | `.claude/skills/run-workflow/SKILL.md` |
| GitHub (Copilot / agents) | `--ide github` | `.github/skills/run-workflow/SKILL.md` |
| CLI / no IDE | `--ide none` | Run `load_workflow.py` from the shell |

`--user --ide cursor` writes `~/.cursor/skills/run-workflow` so every repo
on that laptop can see the skill even without a project pack.

Named Cursor Task types (`developer-agent`, …) exist only with
`--agent-stubs`. Otherwise the parent uses `generalPurpose`.

---

## 8. Git ignore (recommended)

Add:

```gitignore
features/
.pipeline/state/
```

`graphify-out/` is optional in git. Commit it if the team wants a shared
structural graph; ignore it if each checkout re-runs
`pipeline-kit knowledge extract`. `test-knowledge/` (reviewed catalogs) is
usually committed after a bootstrap promote.

Project-scope Archify lives in `.agents/skills/archify/` (Cursor / GitHub) or
`.claude/skills/archify/` (Claude Code). Teams often commit the pinned skill.
`features/{slug}/diagrams/` follows the same policy as other `features/`
artifacts. Uninstalling Archify never deletes those diagrams.

`features/` holds plans, specs, HANDOFFs, and deploy logs for one run.
`.pipeline/state/active-context.json` is the live allowlist. Most teams do
not commit those. Commit `features/` only if you want specs in git.

---

## 9. Optional later

| Item | When a real project needs it |
|------|------------------------------|
| Tracker MCP | Jira (or compatible) workflows. Enable `intake.jira` and authenticate the MCP in the IDE. |
| Wiki | After a painful run, retro adds one page under `.pipeline/wiki/`. Start with the shipped index or empty it. |
| `.pipeline/rules/*.mdc` | Durable coding standards. They do **not** auto-apply in Cursor (not under `.cursor/rules`). Mention a rule in `AGENTS.md` or on a step allowlist. |
| Hooks | Policy guardrails ship in `.pipeline/hooks/` (sibling of `hooks/obs/`). `init --ide cursor` or `--ide claude-code` merges them into the IDE hook file without replacing existing entries. Agent-run observability stays opt-in via `pipeline-kit obs install`. |
| New workflow | See `.pipeline/README.md` (“How to add a workflow”). |

---

## Assessment (optional package)

`pipeline-kit scan` ships as its own package, installed the same way as the orchestrator extra. `pipeline-kit init` does not include it.

```bash
uv tool install -e ".[assess]"
```

The license must include the `assess` area. Build the graph first with `pipeline-kit knowledge extract`.

Scan writes `features/assessment/` (the report, the plan, `answers.md`, and `prompt.md`). On a terminal it asks any kickstarter that is still blank. It does not call a model, and it does not write rule, skill, or agent bodies.

In chat, ask to assess this repo. The shipped `repo-assessment` workflow follows `features/assessment/prompt.md` and fills each draft from the templates in `.pipeline/skills/repo-assessment/assets/`. Those drafts stay in `features/assessment/proposed/` until you copy one into `.cursor/` or `.pipeline/`.

---

## 10. What you should not edit

Follow [DOCUMENT-STANDARD.md](kit/pipeline/docs/DOCUMENT-STANDARD.md) in this
repository. After install the same file is `.pipeline/docs/DOCUMENT-STANDARD.md`.

- `.pipeline/loader/` — allowlist CLI
- `.pipeline/workflows/*.json` — unless you add a workflow
- `.pipeline/agents/*.md` and planning skills — process, not your stack
- Secrets, tokens, tracker site URLs — environment or IDE MCP settings only

You **should** edit the local-deploy runbook, `deploy-local.sh`,
`config.json` (`verify`, `deploy`, `intake.jira`), and testing skills if the
default runners are wrong.

---

## 11. New-project checklist

1. Install: `pipeline-kit init --ide cursor` (or `claude-code` / `none`).
2. Paste the `AGENTS.md` table (section 3.1) and a short product blurb.
3. Edit `.pipeline/config.json`:
   - `verify.rules` for your folders (or leave `[]`)
   - `deploy.targets` for your apps
   - `intake.jira.enabled` (`false` unless you use Jira)
4. Rewrite the local-deploy runbook and `deploy-local.sh` for your stack (section 5).
5. Skim `.pipeline/docs/DOCUMENT-STANDARD.md` before editing any other pack markdown.
6. Add `features/` and `.pipeline/state/` to `.gitignore`.
7. Open the repo root in the IDE. Confirm the `run-workflow` skill is visible.
8. Smoke test: ask “How does X work?” (expect `ask`) and “Add a small label change” (expect `feature-development`).

That is the full customer surface: **AGENTS.md + config.json**, then deploy
and test files if your runners are not the defaults in the testing skills.
