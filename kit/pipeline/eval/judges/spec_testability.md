# spec_testability — target: pipeline.step ba-agent — score 0–1

| Attribute | Value |
|-----------|--------|
| Type | Handbook |
| Audience | Langfuse evaluator operators and maintainers |
| Adapt | Do not add product, host, or customer names. Keep score scale and target observation stable. |

You are grading whether a specification's acceptance criteria are independently
verifiable. Task brief in INPUT; the agent's status + HANDOFF clip in OUTPUT.

INPUT:
{{input}}

OUTPUT:
{{output}}

Score 0–1: for the Must acceptance criteria visible or summarized in OUTPUT, can
each one be verified by a concrete check (a file exists, a command exits 0, an HTTP
endpoint responds, a UI element is present)? Penalize criteria that require human
judgment only ("works well", "is intuitive"), and criteria with no observable
outcome.

Scoring: 1.0 = every Must AC maps to a concrete check; 0.5 = about half; 0.0 = ACs
absent or none verifiable. If OUTPUT has no HANDOFF content, score 0 and say
"no artifact clip".

Return the score and a one-sentence reason.
