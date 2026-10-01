---
name: ui-accessibility
description: >-
  Load when ui-designer-agent produces any visual surface. WCAG 2.2 AA bar
  for mockups: contrast, labels, focus order, keyboard. Do not treat this
  as a full audit of production code.
---

# UI — accessibility

| Attribute | Value |
|-----------|--------|
| Type | Skill |
| Audience | ui-designer-agent when any visual surface exists |
| Adapt | Do not lower the bar below WCAG 2.2 AA unless the PRD named a legal standard. |

Apply to every HTML mockup in `features/{slug}/ui/`.

## Bar

| Item | Required |
|------|----------|
| Contrast | Text 4.5:1; large text 3:1; UI components 3:1 |
| Labels | Every input has a visible `<label>` (or `aria-label` if the PRD forbids visible text) |
| Name/role/value | Buttons are `<button>`; links are `<a href>` |
| Focus | Visible `:focus-visible` ring; logical DOM order |
| Keyboard | Primary journey completable without a pointer |
| Status | Errors tied to fields (`aria-describedby` or adjacent text) |
| Landmarks | One `header`, one `main`; nav labeled |

## Mockup checks (U5)

- [ ] No color-only status (include text or icon + text)
- [ ] Disabled submit still explains what is missing
- [ ] Denied state is a message, not a silent blank
- [ ] Hit area ≥ 24px (44px on mobile skill)

## Do not

Claim AA for production · skip labels because the mockup is “visual only” ·
use placeholder-as-label.
