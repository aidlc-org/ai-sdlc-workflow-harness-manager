---
title: Licensing
description: Which pipeline-kit areas are paid, how a license token is issued and activated, what the exit codes mean, and how the enterprise portal fits in.
---

Everyday kit use is open. Five areas need an org **license**: a signed token that
names the organization, an expiry date and the areas it covers.

## Paid areas

| Area | Unlocks |
|------|---------|
| `orchestrator` | Orchestrator mode: `init`/`setup --mode orchestrator`, `run`, `resume`, `approve`, `workflows --scaffold` |
| `jira` | Running the `jira-story`, `jira-epic`, `jira-bug` workflows, and `features enable jira-intake` |
| `governance` | Running `security-review`, `ci-audit`, `dependency-audit`, `accessibility-review` |
| `evidence` | Agent-run observability and eval: every `obs` command except `report`, `eval`, and `features enable agent-observability` |
| `assess` | Repository assessment: `pipeline-kit scan` (also needs the assess package) |

Kit mode, `ask`, `feature-development`, `knowledge`, `plugins`, `memory` and
`obs report` never read the license.

## Activate

```bash
export PIPELINE_KIT_LICENSE='<token>'
pipeline-kit license activate     # verifies, then stores ~/.pipeline/license.json (mode 0600)
pipeline-kit license status       # org, expiry, and each area on or off
```

- Verification is **offline**, against a public key shipped with the kit.
- `PIPELINE_KIT_LICENSE` in the environment wins over the stored file for that process.
- `status` never prints the token.

The [Enterprise portal](/docs/capabilities/portal) does not hold your token. It shows what
was issued to your organization and the license state each connected project reports
(organization, expiry, areas; never the token), and warns when a license is expiring.

## Exit codes and messages

| Code | When | Message |
|------|------|---------|
| 73 | No token, expired token, or the area is not on the license | `license: missing`, `license: expired`, or `license: <area> is not on this license`, each followed by `Run: pipeline-kit license activate` |
| 64 | Issuing: a missing signing key, a bad date, an unknown feature | The reason, on stderr |

The portal shows the same reasons as inline messages and keeps the same codes where
there is a CLI equivalent.

## Issue (vendor only)

```bash
export PIPELINE_KIT_LICENSE_SIGNING_KEY=/secure/path/signing.pem
pipeline-kit license issue --org "Acme Corp" --expires 2027-06-30
```

Without `--features` the token covers all five areas. Pass a comma list to narrow it,
for example `--features jira,assess`. The token works through the end of the expiry day
(UTC). It is printed to stdout, so capture it with a redirect or a secrets manager.

The signing key must stay with the vendor: keep it out of git and out of customer
environments. A token cannot be revoked once issued, because verification is offline;
issue shorter terms where you need tighter control.
