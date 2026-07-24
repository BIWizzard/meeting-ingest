# 2026-07-20 Level Set

## Where The Product Truly Is

Meeting Ingest is a credible internal-alpha ingestion engine for a technical owner working through an agent host. It reliably turns real `.txt`, `.vtt`, and `.docx` transcripts into useful summary-plus-verbatim Markdown, signals, provenance, ledger state, processed archives, and reconciled inbox state.

It is not a general self-serve product and has not earned a claim that it just works. The engine is stronger than its onboarding, host wrapper, human CLI, release packaging, and current product truth.

The maintainer is the only true power user. Sustained dogfooding lives primarily in the HTV IQ Data Analytics corpus, not the six-meeting repository sample. HTV contains a much deeper legacy/current history whose physical artifacts, valid ledger state, legacy signals, handoffs, identities, and briefing readiness have not been reconciled. Spelman contains additional historical output but is not initialized for the current engine. See [Owner Addendum](08-owner-addendum.md).

## Completed

- project init, discovery, config, hashing, IDs, locking, typed errors, and JSON summaries;
- deterministic extraction for `.txt`, `.vtt`, and `.docx`;
- validated mock, Anthropic, and session-provider boundaries;
- stable summary-plus-verbatim rendering and signal JSONL;
- content-hash idempotency, ledger snapshots, archive, reconcile, and duplicate repair;
- session request/response binding, preflight validation, and resume-safe handoff scanning;
- effective-date selection, override, warning, and controlled repair;
- generalized signal/identity foundation and most deterministic Stakeholder Briefing mechanics;
- real maintainer dogfooding across six meetings and all supported formats;
- a substantially deeper HTV power-user history and a smaller Spelman history, currently unadopted and not fully valid under current contracts;
- 231 passing tests on 2026-07-20.

## Active

- an uncommitted, already-reviewed Layer 5B cleanup/corruption-recovery tail awaiting focused follow-up review;
- North Star governance adoption and owner disposition of this report.

Active does not mean released.

## Not Yet Proven

- a fresh consumer can install, initialize, and process a real meeting without expert intervention;
- the post-response-contract-fix agent workflow closes the external UAT friction;
- one host is production-quality and canonical;
- pending work, completion, and recovery are obvious in human-facing output;
- health reporting distinguishes trust failures from advisories;
- stale locks, stale handoffs, and known partial-write boundaries recover without filesystem expertise;
- supported config controls match behavior;
- alternate output modes work;
- Stakeholder Briefing produces demonstrated user value;
- general self-service, platform-wide experience, or production remote-provider claims.
- safe interpretation, adoption, or useful downstream consumption of the power user's accumulated HTV and Spelman history.

## Proposed Product Definition

> Meeting Ingest turns `.txt`, `.vtt`, and `.docx` transcripts into trustworthy meeting records—summary, decisions, actions, evidence, provenance, and source history—for technical project owners working with coding agents.

## Proposed Next Milestone

**Just Works Ingest**

One selected host, one documented install and initialization path, one natural-language inbox request, three supported input formats, one output mode, truthful pending/completion state, explicit date handling, safe recovery, honest health, independent post-fix proof, and a read-only Power-User Corpus Reckoning across HTV and Spelman.

## Deliverables

- named reference host and 0.1 audience;
- canonical install, version, upgrade, init, consent/config, and first-real-meeting path;
- clear human and JSON states for pending, partial, complete, and failed;
- completion output naming artifacts, archive, reconcile, provider, and date confidence;
- blocker/recoverable/advisory doctor severity;
- guarded stale-lock and stale-handoff recovery;
- diagnosis/recovery for known primary-ledger orphan boundaries;
- config controls implemented, removed, or explicitly unsupported;
- provider-scalar/front-matter safety and a documented privacy/retention model;
- one canonical workflow contract with host-specific deltas verified;
- README, CLI, skills, status, roadmap, questions, and iQ state reconciled after owner approval;
- recorded acceptance and external UAT evidence.
- deterministic read-only HTV/Spelman inventory, contract classification, corpus reconciliation, privacy-safe adoption report, and representative historical continuity proof.

## Measurable Exit Gate

- three fresh-project trials;
- at least one non-author operator;
- at least six non-synthetic meetings spanning `.txt`, `.vtt`, and `.docx`;
- no source inspection, envelope hand-authoring, durable-artifact hand edits, or undocumented cache deletion;
- every success produces and reports Markdown, signals, ledger completion, processed archive, reconcile completion, provider/host, and date confidence;
- invalid response, interruption, duplicate redrop, stale handoff, stale lock, archive/reconcile failure, and known orphan boundary each have tested safe recovery;
- no pending state is presented as completed success;
- post-run `doctor` reports zero trust-invalidating findings and distinguishes advisories;
- no inert supported config remains;
- signal fingerprints verify; artifact integrity follows the owner-approved mutability contract;
- full regression and focused acceptance suites pass;
- at least one post-fix external UAT succeeds without maintainer intervention;
- all product truth surfaces agree.
- HTV/Spelman history is classified as current-valid, adoptable, controlled-repair, legacy-only, conflicting, or ignored, with no client-corpus mutation before separate approval.
- a representative historical sample proves whether the product can provide useful continuity for its actual power user and establishes the boundary for Stakeholder Briefing consumption.

## Must Not Expand Yet

Do not expand Guidance V1.1, contradiction interpretation, communication/OCR/social sources, provider/host breadth, in-place corpus migration, global identity, deeper iQ integration, or public brand/launch scope before the exit gate. Read-only corpus inventory and adoption analysis are required evidence, not prohibited expansion.

The pre-existing cleanup/corruption-recovery slice may only finish its prepared review as bounded carryover if the owner approves it. It must not reopen Layer 5 expansion.

## Release Posture

Continue as internal/private alpha for expert technical operators. Current claims should name three formats, one summary-plus-verbatim output, tested engine reliability, and maintainer dogfooding. Do not claim general self-service, all-host readiness, alternate modes, proven Stakeholder Briefing, or just works.

## Reconvene

Reconvene when the Just Works Ingest gate is complete, or sooner if:

- two fresh-consumer trials fail for different causes;
- the selected host changes;
- the audience broadens;
- a trust-invalidating dogfood or production failure occurs.

## Decisions Awaiting Owner Approval

1. Product definition.
2. First supported host.
3. 0.1 audience.
4. Milestone sequence and scope freeze.
5. Whether meeting Markdown is immutable or user-editable.
6. Low-confidence-date completion policy.
7. Whether alternate modes remain the second candidate milestone.
8. Whether the existing cleanup slice may close as bounded carryover.
9. Whether to approve read-only HTV/Spelman corpus reckoning inside the next milestone and which adoption posture to select after its report.
