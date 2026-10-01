---
name: ui-erp-enterprise
description: >-
  Load only when ui-designer-agent U1 classifies ERP / enterprise density:
  master-detail, filters, bulk actions, role views, data tables, long forms.
  Pair with ui-web-responsive or ui-desktop when those surfaces also match.
---

# UI — ERP / enterprise

| Attribute | Value |
|-----------|--------|
| Type | Skill |
| Audience | ui-designer-agent after U1 selects ERP / enterprise |
| Adapt | Do not add a customer ERP module or vendor name. |

Use this pack for **operational** UIs: queues, ledgers, approvals, catalogs.

## Decide

| Choice | Default unless PRD says otherwise |
|--------|-----------------------------------|
| Density | Compact (4–8px). Tables first, cards second. |
| Pattern | Master list + filters + bulk bar + detail drawer or page |
| Roles | One view per actor that the PRD named (requester vs approver vs admin) |
| Long forms | Sections with save per section; show required markers |
| Bulk | Checkbox column + action bar; confirm destructive bulk |
| Empty | Explain why the queue is empty and the next action |

## Must show in mockups

- Filter + search above the table
- Column headers that imply sort (even if static HTML)
- Role-different screens when actors differ (do not hide behind one layout)
- Permission-denied as a distinct state, not a blank table
- Record count / pagination note

## Do not

Use a consumer marketing layout for a 20-column grid · drop bulk actions ·
merge all roles into one screen unless the PRD said so.
