# scope_control — target: pipeline.step ba-agent — score 0–1

| Attribute | Value |
|-----------|--------|
| Type | Handbook |
| Audience | Langfuse evaluator operators and maintainers |
| Adapt | Do not add product, host, or customer names. Keep score scale and target observation stable. |

You are checking a specification for gold-plating against the original ask.
The original task brief is in INPUT; the agent's status + HANDOFF clip in OUTPUT.

INPUT:
{{input}}

OUTPUT:
{{output}}

Score 0–1 how tightly the specified work matches the ask:
- Every Must requirement traces back to something the user actually asked for.
- Extras (new persistence, auth, routes, settings, analytics) are either absent or
  explicitly parked in out-of-scope.
- The change class (micro/minor/feature) is not inflated by invented requirements.

Scoring: 1.0 = no unrequested Must work; 0.5 = one or two unrequested Musts; 0.0 =
the spec is mostly invented scope. If OUTPUT has no HANDOFF content, score 0 and
say "no artifact clip".

Return the score and a one-sentence reason.
