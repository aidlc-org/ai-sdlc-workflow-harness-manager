# Architecture — {title}

| Attribute | Value |
|-----------|--------|
| Type | Template |
| Audience | The specialist that writes the artifact |
| Adapt | Fill placeholders only. Do not add a product, host, or customer name. |

**Status:** Draft | Ready for BA
**Slug:** `{slug}`
**Requirements:** `features/{slug}/prd.md` | `features/{slug}/intake.md` | `features/{slug}/epic-plan.md`
**Created:** {YYYY-MM-DD}

---

## 1. Context

Who uses the system and which existing modules this change touches. Cite paths.

```mermaid
flowchart LR
  user[Actor] --> app[Existing app]
  app --> dep[Existing dependency]
```

## 2. Containers / modules

What we add or change. Prefer existing modules over new ones.

```mermaid
flowchart TB
  ui[UI surface] --> api[API or store]
  api --> data[Persistence or none]
```

## 3. Sequence (required when a new API or multi-step flow exists)

```mermaid
sequenceDiagram
  actor User
  User->>UI: action
  UI->>Service: call
  Service-->>UI: result
```

`none — single-screen local change` is valid when no new API or multi-step flow
exists. Say so.

## 4. ADRs (architecture decisions)

| ID | Decision | Why | Rejected alternative |
|----|----------|-----|----------------------|
| ADR-1 | … | … | … |

## 5. Child-spec split (technical)

If this differs from the PM / intake split, this table **wins** for BA.

| Child slug | Job | Why it is a separate spec |
|------------|-----|---------------------------|
| `{child-a}` | … | … |

## 6. Constraints

- Paths, interfaces, or patterns developers must reuse
- Authz / PII / secrets boundaries
- What must not be invented

### New dependencies

`none`, or one row each. Mirror these into `state/architect-agent.json`
`context.new_dependencies` — the hooks read the state file, not this table.

| Package | Why nothing existing works |
|---------|----------------------------|
| … | … |

## 7. Risks

| Risk | Why it matters | Mitigation |
|------|----------------|------------|
| … | … | … |

## 8. Open questions

none | OQ-1: … (must be empty or cosmetic before Ready)

## 9. Concerns (HITL)

Record technical findings that the signed requirements did not fully settle.
Copy blocking rows into `questions.md` and HANDOFF `BLOCKED` /
`BLOCKED_CHALLENGE_PM`. Recorded rows stay here for `@signoff:architect`.

| ID | Severity | Audience | Concern | Implied change |
|----|----------|----------|---------|----------------|
| none | — | — | none | — |

Severity is `blocking` or `recorded`. Do not mark Ready while a blocking
row remains.

## 10. Test model delta (only when `TEST_DESIGN_ENABLED`)

Write `features/{slug}/test-design/model-delta.json` from the model-delta
template, or set `no_test_model_change: true` here and in that file.

| Planned node | Kind | Why |
|--------------|------|-----|
| none | — | overlay already covers this change |

## 11. Enhanced diagram artifacts (only when `ARCHIFY_ENABLED`)

Keep the mermaid blocks above. Link Archify JSON/HTML here, or record
`mermaid-fallback` when the plugin is missing or deliver failed.

Write `features/{slug}/diagrams/manifest.json` from the diagram-manifest
template.

| Diagram | Type | JSON | HTML | Status | Visual review |
|---------|------|------|------|--------|---------------|
| none | — | — | — | mermaid-fallback | — |
