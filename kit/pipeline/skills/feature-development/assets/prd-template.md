# Product requirements document (PRD)

| Attribute | Value |
|-----------|--------|
| Type | Template |
| Audience | The specialist that writes the artifact |
| Adapt | Fill placeholders only. Do not add a product, host, or customer name. |

Owned by **feature-development**. PM copies this to `features/{slug}/prd.md`.
This is the **requirements artifact** Architect, BA, and the user sign. A thin
`plan.md` is not a substitute.

A missed or shallow PRD cannot be repaired later by architecture or specs.
Every section below must be filled (`N/A — reason` only when it truly does
not apply). Cite repo paths from `research.md`.

```markdown
# PRD — {title}

**Status:** Draft | Ready for sign-off
**Slug:** `{slug}`
**Created:** {YYYY-MM-DD}
**Source request:** {one-line user ask}
**Codebase grounded:** Yes (paths in research.md) | No (greenfield)
**Timeline:** {stated window or Unknown — asked}

---

## 1. Executive summary

5–8 sentences. What changes, for whom, why now, and what “done” means.
Do not leave this as a restatement of the user ask.

## 2. Business context

| Item | Statement | Source |
|------|-----------|--------|
| Product / customer | {who the product serves} | user / repo / asked |
| Business goal | {outcome the business wants} | … |
| User / customer goal | {job the end user must finish} | … |
| Success metric | {how we know it worked} | … |
| Timeline / constraint | {date, release, or none} | … |
| Why now | {trigger} | … |

If any row is Unknown and it changes scope, stop at P3 and ask.

## 3. Problem

What is painful or missing today? Who feels it? What happens if we do nothing?

## 4. Actors

| Actor | Goal | Constraints / authority |
|-------|------|-------------------------|
| … | … | … |

## 5. As-is (how the product works today)

Required unless greenfield. Map the **current** flow the change touches.
Example shapes: an access-review process, an approval chain, an integration
with an external system. This is analysis, not a guess.

| Step | Who | What happens today | Evidence (path or “user confirmed”) |
|------|-----|--------------------|-------------------------------------|
| 1 | … | … | `{path}` |

Narrative (one short subsection per existing flow):

### 5.1 Current flow — {name}

1. …
2. …

### 5.2 Gaps / breakpoints

Where the current flow fails, stops, or forces a workaround.

## 6. To-be (expected flow)

### 6.1 Primary journeys

Numbered steps. Name the actor at each step.

### 6.2 Alternate and error journeys

Approvals denied, integration down, empty result, unauthorized actor.

### 6.3 External systems

| System | Direction | What we send / receive | Exists today? |
|--------|-----------|------------------------|---------------|
| … | in / out / both | … | yes (path) / no / Unknown |

### 6.4 Surfaces and UX constraints

Required so UI designer (and Architect) do not invent the product shape.
`N/A — API/CLI/batch only` is valid when there is no user-facing surface.

| Item | Statement | Source |
|------|-----------|--------|
| Surfaces | web / mobile / desktop / ERP / mixed / none | user / asked |
| Devices / breakpoints | … | … |
| Density | consumer / enterprise | … |
| Navigation | … | … |
| Must-have screens | … | … |
| Theme | repo path or greenfield | … |
| Accessibility bar | WCAG 2.2 AA or stated | … |
| Empty / error / denied | … | … |

If any row is Unknown and it changes screens or architecture, stop at P3 and ask.

## 7. Goals and non-goals

### Goals
- G-1: …

### Non-goals / out of scope
- …

## 8. Options considered

| Option | Keep? | Why |
|--------|-------|-----|
| A — … | yes (recommended) | … |
| B — … | no | … |

## 9. Recommended direction

One paragraph. Cite research.md facts (R-ids). Say what we will **not** invent.

## 10. Capabilities (product-level)

High-level Must / Should only. BA will write FRs and ACs. Do not skip a
capability that Architect or BA would otherwise invent.

| ID | Capability | Priority | Journey |
|----|------------|----------|---------|
| C-1 | … | Must | 6.1 |

## 11. Proposed child specifications

At least one. Each becomes `features/{slug}/{child-slug}/`.

| Child slug | Job (one line) | Why it is a separate spec |
|------------|----------------|---------------------------|
| `{child-a}` | … | … |

## 12. Constraints

Authz, PII, money, irreversible actions, compliance, timeline, systems we
must reuse. Label Unknowns — do not silently default them.

## 13. Success criteria

- S-1: …
- S-2: …

## 14. Risks and dependencies

| Risk / dependency | Why it matters | Mitigation |
|-------------------|----------------|------------|
| … | … | … |

## 15. Assumptions

| ID | Assumption | Why defaulted | Impact if wrong |
|----|------------|---------------|-----------------|
| A-1 | … | … | … |

## 16. Open questions

none | OQ-1: …

## 17. Evidence index

Point at `research.md` rows. Every as-is claim in §5 needs an R-id or an
explicit user confirmation recorded in `decisions.md`.

## 18. Ready for sign-off

Yes — as-is and to-be are grounded; split is stable; parent may request
requirements sign-off. | No — {what is still blocking}
````
