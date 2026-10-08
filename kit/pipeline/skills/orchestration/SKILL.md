---
name: orchestration
description: >-
  Top layer for any product-work ask. Invoke first when the user wants work
  done: “work on …”, “fix …”, “change …”, “develop …”, or a message that
  contains a tracker issue key, or asks which skills, sub-agents,
  workflows, rules, or hooks to add, or asks to assess this repo. Decide the **workflow** (ask |
  feature-development | jira-story | jira-bug | jira-epic | github-story |
  github-bug | github-epic | test-knowledge-bootstrap | large-codebase-docs |
  module-security-review | system-architecture | repo-assessment). Questions stay on
  `ask` (no Task chain). Product work writes features/{slug}/route.md, then
  drives that workflow’s Task chain. Parent-only. Never implements product
  code and never replaces a workflow skill.
---

# Orchestration (top-layer router)

| Attribute | Value |
|-----------|--------|
| Type | Skill |
| Audience | The named agent, or the parent when this file is on the allowlist |
| Adapt | Change commands or paths only in deploy and testing skills. Planning skills stay product-neutral. |

The parent chat is the orchestrator. It picks **which workflow runs**, not **how** a step is done — each step is a `Task` running its own agent brief and skill.

**Everything tunable lives in [`.pipeline/config.json`](../../config.json).** Chains, skips, tracker settings, and retry caps come from there. Do not hardcode a repo, app, host, port, tracker site, or project key in any pipeline file.

**PIPELINE_COMPLETE** rules do not change: devops `OVERALL=passed`, then `retro-agent` (`SUCCESS` or `NO_NEW_PAGE`).

---

## Steps (parent, no Task for O1/O3/O4)

`O1 DETECT → O2 INTAKE? → O3 RESOLVE → O4 ROUTE → O5 DRIVE`

Weather, locations, and other asks unrelated to this repository: **stop**. Do not run the loader.

### O1 Detect the work source

Read `intake.jira` and `intake.github` from the config. Match the user message in this order (first hit wins):

1. **github** — only when `intake.github.enabled` is true:
   - `https://github.com/{owner}/{repo}/issues/{N}` or `/pull/{N}`
   - `{owner}/{repo}#{N}`
   - bare `#{N}` or `{N}` **only** if `intake.github.repo` is a non-empty `owner/repo`
2. **jira** — only when `intake.jira.enabled` is true and `intake.jira.key_pattern` matches
3. otherwise **text**

| Finding | `work_source` |
|---------|---------------|
| GitHub match and GitHub intake enabled | `github` |
| Jira key match and Jira intake enabled | `jira` |
| Neither, or the matching tracker is disabled | `text` |

A key inside a quoted log line or a file path is **not** a work source. Bare `#123` is **not** GitHub unless `intake.github.enabled` is true **and** `repo` is set. If both a Jira key and a GitHub ref appear, ask which one is the work item before spawning anything. If the user names a key *and* describes something unrelated to it, ask which one is the work item before spawning anything.

When `work_source` is `text`, also classify **intent**:

| Intent | Signals |
|--------|---------|
| `pack_gap` | assess this repo; pack scan; what skills, agents, workflows, rules, or hooks should we add; what is missing from the pipeline. Classify this before `question` and `product` — the words “what” and “add” also appear there |
| `question` | how / what / why / where / explain / “can you tell”, and no product verb |
| `knowledge_bootstrap` | bootstrap QA knowledge, bootstrap test knowledge |
| `codebase_docs` | document the large codebase; monorepo docs; large-codebase-docs; module handbooks under wiki/codebase |
| `module_security` | module security review; security notes per module; module-security-review |
| `system_architecture` | system architecture for the monorepo; cross-module architecture; system-architecture wiki |
| `product` | work on, fix, change, develop, implement, add, build, or an explicit `WORKFLOW:` other than `ask` |

Classify `codebase_docs`, `module_security`, and `system_architecture` **before** `product` when those signals match — they are not the feature ladder.

### O2 Intake (only when `work_source` is `jira` or `github`)

Spawn **one** `Task` — `intake-agent`. For `jira` follow [`../jira-intake/SKILL.md`](../jira-intake/SKILL.md) and inject `JIRA_KEY`. For `github` follow [`../github-intake/SKILL.md`](../github-intake/SKILL.md) and inject `GITHUB_REF`. Do **not** call tracker MCP tools from the parent: the issue payload belongs in its own context window.

Intake returns `ISSUE_TYPE` and writes `features/{slug}/intake.md` (plus `epic-plan.md` when the issue is an epic).

If intake returns `BLOCKED` because the configured tracker connection failed, relay its recovery line to the user (switch `intake.jira.connection` or `intake.github.connection`, fix auth, or paste the description). Do not guess the issue contents. Do not call MCP, `jira`, `gh`, or the API helpers from the parent.

### O3 Resolve the workflow

| `work_source` | Workflow |
|---------------|----------|
| `text` + `pack_gap` | `repo-assessment` — parent only, no Task chain |
| `text` + `question` | `ask` — parent answers from the allowlist; **no Task chain** |
| `text` + `knowledge_bootstrap` | `test-knowledge-bootstrap` — not the feature ladder |
| `text` + `codebase_docs` | `large-codebase-docs` — monorepo module docs under `wiki/codebase/` |
| `text` + `module_security` | `module-security-review` — per-module security notes |
| `text` + `system_architecture` | `system-architecture` — cross-module architecture |
| `text` + `product` | `feature-development` |
| `jira` | `intake.jira.issue_type_map[{issue_type}]`, falling back to that map’s `default` |
| `github` | `intake.github.issue_type_map[{issue_type}]`, falling back to that map’s `default` |

`ask` still runs the loader (`--workflow ask --step parent`) so the pack gate has an allowlist. Then follow [`../ask/SKILL.md`](../ask/SKILL.md) and stop — do not write `route.md` or spawn specialists.

`repo-assessment` runs the loader (`--workflow repo-assessment --step parent`). Then follow [`../repo-assessment/SKILL.md`](../repo-assessment/SKILL.md). Do not write `route.md` or spawn specialists.

`test-knowledge-bootstrap` runs the loader (`--workflow test-knowledge-bootstrap --step parent`). Then follow [`../test-knowledge-bootstrap/SKILL.md`](../test-knowledge-bootstrap/SKILL.md). Do not classify a change class and do not start feature-development.

`large-codebase-docs` runs the loader (`--workflow large-codebase-docs --step parent`). Then follow [`../large-codebase-docs/SKILL.md`](../large-codebase-docs/SKILL.md). Parent runs `pipeline-kit docs extract-modules`; specialists write module handbooks only. No change class. No `route.md`.

`module-security-review` runs the loader (`--workflow module-security-review --step parent`). Then follow [`../module-security-review/SKILL.md`](../module-security-review/SKILL.md). No change class. No `route.md`.

`system-architecture` runs the loader (`--workflow system-architecture --step parent`). Then follow [`../system-architecture/SKILL.md`](../system-architecture/SKILL.md). No change class. No `route.md`.

Then set `change_class`:

- `feature-development`: classify with [`../feature-development/assets/change-routing.md`](../feature-development/assets/change-routing.md).
- Jira and GitHub workflows: start from that workflow’s `default_change_class` in the config, then apply the same hard-upgrade triggers from `change-routing.md`. A bug whose fix needs a new screen or API is still a hard upgrade — say so in `route.md` `reason`.

User override: an explicit `WORKFLOW: {name}` or `CHANGE_CLASS: {class}` in the ask wins, unless a hard-upgrade trigger contradicts `micro`.

### O4 Write `features/{slug}/route.md`

Skip this step for `ask`, `pack_gap`, `test-knowledge-bootstrap`, `large-codebase-docs`, `module-security-review`, and `system-architecture`.

Slug rules:

- `text`: kebab summary of the ask.
- `jira`: `{issue-key lowercased}-{short kebab summary}`, truncated to a readable length. Reuse the folder if it already exists; never fork a second one for the same key.
- `github`: `{owner}-{repo}-{N}-{short kebab summary}`, truncated to a readable length. Reuse the folder if it already exists; never fork a second one for the same issue.

Template and field meanings: [`../feature-development/assets/change-routing.md`](../feature-development/assets/change-routing.md). Fill `workflow`, `work_source`, `jira_key` or `github_ref`, `issue_type` in addition to the class fields. Seed every `skip_*` from the workflow’s `skips` in the config; `skip_tester` still comes from [`../feature-development/assets/tester-policy.md`](../feature-development/assets/tester-policy.md) or a one-run `RUN_TESTER`. Seed `skip_architect: true` and `skip_ui_designer: true` for micro/minor/jira-bug/github-bug. On feature-class **text** work, refine `skip_ui_designer` **after PM** using [`../feature-development/assets/ui-designer-policy.md`](../feature-development/assets/ui-designer-policy.md) or `RUN_UI_DESIGNER`. On feature-class story/epic/text work, refine `skip_architect` **after** `@signoff:requirements` using [`../feature-development/assets/architect-policy.md`](../feature-development/assets/architect-policy.md) or `RUN_ARCHITECT`. Honor [`../feature-development/assets/next-agent-policy.md`](../feature-development/assets/next-agent-policy.md) for legal `context.next_agent` values.

`route.md` is always written at the **parent** slug, even when children exist.

### O5 Drive the chain

Read the chain for the resolved workflow (and class) from the config and spawn **one new `Task` per step**, in order, waiting for each HANDOFF. Apply [`../feature-development/assets/next-agent-policy.md`](../feature-development/assets/next-agent-policy.md): honor `context.next_agent` only when it is a legal successor; otherwise follow the config chain. `@waves` expands to `waves.child_chain` per child, read from `features/{slug}/spec-order.md`. `@signoff:requirements`, `@signoff:architect`, and `@signoff:ba` are **parent-only stops** — present the artifact, wait for the user, write `signoff-*.md`. When UI designer ran, `@signoff:requirements` presents `prd.md` **and** `ui-design.md` / mockups. Do not treat sign-offs as Tasks. When `skip_ui_designer` is true, drop `ui-designer-agent`. When `skip_architect` is true, drop both `architect-agent` and `@signoff:architect`. When `skip_telemetry` is true (the default), drop `telemetry-agent` from `@waves` and write the `EVENTS: none` stub. Insert `telemetry-agent` before each child’s developer only if the user typed `RUN_TELEMETRY: true`. When `test_design.enabled` is true on feature / jira-story / jira-epic / github-story / github-epic, insert `test-designer-agent` after `ba-critic-agent` and before `@signoff:ba` ([test-design-policy.md](../feature-development/assets/test-design-policy.md)). Do not insert it on micro, minor, jira-bug, or github-bug. Expand `tester-agent` into a **layer wave** (parallel `TEST_LAYER` Tasks, then parent join) per [tester-agent.md](../../agents/tester-agent.md). When `architecture_diagrams.enabled` is true, pass `ARCHIFY_ENABLED: true` to Architect ([architecture-diagrams-policy.md](../feature-development/assets/architecture-diagrams-policy.md)); mermaid stays required and missing Archify is not a skip of Architect.

On `CONSULT_REQUESTED` from Architect or BA, spawn one-shot `ui-designer-agent` with `UI_JOB: consult` then resume the requester, capped by `gates.consult_cap` (default 1) unless the user typed `CONSULT_UI: true`.

| Workflow | Chain | Owning skill for the work |
|----------|-------|---------------------------|
| `ask` | none (parent only) | [`../ask/SKILL.md`](../ask/SKILL.md) |
| `repo-assessment` | none (parent only) | [`../repo-assessment/SKILL.md`](../repo-assessment/SKILL.md) |
| `feature-development` | class chain (`micro` / `minor` / `feature`) | [`../feature-development/SKILL.md`](../feature-development/SKILL.md) |
| `jira-story` | intake → `@signoff:requirements` → architect? → `@signoff:architect` → BA → BA critic → `@signoff:ba` → waves → tester → devops → retro | [`../feature-development/SKILL.md`](../feature-development/SKILL.md), BA reads `intake.md` |
| `jira-epic` | same as `jira-story` | same, BA reads `epic-plan.md` and writes one child spec per story |
| `jira-bug` | intake → bug analyst → developer → developer critic → tester → devops → retro | [`../bug-fix/SKILL.md`](../bug-fix/SKILL.md) |
| `github-story` | same as `jira-story` | same, BA reads `intake.md` |
| `github-epic` | same as `jira-epic` | same, BA reads `epic-plan.md` |
| `github-bug` | same as `jira-bug` | [`../bug-fix/SKILL.md`](../bug-fix/SKILL.md) |
| `test-knowledge-bootstrap` | knowledge-curator-agent → one Markdown review → promote | [`../test-knowledge-bootstrap/SKILL.md`](../test-knowledge-bootstrap/SKILL.md) |
| `large-codebase-docs` | parent: docs extract-modules; then module-docs-agent per module | [`../large-codebase-docs/SKILL.md`](../large-codebase-docs/SKILL.md) |
| `module-security-review` | parent ensures graphs; module-security-agent per module | [`../module-security-review/SKILL.md`](../module-security-review/SKILL.md) |
| `system-architecture` | parent merge/extract; one system-architect-agent | [`../system-architecture/SKILL.md`](../system-architecture/SKILL.md) |

Prompts for every step: [`../feature-development/assets/parent-task-prompt.md`](../feature-development/assets/parent-task-prompt.md). Always inject `WORKFLOW`, `CHANGE_CLASS`, `FEATURE_SLUG`, `REPO_ROOT`, and the disk paths that step needs. For docs/security/system workflows inject `MODULE_ID` (when applicable) instead of a feature slug.

---

## What the parent does and does not do

**Parent (no Task):** detect source, resolve workflow, answer `ask` inline, write `route.md` for product work, write `patch.md` / telemetry stubs for micro|minor, paste HANDOFFs between steps, run `@signoff:*`, apply architect-policy after requirements, read `spec-order.md` and fan out waves, set `DEPLOY_TARGET` from `deploy.target`. Default Task type is `generalPurpose` plus `.pipeline/agents/{name}.md` (named Cursor types only if `--agent-stubs` was installed).

**Never in the parent:** tracker MCP calls, root-cause analysis, spec writing, product edits, test runs, deploys.

Every specialist is a **fresh context**. The isolation table in [`../feature-development/SKILL.md`](../feature-development/SKILL.md) applies to the two additions as well:

| Agent | Why a separate window | Inline in parent? |
|-------|----------------------|-------------------|
| `intake-agent` | Raw issue payload and MCP discovery must not fill the parent | **No** |
| `ui-designer-agent` | Design contract + mockups must not share PM or Architect reasoning | **No** |
| `architect-agent` | Challenge + diagrams must not share PM or BA reasoning | **No** |
| `bug-analyst-agent` | Deep code tracing; must not share the fixer’s context | **No** — never the same Task as the developer |
| `knowledge-curator-agent` | Overlay candidates must not mix with feature planning | **No** |
| `test-designer-agent` | Structured cases must not share BA authoring | **No** — never the same Task as BA |
| `module-docs-agent` | One module handbook; must not fill the parent with graph text | **No** |
| `module-security-agent` | One module security note; evidence-scoped | **No** |
| `system-architect-agent` | Cross-module architecture; not feature Architect | **No** |

---

## Failure and retries (all workflows)

Semantics are inherited, not redefined: critic verdicts and failure rows live in [`../feature-development/SKILL.md`](../feature-development/SKILL.md). Retry cap comes from `gates.retry_cap`.

| Situation | Parent |
|-----------|--------|
| Intake `BLOCKED` (no MCP, no permission, key not found) | Stop; relay recovery. Do not fabricate the issue |
| Intake `ISSUE_TYPE` unmapped | Use the map’s `default`, and record the raw type in `route.md` `reason` |
| Bug analyst `BLOCKED` (cannot reproduce) | Stop; ask the user for the missing environment/steps. Do not let the developer “fix” an unreproduced bug |
| `changes-required` | Re-spawn the **previous** agent in a new Task, up to `gates.retry_cap`, then stop |
| `@signoff:*` waiting | Stop; do not spawn the next specialist until `SIGNOFF: approved` is on disk |
| Architect `BLOCKED_CHALLENGE_PM` | Void requirements (and downstream) sign-off; re-spawn PM |
| `CONSULT_REQUESTED` | Spawn `ui-designer-agent` (`UI_JOB: consult`) if under `gates.consult_cap` or `CONSULT_UI: true`; then re-spawn `resume_agent` |
| Scope grows past the class mid-flight | Rewrite `route.md` to the higher class and restart at that class’s first step |
| Docs extract failed for a module | Continue only OK modules or stop if user aborts; do not invent graphs |

---

## Anti-patterns

Calling tracker MCP from the parent · running a specialist inline “to save a turn” · picking a workflow the user’s issue type does not map to · full PM/BA ladder for a bug · developer before an approved root cause · hardcoding a project key, site URL, app folder, or port anywhere outside `pipeline.config.json` · treating devops SUCCESS as done · inventing Graphify graphs · writing monorepo handbooks into `.pipeline/wiki/`.
