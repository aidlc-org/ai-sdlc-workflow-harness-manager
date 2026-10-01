# Wiki index — load one page, not the folder

| Attribute | Value |
|-----------|--------|
| Type | Wiki index |
| Audience | Parent or specialist before reading any wiki page |
| Adapt | Add one row when retro writes a page. Triggers must stay product-neutral. |

Match **triggers** against the current request, error, or pipeline class. Read
**only** the linked page.

| Triggers (any match) | Page |
|----------------------|------|
| Tracker issue key; which workflow; `intake.md`; `rca.md`; `epic-plan.md`; bug vs story vs epic | [orchestration-and-jira-intake.md](orchestration-and-jira-intake.md) |
| `CHANGE_CLASS`; micro vs minor vs feature; skip PM/BA; `route.md` | [feature-pipeline-change-class.md](feature-pipeline-change-class.md) |
| PM first gate; `prd.md`; nested `features/{slug}/{child}/`; `spec-order.md`; waves | [feature-pipeline-pm-and-multi-spec.md](feature-pipeline-pm-and-multi-spec.md) |
| ui-designer-agent; `ui-design.md`; `skip_ui_designer`; `RUN_UI_DESIGNER`; `CONSULT_UI`; mockups | [feature-pipeline-ui-designer.md](feature-pipeline-ui-designer.md) |
| `pipeline-state.json`; agent `state/*.json`; slim handoff; prior HANDOFF pasted | [pipeline-state-and-slim-handoffs.md](pipeline-state-and-slim-handoffs.md) |
| Architect; `architecture.md`; implementation plan; `skip_architect`; `RUN_ARCHITECT`; planning `signoff-*.md`; `decisions.md` | [feature-pipeline-architect-and-signoff.md](feature-pipeline-architect-and-signoff.md) |
| Telemetry contract; `EVENTS: none`; G1–G7; analytics vendor not in the spec | [telemetry-event-extraction.md](telemetry-event-extraction.md) |
| `deploy-local.sh`; port already in use; secret material in HANDOFF | [local-deploy-reuse-listeners.md](local-deploy-reuse-listeners.md) |
| Hooks not loading; `hooks.json`; external portal owns HITL | [ide-hooks-and-external-gates.md](ide-hooks-and-external-gates.md) |
| Agent-run traces; Langfuse; tool-call legitimacy; `pipeline-kit obs` | [agent-observability.md](agent-observability.md) |
| PIPELINE_COMPLETE after health; skip retro; `NO_NEW_PAGE`; `CONVERSATION_DIGEST` | [pipeline-retro-after-devops.md](pipeline-retro-after-devops.md) |
| Visible copy grep misses; text split across source tokens | [ui-copy-split-in-source.md](ui-copy-split-in-source.md) |
| test-strategy; test-plan; FEATURE_SIGNOFF; tester-policy; `RUN_TESTER`; `qa-test-cases` | [feature-pipeline-test-layers.md](feature-pipeline-test-layers.md) |
| Interrupted Task; missing HANDOFF; restart tester | [interrupted-pipeline-task-no-handoff.md](interrupted-pipeline-task-no-handoff.md) |
