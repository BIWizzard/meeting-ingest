# Current Questions — meeting-ingest

## Purpose

This file tracks the highest-value open questions for the `meeting-ingest` rebuild.

The goal is to keep design exploration focused on decisions that materially shape the engine and its usability across hosts and projects.

Some numbered sections preserve historical discovery context. Where a question has been resolved, `DECISIONS.md`, `docs/stakeholder-playbook-design.md`, and `docs/artifact-contract.md` are authoritative.

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
- path discovery from arbitrary current working directory

Why it matters:
- this defines the operating model
- first-run usability depends on it

### 2. Should `ingest` auto-init missing structure, or should init be explicit?

Status: resolved.

Why it matters:
- affects user friction
- affects predictability
- shapes CLI philosophy

Good answer characteristics:
- low-friction
- safe
- easy to reason about

Resolved direction:
- `ingest` does not auto-init
- approved bootstrap is explicit `runtime pin --receipt ... --root ...` followed by `init --root ...`
- runtime pin bootstrap may create only the pin parent and pin, not normal config or corpus state

### 3. What should the stable CLI surface be?

Candidate commands:
- `meeting-ingest init`
- `meeting-ingest ingest`
- `meeting-ingest ingest-inbox`
- `meeting-ingest reconcile`
- `meeting-ingest doctor`
- `meeting-ingest status`

Why it matters:
- this becomes the canonical interface
- hosts should wrap this, not invent different semantics

Resolved direction:
- v1 should include a narrow `reconcile` command or equivalent duplicate/no-op repair path for incomplete archive/reconcile state
- v1 should include a batch inbox ingest command that processes `_inbox/` sequentially and returns per-file JSON results
- fan-out to multiple sub-agents or parallel workers for faster multi-document ingestion is a future enhancement, not the first batch-ingest implementation
- Track 1 adds `runtime inspect`, `readiness`, `runtime pin`, and `runtime update-check`; mutating commands share one engine-level readiness guard

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
- host/session-backed provider handoff for subscription-backed Claude Code, Codex, Supa Code, and T3 Code sessions?

Why it matters:
- determines portability across hosts and models
- determines whether personal workflows can use existing subscriptions without separate API calls

Resolved direction:
- API-backed providers remain necessary for portability and marketability
- host/session-backed providers are also required for personal harness workflows
- both paths must return the same validated provider response shape and use the same renderer, signals, ledger, archive, and reconcile behavior

### 6. What should be user-global vs project-local identity state?

Examples:
- global roster
- project-local overrides
- aliases
- uncertain matches

Why it matters:
- affects cross-project portability
- affects operational clarity

Resolved direction:
- v1 uses deterministic display-name slugification into person IDs
- v1 preserves raw speaker labels and confidence
- global/project-local roster storage is deferred

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
- stale lockfile handling

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

Resolved runtime direction:
- Claude Code is the reference host for the maintainer-only private alpha
- the durable skill is a portable template whose installed copy resolves one absolute approved executable
- consumer runtime selection is an explicit immutable pin, never ambient `uv run`, PATH precedence, or an editable install
- Git hooks and host workflows cannot silently install, update, or repin the runtime
- broader host approval remains deferred; it is not an open Track 1 implementation choice

### 8a. Should existing generated corpora be adopted or left as historical artifacts?

Need to decide:
- whether to backfill ledger records for existing Hearst/Spelman outputs
- whether to normalize old filenames
- whether to migrate old signal files
- whether to leave old outputs read-only and start fresh

Why it matters:
- the maintainer already has real project corpora
- migration policy affects ledger, doctor, and repair tooling

Resolved direction:
- HTV and Spelman must be inventoried and classified read-only before any adoption decision
- redundant repository-local copies do not count as independent dogfood evidence
- no legacy artifact may be relabeled as current-generated
- any adoption or repair requires a deterministic, fingerprinted plan and separate owner approval

Still open:
- which classes should be adopted, mapped, regenerated, preserved as legacy, or ignored

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
- duplicate/no-op may complete unfinished archive/reconcile work when ledger state shows it is incomplete

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
- how contextual date candidates are scored when explicit metadata is absent
- exact manual meeting-date override and controlled date-repair behavior

Why it matters:
- "cleaned verbatim" must preserve substantive content
- users and agents need to know how much the transcript was altered

Resolved direction:
- occurrence, acquisition/download, and processing time are distinct
- file modification time is a low-confidence acquisition-oriented fallback, not a trustworthy occurrence date for downloaded historical transcripts
- the engine must expose a safe explicit-date override and controlled repair path rather than requiring hand edits

### 13. What should the sub-agent contract be?

Need to decide:
- what instructions wrappers give the sub-agent
- what the sub-agent is allowed to decide
- what must always be delegated to the engine
- how Supa Code and T3 Code wrappers should invoke the same behavior
- how a subscription-backed active session should return structured provider JSON without an API key
- JSON run-summary shape
- exit-code contract
- quiet vs verbose output behavior

Why it matters:
- the user likes sub-agent operation
- host-specific wrappers should not fragment the product behavior
- wrappers need a stable machine interface to know what happened

Resolved direction:
- CLI should be a thin adapter over a reusable pipeline/orchestrator API
- `schema.py`, shared errors, shared fixtures, and docs should be lead-owned unless explicitly delegated
- host/session-backed provider extraction uses a request/response JSON handoff documented in `docs/provider-handoff-contract.md`
- the dedicated extraction sub-agent returns only provider-level JSON; the engine still validates output, enriches signals, renders markdown, writes the ledger, archives, reconciles, and emits the run summary
- host/session-backed extraction is a two-phase flow; phase 2 verifies the response against the persisted request, adopts request-side identity, reacquires the lock, and rechecks duplicate/no-op state before consuming response JSON
- canonical provider name is `session`, gated by a dedicated session-provider privacy setting rather than the direct remote-provider gate

### 14. How should stakeholder communication signals be modeled?

Status: resolved at the architectural level; value-level contract parameters and implementation remain.

Why it matters:
- a major workflow goal is helping the user communicate in their own voice with stakeholders
- downstream messaging support depends on clean source-grounded signals

Resolved direction:
- source observations feed deterministic Stakeholder Briefing V1, followed later by provider-assisted Playbook Guidance V1.1
- source observations remain factual and distinguish explicit evidence from strong or weak inference
- the playbook foundation adds narrow `communication_preference`, `communication_behavior`, and `interaction_response` observation types
- `communication_style` is derived pattern vocabulary only and is never extracted as a stakeholder trait
- primary meeting ingest only marks eligible playbook input; deterministic rebuild is an explicit separate operation
- reviewed project-local identity is resolved during derivation without rewriting source observations
- every profile entry preserves evidence, uncertainty, freshness, contradiction, and review state
- the playbook is communication accommodation and memory, not personality, vulnerability, persuasion, or relationship scoring

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
- meeting-derived Stakeholder Briefing V1 comes first
- plain-text email bodies or pasted messages are the first non-meeting pilot
- Teams/text screenshots follow only after OCR and region-addressable evidence contracts are trusted
- public/social sources require a separate privacy, attribution, retention, and acceptable-use policy
- all source kinds reuse generalized provenance while remaining distinguishable in artifacts, evidence, and privacy gates

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
- stakeholder communication should accumulate into deterministic Stakeholder Briefing V1 and later reviewed Playbook Guidance V1.1
- generated markdown lives in the meetings root by default
- playbook derivation is explicit and never part of primary ingest completion
- markdown should be optimized for agent consumption
- ledger records are source-level with mode-specific artifacts
- meeting identity is immutable and separate from mutable title/slug/filename
- meeting signal files are keyed by immutable `meeting_id`; generalized non-meeting signals use communication-neutral `source_id`
- ledger records are full snapshots with explicit event vocabulary
- duplicate/no-op ingest uses exit code `0`
- stakeholder profiles use a small reviewed project-local identity registry; extraction-time IDs remain advisory
- CLI is a thin adapter over a reusable pipeline API
- duplicate/no-op may repair incomplete reconcile state
- signal extraction stays factual and uses narrow source-observation types
- communication artifact ingest follows the meeting-derived briefing foundation in plain-text, image-based, then public/social phases
- file modification time is not considered a reliable occurrence date for downloaded historical Teams transcripts
- approved consumers pin one exact reproducible wheel/receipt/build/executable/workflow unit
- the private-alpha channel announces updates but never installs or repins them
- readiness is fail-closed for ambiguous current execution and separates explicit history warnings from current blockers
- editable client execution requires an invocation-scoped development reason and produces visibly development-marked provenance
- meeting artifact `1.1`, ledger `2.0`, signal `1.2`, run-summary/handoff `1.1`, and playbook `2.0` are the structural runtime-provenance cutover
- session phase 1 and phase 2 must use exactly matching runtime and workflow provenance
- no corpus adoption, repair, or generated-output mutation is authorized by the runtime cutover

Runtime identity, approval, readiness verdicts, development override scope, handoff binding, and update behavior are closed Track 1 policy, now implemented and demonstrated complete as of 2026-07-24: the reference host runs an approved frozen wheel under a runtime pin and processed one fresh non-synthetic transcript end to end through one normal Claude Code request. The frozen shapes remain authoritative in `DECISIONS.md` and `docs/artifact-contract.md`; the demonstration is recorded in `docs/sessions/2026-07-24-task9-htv-cutover.md` and `docs/sessions/2026-07-24-task10-fresh-host-proof.md`. Demonstration does not claim semantic guardrails or qualified history. Remaining relevant questions are corpus class disposition under 8a and the bounded recovery/generated-output mutation questions under 7a; neither was resolved by mutating HTV or Spelman history during Track 1.

## Not In Scope Right Now

- broad generic ingestion types beyond the current meeting/transcript focus
- collapsing into a generic agentic-toolbox repo
- premature rebranding into a larger product family
- dashboard-first design
- full stakeholder messaging assistant behavior inside this repo

## How To Use This File

When starting a new exploration thread, pick 1-3 questions from this file and drive them toward concrete architecture proposals or decisions. Avoid trying to answer everything in a single pass.
