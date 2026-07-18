# Implementation Plan

## Purpose

This plan translates the design and artifact contract into an implementation path for `meeting-ingest`.

The first implementation should produce a working, trustworthy meeting ingestion engine before expanding into broader artifact types, rolling playbook generation, or additional providers.

## Operating Model

Implementation should be orchestrated by the lead agent.

Lead agent responsibilities:

- preserve product scope and decisions
- sequence work into small implementation slices
- assign scoped coding tasks to sub-agents
- review sub-agent output before integration
- keep module boundaries aligned with the artifact contract
- run verification
- ask the user for guidance when decisions affect workflow, output contract, provider choice, or migration policy
- own `docs/`, shared schemas, exception taxonomy, and interface changes

Sub-agent responsibilities:

- implement clearly scoped modules or tests
- work on one assigned module or narrow module group at a time
- follow the existing docs as source of truth
- avoid changing product scope or artifact contract without escalation
- propose contract/schema/interface changes to the lead agent instead of editing them directly
- return concise summaries of files changed, tests added, and open issues

The lead agent remains responsible for final integration quality.

Coordination rules:

- One sub-agent owns a module at a time.
- Every task assignment should name target files and expected tests.
- `schema.py`, `errors.py`, shared fixtures, and docs are lead-owned unless explicitly delegated.
- Provider schema freezes at the end of Milestone 3.
- Ledger record shape freezes at the end of Milestone 4.
- Any post-freeze change to a contract surface requires a doc update before code changes.
- Milestone gates require a green test suite and lead diff review against `docs/artifact-contract.md`.

## Source Of Truth

Implementation should follow these documents in order:

1. `docs/artifact-contract.md`
2. `docs/design-proposal.md`
3. `DECISIONS.md`
4. `CURRENT-QUESTIONS.md`
5. `docs/current-output-evaluation.md`
6. `docs/personal-workflow-scope.md`
7. `docs/context-primer.md`

If these documents conflict, `docs/artifact-contract.md` wins for generated artifact shape, signal JSONL, ledger events, run summaries, and exit codes.

## V1 Scope

V1 implements:

- Python package and CLI scaffold
- reusable pipeline/orchestrator API
- project-local init and path discovery
- content hashing
- v1 identity/person ID normalization
- source-level append-only ledger with full snapshot records
- deterministic `.txt`, `.vtt`, and `.docx` transcript extraction
- deterministic cleaned-verbatim normalization rules
- provider contract with mock provider
- one real provider adapter
- host/session-backed provider path design for subscription-backed agentic harness use
- title/filename inference from provider output
- `summary-plus-verbatim` markdown rendering
- v1 signal JSONL output
- archive and reconcile behavior
- duplicate/no-op reconcile repair
- JSON run summary
- exit-code contract
- basic `doctor`

V1 does not implement:

- rolling stakeholder playbook aggregation
- `summary` mode
- `verbatim` mode
- rename repair command
- split-file derivatives
- `--mode auto`
- communication artifact ingest
- existing-corpus migration tooling
- global/project-local roster storage and cross-project identity resolution
- full regenerate command
- OpenAI/Gemini provider adapters unless selected as the first real adapter
- production-ready host/session-backed provider wrappers for every harness

## Package Layout

Proposed package:

```text
src/meeting_ingest/
  __init__.py
  cli.py
  pipeline.py
  config.py
  paths.py
  errors.py
  clock.py
  ids.py
  identity.py
  hashing.py
  extract.py
  transcript.py
  provider.py
  providers/
    __init__.py
    mock.py
    anthropic.py
  schema.py
  render.py
  signals.py
  ledger.py
  archive.py
  doctor.py
  run_summary.py
  locking.py
```

Tests:

```text
tests/
  fixtures/
    transcripts/
    provider_outputs/
    expected_markdown/
  test_ids.py
  test_identity.py
  test_hashing.py
  test_config.py
  test_paths.py
  test_extract.py
  test_transcript.py
  test_render_summary_plus_verbatim.py
  test_signals.py
  test_ledger.py
  test_archive_reconcile.py
  test_run_summary.py
  test_doctor.py
  test_locking.py
  test_e2e_ingest.py
  test_cli_smoke.py
```

## CLI Surface

V1 commands:

```text
meeting-ingest init
meeting-ingest provider-request <source> [--mode summary-plus-verbatim] --provider session [--quality fast|balanced|deep] [--json]
meeting-ingest ingest <source> [--mode summary-plus-verbatim] [--provider mock|anthropic] [--quality fast|balanced|deep] [--provider-response path] [--json]
meeting-ingest ingest-inbox [--json]
meeting-ingest session-inbox [--quality fast|balanced|deep] [--json]
meeting-ingest doctor
meeting-ingest status
meeting-ingest reconcile
```

`ingest` may auto-init only if the behavior is explicitly configured or passed as a flag. Default v1 recommendation: `ingest` should fail with a clear message if no config/layout exists, while `init` remains easy.

This auto-init decision should be confirmed before implementation.

`reconcile` is included in v1 as a narrow recovery command for sources whose primary artifacts are ready but archive/reconcile did not complete.

`ingest-inbox` should process files directly under `_inbox/` one at a time and skip `_inbox/_done/`. Unsupported formats should be reported as per-file failures using normal ingest/quarantine behavior. It should return a batch JSON summary with per-source results and continue processing after recoverable per-file failures.

`provider-request` is phase 1 for host/session-backed extraction and writes a request envelope under `_cache/provider-requests/` plus an expected response path under `_cache/provider-responses/`. `ingest --provider session --provider-response path` is phase 2 and must verify the matching persisted request before adopting request-side identity and completing the normal ingest pipeline.

Future enhancement: add controlled parallelism for inbox ingestion, such as `--jobs`, or harness-level fan-out to multiple focused sub-agents. This should wait until the engine has explicit coordination for shared ledger writes, lock behavior, provider rate limits, and per-file reporting.

Current personal-workflow state: `ingest-inbox --provider session --json` performs the engine-assisted batch phase 1 by creating one provider request per direct inbox file and returning per-file request/response paths. The active agent must still write provider response JSON and run phase-2 `ingest --provider session --provider-response ...` for each pending result. `meeting_ingest.session_inbox.process_session_inbox` is the thin active-agent wrapper hook: it scans existing provider requests first, completes any ready responses before minting fresh requests, skips fresh phase 1 while unresolved handoffs remain, invokes a host-provided extractor callback for each pending request, runs phase 2 for completed responses, and reports markdown, signals, archive, and reconcile paths. The `session-inbox` CLI command exposes the same wrapper without an extractor callback, so it honestly reports pending responses instead of pretending the CLI can access the active model. The expected agent workflow is documented in `docs/session-provider-inbox-agent-workflow.md`.

## Project Layout

V1 project layout:

```text
_local/project-context/meetings/
  _inbox/
    _done/
  _processed/
  _quarantine/
  _signals/
  _derived/
  _cache/
  _ledger.jsonl
```

Generated meeting markdown lives directly in the meetings root.

## Config

Candidate config path:

```text
_local/project-context/meetings/meeting-ingest.toml
```

Candidate fields:

```toml
schema_version = "1.0"
default_mode = "summary-plus-verbatim"
default_provider = "mock"
default_quality = "balanced"
auto_init = false
reconcile_after_success = true
cache_normalized_transcript = true

[paths]
root = "_local/project-context/meetings"
inbox = "_inbox"
processed = "_processed"
signals = "_signals"
quarantine = "_quarantine"
derived = "_derived"
cache = "_cache"
ledger = "_ledger.jsonl"

[privacy]
allow_remote_provider = false
allow_session_provider = false
```

Provider configuration should avoid accidentally routing sensitive client transcripts to multiple vendors.

## Module Responsibilities

### `cli.py`

Owns command parsing and process exit behavior.

Must:

- emit JSON run summary for `--json`
- map failures to documented exit codes
- avoid printing noisy logs to stdout when `--json` is used
- call `pipeline.py` rather than owning ingest sequencing

### `pipeline.py`

Owns the ingest workflow as a reusable library API.

Must:

- run the contract-defined ingest phases in order
- acquire and release the project lock
- coordinate extraction, provider call, rendering, signals, ledger, archive, and reconcile
- enforce validation before `primary_artifacts_ready`
- write `primary_artifacts_ready` and `ingest_completed` ledger snapshots at the correct times
- decide fail vs quarantine based on typed errors
- return a run-summary object to `cli.py`

No host wrapper should need to reimplement pipeline semantics.

### `config.py`

Owns config loading, defaults, and validation.

Must:

- validate `schema_version`
- resolve provider and quality settings
- enforce privacy gates for remote providers

### `paths.py`

Owns project root detection and path resolution.

Must:

- produce paths relative to meetings root for ledger records
- keep generated markdown in meetings root
- keep source/runtime artifacts in underscore directories
- discover the meetings root by config walk-up from the current working directory, with a clear failure if none is found

### `errors.py`

Owns shared exception and error-summary taxonomy.

Must:

- define typed errors with `phase`, `code`, `message`, `recoverable`, and optional `details`
- map typed errors to exit codes and JSON `errors[]`
- be available from Milestone 1 so later modules do not invent incompatible errors

### `clock.py`

Owns injectable time and deterministic ID suffix hooks.

Must:

- allow tests to freeze `generated_at`
- allow tests to provide deterministic `ingest_run_id` suffixes
- prevent golden tests from depending on wall-clock time

### `ids.py`

Owns immutable IDs.

Must:

- mint `meeting_id` once using best-known effective date and source shorthash
- mint unique `ingest_run_id` per attempt
- never derive durable IDs from mutable slug or filename

### `identity.py`

Owns v1 identity normalization.

V1 stance:

- no global roster
- no project-local roster
- provider-proposed display names are deterministically slugified into person IDs
- uncertain names are preserved with confidence markings

Must:

- produce stable person IDs from display names when no roster exists
- preserve raw speaker labels
- avoid silently collapsing uncertain speakers
- support `stakeholder_id: null` for unresolved or group-directed signals

Global and project-local roster resolution are deferred.

### `extract.py`

Owns source text extraction.

V1 formats:

- `.txt`
- `.vtt`
- `.docx`

Must:

- return normalized source text plus source metadata
- surface unsupported formats cleanly
- infer best-known effective date from source metadata, transcript timestamps, filename, or filesystem metadata
- include date confidence and source in metadata

Fallback policy:

- if no date is detectable, use file modified date with low confidence in v1
- do not quarantine solely for missing date unless the user later prefers stricter behavior

### `transcript.py`

Owns deterministic cleaned-verbatim rules.

Must:

- preserve speaker-attributed chronological content
- apply only documented deterministic cleanup
- mark unknown or uncertain speakers explicitly

### `provider.py`

Defines provider interface and structured response shape.

Provider paths:

- API-backed providers call external model APIs directly.
- Host/session-backed providers let a dedicated extraction sub-agent in an active agentic harness produce the same structured provider response through the current subscription-backed session.

The engine should treat both paths as providers only if they return the same validated response shape.

Provider output should include:

- title proposal
- slug proposal
- meeting type
- participants
- topics
- decisions
- actions
- stakeholder asks
- dependencies/risks
- open questions
- minimal v1 signals
- summary narrative

Provider output must be validated before rendering.

### `schema.py`

Owns shared schemas and validation helpers.

Must:

- validate provider responses
- validate signal records
- validate rendered artifact structure where practical
- validate ledger snapshots
- keep schema versions centralized

Sub-agents should not change schema surfaces without lead approval.

### `render.py`

Owns deterministic markdown generation.

Must:

- implement `summary-plus-verbatim`
- emit all required headings
- emit explicit empty sections
- keep transcript final
- include transcript sentinels
- quote `schema_version` in YAML front matter

### `signals.py`

Owns v1 signal validation and JSONL writing.

Must:

- write to `_signals/<meeting_id>.jsonl`
- validate each signal against the v1 schema
- allow empty valid signal files

### `ledger.py`

Owns append-only full-snapshot ledger records.

Must:

- implement last-valid-record-wins per `source_sha256`
- validate event vocabulary
- write complete snapshots, not deltas
- track per-artifact status
- support duplicate/no-op lookup

### `archive.py`

Owns processed copy and inbox reconciliation.

Must:

- archive canonical processed copy after primary artifact and signal output
- reconcile inbox source only after confirmed primary success
- support skipped reconciliation by config
- support reconcile retry for records stuck after `primary_artifacts_ready`
- allow duplicate/no-op ingest to complete unfinished archive/reconcile work when ledger state shows it is incomplete

### `doctor.py`

Owns diagnostic checks.

V1 checks:

- malformed ledger records
- orphan markdown artifacts
- missing signal files
- missing processed copies
- inbox residue
- stale derived work status
- duplicate-looking meetings by date/title/counterpart heuristic
- stale lockfiles

Doctor/status exit semantics:

- `doctor` exits `0` when no issues are found
- `doctor` exits `1` when issues are found
- `status` exits `0` when it can read project state, even if it reports warnings

### `locking.py`

Owns concurrency control.

V1 can use a simple lockfile under the meetings root.

Lock conflict should return exit code `10`.

Lockfile should include PID and timestamp. Stale lock handling should be conservative and surfaced by `doctor`.

## Implementation Milestones

### Milestone 1: Scaffold, Init, And Foundations

Deliverables:

- package scaffold
- CLI entry point
- `init`
- config loading
- path layout creation
- `pipeline.py` skeleton
- `errors.py` typed exception taxonomy
- `clock.py` injectable clock/ID hooks
- `schema.py` skeleton
- tests for config and paths
- tests for error mapping and deterministic clock behavior

Lead review:

- verify layout matches docs
- decide auto-init behavior with user if still unresolved

### Milestone 2: Extraction And IDs

Deliverables:

- content hashing
- `meeting_id`
- `ingest_run_id`
- v1 `identity.py`
- `.txt`, `.vtt`, `.docx` extraction
- deterministic transcript cleanup skeleton
- tests for ID stability and run ID uniqueness
- tests for v1 person ID normalization
- tests for effective-date fallback metadata

Lead review:

- verify durable IDs do not depend on mutable slug
- verify v1 identity output satisfies the artifact contract without pretending full roster support exists

### Milestone 3: Provider Contract And Renderer

Deliverables:

- provider interface
- mock provider
- structured response validation
- `summary-plus-verbatim` renderer
- golden markdown fixture test
- frozen clock/ID fixture support

Lead review:

- compare rendered markdown to artifact contract

### Milestone 4: Signals, Ledger, Archive

Deliverables:

- v1 signal JSONL validation/writer
- append-only full-snapshot ledger
- `primary_artifacts_ready` and `ingest_completed` events
- processed archive copy
- inbox reconciliation
- minimal `reconcile` recovery command
- duplicate/no-op behavior

Lead review:

- verify duplicate/no-op exits success-class
- verify ledger snapshots do not erase earlier mode artifacts
- verify duplicate/no-op can finish incomplete reconcile when appropriate

### Milestone 5: Run Summary, Exit Codes, Doctor

Deliverables:

- JSON run summary
- exit-code mapping
- `doctor`
- lockfile behavior
- CLI smoke tests
- automated end-to-end ingest test

Lead review:

- run end-to-end fixture ingest
- verify agent-readable output paths

### Milestone 6: First Real Provider

Deliverables:

- one real provider adapter
- provider privacy gate
- provider integration test strategy
- docs for required API key/config

Lead review:

- confirm provider data routing with user before sending real client transcript content
- first real-provider test must use a synthetic fixture transcript, not Hearst/Spelman content

### Milestone 7: Host/Session-Backed Provider Path

Deliverables:

- generic agent-facing extraction prompt that returns provider JSON only
- handoff contract for a dedicated extraction sub-agent to provide structured provider output back to the engine
- CLI or wrapper mechanism for ingesting with externally supplied provider JSON
- Supa Code / T3 Code / Claude Code / Codex usage notes
- tests proving externally supplied provider JSON passes the same schema, renderer, signal, ledger, archive, and reconcile flow

The handoff contract is now specified in `docs/provider-handoff-contract.md`. Implementation should add shared JSON parsing for the existing API-backed provider payload and the host/session response envelope, then route externally supplied provider output into the pipeline immediately before `validate_provider_response`.

Hard dependency: land provider failure semantics first, including typed provider failure, exit `5`, provider-validation exit `6`, and `ingest_failed` ledger recording before primary artifacts are ready. The session provider path should use canonical provider name `session`, respect `privacy.allow_session_provider`, persist provider request/response files under `_cache`, and complete through a two-phase flow where phase 2 verifies the response against the persisted request before adopting request-side identity.

Lead review:

- verify subscription-backed workflows do not require API keys
- verify transcript-heavy extraction context stays in the dedicated sub-agent rather than the main session
- verify host/session-backed extraction does not fragment the artifact contract or done process
- verify API-backed providers remain the canonical portable path

## Test Strategy

Tests should start with mock provider fixtures.

Required v1 test types:

- end-to-end fixture ingest
- config validation
- path initialization
- content hash stability
- `meeting_id` minting
- `ingest_run_id` uniqueness
- v1 identity normalization
- transcript extraction for `.txt`, `.vtt`, `.docx`
- deterministic cleaned-verbatim cleanup
- renderer golden output
- required headings and transcript-final validation
- signal JSONL schema validation
- ledger full-snapshot behavior
- ledger preservation when a later mode artifact is added
- duplicate/no-op behavior
- duplicate/no-op incomplete-reconcile repair
- archive/reconcile behavior
- failure injection for provider validation, ledger write, archive, and reconcile phases
- JSON run-summary shape
- exit-code mapping
- lock conflict
- stale lock reporting

## Roadmap Implementation Plan

This roadmap starts from the working V1 engine and sequences the next product layers. Each layer should be independently shippable: the engine should remain useful after every layer, and unfinished future layers should not weaken the ingest/archive/ledger/reconcile contract.

For the current audited product accounting, use `docs/product-status.md`. This roadmap is directional; the product status document is the first place to check whether a roadmap item has already landed.

Roadmap priorities, with the layer headings below as the canonical dependency order:

1. finish V1 completion polish, including trustworthy effective-date handling
2. keep output modes and repair/regenerate workflows independently shippable
3. finish session inbox and host-wrapper productization
4. harden providers and host wrappers
5. implement generalized provenance and reviewed stakeholder identity
6. ship deterministic Stakeholder Briefing V1
7. add provider-assisted Playbook Guidance V1.1
8. support migration and existing corpus adoption
9. add plain-text, image-based, and public/social communication sources in that order
10. integrate with iQ Context

### Layer 1: V1 Completion Polish

Goal:

- make the current meeting-ingest path trustworthy enough for daily personal use.

Status:

- mostly complete

Done:

- expose rename suggestions in the JSON run summary when fallback naming is used
- ensure every successful run reports primary markdown, signal JSONL, processed archive path, reconcile path, provider, mode, and ledger event
- expand `doctor` checks for inbox residue, malformed ledger entries, orphan signals, missing processed copies, and stale runtime cache
- document the `doctor --json` and `status --json` shapes
- add focused regression fixtures for real observed transcript edge cases
- document the exact done state for `ingest`, `provider-request`, manual session phase 2, `reconcile`, `status`, and `doctor`
- enrich duplicate/no-op summaries with current source, existing artifact, archive/reconcile, and repair state
- extract explicit dates from supported filename shapes and Teams export headers
- record date source and confidence, including low-confidence file-modification fallback

Remaining:

- tighten title and filename inference so `generic-<hash>` is rare on a broader real-transcript set
- add more real observed transcript fixtures as new edge cases appear
- separate meeting occurrence from acquisition/download time throughout the engine-facing contract
- infer meeting occurrence from trustworthy source metadata and corroborated transcript evidence before minting IDs and provider requests
- add an explicit `--meeting-date YYYY-MM-DD` override for known dates
- define and implement controlled effective-date repair for already-ingested artifacts without changing immutable `meeting_id`
- warn prominently whenever file modification time is used as the meeting occurrence fallback

Needs design decision:

- exact confidence threshold for accepting provider-suggested titles and slugs
- whether fallback filenames should include meeting type, counterpart, topic, or only source hash when confidence is low
- whether `doctor` should offer machine-readable repair suggestions only, or also implement interactive repair later
- the deterministic candidate, conflict, and confidence rules for contextual date evidence such as weekday, relative-date, and nearby absolute-date references
- the exact `repair-date` CLI, ledger snapshot, signal timing, artifact rename, and run-summary contract

Acceptance criteria:

- a real inbox transcript can be processed with `provider=session` through the documented two-phase loop and produces a high-signal filename without manual renaming when the transcript contains enough title evidence
- `uv run pytest` passes with regression coverage for filename fallback, run-summary paths, doctor warnings, and duplicate/no-op behavior
- `doctor --json` identifies incomplete archive/reconcile state without mutating project files
- docs clearly state what counts as complete, incomplete, duplicate, failed, and quarantined ingest state
- a downloaded Teams transcript from an earlier day does not silently use its download timestamp as a high-confidence meeting date
- an operator can supply or repair a known meeting date through the engine without hand-editing artifacts, signals, or ledger records

### Layer 2: Output Modes And Repair/Regenerate Workflows

Goal:

- support deliberate artifact variants from the same source without re-ingesting raw input or corrupting ledger state.

Status:

- contract-ready independent product slice
- contract finalized
- not implemented beyond the current `summary-plus-verbatim` default

Preconditions before implementation:

- done: `docs/artifact-contract.md` defines `summary` and `verbatim` section contracts
- done: `docs/artifact-contract.md` defines `repair-title` and `regenerate` semantics, including `title_repaired` and `artifact_regenerated` ledger snapshot shapes

Ready after prerequisites:

- complete `summary` mode using the same structured provider response and deterministic renderer without transcript output
- complete `verbatim` mode using deterministic transcript normalization and minimal provider use
- store mode-specific artifact entries under one source-level ledger snapshot
- add `repair-title` controlled rename command that updates artifact paths and ledger references without changing `meeting_id`
- add `regenerate` for already-processed sources using `_processed/` as the durable source of truth and `_cache/` only as an optimization
- add renderer golden tests for all supported modes

Decided UX and contract:

- title repair command is `meeting-ingest repair-title <meeting-id-or-source-sha> --title ... [--slug ...] [--json]`
- regeneration command is `meeting-ingest regenerate <meeting-id-or-source-sha> --mode summary|summary-plus-verbatim|verbatim ...`
- regeneration atomically replaces the selected current artifact and preserves old paths through append-only ledger history, not public stubs
- repaired filenames also rely on ledger history, not redirect/stub files
- `verbatim` mode is deterministic by default; any provider-assisted speaker repair must be explicit future behavior
- regeneration uses `_processed/` as durable source of truth and `_cache/` only as an optimization
- `regenerate --provider session` starts a fresh phase-1 handoff with a new `ingest_run_id` and cannot reuse prior request/response files

Acceptance criteria:

- one source hash can have `summary`, `summary-plus-verbatim`, and `verbatim` artifacts recorded in the same current ledger snapshot
- regenerating one mode does not delete or rewrite unrelated mode artifacts
- title repair changes filenames and ledger references while preserving `meeting_id`, signal IDs, processed archive path, and source hash identity
- duplicate/no-op ingest reports existing modes and missing modes clearly in JSON

### Layer 3: First-Class Session Inbox Automation

Goal:

- let the user ask an active agent to process the inbox once, while the engine handles the session-provider two-phase workflow predictably.

Status:

- engine/planner side mostly complete
- host adapter productization remains

Done:

- use `meeting_ingest.session_inbox.process_session_inbox` for active-agent wrappers that consume `ingest-inbox --provider session --json` results and complete each pending provider response
- reuse the existing per-file provider response handoff contract for batch orchestration
- avoid reminting requests after interruptions by completing existing ready responses first and skipping fresh phase 1 while unresolved handoffs remain
- expose the shared pending/stale/invalid session handoff planner through `status --json` and `doctor --json`
- report per-file success, failure, skipped duplicate, provider-response-needed, and incomplete-reconcile states
- keep archive, ledger, signal, markdown rendering, and reconcile behavior inside the engine

Remaining:

- productize host-specific extractor adapters
- add stale handoff cleanup/repair command if needed

Needs design decision:

- whether later work should keep all orchestration under `meeting-ingest ingest-inbox --provider session` or add host-specific wrappers above the engine command
- how much of the active agent extraction step can be automated in Codex, Claude Code, Supa Code, and T3 Code without fragmenting behavior
- whether the command should stop on first session extraction failure or continue to later files
- whether to propose a provider-handoff contract change to the current runtime file lifecycle: delete request/response files on success, retain them on failure, and let `doctor` warn on stale files

Acceptance criteria:

- a direct `_inbox/` file can be processed through a single documented agent command using `provider=session`
- batch JSON output includes one record per source with paths for request, response, markdown, signals, archive, and reconcile when applicable
- rerunning after interruption does not duplicate artifacts or lose the existing request/response binding
- `ingest-inbox` or its session wrapper never falls back to `mock` or a remote API provider when the user intended session extraction
- host wrappers do not read `_ledger.jsonl` directly to implement duplicate/no-op or completion logic; they consume engine-reported per-source state

### Layer 4: Provider And Wrapper Hardening

Goal:

- make provider behavior portable, auditable, and consistent across API-backed and subscription-backed workflows.

Status:

- core provider boundary is substantially implemented
- wrapper and provider productization remain

Done:

- verify and close remaining gaps in typed provider failure semantics, including provider failure exit `5`, provider validation exit `6`, and `ingest_failed` ledger records before primary artifacts are ready
- centralize provider response parsing and validation for API-backed responses and session response envelopes
- add provider metadata to artifacts and ledger snapshots, including provider host when session-backed
- keep privacy gates explicit for `allow_remote_provider` and `allow_session_provider`
- keep Codex and Claude Code skills in sync with repo-maintained sources when CLI behavior changes

Remaining:

- productize host wrappers beyond docs/skills
- improve prompt strategy and provider model provenance
- add additional provider adapters only when selected

Needs design decision:

- which API-backed provider should become the first production-quality remote adapter
- which host wrapper gets productized first after the local Codex/Claude Code workflow
- whether provider prompts should have separate fast/balanced/deep variants or one prompt with quality instructions
- how strict provenance should be for model name/version in subscription-backed host sessions where exact model metadata may not be available

Acceptance criteria:

- the same provider response payload shape can drive rendering, signals, ledger, archive, and reconcile regardless of provider path
- provider failures never move the source into `_inbox/_done/` and never emit successful primary artifacts
- privacy-denied provider use fails with a clear typed error and no transcript leaves the local workflow
- wrapper docs and installed skills match the repo source for normal inbox processing behavior

### Layer 5: Stakeholder Briefing And Playbook Guidance

Goal:

- turn source-grounded communication observations into durable stakeholder briefings and later evidence-grounded communication guidance without blocking primary meeting artifacts.

Status:

- accepted durable design baseline exists in `docs/stakeholder-playbook-design.md`
- schema 1.1 and Stakeholder Briefing V1 artifact-contract amendments passed focused review
- no Layer 5 implementation has started

The accepted design replaces the former monolithic playbook milestone with three independently testable increments.

#### Layer 5A: Generalized Provenance And Identity Foundation

Goal:

- make meeting and later non-meeting observations safe to aggregate across time and reviewed stakeholder identity.

Status:

- schema and artifact contract finalized
- implementation not started

Preconditions before implementation:

- done: focused review of the schema 1.1 and playbook artifact-contract amendments
- freeze annotated fixtures for compatibility, date semantics, signal identity, regeneration, and identity resolution
- coordinate provider payload, extraction prompt, and installed skill changes when the new observation taxonomy becomes user-facing

Ready after prerequisites:

- implement tolerant schema 1.0 readers and schema 1.1 writers
- implement generalized `source_id`, `source_kind`, and occurrence/acquisition/processing timing
- implement deterministic signal identity and regeneration supersession for new records
- implement the human-owned registry under `_playbook-state/`
- resolve identities at derivation time and emit unresolved/ambiguous identity candidates
- add status and doctor findings for registry conflicts and identity candidates

Acceptance criteria:

- existing schema 1.0 signals remain consumable
- reviewed aliases resolve retroactively without rewriting source observations
- ambiguous aliases never auto-merge
- occurrence, acquisition, and processing time remain distinct
- regenerated signals preserve stable identity where locators allow and surface supersession where they do not

#### Layer 5B: Stakeholder Briefing V1

Goal:

- deliver a useful deterministic pre-interaction briefing with no model required during derivation.

Status:

- accepted product and technical design exists
- artifact contract finalized
- implementation not started

Ready after Layer 5A:

- implement full deterministic rebuild over validated signal files
- write canonical profile JSON and rendered briefing Markdown into immutable generations
- implement the separate derivation ledger, atomic current-generation index, and input fingerprinting
- implement `playbook update`, `playbook show`, and concise briefing surfaces
- aggregate tracked asks and commitments, priorities, concerns, rationales, preferences, behaviors, interaction responses, freshness, and mechanical contradiction candidates
- implement append-only review controls for rejecting entries, resolving tracked items, suppressing bad observations, and correcting identity
- add stale/missing/failed playbook state to `status` and `doctor`

Acceptance criteria:

- every briefing entry cites qualified source observations
- full rebuilds are deterministic and identity corrections require no signal rewrite
- absent closure evidence is presented as unknown rather than `open`
- new eligible signals make the current generation visibly stale
- playbook failure never changes primary ingest success

#### Layer 5C: Playbook Guidance V1.1

Goal:

- add reviewable provider-assisted semantic judgment without allowing the provider to mint or upgrade source facts.

Status:

- accepted design exists
- derivation provider contract and implementation have not started

Preconditions before implementation:

- Stakeholder Briefing V1 and its review controls are working
- freeze the derivation request/response contract and approach-tag vocabulary
- add dedicated default-false API-backed and session-backed playbook-synthesis privacy gates

Ready after prerequisites:

- implement two-phase provider derivation with input fingerprint revalidation
- add semantic clustering, contextual scope, contradiction confirmation, positive-response patterns, and practical communication cues
- implement accept, reject, and tombstone review controls for guidance
- preserve deterministic briefings when synthesis is unavailable, denied, stale, or invalid

Acceptance criteria:

- one weak observation cannot become guidance
- provider output cannot invent facts, raise confidence, assign reviewed identity, hide contradictions, or resurrect disqualified evidence
- every cue has evidence, scope, caveats, confidence rationale, and review state
- failed synthesis leaves the deterministic briefing usable

### Layer 6: Migration And Existing Corpus Adoption

Goal:

- bring existing meeting artifacts into the new engine's world without pretending old outputs have the same guarantees as new outputs.

Status:

- not started

Ready when selected:

- add read-only corpus scan for existing markdown, signal JSONL, processed copies, inbox done files, and legacy ledger entries
- produce an adoption report that classifies files as adoptable, needs repair, ignored, or conflicting
- support ledger adoption records for existing source hashes only when enough provenance exists
- add migration docs for Hearst/Spelman-style corpora and dry-run-first workflows

Needs design decision:

- whether to mutate existing corpora in place, create a new clean meetings root, or maintain an adoption map
- how much legacy metadata is trusted when source hash or processed source copy is missing
- whether old generated summaries should be copied as legacy artifacts, regenerated from source, or left read-only
- whether migration should support project-specific one-off cleanup scripts

Acceptance criteria:

- migration dry run can inspect an existing corpus and produce a deterministic report without changing files
- adoption never marks legacy artifacts as V1-generated unless they pass the current artifact and ledger contract
- conflicting or missing provenance is surfaced as repair work, not silently normalized
- adopted records remain distinguishable from newly ingested records in ledger and status output

### Layer 7: Broader Communication Artifact Ingest

Goal:

- extend stakeholder memory beyond meeting transcripts while preserving the meeting engine as the source of truth for meeting artifacts.

Status:

- not started

The accepted design sequences broader communication sources by provenance and privacy complexity.

#### Layer 7A: Plain-Text Communication Pilot

Ready after Stakeholder Briefing V1:

- define a communication-neutral ingest surface for an email body or pasted message
- preserve sender, recipients, subject, sent time, thread boundaries, acquisition provenance, and privacy class
- emit generalized schema 1.1 observations without using the meeting artifact namespace
- rebuild stakeholder profiles across meeting and plain-text communication evidence

Acceptance criteria:

- meeting and plain-text evidence remain distinguishable
- both source kinds may support one qualified pattern without losing provenance
- remote/session permission for communication ingest is independent from meeting extraction permission
- non-meeting outputs never appear as generated meeting Markdown

#### Layer 7B: Image-Based Communication Ingest

Ready after Layer 7A evidence handling is trusted:

- add Teams-thread and text-message screenshots
- add OCR provenance and region-addressable evidence locators
- distinguish visible text, OCR output, and inferred thread structure
- define communication-event identity so screenshots and forwarded copies do not double-count one event

Acceptance criteria:

- every screenshot-derived observation links to an image region and records OCR/inference uncertainty
- duplicated representations of one communication event do not inflate recurrence thresholds
- privacy gates are source-kind specific

#### Layer 7C: Public And Social Sources

Ready only after policy review:

- define allowed uses for social posts and social profiles
- distinguish public self-description from inferred stakeholder traits
- preserve URL, capture time, visible content, and source volatility
- prohibit protected-trait, personality, vulnerability, and persuasion profiling

Needs design decision:

- exact Phase 7A email/message metadata and artifact contract
- source-specific OCR and evidence-location requirements for Phase 7B
- public-source retention, refresh, consent, and acceptable-use policy for Phase 7C

Acceptance criteria:

- public/social evidence remains visibly sourced, time-bounded, reviewable, and removable
- social-profile ingest cannot silently produce personality or persuasion guidance

### Layer 8: iQ Context Integration

Goal:

- make durable meeting outputs and communication signals available to project continuity without turning iQ Context into the ingest engine.

Status:

- iQ Context is used operationally for repo continuity
- product integration is not built

Ready after V1 done-process stabilization:

- emit optional iQ Context captures for high-value generated artifacts, decisions, assumptions, discoveries, and stakeholder signals
- add config gates so projects can opt into capture behavior
- store durable links from iQ Context captures back to meeting artifacts and signal records
- define `doctor` checks for missing or stale iQ Context captures only when integration is enabled

Needs design decision:

- which meeting sections qualify for automatic iQ Context capture
- whether capture happens during ingest, as derived post-output work, or through an explicit sync command
- how to avoid duplicating sensitive transcript content in project memory
- whether iQ Context integration should create docs under `docs/sessions/`, `docs/decisions/`, `docs/discoveries/`, and `docs/assumptions/` or only use `.iq-context/` captures

Acceptance criteria:

- iQ Context integration is disabled by default unless project config opts in
- enabled integration records concise, provenance-linked captures without copying whole transcripts
- failed capture sync does not fail primary ingest and is reported as derived-work status
- `iq-context find` can surface useful meeting-derived memory while the original meeting artifact remains the source of truth

### Roadmap Execution Rules

- Do not start a later layer by weakening contracts from an earlier layer.
- Keep all generated artifact shape changes documented before code changes.
- Prefer additive CLI behavior until migration and repair workflows are mature.
- Every roadmap layer needs at least one end-to-end fixture or dry-run verification path.
- User-facing agent skills and host wrapper docs must be updated in the same change as CLI behavior they depend on.
- For session-provider work, the canonical local workflow remains `provider=session` with `privacy.allow_session_provider = true`; do not use `mock` for real workflow tests.
- Where a host wrapper exists, it must consume engine-reported state instead of reimplementing duplicate/no-op, ledger, archive, reconcile, or request/response lifecycle logic.

## User Guidance Needed

The roadmap layer-specific decision lists above are authoritative. Ask the user before deciding:

- whether existing Hearst/Spelman corpora should be migrated, adopted read-only, or left outside the new ledger
- which host wrapper or API-backed provider should receive the next productization investment
- whether Layer 2 output modes should interrupt the active Layer 1 → 5A → 5B sequence
- exact deterministic cleanup or date-resolution rules when fixtures expose genuine ambiguity
- public/social-source retention, consent, and acceptable-use policy before Layer 7C

Already settled and no longer user questions:

- duplicate/no-op may complete unfinished archive/reconcile work
- file modification time is a low-confidence acquisition-oriented fallback, not a trustworthy meeting-occurrence source for downloaded historical transcripts
- Stakeholder Briefing V1 uses explicit deterministic rebuilds rather than running inside primary ingest
- reviewed project-local identity is required for stakeholder profiles

## Suggested Next Coding Session

After the current artifact-contract review is resolved and committed:

1. freeze the manual meeting-date override and controlled date-repair contract
2. add sanitized fixtures for the observed July 10/13 Teams VTT failure and explicit-header controls
3. implement occurrence candidate selection before meeting ID and provider-request minting
4. implement `--meeting-date` as the safe ambiguity escape hatch
5. add the controlled repair path for already-ingested artifacts
6. update `status`, `doctor`, run summaries, and documentation for low-confidence modification-time fallbacks

Then begin Layer 5A with schema 1.1 tolerant readers/writers and the reviewed identity registry.
