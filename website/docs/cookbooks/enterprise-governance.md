---
title: Enterprise governance and portal
description: Use planning gates, activate licenses, and connect projects to the enterprise portal for fleet visibility without the portal reading your disk.
---

**Goal:** Govern agent pipelines across projects — human planning sign-off, entitled features, and a pull-only fleet portal.

**Components used:** [Governance hub](/docs/components/governance), [Planning gates](/docs/capabilities/planning-gates), [Licensing](/docs/reference/licensing), [Portal](/docs/capabilities/portal).

## Prerequisites

- One or more projects with `pipeline-kit init`
- Enterprise plan / portal tenant when using the portal (separate product)
- License token when enabling paid features (orchestrator, Jira intake, portal connect, assess, …)

## Part A — Planning gates

1. Run a workflow that includes planning (`feature-development`, story/epic intake, …).
2. Stop at gate steps; do not skip architecture / BA when policy requires them.
3. In **orchestrator mode**, use CLI control:

```bash
pipeline-kit status --slug my-feature
pipeline-kit approve --slug my-feature   # when a gate is waiting
pipeline-kit resume --slug my-feature
```

Deep dive: [Planning gates and waves](/docs/capabilities/planning-gates).

## Part B — License activate

```bash
pipeline-kit license activate
# or set PIPELINE_KIT_LICENSE per your org runbook
pipeline-kit license status
```

Paid commands **fail closed** without a valid token. Free kit-mode core remains available.

→ [Licensing](/docs/reference/licensing)

## Part C — Connect the portal

1. In the portal UI, **Connect project** → copy the one-time **ingest key**.
2. On the workstation (key is stored outside the repo):

```bash
pipeline-kit portal connect --url https://portal.example.com --key pk_...
pipeline-kit portal status
pipeline-kit portal push
```

3. Successful `init` / `features` / `plugins` / `obs` / `run` / … commands **report automatically** when connected. Failure to reach the portal never fails the local command.

**CI:** set `PIPELINE_PORTAL_URL` and `PIPELINE_PORTAL_KEY` instead of `connect`.

**Verify in portal:** project card shows kit version, mode, features, plugins, packages, last report time.

Deep dive: [Enterprise portal](/docs/capabilities/portal), [Portal protocol](/docs/reference/portal-protocol).

## What governance does *not* do

- Portal does **not** read project disks or rewrite pack files  
- History stores summaries of what changed — not who clicked (see portal docs for audit vs history)  
- Connecting portal is independent of enabling every paid feature  

## Done when

- [ ] Team knows which workflows require human gates  
- [ ] License status matches the features you run  
- [ ] At least one project reports to the portal (if on enterprise plan)  
- [ ] Operators can find fleet drift (kit version, flags) in Analysis  

## Next

- [Governance component hub](/docs/components/governance)
- [Observability cookbook](/docs/cookbooks/observability-eval-testing) for agent scores the portal can reflect as “obs on”
- [Components overview](/docs/components/overview)
