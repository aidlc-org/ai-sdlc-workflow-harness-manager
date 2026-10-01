# UI design contract

| Attribute | Value |
|-----------|--------|
| Type | Template |
| Audience | The specialist that writes the artifact |
| Adapt | Fill placeholders only. Do not add a product, host, or customer name. |

Owned by **feature-development**. UI designer copies this to
`features/{slug}/ui-design.md`. This is the **design artifact** Architect,
BA, and Developer consume. A mood board is not a substitute.

Every section below must be filled (`N/A — reason` only when it truly does
not apply). Cite repo paths for existing theme. Cite mockup files for each
primary screen.

```markdown
# UI design — {title}

**Status:** Draft | Ready for sign-off
**Slug:** `{slug}`
**Created:** {YYYY-MM-DD}
**Surfaces:** web | mobile | desktop | erp | mixed | none
**Skills loaded:** ui-design, {platform skills}, ui-accessibility, ui-html-mockups | none
**Codebase grounded:** Yes (theme paths below) | No (greenfield)
**Mockups:** features/{slug}/ui/index.html | none

---

## 1. Design intent

Who uses the UI, on which surfaces, and what “done” looks like visually.
Do not restate the whole PRD.

## 2. Surfaces and density

| Surface | Density | Primary devices | Skill loaded |
|---------|---------|-----------------|--------------|
| web | consumer | desktop + tablet | ui-web-responsive |
| … | … | … | … |

If `none`: stop after this section. No mockups.

## 3. Information architecture

### 3.1 Navigation

How the user moves: top nav, sidebar, tabs, wizard, master-detail, app shell.

### 3.2 Screen inventory

| ID | Screen | Route / entry | Actors | Mockup file | Journey |
|----|--------|---------------|--------|-------------|---------|
| S-1 | … | … | … | `ui/{file}.html` | … |

## 4. Primary journeys (UI)

Numbered steps. Name the screen id at each step.

## 5. States per primary screen

| Screen | Empty | Loading | Error | Denied | Success |
|--------|-------|---------|-------|--------|---------|
| S-1 | … | … | … | … | … |

## 6. Tokens

| Token | Value | Source |
|-------|-------|--------|
| color-bg | … | `{path}` or greenfield |
| color-text | … | … |
| color-accent | … | … |
| space-unit | … | … |
| font-body | … | … |
| focus-ring | … | … |

Match the repo theme when one exists. Do not invent a second palette.

## 7. Components used

| Component | Where | Notes |
|-----------|-------|-------|
| … | S-1 | existing / new-in-mockup-only |

## 8. Accessibility bar

Target: WCAG 2.2 AA unless the PRD set a higher bar. Keyboard path for
primary journeys. Contrast called out where accent-on-accent is used.

## 9. Constraints for Architect / BA / Developer

- Architect must not invent screens missing from §3.2.
- BA empty/error ACs must match §5.
- Developer implements production UI to match mockups and tokens; do not
  copy `features/{slug}/ui/` into the product tree.

## 10. Assumptions

| ID | Assumption | Why defaulted | Impact if wrong |
|----|------------|---------------|-----------------|
| UA-1 | … | … | … |

## 11. Open questions

none | OQ-1: …
```
