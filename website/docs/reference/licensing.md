---
title: Licensing
description: Which pipeline-kit areas check a local entitlement token, how tokens are issued and activated, and how the proprietary enterprise portal fits in.
---

This repository is **MIT**. You may use, modify, and redistribute the kit,
including areas that check a local license token. Those checks support
commercial entitlement for vendor-distributed builds; they do not narrow the
MIT grant.

**Issue and validation** are implemented in a separate **private** package,
[`pipeline-kit-license`](https://github.com/) (not published with this open
repo). Enterprise users install that package, then activate a vendor token.
Without it, paid commands exit **73**.

Six areas need an org **license** in the distributed CLI: a signed token that
names the organization, an expiry date and the areas it covers.

## Paid areas

| Area | Unlocks |
|------|---------|
| `orchestrator` | Orchestrator mode: `init`/`setup --mode orchestrator`, `run`, `resume`, `approve`, `workflows --scaffold` |
| `jira` | Running the `jira-story`, `jira-epic`, `jira-bug` workflows, and `features enable jira-intake` |
| `governance` | Running `security-review`, `ci-audit`, `dependency-audit`, `accessibility-review` |
| `evidence` | Agent-run observability and eval: every `obs` command except `report`, `eval`, and `features enable agent-observability` |
| `assess` | Repository assessment: `pipeline-kit scan` (also needs the assess package) |
| `portal` | `portal connect` / `portal push` and automatic reporting to a pipeline portal |

Kit mode, `ask`, `feature-development`, `knowledge`, `plugins`, `memory`,
`obs report`, and `portal status` / `disconnect` never require a license.

## Activate

```bash
# Requires the private pipeline-kit-license package on the same Python env as pipeline-kit
export PIPELINE_KIT_LICENSE='<token>'
pipeline-kit license activate     # verifies, then stores ~/.pipeline/license.json (mode 0600)
pipeline-kit license status       # org, expiry, and each area on or off
```

- Verification is **offline**, against a public key shipped with
  `pipeline-kit-license` (not this public repo).
- `PIPELINE_KIT_LICENSE` in the environment wins over the stored file for that process.
- `status` never prints the token.

The [Enterprise portal](/docs/capabilities/portal) does not hold your token. It shows what
was issued to your organization and the license state each connected project reports
(organization, expiry, areas; never the token), and warns when a license is expiring.

## Exit codes and messages

| Code | When | Message |
|------|------|---------|
| 73 | No private package, no token, expired token, or the area is not on the license | Install package hint, `license: missing`, `license: expired`, or `license: <area> is not on this license` |
| 64 | Issuing: a missing signing key, a bad date, an unknown feature | The reason, on stderr |

## Issue (vendor only)

Issuance uses the private package (and optionally the portal UI). The public kit
CLI delegates when `pipeline-kit-license` is installed:

```bash
export PIPELINE_KIT_LICENSE_SIGNING_KEY=/secure/path/signing.pem
pipeline-kit license issue --org "Acme Corp" --expires 2027-06-30
```

Without `--features` the token covers all six areas (including `portal`). Pass a
comma list to narrow it, for example `--features jira,assess`. The token works
through the end of the expiry day (UTC).

The signing key must stay with the vendor: keep it out of git and out of customer
environments. A token cannot be revoked once issued, because verification is offline;
issue shorter terms where you need tighter control.
