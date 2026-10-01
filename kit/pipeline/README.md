# Pipeline pack

| Attribute | Value |
|-----------|--------|
| Type | Handbook |
| Audience | Delivery leads adapting this pack in a customer repository |
| Adapt | Overlay lives in `config.json`, the local-deploy runbook and script, and testing skills. Do not add product names here. |

This folder is the **portable operating model**: skills, agent briefs, workflow
allowlists, wiki, and the loader. The IDE holds only `run-workflow` so it does
not auto-load the rest.

**Start here after install:** [docs/CUSTOMER-GUIDE.md](docs/CUSTOMER-GUIDE.md).
When you add or edit markdown in this folder, follow
[docs/DOCUMENT-STANDARD.md](docs/DOCUMENT-STANDARD.md).

## What a new project changes

| Change this | Leave this |
|-------------|------------|
| `config.json` — tracker, deploy target names, verify rules; drop or reorder `ui-designer-agent` in the feature class chain if this engagement has no UI seat | `loader/` |
| `skills/local-deployment/assets/local-deploy-runbook.md` | `agents/*.md` (process, not stack) |
| `skills/local-deployment/scripts/deploy-local.sh` | `workflows/*.json` unless you add a workflow |
| Testing skills, only if runners or paths differ | Planning skill bodies |
| Root `AGENTS.md` (installer does not write it) | Secrets — those stay in the environment |

## Install (kit repository)

From a clone of the pipeline-kit repository:

```bash
pipeline-kit init                         # creates ./.pipeline
pipeline-kit init /path/to/app
pipeline-kit init /path/to/app --ide cursor --agent-stubs
pipeline-kit setup                        # creates ~/.pipeline
pipeline-kit doctor --ide cursor
pipeline-kit workflows
pipeline-kit uninstall
```

| Scope | Pack location | IDE skill |
|-------|---------------|-----------|
| `--project` | `<repo>/.pipeline` | `<repo>/.cursor/skills/run-workflow` (or `.claude` / `.github`) |
| `--user` | `~/.pipeline` | `~/.cursor/skills/run-workflow` when `--ide cursor` |

Resolution when a workflow runs:

1. Walk up from the current project for `.pipeline/config.json` or `.pipeline/workflows/`.
2. If none, use `~/.pipeline`.
3. A project pack **always wins**.
4. `features/{slug}/` is always written in the **current project**, never in `$HOME`.
5. Active allowlist state is `{pack}/state/active-context.json`.

`--ide none` installs the pack only (including `.pipeline/hooks/` scripts).
`--ide cursor` or `--ide claude-code` also merges policy guardrails into the
IDE hook file. Agent-run observability hooks stay opt-in
(`pipeline-kit obs install`) and merge without replacing existing entries.

## What to add to AGENTS.md

The installer does **not** edit `AGENTS.md`. Paste or adapt this block so the
harness is the entry point:

```markdown
## Which workflow to use

| User intent | What to do |
|-------------|------------|
| Product work (“work on …”, “fix …”, “change …”, “develop …”, or a tracker issue key) | Follow the IDE `run-workflow` skill. Run `.pipeline/loader/load_workflow.py` (or `~/.pipeline/loader/load_workflow.py`). Read only `allowed_reads`. |
| Question about this repo (how / what / why / where / explain) | Same skill, workflow `ask`. No Task chain. |
| Weather, locations, or other unrelated asks | Do not run the loader. Do not load pack files. |

Chains and skips: `.pipeline/config.json` (project, else `~/.pipeline/config.json`).
File lists: `.pipeline/workflows/`. Specialist briefs: `.pipeline/agents/`.
Do not open other `.pipeline/skills/` files unless the active allowlist lists them.
```

Optional: if the team installed `--agent-stubs`, Cursor Task types such as
`developer-agent` exist as thin pointers. Otherwise parent Tasks use
`generalPurpose` and `Follow .pipeline/agents/{name}.md`.

## How to add a workflow

1. Write `.pipeline/skills/{name}/SKILL.md` (plus `assets/` templates if needed).
2. Write `.pipeline/workflows/{name}.json` with `context.parent.files` and
   `context.steps.{agent}.files` (relative paths from the project root, using
   the `.pipeline/…` prefix). List briefs, `SKILL.md`, config, and wiki — not
   skill `assets/`. The loader allowlists assets from the listed skills;
   specialists Read them only when the skill names them.
3. Add `workflows.{name}` in `.pipeline/config.json` (`source`, `chain` or
   `classes`, `skips`). An empty `chain` means parent-only (see `ask`).
4. Optional: add `.pipeline/agents/{role}.md` and list it on that step’s allowlist.
5. If the receptionist should auto-pick it, add one row to
   `.pipeline/skills/orchestration/SKILL.md` (O1 / O3).
6. Activate and check the printed list:

```bash
python3 .pipeline/loader/load_workflow.py --workflow {name} --step parent --slug try-{name}
```

Confirm `seed_bundle` (`features/{slug}/step-context.md`) concatenates `seed_reads`. `allowed_reads` also includes skill assets for later Reads.

Shipped workflows: `ask`, `feature-development`, `jira-story`, `jira-epic`,
`jira-bug`, `test-knowledge-bootstrap`. Feature-class work can run
`architect-agent` after signed-off requirements (see `architect-policy.md`
and `@signoff:*` in `config.json`). `test-designer-agent` is opt-in via
`pipeline-kit knowledge init` (`test_design.enabled`). Enhanced Architect
diagrams are opt-in via `pipeline-kit plugins install archify`
(`architecture_diagrams.enabled`); mermaid in `architecture.md` stays required.

## What you do not edit

- Product source, unless the user’s ask is about it.
- `AGENTS.md` from the installer. Teams edit it using the snippet above
  or the customer guide.
- Secrets, tracker site URLs, and project keys — environment or IDE MCP
  settings only.

## Enterprise layering (guidance)

When several teams share one pack, layer overrides. Do not bake org URLs
into the shared tree.

```text
org template repo  →  team defaults  →  ~/.pipeline (user)  →  <repo>/.pipeline (project wins)
```
