# Clarifying questions format

| Attribute | Value |
|-----------|--------|
| Type | Template |
| Audience | The specialist that writes the artifact |
| Adapt | Fill placeholders only. Do not add a product, host, or customer name. |

Owned by **feature-development**. PM (max **20**), UI designer (max **15**), Architect (max **15**), and
BA (max **15**) use this shape. Follow [clarify-first.md](clarify-first.md)
before writing questions. Write to `features/{slug}/questions.md` and wait for
the user reply.

```markdown
# Questions — {pm | ui-designer | architect | ba}

**slug:** {slug}
**batch:** 1 | 2

Q1. [Decision this unblocks — e.g. who may delete records]
- audience: user | pm
- already_answered_from: none
- A) … (Recommended)
- B) …
- C) Other: …

Why it matters: …
Default if unanswered: A
```

Rules:

- Never ask what the repo or a prior artifact already answers.
- Never re-ask a decision already in `decisions.md` or an earlier `questions.md` batch.
- Each question must unblock a coverage-checklist item (see clarify-first).
- `audience: pm` is Architect-only. On jira-story / jira-epic, use `user` instead.
- After answers, append them to `questions.md` **and** `decisions.md`, then continue.
