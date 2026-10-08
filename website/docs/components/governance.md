---
title: Governance and portal
description: Planning gates, licensing, and the enterprise portal — control and visibility across projects without the portal reading your disk.
---

**Governance** is how teams keep agent pipelines structured, reusable, and under control as they scale from one repo to a fleet.

## Three layers

| Layer | What it is | Open vs enterprise |
|-------|------------|--------------------|
| **Planning gates** | Human sign-off on requirements, architecture, BA before build waves | In the open kit |
| **Licensing** | Feature entitlements (orchestrator, Jira intake, portal, assess, …) | Token + public verify path in the kit |
| **Enterprise portal** | Multi-project fleet UI, roles, audit, license visibility | Separate product; kit ships the report client |

## Planning gates

Named workflows pause for human approval where the pack requires it. Same idea in kit mode (IDE) and orchestrator mode (`pipeline-kit approve` / `resume`).

→ [Planning gates and waves](/docs/capabilities/planning-gates)

## Licensing

Paid surfaces fail closed without a valid license. Free surfaces (kit mode core, most CLI, memory package install) stay available.

→ [Licensing reference](/docs/reference/licensing)

## Enterprise portal

Projects **push** metadata (kit version, features, plugins, packages, doctor summary). The portal never mounts your repo and never receives the long-lived license token in history payloads.

```bash
pipeline-kit portal connect --url https://portal.example.com --key pk_...
pipeline-kit portal status
pipeline-kit portal push
```

→ [Enterprise portal](/docs/capabilities/portal) · [Portal protocol](/docs/reference/portal-protocol)

## Problems this pillar solves

| Problem | Where it lands |
|---------|----------------|
| Cannot reuse and govern the same harness on the next project | Workflows + config overlay + gates |
| No fleet view of what is enabled where | Portal |
| Need org control over who runs paid features | Licensing + portal roles |
| Planning must not skip architecture / BA | Planning gates |

Cookbook: [Enterprise governance and portal](/docs/cookbooks/enterprise-governance).

## Next

- [Components overview](/docs/components/overview)
- [Cookbooks index](/docs/cookbooks/)
