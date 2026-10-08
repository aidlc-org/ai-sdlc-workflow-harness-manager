# Langfuse judge prompts (observation-level)

| Attribute | Value |
|-----------|--------|
| Type | Handbook |
| Audience | Langfuse evaluator operators and maintainers |
| Adapt | Do not add product, host, or customer names. Keep score scale and target observation stable. |

Paste these into Langfuse **Evaluators** after `pipeline-kit eval judges sync` has
created the score configs. One evaluator per file; rule target = observation **name**
filter listed in the prompt header. Never attach judges to `tool:` / `retriever:` /
`generation` observations. Sampling: 100% golden, ~10% live.

Variable mapping: `{{input}}` = observation input (Task prompt), `{{output}}` =
observation output (status + HANDOFF clip + critic verdict JSON written by flush).

| Judge | Target observation | Score |
|---|---|---|
| spec_completeness | `pipeline.step ba-agent` | 0–1 |
| spec_testability | `pipeline.step ba-agent` | 0–1 |
| scope_control | `pipeline.step ba-agent` | 0–1 |
| critic_signal | `pipeline.step ba-critic-agent`, `pipeline.step developer-critic-agent` | 0–1 |
| implementation_faithfulness | `pipeline.step developer-agent` | 0–1 |
| grounding | `pipeline.step developer-agent` | 0–1 |
| test_adequacy | `pipeline.step tester-agent` | 0–1 |
| handoff_honesty | `pipeline.step *` | boolean |
| instruction_following | root observation (`isRootObservation=true`) | 0–1 |
| safety_hygiene | root observation (`isRootObservation=true`) | boolean |
