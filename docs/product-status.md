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

The current reference user is the maintainer, the reference host is Claude Code, and the release posture is maintainer-only private alpha. The engine remains host-neutral by design, but other host experiences are not current release claims. It is not yet a general self-serve product.

## Approved North Star Milestone

The next milestone is **Just Works Continuity**:

> Know which approved logic will run, process the next meeting through one normal Claude Code request, and keep accumulated history usable and explainable without silent mutation.

The ordered milestone tracks and their status are:

1. Approved Runtime and Pre-Meeting Readiness — demonstrated complete 2026-07-24.
2. Read-Only Power-User Corpus Reckoning — read-only reckoning complete; adoption approval-gated.
3. Fresh Claude Code Meeting Proof and Recovery — fresh-host proof demonstrated 2026-07-24; the Semantic Integrity Guardrails quality gate inside this track (`docs/plans/2026-07-20-semantic-integrity-guardrails.md`) is implemented, with acceptance so far recorded only as development evidence.
4. Approval-Gated Historical Qualification and Continuity Proof — not started; approval-gated.

The read-only HTV/Spelman reckoning is complete. Corpus adoption remains separately approval-gated.

The Semantic Integrity Guardrails slice is implemented, and its claim is limited to guarded fresh-ingest output:

- every provider path binds the transcript grounding index into the request and re-checks it before any durable write: attendee raw labels must copy a normalized transcript speaker label verbatim, and signal evidence speakers and non-null timestamps must copy grounding-index entries verbatim;
- tampered persisted request grounding is rejected, and the observed fabricated-affiliation pattern — adding a parenthetical qualifier to a speaker label — cannot pass the gate in an attendee raw label or a signal evidence locator; provider-generated `display_name` and `role_context` remain semantic responsibilities rather than deterministically gated fields;
- semantic judgment is a versioned prompt contract, `semantic_guidance_version` `1.0`, carried in the request alongside the grounding index, with the four maintained provider instruction surfaces aligned to it;
- deterministic behavior is proven by the repository suite, including mutation-killing tests for the direct-provider and phase-2 grounding gates; semantic behavior is measured by the synthetic five-pattern acceptance case in `tests/fixtures/semantic-integrity/` under the procedure in `docs/testing/semantic-integrity-acceptance.md`.

The acceptance run recorded on 2026-07-26 passed all 18 blocking assertions with concordant human semantic review and independent blind review, and its one advisory failure was dispositioned as a fixture pattern gap rather than an extraction defect. It ran on an editable checkout under `--development-override`, so it is development/non-release evidence, not milestone proof; see `docs/sessions/2026-07-26-task7-semantic-acceptance-dev-run.md`. The slice was released as build `g51ff17173bea` (receipt cut from commit `51ff171`, installed and pinned per the release flow), and two release-evidence acceptance attempts on that frozen build then failed semantic assertions with a consistent `semantic_guidance` 1.0 wording gap; both failures are recorded as a contract finding with a guidance 1.1 revision planned, while the deterministic gates passed on the frozen build in both attempts. See `docs/sessions/2026-07-26-task7-release-and-acceptance.md`. Milestone-proof semantic acceptance on the approved runtime is not achieved.

The guardrails govern newly ingested output only. They are not a claim of general semantic correctness, and no existing artifact is adopted, corrected, or mutated by this work. The Just Works Continuity milestone also requires Track 4 and is not met.

The Approved Runtime policy is implemented and demonstrated as of 2026-07-24:

- each consumer pins one exact immutable build tied to a reviewed commit and packaged build;
- a stable channel may announce updates but never silently changes the selected build;
- updates and replacement-build approval are explicit;
- approved Claude Code client work blocks editable builds by default;
- a deliberate maintainer override is available for testing and must remain unmistakable in readiness and generated provenance.

The HTV consumer now runs an approved frozen wheel under a runtime pin, and one fresh non-synthetic transcript was processed end to end through one normal Claude Code request. Track 1 completion demonstrates approved-runtime readiness and persisted provenance only; it does not claim semantic guardrails or qualified history. The 177 legacy findings remain classified history warnings awaiting the separately approval-gated qualification track.

See `docs/north-star-board/002-just-works-continuity/`, `docs/sessions/2026-07-24-task9-htv-cutover.md`, and `docs/sessions/2026-07-24-task10-fresh-host-proof.md`.

## Current Development State

Committed implementation is stable through the session-inbox, handoff-health, and semantic-integrity guardrails work. The Stakeholder Playbook effort is currently a design-and-contract workstream, not a shipped feature.

Current accounting:

- Stakeholder Briefing V1 and Playbook Guidance V1.1 have an accepted durable design baseline in `docs/stakeholder-playbook-design.md`.
- `DECISIONS.md` records the accepted identity, provenance, storage, derivation, review, privacy, and milestone boundaries.
- schema 1.1 and Stakeholder Briefing V1 artifact-contract amendments passed focused review and are frozen for implementation.
- Layer 2 output-mode, title-repair, and regeneration contracts are written, but their implementation has not started.
- no schema 1.1, identity-registry, stakeholder-profile, briefing, guidance, email, screenshot, or social-source code has shipped.
- the current filesystem/JSONL/Markdown architecture remains sufficient for the planned V1 work; no backend or embeddings are planned.

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

Not complete:

- generalized schema 1.1 signal writing
- reviewed stakeholder identity registry and derivation-time resolution
- deterministic Stakeholder Briefing aggregation
- playbook derivation ledger, review overlays, profiles, briefings, status, and doctor behavior

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
- versioned semantic guidance (`1.0`) carried in requests and persisted through response binding, run summaries, artifacts, and ledger provenance

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

Existing HTV and Spelman artifacts remain read-only. Their reviewed defects remain dogfood evidence until a deterministic, fingerprinted adoption or correction plan receives separate owner approval under North Star board record 002, OB-002-1. Whether generated Markdown may be mutated at all is an open owner decision held by record 002 under "Other Later Decisions" and tracked as question 16 in `CURRENT-QUESTIONS.md`.

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

Status: Layer 5A foundation complete; Layer 5B implementation started; Layer 5C not started.

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

Status: not started; governed by Decision 35 in `DECISIONS.md`.

The receipt/pin/explicit-update ceremony is trust-building scaffolding with a recorded sunset: when the Just Works Continuity milestone is met, three consecutive releases ship without a drift incident, and the owner decides to broaden beyond the maintainer-only alpha, a distribution-transition plan convenes the board to amend record 002. Target end state: auto-updating package-manager delivery with attestation verification running invisibly inside the updater, failing closed only on actual verification failure.

Interim (no contract change required):

- collapse the maintainer release flow into a single command wrapping build, receipt, publish, install, and repin
- collapse consumer updates into a single verified update command wrapping fetch, verification, install, and repin

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

## Recommended Next Product Slice

The active product sequence is:

1. freeze and implement effective-date reliability, a manual meeting-date override, and controlled date repair as a Layer 1 prerequisite
2. add annotated schema 1.1 compatibility and adversarial fixtures
3. update provider/prompt/skill contracts when the new observation taxonomy becomes user-facing
4. implement Layer 5A generalized provenance and reviewed identity
5. implement deterministic Stakeholder Briefing V1

Layer 2 output modes remain independently shippable and contract-ready. They are a valid smaller implementation slice, but they are no longer the default priority after the stakeholder-playbook direction was accepted.

Reason: the live July 10/13 Teams VTT failure showed that meeting-date trust must be resolved before freshness and response sequencing can be credible. Once that foundation is reliable, the deterministic briefing is the highest-value next product surface.

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

Current verification on 2026-07-26:

- `uv run pytest` passed with 459 tests
- `git diff --check` passed
- the semantic acceptance run recorded in `docs/sessions/2026-07-26-task7-semantic-acceptance-dev-run.md` passed 18/18 blocking assertions as development/non-release evidence
