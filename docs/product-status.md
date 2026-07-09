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

- rolling stakeholder playbook aggregation
- derived playbook status

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
- decide exact confidence policy for provider-suggested titles/slugs
- decide whether doctor should only report repair suggestions or also implement repairs

### Layer 2: Output Modes And Repair/Regenerate Workflows

Status: not implemented beyond the current default mode.

Done:

- `summary-plus-verbatim` mode
- mode field in config/run summaries/artifacts

Remaining:

- implement `summary` mode
- implement `verbatim` mode
- define and implement title repair
- define and implement artifact regeneration from `_processed/`
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

### Layer 5: Stakeholder Playbook V1

Status: signal foundation exists; playbook not built.

Done:

- per-meeting communication signal schema/output
- signal provenance to meeting/run IDs
- signal markdown mirroring

Remaining:

- playbook schema
- derived `_derived/` artifact location
- per-stakeholder aggregation
- confidence/provenance policy
- playbook update status in doctor/status

### Layer 6: Migration And Existing Corpus Adoption

Status: not started.

Remaining:

- read-only corpus scan
- adoption report
- adoption ledger records
- migration docs and dry-run workflow

### Layer 7: Broader Communication Artifact Ingest

Status: not started.

Remaining:

- artifact taxonomy for non-meeting communications
- email/memo/message/screenshot extraction
- non-meeting signal provenance
- playbook aggregation across meeting and communication sources

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

The recommended next product slice is Layer 2 contract and implementation planning:

1. finalize `summary` and `verbatim` artifact contracts
2. decide repair/regenerate command UX
3. implement `summary` mode
4. implement `verbatim` mode
5. then implement title repair or regenerate

Reason: the core ingest/done-process and session inbox machinery are now strong enough. The next user-visible value is giving the user deliberate control over artifact depth and repair/regeneration.

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

Current verification at the time this status was written:

- `uv run pytest` passed with 133 tests
- `uv run python -m py_compile src/meeting_ingest/*.py` passed
- `git diff --check` passed
