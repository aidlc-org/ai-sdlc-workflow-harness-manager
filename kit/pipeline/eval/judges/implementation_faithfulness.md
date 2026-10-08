# implementation_faithfulness — target: pipeline.step developer-agent — score 0–1

| Attribute | Value |
|-----------|--------|
| Type | Handbook |
| Audience | Langfuse evaluator operators and maintainers |
| Adapt | Do not add product, host, or customer names. Keep score scale and target observation stable. |

You are grading a developer agent's implementation step. Its task brief (which
carries the spec/patch context) is in INPUT; status + HANDOFF clip in OUTPUT.

INPUT:
{{input}}

OUTPUT:
{{output}}

Score 0–1 whether the claimed implementation matches the brief:
- The HANDOFF's claimed changes map to the Must requirements in the brief.
- No unrequested additions are claimed (new persistence, auth, routes, dependencies).
- Explicit out-of-scope items were not implemented.

Scoring: 1.0 = claims cover the Musts with no extras; 0.5 = Musts covered but
unrequested additions appear; 0.0 = claims don't match the brief or Musts missing.
If OUTPUT has no HANDOFF content, score 0 and say "no artifact clip".

Return the score and a one-sentence reason.
