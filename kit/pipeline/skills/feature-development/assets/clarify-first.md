# Clarify-first (planning agents)

| Attribute | Value |
|-----------|--------|
| Type | Policy |
| Audience | Parent (copies values into `route.md`) |
| Adapt | Edit the table columns only. Do not add extra classes. |

Owned by **feature-development**. PM (P3), UI designer (U3), Architect (A2), and BA (S3) follow this
file. Do not invent product or technical decisions. Mine prior artifacts first,
then ask the user every remaining decision on the coverage checklist.

Silent `ASSUMPTIONS_USED` is the exception, not the default.

## Lookup then ask

```text
READ ARTIFACTS → APPEND decisions.md → LIST GAPS → ASK USER (if any) → DRAFT
```

1. Read every file in your lookup table that exists on disk, then the repo.
2. Append extracted facts to `features/{slug}/decisions.md` (load
   [decisions-template.md](decisions-template.md) if the file is missing).
3. Walk your coverage checklist. A row already in `decisions.md` or answered
   in `questions.md` is **not** a question.
4. Remaining Unknowns that change scope, actors, success, journeys, data,
   APIs, authz, child split, or testability: write `questions.md`, HANDOFF
   `BLOCKED`, **stop**. Do not draft a fake-complete PRD, architecture, or spec.
5. Draft only when the checklist is answered on disk, the leftover is
   cosmetic (copy, density), or the user said “proceed” / “use defaults”.

Never ask what the **repo** already answers. Never re-ask a decision already
recorded in `decisions.md` or `questions.md`.

## Lookup tables

| Agent | Must read before asking |
|-------|-------------------------|
| PM | Prior state (if any), `USER_REQUEST`, `route.md`, existing `prd.md` / `research.md` / `questions.md` / `decisions.md` on a re-run, `intake.md` if present, repo facts from P2 |
| UI designer | Prior PM state, then listed files: `prd.md`, `research.md`, `decisions.md`, `questions.md`, repo theme/layout paths from U2 |
| Architect | Prior PM, UI, or intake state, then listed files: signed-off `prd.md` or `intake.md` / `epic-plan.md`, `ui-design.md` and `ui/manifest.json` if present, `research.md`, `decisions.md`, `signoff-requirements.md`, repo |
| BA | Prior Architect (or PM / UI / intake) state, then listed files: PRD/intake, `ui-design.md` and mockup index if present, `architecture.md`, `implementation-plan.md`, `architect-concerns.md`, `decisions.md`, `signoff-architect.md` (when Architect ran) |

## Coverage checklists (ask if not already decided)

**PM**

Ask as if UI designer, Architect, and BA will read the PRD next. A naive
prompt is not an excuse for a thin checklist.

- Business / customer goals and why now
- Timeline or release constraint
- Actors and who may act (include roles that change views)
- Success criteria
- In / out of scope
- As-is flow (how the product works today) vs to-be
- Primary journeys and approvals
- **Surfaces:** web / mobile / desktop / ERP / mixed / none (API-only)
- Devices, breakpoints, density (consumer vs enterprise tables)
- Must-have screens vs later; navigation model
- Existing design system / theme in repo vs greenfield
- Brand, light/dark, accessibility bar
- Empty / error / permission-denied expectations
- External systems / integrations
- Persistence expectations (what is stored)
- MVP vs later
- Authz / PII / money / irreversible actions
- NFRs that change design (latency, volume, offline) if the user stated them
- Child-spec split
- Edge cases that change product meaning

**UI designer**

- Surfaces not already decided in the PRD
- Navigation model and must-have screens
- Density and breakpoints
- Theme: reuse repo tokens vs greenfield
- Empty / loading / error / denied per primary journey
- Role-different views
- Accessibility bar if still Unknown

**Architect**

- Module boundaries
- Data ownership
- APIs and contracts
- Persistence
- Authz model
- Integrations / vendors
- NFRs that change design (latency, volume, offline)
- Technical child-spec split
- Failure modes
- Requirements gaps (blocking vs recorded concerns)
- Screen inventory in `ui-design.md` (do not invent extra screens)

**BA**

- Remaining acceptance criteria
- Empty / loading / error states (must match `ui-design.md` §5 when present)
- Acceptance edges
- Testability (how a tester would fail the AC)
- Anything architecture left open

## Caps and batches

| Agent | Max questions per batch |
|-------|-------------------------|
| PM | 20 |
| UI designer | 15 |
| Architect | 15 |
| BA | 15 |

One batch per turn. A **second** batch is allowed only if answers create new
Unknowns. Format: [questions-format.md](questions-format.md).

## When to use ASSUMPTIONS_USED

Only when the user said “proceed” / “use defaults”, or every leftover is
non-blocking (copy, density, cosmetic). Label each default in the PRD, spec
§11, or architecture ADRs. Otherwise HANDOFF `BLOCKED`.
