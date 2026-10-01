# Pipeline and agent state

| Attribute | Value |
|-----------|--------|
| Type | Policy |
| Audience | Parent and every specialist Task |
| Adapt | Do not add a product name. Paths stay under `features/{slug}/`. |

The orchestrator (parent) must **not** paste prior HANDOFF bodies or long
chat into the next Task. Disk state is the contract.

```text
features/{slug}/pipeline-state.json      # one file for the whole run
features/{slug}/state/{agent}.json       # one file per specialist
features/{slug}/{child}/state/{agent}.json   # wave children only
```

JSON only (not YAML). Load
[pipeline-state-template.json](pipeline-state-template.json) and
[agent-state-template.json](agent-state-template.json).

## Who writes what

| Writer | File | When |
|--------|------|------|
| Parent | `pipeline-state.json` | Create the slug folder. After every HANDOFF and every `@signoff:*`. |
| Specialist | `state/{own-agent}.json` | Before returning. Required even on `BLOCKED`. |
| Specialist | patch own row in `pipeline-state.json` | Same moment as the agent state file. |

Do not invent a second slug folder. Child wave state stays under the child.

## Parent spawn rules

Every specialist prompt includes only:

1. Isolation preamble (new Task).
2. `PIPELINE_STATE_PATH` and `PRIOR_STATE_PATH` (or `none` on the first step).
3. `REPO_ROOT`, `FEATURE_SLUG`, `WORKFLOW`, `CHANGE_CLASS`.
4. A short job (what this step must produce). Not the previous HANDOFF body.

The specialist:

1. Reads `pipeline-state.json`.
2. Reads `PRIOR_STATE_PATH` when it is not `none`.
3. Opens **only** paths in that prior state’s `outputs` and
   `context.next_must_read` (plus its own skill/templates).
4. Does the work.
5. Writes its agent state file and updates `pipeline-state.json`.
6. Returns a **short** HANDOFF (human review). The next Task does not need
   that HANDOFF pasted.

If a listed file is missing, HANDOFF `BLOCKED` `INPUT_MISSING`. Do not guess.

## `pipeline-state.json`

- `current_step` — agent id or `@signoff:requirements` / `@signoff:architect` /
  `@signoff:ba` / `@waves`.
- `current_status` — `not_started` | `in_progress` | `blocked` | `completed` | `failed`.
- `steps.{id}.status` — `pending` | `in_progress` | `completed` | `blocked` | `skipped`.
- `steps.{id}.state_path` — the agent JSON, or `none` for a parent-only sign-off.

Feature-class step ids (create rows up front; mark unused `skipped`):

`product-manager-agent`, `ui-designer-agent`, `signoff-requirements`, `architect-agent`,
`signoff-architect`, `ba-agent`, `ba-critic-agent`, `signoff-ba`, then per
child under `waves.{child}.{telemetry-agent|developer-agent|developer-critic-agent}`,
then `tester-agent`, `devops-agent`, `retro-agent`.

Micro / minor / bug: only the agents that class actually runs.

## Agent state JSON

| Field | Meaning |
|-------|---------|
| `inputs` | What this step was given (prior state, request, listed artifacts). |
| `outputs` | Files this step **wrote**. Downstream reads these. |
| `reads` | Repo or artifact paths this step **analyzed** (as-is evidence). |
| `context.summary` | ≤ 8 sentences. Enough to orient; not a second PRD. |
| `context.goals` | Product or technical goals this step locked. |
| `context.concerns` | Issues for HITL. Architect uses `severity`. |
| `context.next_agent` | Who the parent should spawn (or `signoff` / `stop`). Honor only if [next-agent-policy.md](next-agent-policy.md) lists it. |
| `context.recommend_after_signoff` | UI designer only: `architect-agent` or `ba-agent`. Extra architect-policy trigger, not a spawn. |
| `context.consult_agent` | When status is `CONSULT_REQUESTED`: usually `ui-designer-agent`. |
| `context.consult_reason` | One sentence. |
| `context.consult_questions` | Decisions the consult must settle. |
| `context.resume_agent` | Who the parent re-spawns after consult. |
| `context.next_must_read` | Exact files the next specialist must open. Keep short. |

`status` matches the HANDOFF: `SUCCESS` | `ASSUMPTIONS_USED` | `BLOCKED` |
`BLOCKED_CHALLENGE_PM` | `CONSULT_REQUESTED` | `FAILED` | `NO_NEW_PAGE`.

## Anti-patterns

Pasting a prior HANDOFF into the next prompt · asking the parent to recap ·
writing state only as chat · skipping `pipeline-state.json` · listing the
whole repo in `next_must_read`.
