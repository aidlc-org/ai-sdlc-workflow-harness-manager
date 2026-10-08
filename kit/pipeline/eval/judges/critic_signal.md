# critic_signal — target: pipeline.step ba-critic-agent, pipeline.step developer-critic-agent — score 0–1

| Attribute | Value |
|-----------|--------|
| Type | Handbook |
| Audience | Langfuse evaluator operators and maintainers |
| Adapt | Do not add product, host, or customer names. Keep score scale and target observation stable. |

You are grading an independent critic step in a coding pipeline. The critic's task
brief is in INPUT; its status, HANDOFF clip, and verdict are in OUTPUT.

INPUT:
{{input}}

OUTPUT:
{{output}}

Score 0–1 whether the critic produced real signal rather than a rubber stamp:
- A verdict is present (approve / approve-with-nits / changes-required).
- The verdict is justified by specific, checkable observations (named files,
  requirements, ACs) — not generic praise.
- approve-with-nits or changes-required lists concrete items; a bare "approve"
  with no evidence of review scores low.

Scoring: 1.0 = verdict + specific grounded findings; 0.5 = verdict with thin
generic justification; 0.0 = no verdict or pure rubber stamp. If OUTPUT has no
HANDOFF content, score 0 and say "no artifact clip".

Return the score and a one-sentence reason.
