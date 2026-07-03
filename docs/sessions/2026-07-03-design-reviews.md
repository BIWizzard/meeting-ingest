# Design Reviews & V1 Code Review Cycle — 2026-07-03

**Repo:** meeting-ingest
**Branch:** `main`
**Phase:** Open-ended (pre-phase-tracker) — design validation through first implementation
**Task(s):** Six sequential review rounds: scope coherence, artifact contract, implementation plan, v1 code review, fix-verification follow-up, and real-transcript output evaluation
**Session ID:** 2026-07-03-759c

## Session Summary

This session ran the entire design-to-implementation review cycle for the meeting-ingest rebuild in a single day. Starting from seven planning docs and zero code, the project moved through: (1) a scope/design coherence review, (2) an artifact contract review, (3) an implementation plan review, (4) a full code review of the first working implementation, (5) a follow-up review verifying eight fix commits, and (6) an evaluation of the first two real transcript ingests (a Teams VTT and a Teams DOCX).

Each review's findings were addressed in commits before the next round, and the follow-up review confirmed all five prior high-priority code findings genuinely fixed with tests (suite grew 43 → 56 passing). The implementation now has: immutable meeting IDs decoupled from mutable slugs, a two-event snapshot ledger with failure/quarantine events, contract-compliant front matter pinned by a golden fixture, a validated v1 signal schema, duplicate/no-op repair, a provider registry behind a default-deny privacy gate, and injectable clock/ID hooks for deterministic tests.

The real-transcript test proved the pipeline plumbing works end-to-end on real files but exposed that extraction is not yet Teams-format-aware — the biggest gaps are speaker/timestamp parsing and content-based date inference.

## What Was Built/Changed

Session was review-only from the reviewer side; the maintainer landed these commits between rounds:

- `90c543c` — design scope docs (context primer, personal workflow scope, output evaluation, design proposal)
- `e5d5cba` — `docs/artifact-contract.md` (826 lines) + decision updates from contract review
- `cfdd0bd` — `docs/implementation-plan.md` (631 lines) incorporating plan-review feedback (pipeline.py orchestrator, identity.py, M1 error taxonomy, coordination rules)
- Scaffold through `57858fb` — full v1 Python implementation (21 modules, 43 tests)
- `7f003d6`..`e9bed88` — eight fix commits addressing all five code-review highs (56 tests)

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| `meeting_id` immutable, content/date-derived (`mtg-YYYYMMDD-<shorthash>`), separate from title/slug/filename | Rename repair must not break ledger/signals/cross-references (D12) |
| Ledger records are full snapshots with explicit event vocabulary; last-valid-wins per source hash | Prevents multi-mode artifact erasure under delta records (D17) |
| Signal files keyed by `meeting_id`, never slug | Slug is mutable; rename would orphan signal files |
| Duplicate/no-op is success-class (exit 0) and may repair incomplete archive/reconcile state | Prevents inbox residue becoming permanent debt (D22) |
| V1 identity = deterministic display-name slugification, no roster storage | Contract requires person IDs; full roster deferred (D20) |
| CLI is a thin adapter over `pipeline.py` library API | Harness wrappers call the same orchestrator (D21) |
| V1 signal taxonomy limited to 5 factual types; `communication_guidance` lives in playbook derivation | Anti-profiling boundary + extraction quality (D18) |
| Title inference and minimal signals pulled into slice 1 | Filename pain was the #1 documented product problem; provider contract returns title anyway |

## Discoveries

- **Discovery:** Recording `ingest_failed`/`source_quarantined` ledger events made failed sources permanently un-ingestable — duplicate detection treats any ledger record as "already ingested," and the no-op repair path then archives the never-ingested source and moves it to `_done` with meeting_id `"None"`.
  - **Impact:** Must be fixed before Milestone 6; duplicate detection needs to be event-aware. Regression introduced by an otherwise-correct fix — argues for retry-path tests alongside every failure-path feature.
- **Discovery:** The signal flow is not provider-ready: providers cannot construct valid `SignalRecord`s (they lack `ingest_run_id`/`recorded_at`), the pipeline silently drops non-`SignalRecord` items, and a `SignalRecord`-bearing response would crash the renderer (`.type` vs `.signal_type`) due to render-before-enrichment ordering.
  - **Impact:** Signal enrichment must move into the pipeline (mint signal IDs, stamp identity/timestamps, render after) before the real provider adapter.
- **Discovery:** Real Teams DOCX transcripts use `Name (M:SS):` speaker prefixes — naive colon-splitting minted 90 attendees for a 9-person meeting, plus a phantom attendee from the header date line.
  - **Impact:** Extraction needs structured speaker-turn parsing (speaker, timestamp, text) for both DOCX and VTT before any real-provider work.
- **Discovery:** The Spelman meeting's true date (July 1) was present twice in file content, but date inference only checks filename then mtime — the artifact was minted with the wrong date (July 3) and discloses no confidence.
  - **Impact:** Content-based date extraction should outrank mtime; front matter should emit `date_confidence`/`date_source`. Mint-once rule means the wrong-date ID is permanent for that test artifact.
- **Discovery:** Teams DOCX soft line breaks (`<w:br/>`) are dropped by the extractor, gluing words together ("ground.from ground zero"); VTT cue timestamps are stripped entirely, and consecutive same-speaker cues render as fragment spam.
  - **Impact:** Extraction realism slice: `<w:br/>` handling, cue-timestamp retention, same-speaker merge, header/footer metadata mining.
- **Discovery:** `reconcile_repaired` ledger event exists in code but not in the contract's event vocabulary — code got ahead of the doc despite the post-freeze doc-first rule.
  - **Impact:** Contract + design-proposal need a sync pass; process signal to watch during sub-agent implementation.

## Assumptions Validated/Invalidated

- Brief has no populated assumptions registry yet (stub). Working-assumption outcomes:
  - "Deterministic parts of the current engine are worth preserving": **validated** — the done-process model held up through implementation.
  - "Consistency comes from stable schemas and renderers, not model-invented shapes": **validated** — golden fixture + deterministic renderer worked on real files.
  - Implicit assumption that idealized fixtures represent real Teams exports: **invalidated** — real VTT/DOCX formats differ materially (voice tags, timestamp prefixes, header chrome, soft breaks).

## Problems & Solutions

| Problem | Resolution |
|---------|------------|
| Semantic meeting IDs would break on rename repair | Redesigned to immutable `mtg-` IDs before contract freeze |
| Interrupted ingest left lying ledger + missing archive | `repair_duplicate_source` + `reconcile_repaired` snapshot (verified fixed) |
| Front matter missing contract fields | Fixed; golden fixture now pins full artifact |
| Signal JSONL wrote table-summary shape | Fixed at schema level; flow rework still pending |
| Failed sources permanently blocked from retry | **Open** — top item for next session |
| Teams-format extraction gaps | **Open** — extraction realism slice defined |

## Open Questions

1. Retry semantics: which events count as "already ingested" — and should quarantined files be auto-restored on retry?
2. Signal enrichment design: what exactly do providers return for signals vs. what the pipeline mints?
3. `reconcile_repaired` doc sync (contract + design proposal event lists).
4. Should no-op skip appending a snapshot when nothing was actually repaired?
5. Date-correction disclosure: adopt `date_confidence`/`date_source` front matter fields?
6. Existing Hearst/Spelman corpora: migrate, adopt read-only, or ignore for v1? (Still undecided; shapes doctor/ledger.)

## Retrieval Quality

| Context Need | Method | Max Similarity | Fallback Reason |
|-------------|--------|---------------|-----------------|
| project_status | semantic | 0.706 | — |
| last_session | file_fallback | — | no recent results |
| discoveries | file_fallback | 0.396 | max_sim=0.396, threshold=0.4 |
| practices | sql | — | — |

**Fallback rate:** 2/4 needs fell back (expected — first tracked session; no prior sessions or discoveries existed)
**Query tuning:** None
**Corpus changes:** Initial bootstrap embedded 12 files / 64 chunks at project init

## Tracked Files Changed

- None uncommitted at wrap. During the session (committed by maintainer): README.md, DECISIONS.md, CURRENT-QUESTIONS.md, docs/context-primer.md, docs/design-proposal.md, docs/personal-workflow-scope.md, docs/current-output-evaluation.md, plus new docs/artifact-contract.md and docs/implementation-plan.md.

## Next Steps

1. Recovery-correctness slice: event-aware duplicate detection + retry-after-failure/quarantine tests.
2. Signal flow rework: provider-level signal shape, pipeline enrichment + signal_id minting, render after enrichment, non-empty-signal E2E test.
3. Doc sync: add `reconcile_repaired` to contract/design-proposal event lists; no-op repair clause update.
4. Extraction realism: Teams speaker-turn parsing (DOCX + VTT), content-based date inference + confidence fields, `<w:br/>` handling, header metadata mining, same-speaker merge. Use the two sanitized real transcripts as fixtures.
5. Then Milestone 6: first real provider adapter behind the existing privacy gate (synthetic fixture first).

## Continuation Prompt

> Continue the meeting-ingest v1 build in the meeting-ingest project.
>
> **Last session recap:** Full review cycle from design docs through v1 implementation; all five original code-review highs fixed and verified (56 tests green); first real Teams VTT/DOCX ingests succeeded end-to-end but exposed extraction gaps.
> **Priority:** Fix the retry-after-failure regression (failed/quarantined sources are permanently un-ingestable and the no-op path mishandles them) — it is a data-integrity bug and blocks Milestone 6.
> **Key context:** Duplicate detection must become event-aware (only `primary_artifacts_ready`/`ingest_completed`/`reconcile_repaired` count as ingested). Signal flow needs pipeline-side enrichment before the real provider. Extraction needs Teams-format speaker-turn parsing and content-based date inference — sanitized real fixtures exist from today's test at /tmp/meeting-ingest-realtest2.q3lsBs. `reconcile_repaired` needs adding to the contract's event vocabulary.
> **Brief:** Read `docs/artifact-contract.md` (canonical) and `docs/implementation-plan.md` for full context.
