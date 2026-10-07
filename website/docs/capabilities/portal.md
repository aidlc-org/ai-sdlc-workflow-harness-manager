---
title: Enterprise portal
description: The enterprise web portal for pipeline-kit. Projects report their own state to it with an ingest key; it adds sign-in, roles, analysis, license visibility and audit. A separate product in its own repository.
---

The **Enterprise Pipeline Portal** is a web application where a team sees every
pipeline-kit project in one place. It is a **separate proprietary product in its
own repository** (not open source), offered on the enterprise plan. This kit
ships the public reporting client and protocol; the portal server and UI do not
live in the kit repository.

It works the way an observability tool does. **Projects report to the portal;
the portal never reads a project's folders and never changes a project.** Each
project has its own ingest key, like a Langfuse project key.

:::note Cloud first
The portal runs as a cloud service managed by the vendor, with many customer
organizations on one deployment. The report protocol is the same one an enterprise
would use against a portal it hosts itself, which is planned but not part of this
version.
:::

## How a project connects

1. In the portal, an operator or admin chooses **Connect project**, names it, and
   receives an **ingest key**. It is shown once.
2. In the project folder:

   ```bash
   pipeline-kit portal connect --url https://portal.example.com --key pk_...
   ```

   The command verifies the key, stores the connection in `~/.pipeline/portal.json`
   (outside the project, so it is never committed) and sends a first report.
3. From then on, **a local change is reported automatically**. These commands send a
   fresh report when they succeed:

   | Command | When it reports |
   |---|---|
   | `init`, `update`, `uninstall` | Always |
   | `features` | `enable`, `disable` |
   | `plugins` | `install`, `uninstall` |
   | `obs` | `install`, `uninstall`, `flush` |
   | `memory` | `link`, `import-local` |
   | `knowledge` | `init`, `extract` |
   | `scan`, `run`, `resume`, `approve` | Always |
   | `license` | `activate` |

   `pipeline-kit portal push` sends the current state on demand, and
   `portal status` shows when the portal last heard from the project. In CI, set
   `PIPELINE_PORTAL_URL` and `PIPELINE_PORTAL_KEY` instead of running `connect`.

**Reporting never breaks a command.** If the portal cannot be reached, the command you
ran still succeeds and prints one line saying the change was not reported. The next
report carries the whole state, so nothing is lost.

## What the portal shows

| Area | What it does | Who can use it |
|------|--------------|----------------|
| Sign-in | Username and password, session cookie, lockout after repeated failures, forced password change for new and reset accounts | Everyone |
| Fleet | One card per project, grouped by team: version, mode, what is on, when it last reported | All roles |
| Project | Overview (kit, features, plugins, packages, observability, license, doctor), Runs, Connection | All roles view; operators and admins manage the connection |
| History | A timeline of what changed in a project and when, with the command that caused it. Never who. 90 days | All roles |
| Analysis | Widgets for project health, run status, recent activity, feature adoption, kit version drift, observability, licenses and packages, plus 30-day trend charts for feature adoption, kit drift and reporting health. All projects or one | All roles view; operators and admins add widgets |
| Licenses | What was issued to your organization, and what each project reports about its own license | All roles |
| Users | Create, change role, disable, reset password, delete | Admins |
| Audit log | Sign-ins, user changes, project and key changes, with the acting user | Admins |
| Organizations | Create a customer organization with its first admin; issue license tokens | Vendor staff |

A project that has not reported for 48 hours shows as **not reporting**, with its last
known state. A project that has never reported shows **waiting for first report**.

## Roles

Roles apply inside one organization. Each customer is its own organization, with
separate users, projects, widgets and audit log; one organization cannot see another.

| | Admin | Project operator | Viewer |
|---|:-:|:-:|:-:|
| Fleet, project details, licenses | yes | yes | yes |
| Connect, rename, rotate the key of, and remove projects | yes | yes | no |
| Analysis dashboard | view, add, remove any widget | view, add, remove own | view |
| Users and roles | yes | no | no |
| Audit log | yes | no | no |

The server checks the role on every request. The interface hides what a role cannot
use, but hiding is only a convenience. Vendor staff additionally create organizations
and issue licenses; that is a flag on the user, not a role.

## Keys

- Each project has its own key. It is stored **hashed**, so it cannot be shown again.
  If it is lost, rotate it.
- **Rotating or removing a project stops the old key immediately.** A leaked key affects
  one project and can be shut off without touching the rest. (License tokens are
  different: the kit verifies them offline, so they cannot be revoked.)
- The connection must use `https://`. Plain `http://` is accepted only for `localhost`.

## Read-only in this version

The portal shows what projects report. It cannot change a feature, plugin or setting in
a project. Change those with the kit CLI in the project; the portal updates within
seconds. Letting operators request changes from the portal is possible later, because
the protocol leaves room for it, but it is not built.

## Messages

One message system is used everywhere, so you always know what happened and what to do:

- **Success** appears as a short notice after an action, for example "Project created".
- **Warnings** appear as a banner for standing problems (a license expiring within 30 days on a project) and as a notice when an action went through with a caveat.
- **Errors** appear under the field they belong to (a project name already in use, a weak password) or, when no field applies, at the top of the form. Each carries a hint.

On the CLI side, a connection problem is one plain line with the reason (for example
"the portal did not accept this key. Copy it again from the portal, or rotate it there.").

## Hosting

The portal repository ships a `Dockerfile`, a `docker-compose.yml` that puts the portal
behind Caddy for HTTPS, and a step-by-step guide (`docs/CONTAINER.md` in that repository):
building the image with the open kit's wheel, first start and the default users, creating
customer organizations, turning on license issuing with a mounted signing key (vendor
deployment only), backups and reverse-proxy settings. The container files are written but
have not been built or run yet; the portal's CI builds the image.

## Not in this version

Single sign-on, changing a project's settings from the portal, who made a change (history
records what and when only), history longer than 90 days, per-project access limits for
operators, and a self-hosted edition. See also [what is sent](/docs/reference/portal-protocol) and
[Licensing](/docs/reference/licensing).
