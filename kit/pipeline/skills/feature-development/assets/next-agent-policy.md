# Next-agent policy (bounded graph)

| Attribute | Value |
|-----------|--------|
| Type | Policy |
| Audience | Parent (honors `context.next_agent` only when legal) |
| Adapt | Do not add extra successors that skip sign-off or jump to developer. |

Owned by **feature-development**. Specialists **never** spawn other pipeline
agents. They write `context.next_agent` on their state JSON. The parent
honors it **only** if the value is in the table below. Otherwise follow the
config chain (and skip flags).

Sign-off gates stay parent-owned. BA critic, waves, tester, devops, and retro
are **not** agent-chosen.

## Legal successors

| From (SUCCESS / ASSUMPTIONS_USED) | Legal `context.next_agent` | Parent does |
|-----------------------------------|----------------------------|-------------|
| `product-manager-agent` | `ui-designer-agent` | Apply ui-designer-policy; spawn UI designer if not skipped |
| `product-manager-agent` | `signoff-requirements` | Apply ui-designer-policy anyway (hard triggers can still run UI); else `@signoff:requirements` |
| `ui-designer-agent` (`UI_JOB: full`) | `signoff-requirements` | Combined `@signoff:requirements` (PRD + UI) |
| `ui-designer-agent` (`UI_JOB: consult`) | `{resume_agent}` | Re-spawn Architect or BA with consult state as `PRIOR_STATE_PATH` |
| `architect-agent` | `signoff-architect` | `@signoff:architect` |
| `ba-agent` | `ba-critic-agent` | Spawn BA critic |

Illegal: `developer-agent`, `tester-agent`, `devops-agent`, skipping a
`@signoff:*`, going backwards except the failure rows below.

## Recommendations (not spawns)

UI designer may set `context.recommend_after_signoff` to `architect-agent` or
`ba-agent`. Parent treats `architect-agent` as an extra **run trigger** for
[architect-policy.md](architect-policy.md) after requirements sign-off. It
does not skip BA.

## Consult insert

Architect or BA may return status `CONSULT_REQUESTED` instead of SUCCESS:

```json
"status": "CONSULT_REQUESTED",
"context": {
  "next_agent": "ui-designer-agent",
  "consult_agent": "ui-designer-agent",
  "consult_reason": "{one sentence}",
  "consult_questions": ["{decision the mockup must settle}"],
  "resume_agent": "architect-agent | ba-agent"
}
```

Parent:

1. Count existing `features/{slug}/ui/consult-*.md` for this `resume_agent`.
2. If count ≥ `gates.consult_cap` (default **1**) and the user did not type
   `CONSULT_UI: true`, tell the user; do not spawn.
3. Else spawn `ui-designer-agent` with `UI_JOB: consult`, then re-spawn
   `resume_agent`. Original Architect/BA outputs stay on disk.

PM does **not** consult mid-PRD.

## Failure rows (unchanged)

| Status | Parent |
|--------|--------|
| `BLOCKED` | Wait; re-spawn the same agent |
| `BLOCKED_CHALLENGE_PM` | Void requirements (and downstream) sign-off; re-spawn PM |
| `changes-required` | Re-spawn the previous author |

## Anti-patterns

Honoring an illegal `next_agent` · specialist `Task` nesting · treating
`recommend_after_signoff` as a skip of Architect policy · consult loops
without a cap · skipping `@signoff:requirements` because mockups exist.
