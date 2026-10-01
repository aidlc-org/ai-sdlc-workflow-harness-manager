# Planning sign-off

| Attribute | Value |
|-----------|--------|
| Type | Template |
| Audience | The specialist that writes the artifact |
| Adapt | Fill placeholders only. Do not add a product, host, or customer name. |

Owned by **feature-development**. The **parent** writes this file after the
user approves a planning artifact. Specialists do not write sign-off files.

Write one of:

- `features/{slug}/signoff-requirements.md`
- `features/{slug}/signoff-architect.md`
- `features/{slug}/signoff-ba.md`

```markdown
# Sign-off — {requirements | architect | ba}

**SIGNOFF:** approved
**role:** requirements | architect | ba
**slug:** {slug}
**artifact:** features/{slug}/prd.md | features/{slug}/intake.md | features/{slug}/epic-plan.md | features/{slug}/ui-design.md | features/{slug}/architecture.md | features/{slug}/HANDOFF.md
**ui_artifacts:** none | features/{slug}/ui-design.md, features/{slug}/ui/index.html
**concerns_reviewed:** none | {C-ids the user accepted or deferred}
**approved_at:** {YYYY-MM-DD}
**note:** {optional user comment} | none
```

`SIGNOFF: approved` must appear exactly like that — parent and (customer) hooks
parse the token.

When `ui-designer-agent` ran, `@signoff:requirements` lists both the PRD (or
intake) and `ui-design.md` / `ui/index.html`. Do not write a separate
`signoff-ui.md`.

## Parent rules

- Do not spawn the next specialist until this file exists for that gate.
- On revise: delete or rewrite the file so it no longer says `approved`, then
  re-spawn the author with the user’s comments.
- Void **downstream** sign-offs when an upstream artifact changes:
  - requirements or UI design change → delete `signoff-architect.md` and `signoff-ba.md`
  - architecture change → delete `signoff-ba.md`
- Micro / minor / jira-bug never write these files.
