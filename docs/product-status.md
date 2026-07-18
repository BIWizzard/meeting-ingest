# Product Status

## Purpose

This document is the current product-level status for `meeting-ingest`.

Use it before writing product briefs, planning roadmap work, or deciding what to implement next. It reconciles the roadmap against the current code, tests, contracts, commit history, and session notes.

## Current Product Summary

`meeting-ingest` is a project-local meeting transcript ingestion engine for agent-operated workflows.

It can turn `.txt`, `.vtt`, and `.docx` meeting artifacts into durable project knowledge with:

- structured markdown meeting artifacts
- signal JSONL output
- source-ledger idempotency
- processed-source archive
- inbox reconciliation after successful ingest
- provider-backed structured extraction
- session-provider handoffs for active agent hosts
- doctor/status visibility into incomplete or pending state

The product is currently strongest for a technical owner using Codex, Claude Code, Supa Code, T3 Code, or plain CLI automation. It is not yet a general self-serve product.

## Current Development State

Committed implementation is stable through the session-inbox and handoff-health work. The Stakeholder Playbook effort is currently a design-and-contract workstream, not a shipped feature.

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

- effective-date extraction recognizes explicit supported filename and Teams export-header dates, but VTT transcripts without those forms still fall back to file modification time
- for downloaded historical Teams transcripts, that timestamp is usually acquisition time rather than the meeting occurrence date
- there is no implemented `--meeting-date` override or controlled date-repair command yet

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

Remaining:

- improve title/filename inference quality using more real transcript fixtures
- make meeting occurrence reliable when a transcript is downloaded after the meeting date
- distinguish occurrence, acquisition, and processing time in implemented signal provenance
- add a manual meeting-date override and controlled repair path for already-ingested artifacts
- warn when file modification time may be a download date rather than the meeting date
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

Remaining:

- decide first production-grade remote provider posture
- productize first host wrapper
- improve prompt strategy by quality tier
- decide model provenance expectations for subscription-backed hosts
- add other provider adapters only when selected

### Layer 5: Stakeholder Briefing And Playbook Guidance

Status: accepted design baseline and artifact contract; implementation not started.

Done:

- per-meeting communication signal schema/output
- signal provenance to meeting/run IDs
- signal markdown mirroring
- independent design and arbitration passes
- accepted `docs/stakeholder-playbook-design.md` baseline
- decisions frozen for reviewed identity, deterministic full rebuilds, immutable generations, separate derivation history, review overlays, dedicated synthesis privacy gates, and the Briefing V1/Guidance V1.1 split
- reviewed schema 1.1 and deterministic Stakeholder Briefing artifact contracts

#### Layer 5A: Generalized Provenance And Identity Foundation

Remaining:

- add annotated compatibility and adversarial fixtures
- implement schema 1.1 tolerant readers/writers
- implement generalized source and occurrence/acquisition/processing provenance
- implement deterministic signal identity and regeneration supersession
- implement the reviewed project-local identity registry, derivation-time resolution, and identity candidates

#### Layer 5B: Stakeholder Briefing V1

Remaining:

- implement deterministic full rebuilds
- materialize canonical profile JSON and human/agent-readable briefing Markdown
- implement immutable generations, derivation ledger, current index, and input fingerprints
- implement tracked asks and commitments, priorities, concerns, rationales, preferences, behaviors, interaction responses, freshness, and contradiction candidates
- implement reject, resolve, suppress-signal, and identity-correction controls
- implement `playbook update`, `show`, and briefing surfaces plus status/doctor visibility

#### Layer 5C: Playbook Guidance V1.1

Remaining:

- freeze the structured derivation provider request/response contract and approach-tag vocabulary
- implement dedicated playbook-synthesis privacy gates
- implement semantic clustering, contextual scope, contradiction confirmation, positive-response patterns, communication cues, and caveats
- implement explicit review state for inferred guidance

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

- `049d3a0 feat: expose session handoff status`
- `3f07f59 feat: add session inbox wrapper`
- `a713b3d feat: plan session inbox handoffs`
- `5408126 feat: enrich no-op reconcile summaries`
- `5e6b15b Harden session provider handoff errors`
- `802d190 Add session provider handoff flow`
- `85319c5 Add Anthropic provider adapter`
- `c5e11ca Add sequential inbox batch ingest`

Current verification on 2026-07-18:

- `uv run pytest` passed with 133 tests
- `git diff --check` passed
- committed `main` matched `origin/main` before this documentation checkpoint
