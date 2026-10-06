# Parent Task prompts

| Attribute | Value |
|-----------|--------|
| Type | Template |
| Audience | The parent orchestrator |
| Adapt | Fill placeholders only. Do not add a product, host, or customer name. |

Owned by **feature-development**. Parent picks the **workflow** ([orchestration](../../orchestration/SKILL.md)), **classifies** (`change-routing.md`), then orchestrates. Specialists run in a **new `Task`**. Default `subagent_type` is `generalPurpose` (portable). Teams that installed `--ide cursor --agent-stubs` may use the named Cursor types instead. Each prompt must say `Follow .pipeline/agents/{name}.md`. Include `WORKFLOW:`, `CHANGE_CLASS:` and `FEATURE_SLUG` on every prompt.

State contract: [pipeline-state.md](pipeline-state.md). Do **not** paste a prior HANDOFF body into the next prompt. Pass `PIPELINE_STATE_PATH` and `PRIOR_STATE_PATH` only.

**Always include:** `REPO_ROOT` (absolute), `FEATURE_SLUG`, `WORKFLOW`, `CHANGE_CLASS: micro|minor|feature`, the two state paths, `CONTEXT_PACK`, `SEED_BUNDLE`.

Feature class: parent slug for PM, UI designer, Architect, BA, BA critic, test-designer, tester, devops, retro. Child work uses `FEATURE_SLUG: {parent}/{child}`. When `test_design.enabled`, add `TEST_DESIGN_ENABLED: true` to Architect, BA, BA critic, test-designer, and tester. When `architecture_diagrams.enabled`, add `ARCHIFY_ENABLED: true` to Architect.

`@signoff:requirements`, `@signoff:architect`, and `@signoff:ba` are parent-only. Do not spawn a Task. Present the artifact **and recorded concerns**, wait for the user, write `signoff-*.md` from [planning-signoff-template.md](planning-signoff-template.md), update `pipeline-state.json`. When UI designer ran, `@signoff:requirements` presents `prd.md` **and** `ui-design.md` / `ui/index.html`.

---

## Isolation preamble (every specialist)

```text
CONTEXT: This is a new Task. You do not have the parent chat.
Use only this prompt and files on disk. Do not spawn other pipeline agents.
WORKFLOW: {feature-development|jira-story|jira-bug|jira-epic}
CHANGE_CLASS: {micro|minor|feature}
REPO_ROOT: {absolute path}
FEATURE_SLUG: {slug}
PIPELINE_STATE_PATH: features/{slug}/pipeline-state.json
PRIOR_STATE_PATH: features/{slug}/state/{prior-agent}.json | none
CONTEXT_PACK: features/{slug}/context-pack.json
SEED_BUNDLE: features/{slug}/step-context.md

1. Read PIPELINE_STATE_PATH.
2. If PRIOR_STATE_PATH is not none, read it. Open only outputs and context.next_must_read.
3. Read SEED_BUNDLE once. Do not Read .pipeline/agents or .pipeline/skills separately — they are in the bundle.
4. Do your job from that bundle. Load named assets only when the skill says to, if they are on allowed_reads.
5. Write features/{slug}/state/{your-agent}.json (child waves: features/{parent}/{child}/state/{your-agent}.json).
6. Update your row in pipeline-state.json.
7. Return a short HANDOFF. The parent will not paste that HANDOFF into the next Task.
```

---

## Parent: create state (before the first specialist)

Write `features/{slug}/pipeline-state.json` from [pipeline-state-template.json](pipeline-state-template.json). Set `current_step` to the first agent. Mark unused class steps `skipped`. After each HANDOFF, set that step `completed` or `blocked` and move `current_step`.

---

## Knowledge curator step (`test-knowledge-bootstrap` only)

```text
subagent_type: generalPurpose
{isolation preamble}
FEATURE_SLUG: qa-knowledge-bootstrap
CANDIDATE_RUN: {run}
PRIOR_STATE_PATH: none
You are the knowledge curator. Follow .pipeline/agents/knowledge-curator-agent.md
and .pipeline/skills/test-knowledge-bootstrap/SKILL.md exactly.

Require graphify-out/graph.json. Write candidates only under
test-knowledge/_candidates/{run}/. Write REVIEW.md. Do not promote.
Do not import Graphify. Do not invent a graph.
```

---

## Intake step (tracker workflows only, first step)

**Jira** (`work_source: jira`):

```text
subagent_type: generalPurpose
{isolation preamble}
PRIOR_STATE_PATH: none
You are the intake agent. Follow .pipeline/agents/intake-agent.md and .pipeline/skills/jira-intake/SKILL.md exactly.
If the issue is an epic, continue in this same Task with .pipeline/skills/epic-breakdown/SKILL.md.

JIRA_KEY: {KEY}
USER_REQUEST: {verbatim}
CONFIG_PATH: .pipeline/config.json

Fetch read-only. Normalize to features/{slug}/intake.md. Write state/intake-agent.json.
Do not write back to the tracker. Do not write specs or code.
```

**GitHub** (`work_source: github`):

```text
subagent_type: generalPurpose
{isolation preamble}
PRIOR_STATE_PATH: none
You are the intake agent. Follow .pipeline/agents/intake-agent.md and .pipeline/skills/github-intake/SKILL.md exactly.
If the issue is an epic, continue in this same Task with .pipeline/skills/epic-breakdown/SKILL.md.

GITHUB_REF: {REF}
USER_REQUEST: {verbatim}
CONFIG_PATH: .pipeline/config.json

Fetch read-only. Normalize to features/{slug}/intake.md. Write state/intake-agent.json.
Do not write back to GitHub. Do not write specs or code.
```

The parent writes `route.md` **after** this HANDOFF, using its `ISSUE_TYPE` / `WORKFLOW`, and updates `pipeline-state.json`.

---

## Bug analyst step (bug workflow, after intake)

```text
subagent_type: generalPurpose
{isolation preamble}
PRIOR_STATE_PATH: features/{slug}/state/intake-agent.json
You are the bug analyst. Follow .pipeline/agents/bug-analyst-agent.md and .pipeline/skills/bug-fix/SKILL.md steps B1–B6.

Reproduce the defect, write features/{slug}/rca.md, write state/bug-analyst-agent.json.
Do not edit product code. Do not spawn the developer.
```

---

## Developer step (bug workflow)

```text
subagent_type: generalPurpose
{isolation preamble}
PRIOR_STATE_PATH: features/{slug}/state/bug-analyst-agent.json
You are the developer. Follow .pipeline/agents/developer-agent.md and bug-fix/SKILL.md step B7.

Implement the recommended option from rca.md only. Write state/developer-agent.json.
Do not spawn the critic.
```

---

## Micro / minor — developer (after parent wrote route.md + patch.md)

```text
subagent_type: generalPurpose
{isolation preamble}
PRIOR_STATE_PATH: none
You are the developer. Follow .pipeline/agents/developer-agent.md.
Scope is patch.md only. Do not expand into a new screen/API.

PATCH_PATH: features/{slug}/patch.md
ROUTE_PATH: features/{slug}/route.md
TELEMETRY_CONTRACT_PATH: features/{slug}/telemetry-contract.md

Implement AC-1 in patch.md. Write state/developer-agent.json. Do not spawn critic or devops.
```

For **minor**, next Task is developer-critic (`PRIOR_STATE_PATH` = developer state). For **micro**, next Task is devops, then retro.

---

## PM step (feature class only)

```text
subagent_type: generalPurpose
{isolation preamble}
PRIOR_STATE_PATH: none
You are the product manager. Follow .pipeline/agents/product-manager-agent.md and .pipeline/skills/product-planning/SKILL.md exactly.

USER_REQUEST: {verbatim}

Run P1–P6. Analyze as-is in the repo. Write prd.md (not a thin plan). Write state/product-manager-agent.json.
If interactive questions are required, return BLOCKED with questions.md and stop.
Do not call UI designer, Architect, BA, or developer. Do not write specification.md.
```

---

## UI designer step (feature class, when skip_ui_designer is false)

```text
subagent_type: generalPurpose
{isolation preamble}
PRIOR_STATE_PATH: features/{slug}/state/product-manager-agent.json
You are the UI designer. Follow .pipeline/agents/ui-designer-agent.md and .pipeline/skills/ui-design/SKILL.md exactly.

UI_JOB: full

Run U1–U6. Classify surfaces; Read only matching platform skills. Write ui-design.md, ui/ mockups, ui/manifest.json, state/ui-designer-agent.json.
If interactive questions are required, return BLOCKED with questions.md and stop.
Do not call Architect, BA, or developer. Do not edit product source.
```

---

## UI designer consult (Architect or BA CONSULT_REQUESTED)

```text
subagent_type: generalPurpose
{isolation preamble}
PRIOR_STATE_PATH: features/{slug}/state/{architect-agent|ba-agent}.json
You are the UI designer on a consult insert. Follow .pipeline/agents/ui-designer-agent.md and .pipeline/skills/ui-design/SKILL.md (consult job).

UI_JOB: consult
RESUME_AGENT: architect-agent | ba-agent
CONSULT_REASON: {one sentence}
CONSULT_QUESTIONS: {list}

Answer the consult questions. Patch ui-design.md / mockups if needed. Write ui/consult-{n}.md and state/ui-designer-agent.json.
Set context.next_agent to RESUME_AGENT. Do not re-run the full inventory. Do not spawn the requester.
```

---

## Architect step (feature class, when skip_architect is false)

```text
subagent_type: generalPurpose
{isolation preamble}
PRIOR_STATE_PATH: features/{slug}/state/ui-designer-agent.json | features/{slug}/state/product-manager-agent.json | features/{slug}/state/intake-agent.json
You are the architect. Follow .pipeline/agents/architect-agent.md and .pipeline/skills/architecture-design/SKILL.md exactly.

PLAN_SOURCE_KIND: pm-plan | jira-story | jira-epic

Run A1–A5. Open files from the prior state only. Raise blocking or recorded concerns.
Read ui-design.md and ui/manifest.json when they exist. Do not invent extra screens.
Write architecture.md, implementation-plan.md, state/architect-agent.json.
If TEST_DESIGN_ENABLED is true, also write features/{slug}/test-design/model-delta.json or set no_test_model_change.
If ARCHIFY_ENABLED is true, follow .pipeline/skills/architecture-visualization/SKILL.md: keep mermaid, write features/{slug}/diagrams/manifest.json (delivered or mermaid-fallback). Do not BLOCK only because Archify is missing.
If a layout/IA gap blocks an honest design, return CONSULT_REQUESTED. Do not call BA, UI designer, or developer. Do not write specification.md.
```

---

## BA step (spec-driven workflows)

```text
subagent_type: generalPurpose
{isolation preamble}
PRIOR_STATE_PATH: features/{slug}/state/architect-agent.json | features/{slug}/state/product-manager-agent.json | features/{slug}/state/intake-agent.json
You are the BA agent. Follow .pipeline/agents/ba-agent.md and .pipeline/skills/spec-generation/SKILL.md exactly.

PLAN_SOURCE_KIND: pm-plan | jira-story | jira-epic

Read the prior state, then only listed files. Honor the Architect child split when it exists.
Write child specification.md files, spec-order.md, test-plan.md, state/ba-agent.json.
If TEST_DESIGN_ENABLED is true, bind each Must AC to overlay nodes and a lowest test level. Do not write free-form automation steps.
If interactive questions are required, return BLOCKED and stop.
Do not call the critic or developer. Do not edit product source.
```

`jira-epic` adds: “Write exactly one child spec per story in the epic plan’s child table.”

---

## BA critic step

```text
subagent_type: generalPurpose
{isolation preamble}
PRIOR_STATE_PATH: features/{slug}/state/ba-agent.json
You are the BA critic. Follow .pipeline/agents/ba-critic-agent.md. Read-only.

Review files listed in the BA state. Flag specs that ignore signed-off ADRs or recorded architect concerns.
Write state/ba-critic-agent.json. Do not spawn telemetry or developer.
If TEST_DESIGN_ENABLED is true, also review AC bindings and that the test plan is not free-form automation.
```

---

## Test designer step (feature class, only when test_design.enabled)

Spawn only after ba-critic `approve` | `approve-with-nits`, before `@signoff:ba`. Skip on micro, minor, and jira-bug.

```text
subagent_type: generalPurpose
{isolation preamble}
PRIOR_STATE_PATH: features/{slug}/state/ba-critic-agent.json
TEST_DESIGN_ENABLED: true
You are the test designer. Follow .pipeline/agents/test-designer-agent.md and .pipeline/skills/test-design/SKILL.md exactly.

Write inventory.json and cases.json under features/{slug}/test-design/.
Every ui / browser e2e case needs numbered steps[].do and expected[].see
(click-path: open, sign-in from env names, navigate, click, assert).
Overlay IDs alone are not enough. Run pipeline-kit knowledge render --slug {slug}.
Do not write product test trees. Do not import Graphify.
```

---

## Telemetry step (per child, after BA critic approve)

```text
subagent_type: generalPurpose
{isolation preamble}
FEATURE_SLUG: {parent-slug}/{child-slug}
PRIOR_STATE_PATH: features/{parent-slug}/state/ba-agent.json
You are the telemetry agent. Follow .pipeline/agents/telemetry-agent.md and .pipeline/skills/observability-telemetry/SKILL.md.

Write features/{parent-slug}/{child-slug}/telemetry-contract.md and
features/{parent-slug}/{child-slug}/state/telemetry-agent.json.
```

---

## Developer step (per child)

```text
subagent_type: generalPurpose
{isolation preamble}
FEATURE_SLUG: {parent-slug}/{child-slug}
PRIOR_STATE_PATH: features/{parent-slug}/{child-slug}/state/telemetry-agent.json
You are the developer. Follow .pipeline/agents/developer-agent.md.

Implement this child’s Must FRs and the telemetry allowlist only. Follow the signed-off implementation plan when the prior state lists it.
Write features/{parent-slug}/{child-slug}/state/developer-agent.json.
Do not spawn the critic.
```

---

## Developer critic step (per child)

```text
subagent_type: generalPurpose
{isolation preamble}
FEATURE_SLUG: {parent-slug}/{child-slug}
PRIOR_STATE_PATH: features/{parent-slug}/{child-slug}/state/developer-agent.json
You are the developer critic. Follow .pipeline/agents/developer-critic-agent.md. Read-only.

Write features/{parent-slug}/{child-slug}/state/developer-critic-agent.json. Do not spawn tester.
```

---

## Tester step

Spawn only when `route.md` has `skip_tester: false` (from [tester-policy.md](tester-policy.md) or `RUN_TESTER`). Feature: after all child critics. Minor: after developer-critic. Micro: after developer. **Bug workflow:** after developer-critic approves.

If `qa-test-cases.md` and `test-design/cases.json` are both missing, spawn **one** Task with `TESTER_MODE: cases-only` first. Then fan out.

For each required layer (`unit` / `api` / `ui` from the test plan or tagged cases), spawn a **parallel** Task. Skip `n/a`. Join all HANDOFFs before devops.

On `NEEDS_APPROVAL`: present `tester-rca-{layer}.md` and wait. After the user approves, re-spawn the owning child’s developer with the RCA path. After critic approve, re-run **all** required layer Tasks. Do not write product code in the parent.

Parent writes `qa-signoff.md` and `HANDOFF-tester.md`. `FEATURE_SIGNOFF: passed` only if every required layer is SUCCESS.

```text
subagent_type: generalPurpose
{isolation preamble}
TEST_LAYER: unit | api | ui
TESTER_MODE: cases-only   # only on the optional planner Task
PRIOR_STATE_PATH: features/{slug}/state/ba-agent.json | features/{slug}/state/developer-critic-agent.json
You are the tester agent for TEST_LAYER only. Follow .pipeline/agents/tester-agent.md.
If TEST_DESIGN_ENABLED is true and features/{slug}/test-design/cases.json exists, use it. Do not re-plan from Must ACs.
Do not edit product source. Product cause → NEEDS_APPROVAL.
```

---

## Devops step

```text
subagent_type: generalPurpose
{isolation preamble}
PRIOR_STATE_PATH: features/{slug}/state/tester-agent.json | features/{slug}/state/developer-agent.json
You are the devops agent. Follow .pipeline/agents/devops-agent.md and .pipeline/skills/local-deployment/SKILL.md.
Run only .pipeline/skills/local-deployment/scripts/deploy-local.sh.

DEPLOY_TARGET: {one of deploy.targets in .pipeline/config.json}

Write state/devops-agent.json. PARENT_NEXT: retro-agent.
```

---

## Retro step (after devops SUCCESS, every class)

```text
subagent_type: generalPurpose
{isolation preamble}
PRIOR_STATE_PATH: features/{slug}/state/devops-agent.json
You are the retro agent. Follow .pipeline/agents/retro-agent.md and .pipeline/skills/pipeline-retro/SKILL.md.

CONVERSATION_DIGEST: {optional ≤30 lines, no secrets}

Write RETRO.md and state/retro-agent.json. Mark pipeline-state current_status completed.
PARENT_NEXT: PIPELINE_COMPLETE.
```
