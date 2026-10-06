---
name: github-intake
description: >-
  Invoke when the pipeline must turn a GitHub issue or pull request into
  on-disk work input: the orchestrator matched a github.com URL, owner/repo#N,
  or #N with intake.github.repo set. Fetch using intake.github.connection
  (mcp, cli, or api; read-only), normalize it to features/{slug}/intake.md,
  and classify it as story | bug | epic so the orchestrator can pick a
  workflow. Do not write specs, code, or tests.
---

# GitHub intake (read-only)

| Attribute | Value |
|-----------|--------|
| Type | Skill |
| Audience | The named agent, or the parent when this file is on the allowlist |
| Adapt | Change commands or paths only in deploy and testing skills. Planning skills stay product-neutral. |

Turn one GitHub issue or PR into **one normalized file** the rest of the pipeline can read without ever calling GitHub again.

**Success:** `features/{slug}/intake.md` is complete and factual, `ISSUE_TYPE` is set, no secrets or personal data leaked to disk.
**Failure:** invented requirements, a summarized description that drops acceptance criteria, or a GitHub write.

All GitHub settings come from `intake.github` in [`.pipeline/config.json`](../../config.json). Never hardcode a host, owner, repo, or token in this skill or in the output. `GH_TOKEN` / `GITHUB_TOKEN` stay in the environment.

| When | Read |
|------|------|
| Issue type maps to the epic workflow | [`../epic-breakdown/SKILL.md`](../epic-breakdown/SKILL.md) |
| I4 (normalize) | [`../jira-intake/assets/intake-template.md`](../jira-intake/assets/intake-template.md) |
| `connection` is `api` | [scripts/github_api.py](scripts/github_api.py) |

---

## Steps

`I1 CONFIG → I2 CONNECT → I3 FETCH → I4 NORMALIZE → I5 CLASSIFY → I6 HANDOFF`

### I1 Config

Read `intake.github`: `connection`, `repo`, `mcp_namespaces`, `tools`, `cli`, `api`, `issue_type_map`, `include_comments`, `write_back`, `max_children`.

`connection` is `mcp` | `cli` | `api`. Missing `connection` means `cli`. Any other value is `BLOCKED` — do not guess.

Confirm the injected `GITHUB_REF` is a `github.com/{owner}/{repo}/issues|pull/{N}` URL, `owner/repo#N`, or `#N` / `N` when `intake.github.repo` (or `GITHUB_REPO`) is set. Bare `#N` without a repo is `BLOCKED` — do not guess a repository.

Use **only** the chosen connection. Do not try the other two if it fails.

### I2 Connect

Substitute `{N}` (issue/PR number) and `{REPO}` (`owner/repo`) in CLI argv from `GITHUB_REF` plus `intake.github.repo`.

#### `mcp`

1. If `mcp_namespaces` is non-empty, try those namespaces in order.
2. If it is empty, **discover**: list available namespaces and pick the one exposing the configured `tools.issue` name. Inspect the tool schema before calling it.
3. If a namespace reports `needsAuth`, run its auth tool once, then retry.

No reachable GitHub namespace ⇒ `BLOCKED` with this recovery:

```text
No GitHub MCP tool is available for {REF}. Set intake.github.connection to cli
(if gh is installed) or api (GH_TOKEN), or connect GitHub MCP and set
intake.github.mcp_namespaces, or paste the issue title, body, and acceptance
criteria into the chat and re-run with work_source: text.
```

#### `cli`

Read `cli.bin` (default `gh`) and `cli.issue_view` (or `cli.pr_view` when the ref is a pull URL).

1. Resolve `{N}` and `{REPO}` in the argv. Run `{bin} {issue_view…}` from the repo root.
2. If the binary is missing or the command exits non-zero, `BLOCKED`:

```text
GitHub CLI failed for {REF} (intake.github.connection=cli). Install and
authenticate gh (or the client in intake.github.cli.bin), set intake.github.repo
if the ask was only #N, or set connection to mcp or api, or paste the issue
title, body, and acceptance criteria and re-run with work_source: text.
```

Do not call `curl` / `wget`. Do not invent a different CLI.

#### `api`

1. Confirm `GH_TOKEN` or `GITHUB_TOKEN` is set. Optional `GITHUB_API_URL` for GitHub Enterprise. Do not write these into config or into `intake.md`.
2. Run, from the repo root:

```bash
python .pipeline/skills/github-intake/scripts/github_api.py issue get {REF}
```

Pass `--repo {owner/repo}` when `{REF}` is only a number.

3. Missing env, HTTP 401/403, or a non-zero exit ⇒ `BLOCKED`:

```text
GitHub API failed for {REF} (intake.github.connection=api). Set GH_TOKEN or
GITHUB_TOKEN in the environment (not in config.json), or set connection to mcp
or cli, or paste the issue title, body, and acceptance criteria and re-run with
work_source: text.
```

Do not call `curl` / `wget`. Do not put the token in chat.

### I3 Fetch (read-only)

Collect, when present: key (`owner/repo#N`), issue type, status, summary (title), description (body), labels, milestone, reporter/assignee **logins only**, URL, and attachment / image **file names** from the body.

How to fetch depends on `connection`:

- **mcp** — call `tools.issue` for the number and repo.
- **cli** — parse the CLI stdout from I2. If it is not enough, do not call MCP; `BLOCKED` and ask the user to switch `connection` or paste the body.
- **api** — parse the JSON stdout from `github_api.py`. That object is the issue.

Shared rules:

- **Reads only.** `write_back` is `false` by default: no comments, labels, closes, or PR reviews. Ask the user first even when it is `true`. CLI writes also need `PIPELINE_ALLOW_GITHUB=1`. MCP writes need `PIPELINE_ALLOW_MCP=1`.
- Do not download attachment bodies. Record names so the analyst can ask for one.
- Fetch comments only when `include_comments` is `true`, and then only comments that add requirements or reproduction facts.
- One retry on a transient error, then `BLOCKED`. A permission error is `BLOCKED`, not an empty issue.

### I4 Normalize

Load [`../jira-intake/assets/intake-template.md`](../jira-intake/assets/intake-template.md) and write `features/{slug}/intake.md`.

- Copy the **body and acceptance criteria verbatim** (converted to Markdown). Summarizing here is how Must requirements get lost.
- Convert GitHub Markdown as-is; keep code blocks, tables, and step numbering intact.
- Mark anything the issue does not state as `Unknown — not in the issue`. Never fill a gap from imagination; the BA or bug analyst handles gaps with labeled assumptions.
- **Redaction (mandatory):** no tokens, keys, passwords, cookies, auth headers, connection strings, or customer PII (emails, phone numbers, account numbers, addresses). Replace with `[redacted]` and note the field. Logins of reporter/assignee are allowed; nothing else about them is.

### I5 Classify

Lowercase the issue type (GitHub issue type name, else `bug` if a bug/defect/incident label is present, else `pull_request` for PRs, else `issue`) and map it through `issue_type_map`, falling back to `default`. Record both the raw type and the mapped workflow. A story that is really a defect stays whatever GitHub says — reclassifying is the user's call, not yours; flag it in `NOTES` instead.

### I6 Epic extension

When the mapped workflow is the epic one, continue with [`../epic-breakdown/SKILL.md`](../epic-breakdown/SKILL.md) **in this same Task** — you already hold the connection — and write `features/{slug}/epic-plan.md` before handing off. GitHub children are **sub-issues**, not JQL.

---

## Outputs

```text
features/{slug}/intake.md
features/{slug}/epic-plan.md        # epic only, via epic-breakdown
features/{slug}/HANDOFF-intake.md
```

## Failure handling

| Situation | HANDOFF |
|-----------|---------|
| Chosen connection unreachable / auth fails | `BLOCKED` + the recovery block from I2 for that connection |
| Unknown `connection` value | `BLOCKED` — valid values are mcp, cli, api |
| Issue not found or no permission | `BLOCKED` — never continue with an empty issue |
| Bare `#N` and `repo` empty | `BLOCKED` `INPUT_MISSING` |
| Description empty and no acceptance criteria | `ASSUMPTIONS_USED`; list what is missing so BA or the analyst asks |
| Issue type not in the map | `SUCCESS` with the map `default`; put the raw type in `NOTES` |
| Epic with no sub-issues | `ASSUMPTIONS_USED`; `epic-plan.md` records zero stories and the parent should ask the user |

## HANDOFF (`features/{slug}/HANDOFF-intake.md`)

```text
HANDOFF intake-agent → parent
STATUS: SUCCESS | ASSUMPTIONS_USED | BLOCKED
GITHUB_REF: {REF}
ISSUE_TYPE: story | bug | epic | {raw type}
WORKFLOW: {mapped workflow}
INTAKE_PATH: features/{slug}/intake.md
EPIC_PLAN_PATH: features/{slug}/epic-plan.md | n/a
CHILDREN: n/a | {count} ({keys})
REDACTIONS: NONE | {fields}
NOTES: {ambiguities, missing ACs, raw type mismatch}
PARENT_NEXT: @signoff:requirements | bug-analyst-agent | stop for user
```

## Anti-patterns

Summarizing the body · inventing acceptance criteria · writing to GitHub · pasting the raw payload into chat instead of disk · storing tokens or customer data · fetching every comment · calling GitHub MCP from the parent chat · hardcoding owner/repo or a host · calling `curl`/`wget` · silently switching `connection` when the configured one fails · treating a bare `#N` as GitHub when `intake.github.enabled` is false or `repo` is empty.
