---
title: Enterprise readiness
description: What an organisation gets from pipeline-kit today for control, cost visibility, guardrails and model routing, and what is portal-only or roadmap.
---

This page answers one question: can a team become AI-native quickly with pipeline-kit, and who controls it?

Every row says where the capability lives. **Shipped** means it is in this repository and you can run it today. **Portal** means it is in the separate [Enterprise portal](/docs/capabilities/portal) product. **Roadmap** means it does not exist yet; nothing here implies otherwise.

| Need | Status | What you get today | Where to read more |
|------|--------|--------------------|--------------------|
| Guardrails on agent actions | Shipped | Hook gates on read, shell, MCP and write; planning gates that stop for human sign-off; opt-in [agent security](/docs/capabilities/agent-security) in `audit`, `warn` or `block` mode | [Planning gates](/docs/capabilities/planning-gates), [Agent security](/docs/capabilities/agent-security), [Hooks troubleshooting](/docs/troubleshooting/hooks) |
| Turning capabilities on and off per project | Shipped | Named feature flags that mirror `config.json` | [Feature flags](/docs/capabilities/feature-flags) |
| Run evidence and quality scores | Shipped | A local observability ledger, deterministic scores, and a Langfuse, Datadog or OTLP export. Paid area `evidence` | [Agent-run observability](/docs/capabilities/observability), [Licensing](/docs/reference/licensing) |
| Cost visibility (tokens) | Shipped locally, not in the portal | The ledger records token counts when the IDE sends them, and they reach Langfuse on `obs flush`. Child task traces can show 0 until the IDE reports usage. The portal receives only the number of unflushed ledger bytes, not tokens | [Agent-run observability](/docs/capabilities/observability), [Portal report format](/docs/reference/portal-protocol) |
| Cost control (budgets, quotas, chargeback) | Roadmap | Not built. There is no spend cap or per-team budget in the kit or the portal report | |
| Control over who may use paid features | Shipped | Signed organisation licence; paid areas fail closed without one | [Licensing](/docs/reference/licensing) |
| Fleet view across projects, roles, audit | Portal | Projects push metadata only; the portal adds sign-in, roles, history and licence visibility. The kit ships the report client | [Enterprise portal](/docs/capabilities/portal), [Portal report format](/docs/reference/portal-protocol) |
| Model routing | Partial | In kit mode the loader resolves model pins per step and records the choice, but the IDE chat does not enforce it. In orchestrator mode (`pipeline-kit run`) routing is enforced through a decider (`jev` or `fixed`) | [Two kits](/docs/capabilities/modes) |
| AI gateway or agent gateway (one proxy that meters, filters and routes every model call) | Roadmap | Not built. Model traffic goes from the IDE or agent CLI to the provider, not through the kit | |
| Rapid rollout to many teams | Shipped | `pipeline-kit init` in each repo, a shared `config.json` in git, per-IDE adapters | [Quick start](/docs/getting-started/first-project), [Install scopes](/docs/getting-started/install-scopes), [IDE adapters](/docs/getting-started/ide-adapters) |

## How to read the status

- **Shipped** claims here were checked against the code and CLI when this page was written. If you find one that is wrong, treat it as a docs bug.
- **Shipped locally, not in the portal** is deliberate. The portal report is metadata only; see [what is never sent](/docs/reference/portal-protocol#what-is-never-sent).
- **Roadmap** rows are listed so the gap is visible. They are not commitments or dates.

## A sensible rollout

1. Install in one repository and run a [first feature](/docs/cookbooks/first-feature).
2. Turn on [agent security](/docs/capabilities/agent-security) in `audit` mode and review findings for a week before moving to `warn` or `block`.
3. Commit `.pipeline/config.json` so every developer gets the same gates. See [Config](/docs/guides/config).
4. Add [observability](/docs/capabilities/observability) if you need token and quality data.
5. Connect the [portal](/docs/capabilities/portal) if you need a fleet view.

Cookbook: [Enterprise governance and portal](/docs/cookbooks/enterprise-governance). Overview: [Governance and portal](/docs/components/governance).
