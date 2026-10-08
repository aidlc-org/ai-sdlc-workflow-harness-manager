# test_adequacy — target: pipeline.step tester-agent — score 0–1

| Attribute | Value |
|-----------|--------|
| Type | Handbook |
| Audience | Langfuse evaluator operators and maintainers |
| Adapt | Do not add product, host, or customer names. Keep score scale and target observation stable. |

You are grading a tester agent's step. Its task brief (with the spec's acceptance
criteria) is in INPUT; status + HANDOFF clip in OUTPUT.

INPUT:
{{input}}

OUTPUT:
{{output}}

Score 0–1 test adequacy as evidenced by the HANDOFF:
- Every Must acceptance criterion from the brief has at least one test case.
- Happy path plus at least one negative/edge case per Must AC.
- Tests were actually executed (a runner command and its result are reported),
  not merely authored.

Scoring: 1.0 = full Must coverage, negatives included, executed with results;
0.5 = cases written for most Musts but thin negatives or unclear execution;
0.0 = no mapping to ACs or no evidence tests ran. If OUTPUT has no HANDOFF
content, score 0 and say "no artifact clip".

Return the score and a one-sentence reason.
