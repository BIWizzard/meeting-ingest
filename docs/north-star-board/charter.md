# North Star Board — Charter (Meeting Ingest)

## Panel (five-seat Apple lens)

| Seat | File | Lens |
|---|---|---|
| Steve Jobs | 01 | product essence, taste, simplicity, focus, coherence, release judgment |
| Apple Product Manager | 02 | customer, job to be done, evidence, priorities, roadmap, acceptance, sequencing |
| Apple Engineer | 03 | architecture, correctness, data integrity, recovery, security, portability, release risk |
| Apple Developer | 04 | installation, onboarding, daily workflow, command ergonomics, recovery, maintenance |
| Apple Marketing/Branding | 05 | positioning, naming, language, claims, differentiation, launch posture |

Seats run as claude-implementer agents, blind, in parallel, from an identical
dated brief with read-only repository access. A seat must not see another
seat's report before completing its own. Seats report findings only; the
primary agent is the sole writer of review artifacts and durable state. The
orchestrator chairs and synthesizes; the owner ratifies. The Jobs seat is a
historically informed product-leadership lens, never a license to invent
quotations.

## Convening triggers

- Before changing the canonical roadmap or product definition.
- Before claiming a major milestone, beta, release, or "just works" experience.
- After meaningful external dogfooding exposes a trust or usability gap.
- When implementation and active state materially outrun product documentation.
- When a new product surface competes with an unfinished primary workflow.
- After a release gate fails twice for different reasons.
- At least once per major roadmap layer, even if no crisis triggers it.
- Contested deviations escalated from check-ins.

## Decision standard

Each seat renders SHIP / AMEND / REDESIGN with evidence. The chair synthesizes
without vote counting, distinguishing unanimous or majority consensus, seat
disagreements, personal judgment, evidence-backed conclusions, and
interpretation. The canonical roadmap is never changed silently: the owner
receives the verdict, proposed direction, dispositions, and judgment calls
before direction changes. The owner's ratification is the authority; owner
deviations from panel consensus are legitimate and logged.

## Review history

| Record | Date | Subject | Status |
|---|---|---|---|
| 001 | 2026-07-20 | Founding product review and level-set | superseded |
| 002 | 2026-07-20 | Reconvened: Just Works Continuity milestone and approved-runtime policies | ratified |

## Migration note (2026-07-24)

This registry was migrated from the legacy layout to the codified board-skill
layout on 2026-07-24: `reviews/2026-07-20/` became `001-founding-review/` and
`reviews/2026-07-20-reconvened/` became `002-just-works-continuity/`. Record
contents were moved byte-identical and never edited; internal references to the
old directory names inside ratified record files are preserved as written and
map per the renames above. Record 002's ratified owner decisions live in its
original `09-owner-decisions.md`; `07-owner-decisions.md` is a migration
adapter pointing there and formalizing the obligations table.
