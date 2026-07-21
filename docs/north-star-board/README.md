# North Star Review Board

## Purpose

The North Star Review Board is Meeting Ingest's recurring product-governance practice. It keeps the product aligned with its original user outcome as implementation, real-world usage, and release pressure accumulate.

The board does not grade feature count. It asks whether the intended outcome is real, coherent, trustworthy, and demonstrable. It establishes evidence and independent judgment before implementation or roadmap changes begin.

## Board Seats

1. **Steve Jobs seat** — product essence, taste, simplicity, focus, coherence, and release judgment. This is a historically informed product-leadership lens, not a claim of literal identity and never a license to invent quotations.
2. **Apple product manager seat** — customer, job to be done, audience, evidence, priorities, roadmap, acceptance criteria, and sequencing. It separates demonstrated user value from plausible feature value.
3. **Apple engineer seat** — architecture, correctness, data integrity, recovery, security, portability, observability, and release risk. It identifies trust claims that exceed engineering guarantees.
4. **Apple developer seat** — installation, onboarding, daily workflow, command ergonomics, documentation, recovery, and maintenance. It evaluates whether the real happy and unhappy paths feel lighter than the work replaced.
5. **Apple marketing and branding seat** — positioning, audience, naming, language, claims, differentiation, first impression, packaging, and launch posture. It requires every important claim to be demonstrated by the current product.

The primary project owner chairs the board and owns synthesis. The chairman must separate personal product judgment from board consensus and disagreements.

## Independence Protocol

- Every seat receives the same dated source brief and read-only repository access.
- Seats review independently and, when agents are available, in parallel.
- A seat must not see another seat's report before completing its own.
- Reviewers report findings only. They must not edit files, mutate git state, commit, update iQ Context, or change external systems.
- The primary agent is the sole writer of review artifacts and durable project state.
- All five independent reports are preserved before chairman synthesis begins.
- The chairman report distinguishes unanimous or majority consensus, seat disagreements, personal judgment, evidence-backed conclusions, and interpretation.
- The canonical roadmap is not changed silently. The human owner receives the verdict, proposed product definition and milestone sequence, accepted/deferred/rejected recommendations, release posture, and judgment calls before direction changes.

## When To Convene

Convene the board:

- before changing the canonical roadmap or product definition;
- before claiming a major milestone, beta, release, or “just works” experience;
- after meaningful external dogfooding exposes a trust or usability gap;
- when implementation and active state materially outrun product documentation;
- when a new product surface competes with an unfinished primary workflow;
- after a release gate fails twice for different reasons;
- at least once per major roadmap layer, even if no crisis triggers it.

Reconvene dates or trigger conditions must be stated in every level set.

## Required Source Material

Each dated source brief reconciles, rather than merely repeats:

- original vision, product principles, requirements, specifications, and plans;
- current internal and public product definitions;
- target user and job to be done;
- initial and current roadmaps;
- implementation inventory and end-to-end workflow;
- package, distribution, installation, CLI help, and first-run behavior;
- supported inputs, extraction, normalization, provider, render, signal, ledger, archive, and reconcile paths;
- artifact and provider contracts;
- error handling, recovery, idempotency, duplicate behavior, and security boundaries;
- tests, fixtures, safe validation results, git status, and recent history;
- generated artifacts, dogfooding, external UAT, captures, failures, and downstream integrations;
- known gaps, unresolved questions, and repository state at review start;
- the exact review question and decision standard.

Documentation is evidence of intent or claim, not automatic proof. Claims must be checked against code, tests, CLI behavior, generated artifacts, history, and observed use.

## Required Outputs

Every review lives at `docs/north-star-board/reviews/YYYY-MM-DD/` and contains:

- `00-source-brief.md`
- `01-steve-jobs.md`
- `02-apple-product-manager.md`
- `03-apple-engineer.md`
- `04-apple-developer.md`
- `05-apple-marketing-branding.md`
- `06-chairman-report.md`
- `07-level-set.md`
- `README.md`

Every independent report contains:

1. Verdict
2. Evidence
3. What is working
4. Gaps and risks
5. Recommendations in priority order
6. What to stop, defer, or simplify
7. Release decision
8. Confidence and unresolved questions

File and line references are required wherever practical. Reviewers say explicitly when an examined area has no issue rather than inventing concerns.

The chairman report records the overall verdict, consensus, disagreements, chairman judgment, product definition, user/job, release posture, blockers, milestone order, frozen work, and measurable release gates.

The level set is the concise operational conclusion: true present state, completed and active work, unproven claims, next milestone and deliverables, measurable exit gate, frozen expansion, and reconvene trigger.

## Work-State Classification

Every review classifies meaningful work as one of:

- complete;
- active;
- planned;
- absorbed into another outcome;
- deferred;
- superseded;
- abandoned or cancelled.

“Implemented” is not synonymous with “demonstrated,” and “documented” is not synonymous with either.

## Decision Standard

The board approves an aligned release posture only when:

- the product can be explained in one human sentence;
- the primary workflow is obvious;
- behavior matches documentation and product claims;
- failures preserve trust and provide recovery;
- generated artifacts are useful, predictable, and inspectable;
- reprocessing and retries behave safely;
- the product removes more ceremony than it creates;
- a real supported meeting reaches useful output without expert intervention;
- dogfooding proves the intended outcome outside synthetic fixtures;
- current state, roadmap, implementation, and public truth agree.

Important claims require reproducible demonstration. A missing gate narrows the release posture or claim; it is not offset by unrelated feature breadth.

## Review History

| Date | Review | Status |
| --- | --- | --- |
| 2026-07-20 | [Founding North Star Review](reviews/2026-07-20/) | Convened; verdict and level set recorded in the review package |
| 2026-07-20 | [Reconvened North Star Review](reviews/2026-07-20-reconvened/) | Convened after owner correction; proposes Just Works Continuity pending owner approval |
