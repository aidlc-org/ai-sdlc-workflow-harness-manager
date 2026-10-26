---
title: Team best practices
description: How a team shares one pipeline-kit setup in git, keeps per-machine settings local, sets review gates and guardrails, and onboards a new developer.
---

This page is for the person who rolls the kit out to a team. It covers what to commit, what stays on each laptop, which gates to keep, and how a new developer gets running. It links to the reference pages for values instead of repeating them.

## Commit the shared setup

Commit the files that define how the pipeline behaves, so every developer and CI run sees the same rules.

| Commit | Why |
|--------|-----|
| `.pipeline/` (pack, `config.json`, deploy runbook and script) | One chain, one set of gates, one deploy contract |
| `AGENTS.md` | The workflow table the agent reads first. See [AGENTS.md guide](/docs/guides/agents-md) |
| The IDE adapter folder (`.cursor/`, `.claude/` or `.github/`) | Skill and guardrail hooks travel with the repo |
| `test-knowledge/` after a bootstrap promote | Reviewed QA catalog |

Do not commit run output. Add `features/` and `.pipeline/state/` to `.gitignore`. Commit `features/` only if you want specs in git. Details: [git ignore](/docs/guides/gitignore).

Keep `config.json` small and reviewed like code. Change `verify.rules`, `deploy` and the intake blocks in a pull request. Leave `workflows.*` chains and `gates.*` at their defaults unless the team decides otherwise. See [adapt config.json](/docs/guides/config) and the [config reference](/docs/reference/config).

Hook configs contain the Python interpreter that `init` found on the machine that ran it. After a clone, or on a machine where Python moved, run `pipeline-kit init --ide <ide>` again. It merges and keeps existing entries.

Upgrade deliberately. Run `pipeline-kit update` in one branch, review the diff, and merge. `update` refreshes managed files and keeps local `config.json` values. See [Where you can install](/docs/getting-started/install-scopes).

## Keep per-machine settings local

Some settings must not be shared. Keep them on the machine or in the environment.

| Setting | Where it lives |
|---------|----------------|
| Jira and GitHub tokens (`JIRA_API_TOKEN`, `GH_TOKEN`, `GITHUB_TOKEN`) | Environment. Never in `config.json` |
| License token | `PIPELINE_KIT_LICENSE` or `~/.pipeline/license.json`, written by `pipeline-kit license activate` |
| Portal connection | `~/.pipeline/portal.json` from `pipeline-kit portal connect`. In CI use `PIPELINE_PORTAL_URL` and `PIPELINE_PORTAL_KEY` |
| Model API keys (`CURSOR_API_KEY`, `TYPESAFE_API_KEY`) | Environment |
| Memory bank MCP entry | Each developer's own MCP config. See [Memory bank](/docs/capabilities/memory) |
| One-run overrides (`RUN_ARCHITECT`, `RUN_TESTER`, `CONSULT_UI`, `ALLOW_DEPENDENCY`) | The prompt or shell for that run |

A project pack always wins over the user pack in `~/.pipeline`. Use the user pack only as a laptop default for repos that have no pack of their own.

## Keep the review and planning gates on

The gates are the point of the kit. Feature-class work stops for three sign-offs: requirements, architecture and BA. Developers do not start until `signoff-ba.md` exists.

- Leave `gates.require_planning_signoff_before_build` and `gates.require_signoff_before_deploy` at `true`.
- Do not let anyone start `developer-agent` because an earlier specialist wrote `next_agent: developer-agent`. Honor the sign-off files.
- Keep `retry_cap` at its default so a critic cannot loop forever.
- Decide who signs each gate. The kit records the file, not the person.

Details: [Planning gates](/docs/capabilities/planning-gates).

## Set guardrails

Guardrail hooks ship with every `init` for Cursor, Claude Code and GitHub. They deny commits and pushes, undeclared dependency installs, secret reads, remote shell pipes and MCP writes unless you opt in. See the [adapter pages](/docs/getting-started/ide-adapters) for what each IDE wires.

Rules for a shared or customer machine:

- Do not set `PIPELINE_ALLOW_ALL=1` or `PIPELINE_HOOK_SKIP=1`. They disable the commit, network, MCP and artifact gates.
- Use the narrow overrides only for one run: `PIPELINE_ALLOW_GIT=1`, `PIPELINE_ALLOW_DEPS=1`, `PIPELINE_ALLOW_NET=1`, `PIPELINE_ALLOW_MCP=1`, `PIPELINE_ALLOW_JIRA=1`, `PIPELINE_ALLOW_GITHUB=1`.
- Do not copy `features/{slug}/ui/` mockups into application source. The write hook denies it.
- Do not put production secrets or real personal data in PRDs or mockups.
- Leave `failClosed` off. A crashed hook should not freeze the IDE. See [hooks troubleshooting](/docs/troubleshooting/hooks).
- Add `verify.rules` for your folders so edits to risky paths get a reminder.

Two opt-in layers add more:

- [Agent security](/docs/capabilities/agent-security) records or blocks risky actions. Start in `audit` mode with `pipeline-kit security install . --mode audit`, review findings, then move to `warn` or `block`.
- [Agent-run observability](/docs/capabilities/observability) traces what agents did. It needs the `evidence` license area except for `obs report`.

These guardrails are process and tool policy. They are not a security certification.

## Choose models

Model choice lives in the `orchestrator` block of `config.json`. What it does depends on the mode.

| Mode | Behavior |
|------|----------|
| Orchestrator mode (`pipeline-kit run`) | Enforced. The engine picks a model before each agent |
| Kit mode | Advisory. The loader writes `chosen_model` to `features/{slug}/context-pack.json` and `model-routing.json`. An agent CLI may pass it on if its Task API takes a model field. IDE chat does not enforce it |

Set the shortlist once in `orchestrator.models.candidates`, pin a step in `orchestrator.models.steps`, and set `orchestrator.fallback_model`. Kit mode resolves pins and the fallback offline by default. Set `PIPELINE_KIT_MODEL_ROUTING=0` to turn kit-side resolution off. Do not tell the team that kit mode forces a model. See [Modes](/docs/capabilities/modes).

## Govern across projects

For several repos, use the enterprise path: activate the license, then connect each project to the portal. Steps are in the [enterprise governance cookbook](/docs/cookbooks/enterprise-governance). The portal reports metadata only. See [Portal](/docs/capabilities/portal).

## Onboard a new developer

1. Install the CLI. See [Install the CLI](/docs/getting-started/install-cli) and run `pipeline-kit --version`.
2. Clone the repo.
3. Run `pipeline-kit init --ide <ide>` in the repo root so hooks use this machine's Python. Use `cursor`, `claude-code`, `github` or `none`.
4. Run `pipeline-kit doctor` and fix anything it reports.
5. Set the tokens the team uses (Jira, GitHub) in the environment. Activate the license if the team uses paid areas.
6. Open the repository root in the IDE. A multi-root window whose first folder is another repo will not load these hooks.
7. Smoke test with two prompts: "How does X work?" should run `ask`. "Add a small label change" should run `feature-development`.
8. Read the [workflow tour](/docs/workflows/tour) and the [troubleshooting index](/docs/troubleshooting).

Give the new developer the team's rules in one place, ideally the top of `AGENTS.md`: who signs each gate, which overrides are allowed, and where tokens come from.

## Checklist

- [ ] `.pipeline/`, `AGENTS.md` and the IDE folder are committed
- [ ] `features/` and `.pipeline/state/` are ignored
- [ ] No secrets in `config.json`
- [ ] Planning gates left on
- [ ] No one has `PIPELINE_ALLOW_ALL=1` or `PIPELINE_HOOK_SKIP=1` set
- [ ] Deploy script and test runners match the repo. See [Adapt to your stack](/docs/guides/adapt-to-your-stack)
- [ ] New developers follow the onboarding list above
