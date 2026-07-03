# Current Questions — meeting-ingest

## Purpose

This file tracks the highest-value open questions for the `meeting-ingest` rebuild.

The goal is to keep design exploration focused on decisions that materially shape the engine and its usability across hosts and projects.

## Open Questions

### 1. What should the project-local directory and config layout be?

Likely concerns:
- meetings root
- `_inbox/`
- `_processed/`
- `_signals/`
- `_quarantine/`
- `_inbox/_done/`
- `_derived/`
- `_cache/`
- ledger
- project config

Why it matters:
- this defines the operating model
- first-run usability depends on it

### 2. Should `ingest` auto-init missing structure, or should init be explicit?

Why it matters:
- affects user friction
- affects predictability
- shapes CLI philosophy

Good answer characteristics:
- low-friction
- safe
- easy to reason about

### 3. What should the stable CLI surface be?

Candidate commands:
- `meeting-ingest init`
- `meeting-ingest ingest`
- `meeting-ingest reconcile`
- `meeting-ingest doctor`
- `meeting-ingest status`

Why it matters:
- this becomes the canonical interface
- hosts should wrap this, not invent different semantics

### 4. What should the extraction contract be?

Need to define:
- required inputs
- required outputs
- observation schema
- validation strategy
- error behavior

Why it matters:
- this is the seam between deterministic engine logic and provider-backed extraction

### 5. How should provider plugins be modeled?

Need to decide:
- simple interface?
- runtime registry?
- config-driven provider selection?
- direct SDK adapters?

Why it matters:
- determines portability across hosts and models

### 6. What should be user-global vs project-local identity state?

Examples:
- global roster
- project-local overrides
- aliases
- uncertain matches

Why it matters:
- affects cross-project portability
- affects operational clarity

### 7. How should failure handling and quarantine work?

Need to decide:
- unsupported formats
- extraction failure
- partial write handling
- bad or ambiguous identity resolution
- corrupt source input

Why it matters:
- ingest reliability depends on this

### 7a. How should partial writes, regeneration, and locking work?

Need to decide:
- lockfile or other concurrency control for simultaneous agent/harness runs
- artifact-written-but-ledger-failed recovery
- ledger-written-but-render-failed recovery
- regeneration from `_processed/`
- per-artifact status transitions
- reserved concurrency exit code behavior

Why it matters:
- agentic harnesses may run overlapping commands
- append-only ledgers and filesystem artifacts need explicit recovery semantics

### 8. What is the migration path from the existing Claude-first implementation?

Need to decide:
- what code to port directly
- what to rewrite
- what behavior to preserve exactly
- what packaging/orchestration assumptions to discard

Why it matters:
- preserves momentum without freezing old architecture into place

### 8a. Should existing generated corpora be adopted or left as historical artifacts?

Need to decide:
- whether to backfill ledger records for existing Hearst/Spelman outputs
- whether to normalize old filenames
- whether to migrate old signal files
- whether to leave old outputs read-only and start fresh

Why it matters:
- the maintainer already has real project corpora
- migration policy affects ledger, doctor, and repair tooling

### 9. How should tests be structured?

Likely areas:
- deterministic engine tests
- provider contract validation
- directory/init behavior
- reconcile behavior
- end-to-end ingest fixtures

Why it matters:
- this tool touches real workflow state and should be trustworthy

### 10. How should `meeting-ingest` relate to `iQ Context` over time?

Potential integration points:
- tracked generated artifacts
- optional project init support
- retrieval over signals/markdown outputs

Why it matters:
- the tools should cooperate cleanly without boundary collapse

### 11. How should output modes affect artifact and ledger behavior?

Initial modes:
- smart summary
- summary plus verbatim
- verbatim only

Need to decide:
- mode names
- whether summary-plus-verbatim should also emit optional split derivatives
- duplicate/no-op source disposition in `_inbox`
- filename collision policy details
- date-correction-after-meeting-id-mint policy confirmation

Why it matters:
- this directly addresses current inconsistent output
- it affects re-ingest and reconciliation semantics
- personal workflows depend on being able to scan meeting files by date, topic, and one-on-one counterpart

Resolved direction:
- default mode is `summary-plus-verbatim`
- generated markdown should live in the meetings root
- filenames should be inferred from date, meeting identity, topic, and one-on-one counterpart when applicable
- ledger records should be source-level with mode-specific artifacts
- signal files should be keyed by immutable `meeting_id`
- duplicate/no-op uses exit code `0` with `status: "no_op"`
- filename collisions use numeric suffixes with run-summary warnings

### 12. How should performance and model right-sizing work?

Need to decide:
- which phases are deterministic
- which phases require provider calls
- whether summary, signals, and transcript cleanup use separate model tiers
- whether normalized transcript text should be cached by source hash
- retry behavior for failed provider steps
- transcript length limits, chunking strategy, and cost guards
- provider data routing/privacy policy

Why it matters:
- the current workflow is useful but slow
- personal daily use depends on speed and predictable cost
- client-sensitive transcripts should not accidentally route to multiple vendors

### 12a. What exactly are deterministic cleaned-verbatim rules?

Need to decide:
- which filler artifacts are removed without a model
- how obvious ASR junk is identified
- how uncertain cleanup is marked
- when transcript repair requires a provider call

Why it matters:
- "cleaned verbatim" must preserve substantive content
- users and agents need to know how much the transcript was altered

### 13. What should the sub-agent contract be?

Need to decide:
- what instructions wrappers give the sub-agent
- what the sub-agent is allowed to decide
- what must always be delegated to the engine
- how Supa Code and T3 Code wrappers should invoke the same behavior
- JSON run-summary shape
- exit-code contract
- quiet vs verbose output behavior

Why it matters:
- the user likes sub-agent operation
- host-specific wrappers should not fragment the product behavior
- wrappers need a stable machine interface to know what happened

### 14. How should stakeholder communication signals be modeled?

Need to decide:
- signal schema
- confidence and provenance fields
- how to distinguish explicit asks from inferred priorities
- how to represent communication style cues
- how to avoid turning the tool into a broad profiling or messaging product

Why it matters:
- a major workflow goal is helping the user communicate in their own voice with stakeholders
- downstream messaging support depends on clean source-grounded signals

Resolved direction:
- per-meeting signals should feed a rolling stakeholder playbook
- primary meeting markdown should be available before slower playbook maintenance blocks the user
- signal records should distinguish explicit statements from inferred patterns
- v1 signal taxonomy should stay small and factual
- communication guidance belongs in playbook derivation, not raw per-meeting signals

### 15. How should future communication artifact ingest be bounded?

Potential future sources:
- email bodies
- email screenshots
- memos
- Teams messages or threads
- attachments containing stakeholder requests or decisions

Need to decide later:
- whether this belongs in `meeting-ingest` or a sibling tool
- what source types are supported first
- how non-meeting artifacts should be named and stored
- whether they produce markdown artifacts, signals only, or both
- how screenshot/OCR ingestion should work

Why it matters:
- stakeholder playbook quality improves when important stakeholder voice is not limited to meetings
- broadening too early could dilute the meeting/transcript ingest engine

Current stance:
- valuable future extension
- not part of the first implementation target
- architecture should keep source and signal models flexible enough to support it later

## Already Decided

- this repo stays focused on the ingestion engine
- product direction is CLI-first and host-neutral
- first-run project setup is required
- strong done-process semantics are required
- idempotency stays content-hash based
- `iQ Context` is separate but complementary
- initial scope is personal-workflow first
- output modes should be explicit
- sub-agent operation remains desirable
- summary plus verbatim is the default mode
- output filenames must be scannable and may be repaired after ingest
- stakeholder communication should accumulate into a rolling playbook
- generated markdown lives in the meetings root by default
- primary meeting artifacts are ready before derived playbook work blocks the user
- markdown should be optimized for agent consumption
- ledger records are source-level with mode-specific artifacts
- meeting identity is immutable and separate from mutable title/slug/filename
- signal files are keyed by immutable `meeting_id`
- ledger records are full snapshots with explicit event vocabulary
- duplicate/no-op ingest uses exit code `0`
- v1 signal extraction should stay factual and minimal
- communication artifact ingest is a future extension, not the first build target

## Not In Scope Right Now

- broad generic ingestion types beyond the current meeting/transcript focus
- collapsing into a generic agentic-toolbox repo
- premature rebranding into a larger product family
- dashboard-first design
- full stakeholder messaging assistant behavior inside this repo

## How To Use This File

When starting a new exploration thread, pick 1-3 questions from this file and drive them toward concrete architecture proposals or decisions. Avoid trying to answer everything in a single pass.
