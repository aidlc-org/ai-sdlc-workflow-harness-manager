# grounding — target: pipeline.step developer-agent — score 0–1

| Attribute | Value |
|-----------|--------|
| Type | Handbook |
| Audience | Langfuse evaluator operators and maintainers |
| Adapt | Do not add product, host, or customer names. Keep score scale and target observation stable. |

You are checking whether a developer agent's HANDOFF claims are grounded rather
than fabricated. Task brief in INPUT; status + HANDOFF clip in OUTPUT.

INPUT:
{{input}}

OUTPUT:
{{output}}

Score 0–1 how grounded the claims are:
- Claimed edits name specific files/paths, not vague areas.
- Claimed verification (build/test/run) names the actual command or result.
- Claims are internally consistent (no "all tests pass" next to unresolved errors,
  no SUCCESS next to admitted failures).

Scoring: 1.0 = specific files + verification evidence, consistent; 0.5 = specific
claims but no verification evidence; 0.0 = vague or self-contradictory claims.
If OUTPUT has no HANDOFF content, score 0 and say "no artifact clip".

Return the score and a one-sentence reason.
