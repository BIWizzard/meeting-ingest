# Product Status

## Purpose

This document is the current product-level status for `meeting-ingest`.

Use it before writing product briefs, planning roadmap work, or deciding what to implement next. It reconciles the roadmap against the current code, tests, contracts, commit history, and session notes.

## Current Product Summary

`meeting-ingest` turns each meeting into a trustworthy project record and keeps accumulated meeting history usable and explainable through one approved agent workflow.

It can turn `.txt`, `.vtt`, and `.docx` meeting artifacts into durable project knowledge with:

- structured markdown meeting artifacts
- signal JSONL output
- source-ledger idempotency
- processed-source archive
- inbox reconciliation after successful ingest
- provider-backed structured extraction
- session-provider handoffs for active agent hosts
- doctor/status visibility into incomplete or pending state
- approved-runtime readiness gating before writes
- persisted runtime provenance across artifacts, ledgers, and signals
- deterministic transcript grounding enforced before any durable write
- versioned semantic extraction guidance bound into requests and persisted provenance

The current reference user is the maintainer, the reference host is Claude Code, the reference consumer is the formalized site where activation evidence is collected, and the release posture is maintainer-only private alpha. The engine remains host-neutral by design, but other host experiences are not current release claims. It is not yet a general self-serve product.

## Approved North Star Milestone

The next milestone is **Just Works Continuity**:

> Know which approved logic will run, process the next meeting through one normal Claude Code request, and keep accumulated history usable and explainable without silent mutation.

The ordered milestone tracks and their status are:

1. Approved Runtime and Pre-Meeting Readiness — demonstrated complete 2026-07-24.
2. Read-Only Power-User Corpus Reckoning — read-only reckoning complete; adoption approval-gated.
3. Fresh Claude Code Meeting Proof and Recovery — fresh-host proof demonstrated 2026-07-24; the Semantic Integrity Guardrails quality gate inside this track (`docs/plans/2026-07-20-semantic-integrity-guardrails.md`) is implemented, with release-evidence acceptance recorded on the frozen 0.2.0 build and its claim scoped to exclude rule 6.
4. Approval-Gated Historical Qualification and Continuity Proof — not started; approval-gated.

The read-only legacy corpora A/B reckoning is complete. Corpus adoption remains separately approval-gated.

The Semantic Integrity Guardrails slice is implemented, and its claim is limited to guarded fresh-ingest output:

- every provider path binds the transcript grounding index into the request and re-checks it before any durable write: attendee raw labels must copy a normalized transcript speaker label verbatim, and signal evidence speakers and non-null timestamps must copy grounding-index entries verbatim;
- tampered persisted request grounding is rejected, and the observed fabricated-affiliation pattern — adding a parenthetical qualifier to a speaker label — cannot pass the gate in an attendee raw label or a signal evidence locator; provider-generated `display_name` and `role_context` remain semantic responsibilities rather than deterministically gated fields;
- semantic judgment is a versioned prompt contract, `semantic_guidance_version` `1.1`, carried in the request alongside the grounding index, with the four maintained provider instruction surfaces aligned to it; `1.1` shipped in build `meeting-ingest-0.2.0-g3695fc350c77-s61e1660c5dc8`, and it carries release-evidence acceptance on that frozen build, scoped to exclude rule 6; both pinned consumers have since moved to build `meeting-ingest-0.3.0-gbcfe8e532721-s30753a330500`, which carries guidance `1.1` unchanged;
- deterministic behavior is proven by the repository suite, including mutation-killing tests for the direct-provider and phase-2 grounding gates; semantic behavior is measured by the synthetic five-pattern acceptance case in `tests/fixtures/semantic-integrity/` under the procedure in `docs/testing/semantic-integrity-acceptance.md`.

Guidance 1.0's acceptance history stands as recorded. The run on 2026-07-26 passed all 18 blocking assertions with concordant human semantic review and independent blind review, and its one advisory failure was dispositioned as a fixture pattern gap rather than an extraction defect; it ran on an editable checkout under `--development-override`, so it is development/non-release evidence. The slice was released as build `g51ff17173bea` (receipt cut from commit `51ff171`, installed and pinned per the release flow), and two release-evidence acceptance attempts on that frozen build then failed semantic assertions with a consistent `semantic_guidance` 1.0 wording gap; both failures are recorded as a contract finding, while the deterministic gates passed on the frozen build in both attempts. See `docs/sessions/2026-07-26-task7-semantic-acceptance-dev-run.md` and `docs/sessions/2026-07-26-task7-release-and-acceptance.md`.

Guidance 1.1 answers that finding and is released. Its acceptance run on 2026-07-29 passed 18/18 blocking assertions and 1/1 advisory with both required reviews concordant, closing both 1.0 failures and recording four framing-restraint quality findings; it also ran on an editable checkout under `--development-override` and is development/non-release evidence. See `docs/sessions/2026-07-29-guidance-1_1-semantic-acceptance-dev-run.md`. The slice was released as build `meeting-ingest-0.2.0-g3695fc350c77-s61e1660c5dc8` (receipt cut from commit `3695fc3`, published, installed, and pinned per the release flow), and the reference consumer ran pinned to it through the acceptance period. Both consumers — the reference consumer and the secondary consumer (onboarded 2026-08-13) — are now pinned to `meeting-ingest-0.3.0-gbcfe8e532721-s30753a330500` (receipt cut from commit `bcfe8e5`), which carries guidance `1.1` unchanged, fixes the stale `generated_by` stamp reported by the first three dogfood relays (shipped in 0.2.1), and makes `meeting-ingest init` a true one-command consumer bootstrap. See `docs/sessions/2026-08-30-one-command-init-release.md`. See `docs/sessions/2026-07-29-guidance-1_1-release.md`.

Release-evidence acceptance on the frozen 0.2.0 build was performed on 2026-07-29 and passed 18/18 blocking and 1/1 advisory under clean approved-runtime conditions — readiness `ready` with zero findings, no development override, no interventions — with the host-loaded agent definition verified against the receipt-installed copy before the run and the full workflow chain verified at 8/8 pin and 8/8 receipt comparisons. Both required reviews are concordant. It is **accepted as milestone proof with a scoped claim**:

- rules 4 and 5 are confirmed against the failures they were written for: S5, S6 and S10 passed on the frozen build, and S10 and S6 are the assertions that sank both 1.0 release-evidence runs;
- rule 6 is **falsified rather than merely unproven**. It shipped accepted as unproven with no fixture detection behind it, and this run widened a committed action item beyond the scope its owner accepted. The claim excludes rule 6. Fixture detection has since been written against that failing case — assertions S14 and S15 in `tests/fixtures/semantic-integrity/expected-review.json` (`bb7591d`), executed by the in-repo acceptance evaluator (`c5d646c`) — but rule 6 remains unproven until an acceptance run on a frozen build carrying them.

The assertion floor was measured on an evaluator verified twice before its tally was accepted — synthetic self-test in both directions for all eight executable operators, plus seven targeted mutations of the run's own payload, each detected. See `docs/sessions/2026-07-29-guidance-1_1-release-evidence-acceptance.md`.

The guardrails govern newly ingested output only. They are not a claim of general semantic correctness, and no existing artifact is adopted, corrected, or mutated by this work. The Just Works Continuity milestone also requires Track 4 and is not met.

The Approved Runtime policy is implemented and demonstrated as of 2026-07-24:

- each consumer pins one exact immutable build tied to a reviewed commit and packaged build;
- a stable channel may announce updates but never silently changes the selected build;
- updates and replacement-build approval are explicit;
- approved Claude Code client work blocks editable builds by default;
- a deliberate maintainer override is available for testing and must remain unmistakable in readiness and generated provenance.

The reference consumer now runs an approved frozen wheel under a runtime pin, and one fresh non-synthetic transcript was processed end to end through one normal Claude Code request. Track 1 completion demonstrates approved-runtime readiness and persisted provenance only; it does not claim semantic guardrails or qualified history. The 177 legacy findings remain classified history warnings awaiting the separately approval-gated qualification track.

See `docs/north-star-board/002-just-works-continuity/`, `docs/sessions/2026-07-24-task9-reference-consumer-cutover.md`, and `docs/sessions/2026-07-24-task10-fresh-host-proof.md`.

## Current Development State

Committed implementation is stable through the session-inbox, handoff-health, semantic-integrity guardrails, and one-command init work. The Stakeholder Playbook effort has moved past design-and-contract: Layer 5A generalized provenance and reviewed identity and the Layer 5B Stakeholder Briefing V1 foundation are implemented and published. Layer 5C Playbook Guidance V1.1 remains a design-and-contract workstream. "Shipped" is reserved for the defined sense — running at the reference consumer — and is accounted for under Activation Accounting, not asserted here.

Current accounting:

- Stakeholder Briefing V1 and Playbook Guidance V1.1 have an accepted durable design baseline in `docs/stakeholder-playbook-design.md`.
- `DECISIONS.md` records the accepted identity, provenance, storage, derivation, review, privacy, and milestone boundaries.
- schema 1.1 and Stakeholder Briefing V1 artifact-contract amendments passed focused review, and their implementation is published.
- Layer 2 output-mode, title-repair, and regeneration contracts are written, but their implementation has not started.
- schema 1.1 signal identity, the reviewed identity registry, deterministic stakeholder profiles, and deterministic Stakeholder Briefing derivation are implemented and published; no Playbook Guidance V1.1, email, screenshot, or social-source code is implemented.
- the current filesystem/JSONL/Markdown architecture remains sufficient for the planned V1 work; no backend or embeddings are planned.

## Activation Accounting

Shipped means running at the reference consumer (North Star board record 003, P2). A capability is therefore tracked on two axes:

- `implemented` — the code is committed, tested, and carried in a published build.
- `active-at-reference-consumer` — that capability is observably running at the reference consumer.

Every feature ships active to the reference consumer unless it is explicitly scoped away from it. A capability can be `implemented` and not active; that gap is the point of this section, not a defect in it.

**As of.** This accounting is as of `main` on 2026-08-30, with `meeting-ingest-0.4.0-g65e509019e43-s18795c80069c` (commit `65e5090`) as the published build, released and consumed through the release/update command pair. Work committed past a published build is marked `implemented (unpublished)`: it satisfies "committed and tested" but is not yet carried in a published build, so it cannot be active anywhere.

**Derivation rule.** Activation claims in this section come from tool output. `meeting-ingest status --json` and `meeting-ingest readiness` already know the pin, the registry, and the derivation state, so every `active-at-reference-consumer` cell names the command and field it derives from and carries no value that is not backed by the snapshot below. Hand-edited activation prose is a defect: a release run refreshes this section by replacing the snapshot block with fresh command output, not by editing the table's wording. Where no captured field value stands behind a claim, the cell reads `not yet evidenced` — which is a statement about the evidence, not a claim that the capability is idle.

The next refresh reads a different tool than this snapshot did. From the next published build onward, readiness fields are captured with `meeting-ingest readiness --verdict-only --json` (the reduced view shipped in the 0.4.0 build), and the verdict vocabulary includes `core_inactive` — so a reference consumer with an implemented but unrun core capability reports `core_inactive` rather than a clean verdict.

Activation evidence is metadata only — verdicts, counts, build ids, statuses. It never carries corpus content: no meeting titles, person names, client names, or artifact excerpts.

### Evidence Snapshot

Captured: 2026-08-30, at the 0.4.0 release run — the first snapshot pasted directly from command output at the reference consumer, replacing the interim transcription. It is replaced wholesale at each release run.

```
site:    the reference consumer
command: meeting-ingest readiness --verdict-only --json

  verdict                            core_inactive
  running_build                      meeting-ingest-0.4.0-g65e509019e43-s18795c80069c
  approved_build                     meeting-ingest-0.4.0-g65e509019e43-s18795c80069c
  match                              true
  finding_counts.by_category         core_inactive 1, history 176
  finding_counts.by_severity         warning 177
  next_action                        Run `meeting-ingest playbook update` to regenerate
                                     the playbook from the current corpus; the current
                                     output does not reflect it.

command: meeting-ingest status --json

  project.ledger_records                         159
  project.known_sources                          71
  project.inbox_files                            0
  project.session_handoffs.total                 0
  project.identity_registry.status               valid
  project.identity_registry.people               17
  project.identity_registry.identity_candidates  5
  project.identity_registry.issues               0
  project.signal_contract.status                 invalid (legacy pre-1.1 formats in the
                                                 unadopted corpus; classified as history
                                                 warnings by readiness)
  project.playbook.status                        stale
  project.playbook.latest_attempt_status         success
  project.playbook.profile_count                 16
  project.playbook.unresolved_identity_count     5
  project.playbook.rejected_or_suppressed_count  0
  project.playbook.guidance_status               not_available_in_briefing_v1
```

The `core_inactive` verdict is the readiness legibility ruling working as ratified: the playbook derivation exists (latest attempt succeeded, 16 profiles) but is stale against the current corpus, and the verdict names the activating command instead of hiding it among history warnings. The 176 history findings belong to the separately approval-gated qualification track and are judged independently of activation.

### Capability Accounting

| Capability | Implemented | Active at the reference consumer | Derived from |
|---|---|---|---|
| Approved-runtime pin and readiness gate | yes | active | `readiness --verdict-only`: `verdict`, `running_build`, `approved_build`, `match` |
| Meeting ingest to durable artifacts, signals, and ledger | yes | active (159 ledger records, 71 known sources) | `status --json`: `project.ledger_records`, `project.known_sources` |
| Session-provider handoff ingest | yes | not yet evidenced (no handoffs outstanding at capture; completed handoffs leave no counter) | `status --json`: `project.session_handoffs` |
| Schema 1.1 signal identity and generalized provenance | yes | not yet evidenced (`signal_contract.status` reports corpus-wide `invalid` from legacy pre-1.1 files; no field isolates new-write conformance) | `status --json`: `project.signal_contract.status` |
| Reviewed identity registry and derivation-time resolution | yes | active (status `valid`, 17 reviewed entries, 5 candidates, 0 issues) | `status --json`: `project.identity_registry.people`, `.issues`, `.identity_candidates` |
| Stakeholder Briefing V1 derivation (`playbook update`) | yes | active, stale at capture (latest attempt `success`, 16 profiles; verdict `core_inactive` names the refresh) | `status --json`: `project.playbook.status`, `.profile_count`, `.unresolved_identity_count` |
| Playbook review overlays (reject/restore/resolve/suppress) | yes | not yet evidenced | `status --json`: `project.playbook.rejected_or_suppressed_count` |
| Release/update command pair (`scripts/release-approved-runtime.py`, `meeting-ingest update`) | yes | active (the 0.4.0 release and both consumer moves ran through them) | Layer 5D interim relief; 0.4.0 release evidence |
| Readiness `core_inactive` category and verdict | yes | active (the snapshot verdict above is `core_inactive`) | `readiness --verdict-only`: `verdict`, `finding_counts.by_category` |
| Output modes `summary`/`verbatim`, title repair, regeneration | no | not applicable | Layer 2, not implemented |
| Playbook Guidance V1.1 semantic synthesis | no | not applicable | `status --json`: `project.playbook.guidance_status` reports `not_available_in_briefing_v1` |
| Email, screenshot, and social-source ingest | no | not applicable | Layer 7, not started |

## Available User Workflows

### Single-File Ingest

Use when one transcript source should become a durable meeting artifact.

Available behavior:

- read source
- normalize transcript
- call selected provider
- validate structured provider output
- render markdown
- write signal JSONL
- append ledger snapshots
- archive processed source
- reconcile inbox source to `_inbox/_done/`
- return JSON run summary

### Sequential Inbox Ingest

Use when direct files under `_inbox/` should be processed one at a time.

Available behavior:

- processes direct inbox files
- skips `_inbox/_done/`
- continues after recoverable per-file failures
- quarantines unsupported inbox sources
- reports per-file success/failure/no-op results

### Session-Backed Active Agent Ingest

Use when the user is already operating inside Codex, Claude Code, Supa Code, or T3 Code and wants subscription-backed model judgment instead of a separate API call.

Available behavior:

- `provider-request` creates a transcript-bearing request
- active agent or sub-agent writes provider response JSON
- `ingest --provider session --provider-response ...` completes validation, rendering, ledger, archive, and reconcile
- `ingest-inbox --provider session` creates batch phase-1 handoffs
- `session-inbox` scans existing handoffs, completes ready responses, avoids reminting duplicate requests after interruption, and reports pending/stale/invalid states

### Pre-Ingest Correction After A Failed Validation

Use when deterministic validation rejects a provider response, before any durable primary output exists.

Available behavior:

- `validate-response` reports every shape and grounding issue in the parsed provider output as one list, and writes nothing
- a failing preflight or phase 2 retains the persisted request and the provider response
- grounding failures report the exact speaker labels and timestamps the transcript supports
- the correction is a rewrite of the provider response only; the persisted request is reused unchanged
- the retry is the same two steps: re-run `validate-response`, then re-run phase 2
- a phase-2 provider or validation failure appends an `ingest_failed` snapshot and produces no markdown, signals, archive, or reconcile state

Boundaries:

- failed grounding never writes or partially replaces durable primary output, so there is no partial-write repair to perform; the failure snapshot is the only durable record it writes
- a `runtime_handoff_mismatch` deliberately writes no failure snapshot, so the handoff stays recoverable under its bound runtime
- payload-decoding failures report before shape and grounding validation, so a badly typed response surfaces grounding issues only on the next attempt
- editing the persisted request is not a correction path; a genuinely stale request requires a fresh phase 1
- a semantic defect discovered after a successful ingest has no available correction path today; see Layer 2 in Roadmap Accounting
- open questions recorded against this loop are 17 (self-authenticating persisted transcript) and 19 (payload-decoding aggregation) in `CURRENT-QUESTIONS.md`

### Project Hygiene And Recovery

Use when the user wants to know if the meetings root is healthy.

Available behavior:

- `status --json` reports project counts and session handoff state
- `doctor --json` reports hygiene issues
- `reconcile --json` repairs duplicate inbox residue when primary artifacts already exist
- duplicate/no-op ingest can repair incomplete archive/reconcile state

## Built Capabilities

### Engine And CLI

Complete:

- Python package and CLI scaffold
- project-local init and path discovery
- config loading and defaults
- content hashing
- deterministic meeting and ingest run IDs
- project lock handling
- typed error taxonomy and exit codes
- JSON run summaries

### Source Extraction

Complete:

- `.txt` extraction
- `.vtt` extraction
- `.docx` extraction
- Teams transcript cleanup improvements
- cleaned-verbatim transcript normalization
- unsupported inbox source quarantine

Known limitation:

- occurrence candidate selection is deterministic, with precedence `override` > `content` > `filename` > `file_mtime`
- operators can supply a known occurrence date with `--meeting-date` before ingest or use `repair-date` for an already-ingested artifact
- file modification time remains the low-confidence fallback when no stronger candidate exists; run summaries warn that it may be acquisition time, and `doctor` reports the advisory condition

### Artifact Generation

Complete:

- `summary-plus-verbatim` markdown renderer
- required stable markdown sections
- front matter with provenance
- transcript-final output
- signal table mirroring
- filename collision handling
- low-confidence title/filename metadata
- rename suggestion in run summary when fallback naming is used

Not complete:

- `summary` mode implementation
- `verbatim` mode implementation
- title repair command
- artifact regenerate command

### Signals And Ledger

Complete:

- provider communication signal parsing
- signal JSONL output
- signal enrichment with meeting/run identity
- append-only ledger snapshots
- full current-state ledger reads
- primary artifact ready snapshots
- ingest completed snapshots
- ingest failed snapshots
- reconcile repaired snapshots
- generalized schema 1.1 signal writing, deterministic signal identity, and signal-set fingerprints
- reviewed stakeholder identity registry and derivation-time resolution
- deterministic Stakeholder Briefing aggregation
- playbook derivation ledger, review overlays, profiles, briefings, status, and doctor behavior

Not complete:

- prior signal-set fingerprint recording and explicit supersession details, which land with the Layer 2 `regenerate` command
- mechanical contradiction candidates from structured mutually exclusive source values
- Playbook Guidance V1.1 synthesis, review state for inferred guidance, and dedicated synthesis privacy gates

### Archive, Reconcile, And Idempotency

Complete:

- processed-source archive copy
- inbox reconcile only after success
- duplicate/no-op by content hash
- duplicate inbox residue repair
- no-op summaries with existing artifact details
- incomplete archive/reconcile repair
- `reconcile --json` repaired/skipped reporting

### Providers

Complete:

- mock provider
- Anthropic adapter behind `allow_remote_provider`
- session provider handoff behind `allow_session_provider`
- shared provider response parsing
- provider validation failure path
- provider failure path
- provider metadata in artifacts and ledger
- provider host provenance for session-backed runs
- transcript grounding index bound into direct and session provider requests
- grounding enforcement before signals, markdown, ledger success snapshots, archive, reconcile, and cache cleanup
- versioned semantic guidance (`1.1`) carried in requests and persisted through response binding, run summaries, artifacts, and ledger provenance

Not complete:

- OpenAI adapter
- Gemini adapter
- production-quality host adapters for every target harness
- finalized prompt strategy for fast/balanced/deep quality variants

### Session Provider And Inbox Automation

Complete:

- two-phase session handoff contract
- persisted request verification
- request-side identity adoption
- response/source hash verification
- success cleanup for request/response files
- stale provider cache doctor checks
- `ingest-inbox --provider session` batch phase 1
- `session-inbox` wrapper surface
- resume-safe pending handoff scanner
- non-failing `stale_handoff` classification
- `status --json` session handoff counts/results
- `doctor --json` pending/stale/invalid handoff issues
- Codex and Claude skill sync from repo sources
- AGENTS.md workflow sync

Not complete:

- fully automated host-specific extractor adapters
- user-facing stale handoff cleanup/repair command

## Roadmap Accounting

### Layer 1: V1 Completion Polish

Status: mostly complete.

Done:

- title/filename confidence metadata
- rename suggestions for low-confidence fallback titles
- successful run summaries with primary artifacts, signals, archive, reconcile, provider, quality, and mode
- richer no-op/reconcile summaries
- doctor/status JSON contracts
- doctor checks for inbox residue, malformed ledger lines, missing artifacts, missing signals, missing processed copies, incomplete reconcile, stale lock, stale provider cache, and session handoff state
- focused regression coverage for run summaries, filename fallback, doctor warnings, duplicate/no-op repair, provider failures, and archive/reconcile failures
- done-state documentation across artifact and provider contracts
- reliable occurrence candidate selection for transcripts downloaded after the meeting date
- occurrence, acquisition, and processing time distinction in the engine-facing contract
- manual meeting-date override for single-source `ingest` and `provider-request`
- controlled `repair-date` path for already-ingested artifacts
- prominent run-summary warnings when file modification time is used as the meeting occurrence fallback

Remaining:

- improve title/filename inference quality using more real transcript fixtures
- decide exact confidence policy for provider-suggested titles/slugs
- decide whether doctor should only report repair suggestions or also implement repairs

### Layer 2: Output Modes And Repair/Regenerate Workflows

Status: contract finalized; implementation not started beyond the current default mode.

Done:

- `summary-plus-verbatim` mode
- mode field in config/run summaries/artifacts
- `summary` and `verbatim` artifact section contracts
- `repair-title` command UX and `title_repaired` ledger semantics
- `regenerate` command UX and `artifact_regenerated` ledger semantics

Remaining:

- implement `summary` mode
- implement `verbatim` mode
- implement title repair
- implement artifact regeneration from `_processed/`
- support multiple mode artifacts for one source hash
- add renderer golden tests for all modes

Correction of already-ingested output: not available.

Semantic correction of ingested output requires the contracted regeneration path, because generated markdown, the signal JSONL set, and the ledger's current state are bound to each other by fingerprints, producer links, and recorded provenance. The mechanism is frozen in the `Regeneration Contract` and `Signal Regeneration And Supersession` sections of `docs/artifact-contract.md` and is not implemented; no second semantic-correction design exists.

Manual edits to generated markdown or signal JSONL are not a correction mechanism and are not an interim workaround. A hand-edited artifact still carries the ledger provenance, fingerprints, producer links, and bound `semantic_guidance_version` of the output it replaced.

Existing legacy corpora A and B artifacts remain read-only. Their reviewed defects remain dogfood evidence until a deterministic, fingerprinted adoption or correction plan receives separate owner approval under North Star board record 002, OB-002-1. Whether generated Markdown may be mutated at all is an open owner decision held by record 002 under "Other Later Decisions" and tracked as question 16 in `CURRENT-QUESTIONS.md`.

Approval-gated follow-on slice — implement `regenerate --provider session`:

This is the only contracted path to semantic correction of already-ingested output. It is a separate follow-on slice, not part of the current guardrails work, and it does not start until the owner approves both the generated-Markdown mutability policy and client-corpus correction. Approval of the slice is not approval to run it against any existing corpus; that remains separately gated under OB-002-1.

Its acceptance must cover the already-contracted behavior:

- atomic replacement of the selected mode's artifact and any refreshed signal file, with no timestamped public replacement and no stub or redirect
- a fresh phase-1 request bound to the new `ingest_run_id`, never a reused request/response pair, with phase 2 verifying it exactly as normal session ingest does
- the source-ledger signal block recording the current signal-set fingerprint and the `artifact_regenerated` event recording the prior one
- an append-only `artifact_regenerated` snapshot written after the regenerated markdown and any refreshed signal file are ready, preserving current ledger entries for all other modes
- downstream supersession behavior: signal identity retention, explicit supersession when identity cannot be retained, playbook rebuild reporting of review events referencing absent observations, and `doctor` reporting of suppressed content re-emerging under a new signal ID
- failure before the replacement artifact is ready leaves the current artifact as current state

### Layer 3: First-Class Session Inbox Automation

Status: engine/planner side mostly complete; host adapter productization remains.

Done:

- batch phase-1 handoff creation
- `session-inbox` wrapper
- active-agent callback API
- resume-safe existing request scan
- ready response completion before fresh phase 1
- pending handoff no-remint behavior
- stale/out-of-scope handoff classification
- `status`/`doctor` handoff visibility
- skill and AGENTS workflow sync

Remaining:

- productize host-specific extractor adapters
- decide long-term CLI surface between `session-inbox`, `ingest-inbox`, and host wrappers
- decide stop/continue behavior for host extraction failures
- add stale handoff cleanup/repair command if needed

### Layer 4: Provider And Wrapper Hardening

Status: provider boundary is solid; product wrapper hardening remains.

Done:

- mock, Anthropic, and session provider paths
- explicit privacy gates
- typed provider failure semantics
- shared provider response parsing
- provider provenance in artifacts/ledger
- session handoff validation and identity verification
- deterministic transcript grounding enforcement shared by direct and session provider paths
- one versioned semantic guidance source consumed by every provider request and the four maintained extraction instruction surfaces
- synthetic five-pattern semantic acceptance case with machine-readable assertions and a documented run procedure

Remaining:

- decide first production-grade remote provider posture
- productize first host wrapper
- improve prompt strategy by quality tier
- decide model provenance expectations for subscription-backed hosts
- add other provider adapters only when selected

### Layer 5: Stakeholder Briefing And Playbook Guidance

Status: Layer 5A foundation complete; Layer 5B foundation implemented with one remaining item; Layer 5C not started.

Done:

- per-meeting communication signal schema/output
- signal provenance to meeting/run IDs
- signal markdown mirroring
- independent design and arbitration passes
- accepted `docs/stakeholder-playbook-design.md` baseline
- decisions frozen for reviewed identity, deterministic full rebuilds, immutable generations, separate derivation history, review overlays, dedicated synthesis privacy gates, and the Briefing V1/Guidance V1.1 split
- reviewed schema 1.1 and deterministic Stakeholder Briefing artifact contracts

#### Layer 5A: Generalized Provenance And Identity Foundation

Implemented:

- annotated compatibility and adversarial fixtures
- schema 1.1 tolerant readers/writers
- generalized source and occurrence/acquisition/processing provenance
- deterministic locator/evidence-based signal identity, duplicate collapse, collision suffixing, and signal-set fingerprints
- reviewed project-local identity registry, derivation-time resolution, and identity candidates
- status visibility and doctor findings for registry conflicts and invalid schema 1.1 signal identity/locators

Remaining integration:

- record prior signal-set fingerprints and explicit supersession details when the Layer 2 `regenerate` command is implemented
- consume identity-candidate artifacts from immutable Layer 5B derivation generations

#### Layer 5B: Stakeholder Briefing V1

Implemented foundation:

- deterministic eligible-input discovery and fingerprinting across signals, reviewed identity, overrides, rules, schemas, and renderer version
- schema 1.0 source-ledger identity normalization plus schema 1.1 generalized source identity
- explicit `playbook update` full rebuild command
- immutable generation directories with identity candidates, canonical profile JSON, and deterministic briefing Markdown
- append-only successful derivation records followed by an atomic current index update
- exact-type/tag deterministic aggregation, recurrence promotion, freshness, and recent-change comparison
- append-only reject/restore, resolve, suppress/unsuppress review controls with rebuild-time overlay application
- failed derivation records that preserve the prior usable index
- live current/stale/missing/failed status plus derivation, profile, review, orphan, and uncommitted-generation doctor diagnostics
- explicit index repair and alias-aware `playbook show` and concise `playbook brief` readers
- evidence index with source artifact, evidence kind, excerpt, speaker, and locator detail
- validated project-configurable briefing thresholds with frozen effective ruleset fingerprints
- suppression re-emergence diagnostics and deterministic nearest-successor hints for orphaned entry reviews
- explicit safe cleanup for uncommitted generations plus corrupted-index and unsafe-ledger-path recovery fixtures

Remaining:

- add mechanical contradiction candidates when a source schema exposes structured mutually exclusive values; same-type or same-topic collisions remain non-contradictory

#### Layer 5C: Playbook Guidance V1.1

Remaining:

- freeze the structured derivation provider request/response contract and approach-tag vocabulary
- implement dedicated playbook-synthesis privacy gates
- implement semantic clustering, contextual scope, contradiction confirmation, positive-response patterns, communication cues, and caveats
- implement explicit review state for inferred guidance

### Layer 5D: Distribution Transition (Sunset Of The Manual Release Apparatus)

Status: interim relief published and exercised — the 0.4.0 release ran through both commands; the distribution transition itself is not started and board-gated by Decision 35 in `DECISIONS.md`.

The receipt/pin/explicit-update ceremony is trust-building scaffolding with a recorded sunset: when the Just Works Continuity milestone is met, three consecutive releases ship without a drift incident, and the owner decides to broaden beyond the maintainer-only alpha, a distribution-transition plan convenes the board to amend record 002. Target end state: auto-updating package-manager delivery with attestation verification running invisibly inside the updater, failing closed only on actual verification failure. None of the three exit criteria is met, and a broadening intent or a transition plan convenes the board under OB-003-6.

Interim relief (no contract change required) — implemented in `4a62db9` under OB-003-1 and issue #16, published in the 0.4.0 build and exercised by the 0.4.0 release run:

- `scripts/release-approved-runtime.py` collapses the maintainer release flow into a single command wrapping build, receipt, publish, install, and repin
- `meeting-ingest update` collapses a consumer move to the channel-latest approved runtime into a single verified command wrapping fetch, digest verification, install, repin, and readiness
- the README Release Flow leads with the two commands; the explicit steps remain documented as the flow they drive

### Layer 6: Migration And Existing Corpus Adoption

Status: not started.

Remaining:

- read-only corpus scan
- adoption report
- adoption ledger records
- migration docs and dry-run workflow

### Layer 7: Broader Communication Artifact Ingest

Status: not started.

#### Layer 7A: Plain-Text Communication Pilot

Remaining:

- email-body or pasted-message ingest
- sender/recipient/subject/thread/sent-time/acquisition provenance
- generalized observations that can rebuild the same stakeholder profiles as meeting evidence

#### Layer 7B: Image-Based Communication Ingest

Remaining:

- Teams and text-message screenshots
- OCR provenance and image-region evidence locators
- communication-event identity to prevent double-counting duplicate representations

#### Layer 7C: Public And Social Sources

Remaining:

- public/social acceptable-use and privacy policy
- social post and profile provenance, retention, and refresh semantics
- safeguards against personality, vulnerability, protected-trait, or persuasion profiling

### Layer 8: iQ Context Integration

Status: operational continuity exists; product integration not built.

Done:

- repo uses iQ Context for agent continuity
- durable state policy exists
- session notes and workstream state are maintained

Remaining:

- config-gated ingest-to-iQ capture behavior
- provenance links from captures to meeting artifacts
- doctor/status checks for capture sync state
- policy to avoid copying sensitive transcript content into project memory

## Next Product Work

The backlog of record is the GitHub issue tracker on this repository (`gh issue list --label backlog`). This document does not carry a parallel roadmap; the five-step sequence it previously listed here is superseded, and the layer accounting above is where implementation state lives. Four of its five steps are verified built. The exception is step 3 — updating the provider, prompt, and skill contracts when the new observation taxonomy becomes user-facing — which was conditional and is not discharged: `docs/artifact-contract.md` still states that the provider payload contract does not permit the three new playbook-facing types or the `interaction_response` extension, and that providers must not emit them until the handoff contract, payload validation, extraction prompts, and both skill copies are amended together.

Near-term work is gated by the standing obligations in `docs/north-star-board/board-log.md` rather than by a sequence recorded here. That obligations table is the live list; this document does not enumerate it, for the same reason activation claims are derived rather than hand-typed.

Layer 2 output modes remain independently shippable and contract-ready. They are a valid smaller implementation slice, but they are not the default priority after the stakeholder-playbook direction was accepted.

## Evidence

Recent implementation commits include:

- `af2a130 test: record dev-evidence semantic acceptance run and widen S11 pattern`
- `7e44a5d docs: define correction and recovery boundaries`
- `8a486e7 test: add semantic integrity acceptance case and align extraction surfaces`
- `9a4d015 test: kill grounding-gate mutations and cover stakeholder speaker mapping`
- `3f64f31 feat: enforce transcript grounding before side effects`
- `c2e297b feat: bind provider responses to transcript grounding`
- `4dd6698 feat: index transcript speakers and evidence timestamps`
- `049d3a0 feat: expose session handoff status`
- `3f07f59 feat: add session inbox wrapper`
- `a713b3d feat: plan session inbox handoffs`
- `5408126 feat: enrich no-op reconcile summaries`
- `5e6b15b Harden session provider handoff errors`
- `802d190 Add session provider handoff flow`
- `85319c5 Add Anthropic provider adapter`
- `c5e11ca Add sequential inbox batch ingest`

Latest recorded full-suite verification on `main`, at `65e5090` (the 0.4.0 release commit) on 2026-08-30:

- the repository suite passed with 569 tests (`65e5090`; 568 at `e2a6d9e`, 555 at `4a62db9`)

Full-suite verification at the published 0.3.0 release build, commit `bcfe8e5` on 2026-08-30:

- the repository suite passed with 494 tests (`docs/sessions/2026-08-30-one-command-init-release.md`)

Earlier verification recorded on 2026-07-26:

- `uv run pytest` passed with 459 tests
- `git diff --check` passed
- the semantic acceptance run recorded in `docs/sessions/2026-07-26-task7-semantic-acceptance-dev-run.md` passed 18/18 blocking assertions as development/non-release evidence

Current runtime and activation evidence is not restated here; it lives in the Evidence Snapshot under Activation Accounting and is refreshed from tool output at each release run.
