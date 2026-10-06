---
title: Portal report format
description: Exactly what a pipeline-kit project sends to the enterprise portal, what is never sent, and how the portal protects itself from a modified client.
---

This page is for security reviews. A project reports to the
[Enterprise portal](/docs/capabilities/portal) with an HTTPS request authenticated by a
per-project ingest key. The report is **metadata only**.

## Requests

| Request | Purpose |
|---------|---------|
| `GET /api/ingest/v1/ping` | Checks the key. Returns the organization and project name and the time of the last report. Used by `portal connect` and `portal status`. |
| `POST /api/ingest/v1/report` | Stores the project's latest state. |

Both send `Authorization: Bearer <key>`. A missing or wrong key returns `401`
(`key_required` or `bad_key`). A project may send at most 120 reports a minute (`429`).
An unknown report format returns `400 unsupported_schema` with a hint to upgrade the kit.

## What is sent

| Field | Contents |
|-------|----------|
| `schema`, `reason`, `sent_at` | Format version (1), the command that triggered the report (for example `features.enable`), and a timestamp |
| `project.name` | The project folder's name. **Not its path.** |
| `kit` | Installed pack version, the kit version running, whether the pack is behind, mode (`kit` or `orchestrator`), scope |
| `packages` | Whether the `assess` and `memory` packages are installed |
| `license` | State (`active`, `expiring`, `expired`, `missing`); when active, the organization name, expiry date, days left and licensed areas |
| `features` | Each feature flag as `on` or `off` |
| `plugins` | Graphify graph freshness; whether Archify is on |
| `observability` | Whether it is enabled, the adapter name, bytes not yet flushed |
| `runs`, `boards` | For up to 100 each: slug, workflow, status, current step, last-updated time, pending gates |
| `doctor` | Checks passed, total, and the **names** of failed checks |

## What is never sent

- `config.json` or any other file's contents
- File paths or the machine's name
- Prompts, agent output, requirements, plans or source code
- The license token, the ingest key, Jira or other credentials
- Anything from the observability ledger beyond the unflushed byte count

## What the portal does with it

- **Whitelists every field.** Anything not in the table above is dropped, and strings and
  lists are length-limited. A modified client cannot make the portal store extra content.
- **Keeps the latest report, plus a change history.** The latest report is replaced by each new one.
  History stores only a small summary when something changed (version, feature flags, packages, license
  state, plugin and observability state, failing doctor checks) with a plain-language description of the
  change. Run and board details are never part of it. It records what changed and when, **not who**, and is
  deleted after 90 days (a project's newest row is kept) or when the project is removed.
- **Stores keys hashed.** A key is shown once, when it is created or rotated.
- **Never connects back.** The portal makes no request to a project or its network.
- **Separates organizations.** Every project, report, user and audit entry belongs to one
  organization, and every query is scoped to the caller's organization.

## On the project side

- The connection (`url` and `key`) is kept in `~/.pipeline/portal.json`, owner-only where
  the operating system supports it, or in `PIPELINE_PORTAL_URL` and `PIPELINE_PORTAL_KEY`.
  It is never written inside the project.
- Plain `http://` is refused except for `localhost`, so the key is not sent unencrypted.
- A report has a 4-second limit and a failure never changes a command's result.
