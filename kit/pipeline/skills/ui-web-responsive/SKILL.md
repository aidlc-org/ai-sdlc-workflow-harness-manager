---
name: ui-web-responsive
description: >-
  Load only when ui-designer-agent U1 classifies a browser / SaaS / admin /
  marketing surface. Breakpoints, navigation, and form patterns for the web
  mockups. Do not use for native mobile, dense ERP tables, or product code.
---

# UI — web responsive

| Attribute | Value |
|-----------|--------|
| Type | Skill |
| Audience | ui-designer-agent after U1 selects web |
| Adapt | Do not add a product, host, or framework name. |

Use this pack for **browser** surfaces. HTML mockups still follow
[ui-html-mockups](../ui-html-mockups/SKILL.md).

## Decide

| Choice | Default unless PRD says otherwise |
|--------|-----------------------------------|
| Breakpoints | 360 / 768 / 1024 / 1280 |
| Navigation | Top bar for marketing; sidebar for authenticated app shells |
| Forms | One column on narrow; labels above fields; submit at the end of the group |
| Tables | Card list below 768; table at 1024+ |
| Feedback | Inline field errors; page-level alert for server failure |

## Must show in mockups

- Skip link + main landmark
- Nav that collapses below 768 (details/summary is enough; no JS required)
- Primary CTA visible without horizontal scroll at 360
- Focus styles on interactive controls

## Do not

Assume a native app chrome · skip tablet · invent a CSS framework · emit
React/Vue.
