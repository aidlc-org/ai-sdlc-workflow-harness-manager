# AI SDLC Workflow Harness Manager
Portable **workflow pack** and installer for coding agents.

# If you are an enterprise and working on any project, make it AI ready in 2 weeks rather than 3-6 months which organizations take today

Clone this repository, then install `.pipeline` into any customer project
(or into `~/.pipeline`). Process lives in the pack. The IDE is a thin adapter
(`run-workflow` only). The pack is not tied to a product, language, or IDE.

The repo is grouped by role: two **modes** (`kit/`, `orchestrator/`),
**extensions** for new workflows in either mode, and **capabilities**
(plugins, knowledge, observability, eval, feature flags, and the optional
`assess` package).

**Documentation site (local):** [website/](./website/) — what the kit is,
install, capabilities, plugins, knowledge, observability, and CLI.

```bash
cd website
npm install
npm start
```

Opens `http://127.0.0.1:3000`. The in-repo adaptation contract remains
[CUSTOMER-GUIDE.md](./CUSTOMER-GUIDE.md) (copied to `.pipeline/docs/` on
`init`). This README is the project landing page.

**Agent-run observability (Langfuse, hooks, scores):**
[OBSERVABILITY.md](./OBSERVABILITY.md) — install without running the full
pipeline ladder, trace identity, token usage, score meanings, and ideal values.

Requires **Python 3.11+**. Optional extras add more packages (orchestrator SDK, assess, memory). Enterprise license **issue/validate** is a separate private package (`pipeline-kit-license`); without it, paid CLI areas fail closed.

---

## Contents

1. [Why this exists](#why-this-exists)
2. [Quick start](#quick-start) — install the CLI, init a project, optional extras
3. [Local setup (developers)](#local-setup-developers) — clone, editable install, tests, sibling packages
4. [What you get after install](#what-you-get-after-install)
5. [Adapt per customer](#adapt-per-customer)
6. [Repository map](#repository-map)
7. [QA knowledge flow](#qa-knowledge-flow-opt-in)
8. [Project features](#project-features-opt-in-flags)
9. [Optional plugins](#optional-plugins)
10. [Tests](#tests)


**How to move through this repo**

1. Install `pipeline-kit` once ([Quick start](#quick-start) or [Local setup](#local-setup-developers)).
2. In each product repo: `pipeline-kit init --ide cursor`, then `doctor` / `workflows`.
3. Overlay the engagement ([Adapt per customer](#adapt-per-customer)).
4. Optional extras — install into the **same** `uv tool` CLI, then use:
   - Orchestrator: `uv tool install -e ".[orchestrator]"`
   - Assess: `uv tool install -e ".[assess]"`
   - Memory: `uv tool install -e ".[memory]"` — [step-by-step](./packages/pipeline-kit-memory/README.md)
5. Optional plugins and observability ([Optional plugins](#optional-plugins)).

Handbook: [CUSTOMER-GUIDE.md](./CUSTOMER-GUIDE.md). Docs site: [website/](./website/).

---

## Why this exists

Teams already use coding agents. They lack a repeatable operating model:
IDE folders explode with skills, process is glued to one editor, every
customer’s stack leaks into the pack, and every ask becomes the same delivery
ladder.

How the architecture solves that — portable pack, workflow as the unit of
scale, per-step allowlists, config as the engagement overlay — is in the
guide:

- [Problem statement](./CUSTOMER-GUIDE.md#problem-statement)
- [How this architecture solves it](./CUSTOMER-GUIDE.md#how-this-architecture-solves-it)

---

## Quick start

Install the `pipeline-kit` tool once (Python **3.11+**):

```bash
# Recommended: tool install from the public repo
uv tool install git+https://github.com/digitalneedstech/ai-sdlc-workflow-harness-manager.git
# or: pipx install git+https://github.com/digitalneedstech/ai-sdlc-workflow-harness-manager.git
```

For a local clone, `./install.sh` performs the same tool install with `uv`
or `pipx`.

Editable checkout (contributors):

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

Set up a customer repository:

```bash
cd /path/to/customer-app
pipeline-kit init --ide cursor
pipeline-kit doctor --ide cursor
pipeline-kit workflows
```

Optional **orchestrator mode** (`--mode orchestrator`) runs the same
workflows from Python in the wheel via the Cursor SDK. Install the extra
(`uv tool install -e ".[orchestrator]"`) and pass the user ask with
`--request` or `features/<slug>/request.md` — the chat session is not
inherited. Kit mode stays the default. Associates add extra workflows with
`pipeline-kit workflows --scaffold NAME` (orchestrator only).
Copy-ready examples (security review, CI audit, dependency audit,
accessibility review): [`extensions/orchestrator/`](./extensions/orchestrator/).

Optional **assessment** is a separate package, the same kind of extra as
orchestrator. It is a **paid area**: install it with
`uv tool install -e ".[assess]"` and activate a license that includes `assess`. `pipeline-kit scan` then writes `features/assessment/`
from the Graphify graph. It does not call a model. In chat, the shipped
`repo-assessment` workflow fills rule, skill, and agent drafts from the
templates in `.pipeline/skills/repo-assessment/assets/`. Details:
[CUSTOMER-GUIDE.md](./CUSTOMER-GUIDE.md).

Optional **memory bank** keeps `features/{slug}/` artifacts in a separate git
repo (FTS search + optional MCP). It is **free**. `pipeline-kit init` does not
install it. If you installed the CLI with `uv tool` / `./install.sh`, add the
extra in the **same** environment (do not `pip install` into another Python):

```bash
cd /path/to/this-checkout
uv tool install -e ".[memory]"
pipeline-kit memory doctor .
```

Then in the **product** repo (must already have `.pipeline/`):

```bash
pipeline-kit memory link /abs/path/to/memory-bank .
pipeline-kit memory import-local .    # skip if no local features/ yet
pipeline-kit memory index .
pipeline-kit memory search "architecture" . --limit 5
```

`--help` on `memory` only proves argparse. A real subcommand (`doctor`,
`status`, `link`) is what imports `pipeline_memory`. Full steps:
[packages/pipeline-kit-memory/README.md](./packages/pipeline-kit-memory/README.md).

**Open and paid.** Kit mode, free workflows, `obs report`, and most local commands
are open. These areas need an org **license** (private `pipeline-kit-license`
package + signed token): **orchestrator**, **Jira** intake, **governance**
workflows, **evidence** (agent-run observability and eval), **assess**
(`pipeline-kit scan`), and **portal** connect/push. Check with
`pipeline-kit license status`; activate with `pipeline-kit license activate`.
Details: [CUSTOMER-GUIDE.md](./CUSTOMER-GUIDE.md).

**Enterprise Pipeline Portal.** The web portal is a **separate proprietary
product** in its own repository (not open source). It gives a team one place to
see every project: fleet health, features, plugins, packages, runs and licenses,
with sign-in, roles (admin, project operator, viewer), an analysis dashboard,
user management and an audit log. This repository does not contain it.

Projects **report to the portal**; the portal never reads your folders or
changes a project. Create a project in the portal to get an ingest key, then
run `pipeline-kit portal connect --url <portal> --key <key>` in the project.
From then on, every local change to settings, features, plugins, packages,
runs or the license is reported automatically. Only metadata is sent (never
`config.json`, file paths, prompts, source or the license token); see
[what is sent](./website/docs/reference/portal-protocol.md). The same protocol
serves the vendor-hosted portal and, later, a portal an enterprise hosts itself.
More: [Enterprise portal](./website/docs/capabilities/portal.md).

Before each orchestrator agent, a decider chooses the Cursor model. `jev` (default) asks TypeSafe with a shortlist (`models.candidates`), not the full catalog. `fixed` skips that call. Planning and review prefer Opus or GPT; implementation prefers Composer. Add a model as an object in `candidates`, or as a string plus `models.cards` — not both. A pin skips Jev for one step:

```json
"orchestrator": {
  "decider": "jev",
  "fallback_model": "composer-2.5",
  "models": {
    "steps": { "developer-agent": "composer-2.5" },
    "candidates": ["composer-2.5", "claude-opus-5", "gpt-5.5"],
    "cards": {}
  }
}
```

`--dry-run` prints `need`, `basis`, `sent`, and a `summary` table. It does not start Cursor agents. Details: [`orchestrator/README.md`](./orchestrator/README.md#model-choice).

**Kit mode** resolves the same `orchestrator.models` pins/fallback when `load_workflow.py` activates a specialist step (`chosen_model` in the loader JSON and `features/{slug}/model-routing.json`). That is **advisory** for agent-CLI Task spawn; **IDE chat does not force** the model. **Enforced** routing remains orchestrator (`pipeline-kit run`). Disable kit resolution with `PIPELINE_KIT_MODEL_ROUTING=0`.

Use `--ide claude-code`, `--ide github`, or `--ide none` when appropriate.
To install a shared user pack instead, run `pipeline-kit setup --ide cursor`.

`init` writes `<repo>/.pipeline`; `setup` writes `~/.pipeline`. At runtime
the project pack wins, otherwise the user pack is used. Run artifacts always
land in the **current** project’s `features/`.

After install, the same handbook is copied to
`.pipeline/docs/CUSTOMER-GUIDE.md` in the target repo.

---

## Local setup (developers)

For maintainers and contributors working from a **clone** of this repo (and optional
private siblings). End users should follow [Quick start](#quick-start) only.

### Prerequisites

- Python **3.11+**
- `pip` (and optionally `uv` or `pipx` for a tool install)
- Git

Suggested sibling layout when you also develop enterprise packages:

```text
d:/projects/python/
  ai-sdlc-workflow-harness-manager/   # this public repo (pipeline-kit)
  pipeline-kit-license/               # private — optional for paid-area tests
  pipeline-kit-portal-enterprise/     # private — portal server only
```

### Clone and editable install

```bash
git clone https://github.com/digitalneedstech/ai-sdlc-workflow-harness-manager.git
cd ai-sdlc-workflow-harness-manager

python -m pip install -U pip
python -m pip install -e ".[dev]"
# Optional extras used by some tests and features (assess/memory are in-repo packages):
# python -m pip install -e ./packages/pipeline-kit-assess -e ./packages/pipeline-kit-memory -e ".[dev,orchestrator]"
```

Install the CLI onto your PATH from the same checkout:

```bash
python -m pip install -e .
pipeline-kit --version

# macOS/Linux tool-style install from this folder:
# ./install.sh
# or: uv tool install -e .
```

### Run tests

```bash
python -m pytest -q
```

Public CI has **no** private `pipeline-kit-license`. Crypto entitlement tests are
marked `requires_license_engine` and skip there. Fail-closed paths use
`license_absent`.

To exercise the full license suite locally:

```bash
python -m pip install -e ../pipeline-kit-license
python -m pytest -q tests/test_license.py tests/test_portal_link.py
```

To simulate public CI on a machine that already has the license package:

```bash
# PowerShell
$env:PIPELINE_KIT_TEST_WITHOUT_LICENSE = "1"
python -m pytest -q
```

### Optional private packages (same machine)

Paid CLI features need the private license **engine** next to this kit:

```bash
python -m pip install -e ../pipeline-kit-license
# Issue a test token with your vendor signing key, then:
# export PIPELINE_KIT_LICENSE='...'   # Windows: $env:PIPELINE_KIT_LICENSE='...'
pipeline-kit license activate
pipeline-kit license status
```

The portal package is **not** required for kit development. See the portal repo
README for local portal host setup.

### Docs site (optional)

```bash
cd website
npm ci
npm start
# http://127.0.0.1:3000
```

### Try the CLI against a throwaway project

```bash
# Windows PowerShell example:
# mkdir $env:TEMP\demo-app; cd $env:TEMP\demo-app
mkdir -p /tmp/demo-app && cd /tmp/demo-app
pipeline-kit init --ide none
pipeline-kit doctor --ide none
pipeline-kit workflows
```

More: [CONTRIBUTING.md](./CONTRIBUTING.md), [website/docs/maintainers/repo.md](./website/docs/maintainers/repo.md).

---

## What you get after install

| Path | Role |
|------|------|
| `.pipeline/` | Workflows, skills, agent briefs, rules, wiki, loader |
| `.pipeline/config.json` | This engagement: chains, tracker, verify, deploy |
| `.pipeline/docs/CUSTOMER-GUIDE.md` | Copied handbook |
| `.pipeline/docs/OBSERVABILITY.md` | Agent-run observability (after `init`; see repo [OBSERVABILITY.md](./OBSERVABILITY.md)) |
| `.pipeline/hooks/` | Policy guardrails (shell, MCP, pack allowlist). Merged on `init --ide cursor` / `claude-code` |
| `.pipeline/hooks/obs/` | Observability collectors (off until `obs install`) |
| `.cursor/skills/run-workflow/` or `.claude/skills/run-workflow/` | The only IDE-discovered skill |

Shipped workflows: `ask`, `feature-development`, `jira-story` / `jira-epic` /
`jira-bug`, `test-knowledge-bootstrap`. Structured test design is opt-in
(`pipeline-kit knowledge init`). Details: [What you get](./CUSTOMER-GUIDE.md#1-what-you-get).

---

## Adapt per customer

The kit is generic. Every new project must customize two files, then deploy
and test runbooks if the sample script does not match the stack.

| Step | Where |
|------|--------|
| Routing table + product blurb | [AGENTS.md](./CUSTOMER-GUIDE.md#31-agentsmd-create-or-edit) |
| Verify, deploy targets, Jira on/off | [`config.json`](./CUSTOMER-GUIDE.md#4-configjson--what-each-area-is-for) |
| Local start / health checks | [Adapt local deploy](./CUSTOMER-GUIDE.md#5-adapt-local-deploy-different-tech) |
| Test runners | [Adapt tests](./CUSTOMER-GUIDE.md#6-adapt-tests-different-runners) |
| Cursor / Claude Code / GitHub / none | [IDE and editor differences](./CUSTOMER-GUIDE.md#7-ide-and-editor-differences) |
| Ignore run artifacts | [Git ignore](./CUSTOMER-GUIDE.md#8-git-ignore-recommended) |
| Tracker MCP, wiki, hooks, new workflow | [Optional later](./CUSTOMER-GUIDE.md#9-optional-later) |
| Loader, workflow JSON, secrets | [What you should not edit](./CUSTOMER-GUIDE.md#10-what-you-should-not-edit) |
| End-to-end checklist | [New-project checklist](./CUSTOMER-GUIDE.md#11-new-project-checklist) |

Must-configure overview:
[What you must configure](./CUSTOMER-GUIDE.md#3-what-you-must-configure-every-new-project).

---

## Repository map

```text
kit/                    kit mode — portable pack copied to .pipeline
orchestrator/           orchestrator mode — Python engine (import: pipeline_orchestrator)
extensions/
  kit/                  add a markdown workflow (skill + JSON + config)
  orchestrator/         associate Python workflows (copy pipeline_extensions/)
capabilities/
  plugins/              Graphify + Archify (import: pipeline_plugins)
  knowledge/            QA overlay that consumes Graphify
  observability/        agent-run traces (import: pipeline_observability)
  eval/                 judges / Langfuse eval (import: pipeline_eval)
  feature_flags/        named on/off keys (import: pipeline_features)
packages/               separate installable extras (own pyproject.toml each)
  pipeline-kit-assess/  licensed repo assessment (import: pipeline_assess)
  pipeline-kit-memory/  external artifact bank + MCP (import: pipeline_memory)
website/                local Docusaurus docs
tests/
```

Python **import names are unchanged** (`pipeline_plugins`,
`pipeline_orchestrator`, …) so hooks and associate workflows keep working.
Folder names are the product map.

| Path | Role |
|------|------|
| `pyproject.toml` / `install.sh` | Install the `pipeline-kit` command with `uv` or `pipx` |
| `install.py` | CLI implementation and backward-compatible Python installer |
| [`kit/`](./kit/) | Kit-mode pack (`kit/pipeline/` → `<app>/.pipeline`) |
| [`orchestrator/`](./orchestrator/) | Orchestrator-mode engine (`--mode orchestrator`) |
| [`extensions/`](./extensions/) | Add workflows in kit mode or orchestrator mode |
| [`capabilities/`](./capabilities/) | Plugins, knowledge, observability, eval, feature flags |
| [`packages/`](./packages/README.md) | Optional extras (`assess`, `memory`). Same `uv tool` CLI as `pipeline-kit` |
| [`packages/pipeline-kit-assess/`](./packages/pipeline-kit-assess/) | Licensed repo assessment. Install with `uv tool install -e ".[assess]"` |
| [`packages/pipeline-kit-memory/`](./packages/pipeline-kit-memory/README.md) | External artifact bank + MCP. Install with `uv tool install -e ".[memory]"` |
| Enterprise Pipeline Portal | Separate **proprietary** repository and product (enterprise plan). Projects report to it with `pipeline-kit portal connect`. See [the docs page](./website/docs/capabilities/portal.md) |
| [CUSTOMER-GUIDE.md](./CUSTOMER-GUIDE.md) | Architect / developer handbook |
| `website/` | Local Docusaurus documentation (`npm start` in that folder) |
| `tests/` | Installer tests (`pytest`) |

Maintainers who edit a live `.pipeline` in this repo can refresh the bundle
using the backward-compatible maintainer command:

```bash
python3 install.py --sync-kit
```

To cut a release, bump the single source of truth (`VERSION`) rather than editing it by hand:

```bash
pipeline-kit version bump patch --commit --tag   # or: minor | major | version set 1.3.0
git -C /path/to/pipeline-kit push --follow-tags
```

The write and the commit always land in **this** repository — resolved from `--repo`, then
`$PIPELINE_KIT_REPO`, then upwards from the current directory — never in the project where the
kit is installed. Without `--commit` the files change and the git commands are printed instead.
Details: [website/docs/maintainers/repo.md](./website/docs/maintainers/repo.md).

How to add a workflow: kit mode after install is `.pipeline/README.md`
(“How to add a workflow”); both modes in this repo are
[`extensions/`](./extensions/).

Common tool commands:

```bash
pipeline-kit init [project]       # install/update a project pack
pipeline-kit setup                # install/update the user pack
pipeline-kit update [project]     # refresh while preserving config.json
pipeline-kit doctor [project]     # verify the active pack and optional IDE adapter
pipeline-kit workflows [project]  # list available workflows
pipeline-kit knowledge init       # opt-in QA overlay (does not run Graphify)
pipeline-kit knowledge extract    # official graphify extract --code-only
pipeline-kit knowledge status     # Graphify CLI and graphify-out
pipeline-kit knowledge render --slug {slug}
pipeline-kit knowledge playwright --slug {slug}
pipeline-kit knowledge promote-feature --slug {slug}
pipeline-kit plugins list         # optional Graphify / Archify plugins
pipeline-kit plugins install graphify
pipeline-kit plugins install archify
pipeline-kit plugins status
pipeline-kit plugins uninstall graphify
pipeline-kit plugins uninstall archify
pipeline-kit features list        # named on/off capabilities
pipeline-kit features status
pipeline-kit features enable telemetry
pipeline-kit features disable telemetry
pipeline-kit obs install          # merge agent-run hooks (does not replace existing)
pipeline-kit obs status
pipeline-kit obs report
pipeline-kit obs flush
# Full guide: OBSERVABILITY.md
pipeline-kit license status       # org, expiry, and which paid areas are on
pipeline-kit license activate     # store the token from PIPELINE_KIT_LICENSE
pipeline-kit memory link <bank> . # optional extra: uv tool install -e ".[memory]"
pipeline-kit memory index .
pipeline-kit memory search "query" .
pipeline-kit memory doctor .
pipeline-kit portal connect --url <portal> --key <key>   # report this project to a portal
pipeline-kit portal status        # connection, and when the portal last heard from this project
pipeline-kit portal push          # send the current state now
pipeline-kit portal disconnect    # forget the connection on this machine
pipeline-kit uninstall [project]  # remove files managed by the kit
pipeline-kit version              # current kit VERSION (maintainers: bump / set)
pipeline-kit --version
```

---

## QA knowledge flow (opt-in)

`pipeline-kit init` does **not** enable this. Absent `test_design.enabled`,
the feature ladder is unchanged.

**One-time**

1. `pipeline-kit knowledge init [--register-skill]` — `test-knowledge/` + flag on.
2. `pipeline-kit knowledge extract` — official Graphify → `graphify-out/graph.json`.
3. In the IDE: **Bootstrap QA knowledge for this repo**. Approve one Markdown report, then promote.

**Each feature** (only if the flag is on)

1. Architect writes `test-design/model-delta.json` or `no_test_model_change`.
2. BA binds Must ACs to overlay nodes and a lowest test level.
3. `test-designer-agent` writes `cases.json` and `qa-test-cases.md`.
4. You sign off BA. Waves run developer → critic (telemetry only if `RUN_TELEMETRY`).
5. Tester wave: parallel unit / api / ui Tasks. UI codegen is
   `pipeline-kit knowledge playwright` (a projector of `cases.json`, not Graphify).

Graphify and Archify stay under Optional plugins. Observability is the bundled
add-on in that same section (`obs install`). Do not `import graphify`.

## Project features (opt-in flags)

Same keys as `.pipeline/config.json`. Does not replace `knowledge init` or
`plugins install`. Chat overrides (`RUN_TESTER`, `RUN_TELEMETRY`) still win
for a single run.

```bash
pipeline-kit features list
pipeline-kit features status
pipeline-kit features enable test-design
pipeline-kit features disable telemetry
```

---

## Optional plugins

`pipeline-kit init` does not turn these on. **External plugins** (Graphify,
Archify) use `pipeline-kit plugins`. **Agent-run observability** is a
bundled add-on: use `pipeline-kit obs install`, not `plugins install`.
Langfuse is the default adapter, not a plugin. The kit never vendors
Graphify or Archify and never `import`s Graphify.

| Add-on | Kind | What it does | Default |
|--------|------|----------------|---------|
| **Graphify** | External plugin | Official CLI writes `graphify-out/graph.json` for QA test design | Off until `knowledge init` / `plugins install graphify` |
| **Archify** | External plugin | Pinned Agent Skill (`tt-a1i/archify` `v2.16.0`) for Architect HTML diagrams | Off until `plugins install archify`. Mermaid in `architecture.md` stays required |
| **Agent-run observability** | Bundled add-on | Coding-agent traces and scores (hooks → ledger → Langfuse) | Off until `obs install`. Distinct from `telemetry-agent` |

### Graphify

Prerequisites: Graphify CLI (`uv tool install graphifyy`).

```bash
pipeline-kit knowledge init --register-skill --ide cursor
# same skill registration:
pipeline-kit plugins install graphify --ide cursor
pipeline-kit knowledge extract
pipeline-kit plugins status --plugin graphify
pipeline-kit plugins uninstall graphify --ide cursor
# also delete graphify-out/:
pipeline-kit plugins uninstall graphify --ide cursor --purge
```

Cursor project install writes `.cursor/rules/graphify.mdc` via Graphify's
own `graphify cursor install`. Uninstall calls `graphify cursor uninstall`.
`--purge` is the only way the kit deletes `graphify-out/`.

### Archify

Prerequisites: GitHub CLI **v2.90+** (`gh skill`), **Node.js 18+**. Chrome
is optional (visual-check). Project-scope Cursor install lands in
`.agents/skills/archify/`.

```bash
pipeline-kit plugins install archify --ide cursor --scope project
pipeline-kit plugins status --plugin archify
pipeline-kit plugins uninstall archify --ide cursor
```

Install runs the pinned command (never `main`):

```bash
gh skill install tt-a1i/archify archify --pin v2.16.0 --agent cursor --scope project
```

Uninstall removes only that managed skill directory. It does **not** delete
`features/*/diagrams/`. `gh skill` has no remove command; the kit verifies
source (`tt-a1i/archify`) and path before deleting.

Delivered HTML is interactive (inline JavaScript). Treat it as active
content. Unattended Architect runs set `ARCHIFY_UPDATE_CHECK_DISABLED=1`.
If Archify is missing or deliver fails, Architect keeps mermaid and records
`mermaid-fallback`.

Troubleshooting: `pipeline-kit plugins status --plugin archify` prints
recovery. Typical causes are missing `gh skill`, Node below 18, or an
unpinned skill.

Details: [CUSTOMER-GUIDE.md](./CUSTOMER-GUIDE.md#22-optional-plugins).

### Agent-run observability

Traces and deterministic scores for **coding-agent** tool runs (Cursor / Claude /
Copilot hooks → local ledger → Langfuse). Distinct from customer-app
`telemetry-agent`. Not an entry in `plugins list`.

```bash
pipeline-kit init --ide cursor
pipeline-kit obs install --ide cursor --adapter langfuse
# LANGFUSE_* in .env, then use the IDE in that project root
pipeline-kit obs report
pipeline-kit obs flush
```

Install, identity model, Langfuse usage/cost, every score, ideal targets, and
troubleshooting: **[OBSERVABILITY.md](./OBSERVABILITY.md)**.

---

## Tests

```bash
python3 -m pip install -e ".[dev]"
python3 -m pytest -q tests
```

Public CI does not install the private license package. Crypto entitlement tests
skip unless `pipeline-kit-license` is available locally.
