# Owner Addendum: Power-User Corpus Evidence

Added: 2026-07-20, after the five independent seat reports and chairman synthesis were complete.

## Why This Is An Addendum

The independent board reviewed a frozen shared brief and must remain historically honest. This evidence was supplied by the product owner afterward, so it does not retroactively change what the seats saw or claim that they considered it.

It does change the operational level set and proposed next milestone.

## Owner Correction

Meeting Ingest currently has one true power user: the maintainer. The product is used in the HTV IQ Data Analytics project for Hearst, a client engagement. That project contains a substantially deeper transcript, artifact, signal, processed-source, and ledger history than the six-meeting corpus inside the Meeting Ingest repository.

The Spelman project also contains historical Meeting Ingest outputs and previously exposed a real occurrence-date failure. Its history has not been brought through the current engine or used to prove current behavior.

The owner characterized this as a development failure. The chairman's interpretation is more specific: the missing discipline was closing the product-validation loop around the actual power user's accumulated history. The product was dogfooded transactionally, but the historical corpus was not reconciled back into product truth, migration/adoption decisions, health behavior, or Stakeholder Briefing proof.

## Prior Repository Evidence

- `docs/current-output-evaluation.md:5-13` identifies the Hearst meetings directory as the primary reviewed corpus because it represented sustained real use, with Spelman as the secondary sanity-check corpus.
- `docs/current-output-evaluation.md:259` previously recorded 81 processed copies, 81 ledger entries, and 80 `_inbox/_done` files in Hearst, plus unresolved directory hygiene.
- `CURRENT-QUESTIONS.md:148-158` explicitly asks whether existing Hearst/Spelman outputs should be adopted, migrated, normalized, or left historical.
- `docs/implementation-plan.md:960-987` already defines a dry-run-first corpus-adoption layer with read-only scan, deterministic classification, and no claim that legacy artifacts are V1-generated unless they pass current contracts.
- `docs/sessions/2026-07-03-design-reviews.md:48` records that the Spelman meeting contained its true date in content but was minted with the wrong date under the legacy inference path.
- iQ Context capture `cap_20260718T220148Z_a28fa2b4` records the first current-engine external UAT in HTV and its response-contract, date, stale-handoff, and slug findings.

## Read-Only Live Evidence

No client transcript content was copied into this review. Only filesystem counts, configuration posture, and current engine status were inspected.

### HTV IQ Data Analytics

Path: `/Users/kmgdev/dev_projects/hearst-client/HTV-IQ-DataAnalytics/_local/project-context/meetings`

Filesystem inventory on 2026-07-20:

- 190 top-level meeting Markdown files;
- 173 physical source-ledger lines;
- 118 signal JSONL files;
- 118 processed-source files;
- 138 `_inbox/_done` files;
- zero direct inbox files;
- two cached provider requests and three cached provider responses.

Current engine `status --json`:

- 38 recognized sources;
- 92 valid ledger records;
- signal contract invalid with 81 legacy signal issues;
- two stale session handoffs;
- 31 identity candidates but zero reviewed people;
- no current Stakeholder Briefing generation.

The project is configured for the intended personal workflow: session provider, balanced quality, remote provider disabled, session provider enabled.

### Spelman

Path: `/Users/kmgdev/dev_projects/spelman/_local/project-context/meetings`

Filesystem inventory on 2026-07-20:

- two top-level meeting Markdown files;
- one ledger line;
- one signal file;
- one processed source;
- one `_inbox/_done` source;
- no active handoff files.

The current engine reports `config_not_found`; Spelman is historical output, not an initialized current-engine consumer.

## Revised Product Judgment

The six-meeting repository corpus should no longer be described as the full dogfood corpus. It is the small current-engine reference corpus.

The deeper HTV history is both:

- the strongest available evidence of sustained power-user value; and
- the clearest evidence that the product has not yet reconciled legacy history, current contracts, health, identity, and downstream briefing value.

This does not weaken the board's Just Works conclusion. It broadens it: just works must mean not only that the next meeting processes successfully, but that the product can safely understand and serve the power user's accumulated meeting history.

## Revision To The Next Milestone

**Just Works Ingest** should include a read-only **Power-User Corpus Reckoning** lane.

Required outcomes:

1. Deterministic read-only inventory of HTV and Spelman artifacts, ledgers, signals, archives, inbox/done state, handoffs, dates, and identities.
2. Classification of every relevant historical item as:
   - current-contract valid;
   - adoptable without mutation;
   - adoptable after controlled repair;
   - legacy-compatible only;
   - conflicting or ambiguous;
   - intentionally ignored.
3. Reconciliation between physical ledger lines, current valid records, source/artifact counts, and duplicate or split legacy representations.
4. A privacy-safe report that records counts, categories, gaps, and proposed actions without copying client transcript content into Meeting Ingest documentation.
5. A dry-run adoption plan with no in-place mutation, ledger append, artifact rewrite, or date repair until separately reviewed and approved.
6. A representative historical validation sample spanning recurring standups, one-on-ones, technical reviews, and the Spelman date case.
7. A decision on whether the current Stakeholder Briefing can consume qualified legacy history, requires controlled adoption, or must remain current-engine-only.
8. A demonstration that the product produces useful continuity for its actual power user, not only correct artifacts for newly ingested meetings.

## Scope Boundary

This addendum does not authorize:

- modifying the HTV or Spelman corpora;
- backfilling or rewriting ledgers;
- repairing dates;
- deleting stale handoffs;
- normalizing legacy signals;
- generating or publishing client-derived content;
- changing the canonical roadmap without owner approval.

The next step is evidence and a dry-run adoption decision, not migration.

## Additional Human Decision

Approve one of these corpus postures before any mutation:

1. adopt qualifying history into current contracts through controlled, append-only records;
2. maintain a read-only legacy adoption map alongside current-engine history;
3. preserve legacy corpora as historical reference and start current truth from a defined cutoff;
4. use a hybrid policy by artifact class and confidence.

The chairman recommends the hybrid policy be evaluated from the read-only report rather than selected in advance.
