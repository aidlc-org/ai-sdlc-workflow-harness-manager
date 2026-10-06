# Pack document standard

| Attribute | Value |
|-----------|--------|
| Type | Handbook |
| Audience | Anyone who edits markdown under `.pipeline/` |
| Adapt | Do not add product, host, or customer names. Update this file only when the document types change. |

Use this file when you add or edit markdown under `.pipeline/`. The pack is
an **enterprise operating model**, not a product demo. Every page must stay
portable across customers, stacks, and IDEs.

## Why this exists

New projects should be able to:

1. Open a file and know **what it is** (brief, procedure, template, policy, wiki).
2. See **who reads it** and **what they may change**.
3. Adapt deploy, test, and tracker settings **without rewriting** agent briefs.

If a sentence names a customer app, host, port, or tracker site, it is in the
wrong file.

## Document types

| Type | Path | Purpose | What a new project changes |
|------|------|---------|----------------------------|
| Agent brief | `agents/*.md` | Role, isolation, inputs, outputs, handoff | Almost never. Do not add folder names here. |
| Skill | `skills/*/SKILL.md` | Step-by-step procedure | Commands, runners, or paths **only** in the skill that owns them (deploy, test). |
| Template | `skills/*/assets/*-template.md` | Shape of a `features/{slug}/` artifact | Placeholders only. Do not fill with a real product. |
| Policy | `*-policy.md`, `clarify-first.md` | Tables the parent copies into `route.md` | The `true`/`false` columns. |
| Wiki | `wiki/*.md` | Reusable lesson from a past run | Add a page after retro. Do not store customer incidents with secrets. |
| Rule | `rules/*.mdc` | Durable coding standard | Narrow `globs` in the frontmatter to this repository's folders. |
| Handbook | `docs/CUSTOMER-GUIDE.md`, `docs/DOCUMENT-STANDARD.md`, pack `README.md` | How to install, overlay, and author this pack | Per engagement: `AGENTS.md` and `config.json` in the **project**, not these files. |

## Required header (after the title)

Every agent brief, skill, policy, wiki page, rule, and handbook starts with:

```markdown
| Attribute | Value |
|-----------|--------|
| Type | Agent brief \| Skill \| Template \| Policy \| Wiki \| Rule \| Handbook |
| Audience | Who reads this file |
| Adapt | What a new project may change — or “do not add product names” |
```

Templates may use a short **Owner / Writes to / Adapt** block instead of the
table if the body is a fill-in form.

## Section order

**Agent brief:** Role → Isolation → Inputs → Procedure → Outputs → Failure → Parent next.

**Skill:** Purpose → When to use / not → Adapt for this project (if any) → Procedure → Failure → Anti-patterns.

**Wiki:** Symptom → Root cause → Do not → Convention → Files → Verify.

Do not invent extra top-level sections unless they are durable (for example
**Bug workflow** on tester). Keep the names above so authors can find the
same gate in every file.

## Language

- Write for a regulated enterprise delivery team: precise, short, no slang.
- Name **roles** (product manager, architect, developer) and **artifacts**
  (`prd.md`, `signoff-ba.md`), not a demo brand.
- Say “the application under `REPO_ROOT`” or “the target in `deploy.targets`”.
- Secrets, tokens, customer data, and tracker site URLs never appear in pack
  markdown. Put them in the environment or IDE MCP settings.

## Forbidden in this pack

Application folder names, sample shop names, internal platform names, specific
localhost ports used by a demo, and issue keys from a past engagement.

Those belong in the **project overlay**:

| Concern | File the project edits |
|---------|------------------------|
| Tracker on/off, connection (mcp/cli/api), issue-type map | `.pipeline/config.json` → `intake.jira` or `intake.github` |
| Build / preview / health | `.pipeline/skills/local-deployment/assets/local-deploy-runbook.md` and `scripts/deploy-local.sh` |
| Deploy target names | `.pipeline/config.json` → `deploy.targets` |
| Path-based verify hints | `.pipeline/config.json` → `verify.rules` |
| Test runners | Testing skills, only if the defaults do not match |
| Product blurb | Root `AGENTS.md` (installer does not write it) |

## Adding a file

1. Pick a type from the table above.
2. Copy the header and section order.
3. List the file on the workflow allowlist (`workflows/*.json`) if a step
   must read it.
4. Do not add the file under `.cursor/` or `.claude/` — the pack stays in
   `.pipeline/` so the IDE does not auto-load it.
