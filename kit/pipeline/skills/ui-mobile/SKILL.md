---
name: ui-mobile
description: >-
  Load only when ui-designer-agent U1 classifies a phone / tablet /
  touch-first surface. Thumb zones, touch targets, and mobile nav for HTML
  approximations of iOS HIG / Material. Do not emit native code.
---

# UI — mobile

| Attribute | Value |
|-----------|--------|
| Type | Skill |
| Audience | ui-designer-agent after U1 selects mobile |
| Adapt | Do not add a product, host, or store listing. |

HTML mockups approximate mobile. They are **not** iOS/Android projects.

## Decide

| Choice | Default unless PRD says otherwise |
|--------|-----------------------------------|
| Width | 390px frame (phone); 768px frame (tablet) |
| Touch targets | ≥ 44×44 px |
| Thumb zone | Primary CTA in the lower third |
| Navigation | Bottom tabs for 3–5 top destinations; else stacked list |
| Gestures | Document only (swipe to refresh). Do not require JS. |
| Platform flavor | Neutral. Note iOS vs Material **copy/icon** only if the PRD named one OS. |

## Must show in mockups

- Safe-area padding (status + home indicator as CSS padding)
- One-handed primary action
- Full-screen blocking error, not a tiny toast-only failure
- Keyboard-safe note on forms (CTA not covered)

## Do not

Generate Xcode/Android Studio trees · assume hover states · use hover-only
affordances · load `ui-desktop` unless U1 also selected desktop.
