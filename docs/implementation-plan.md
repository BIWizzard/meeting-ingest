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
meeting-ingest ingest <source> [--mode summary-plus-verbatim] [--provider mock|anthropic] [--quality fast|balanced|deep] [--json]
meeting-ingest ingest-inbox [--json]
meeting-ingest doctor
meeting-ingest status
meeting-ingest reconcile
```

`ingest` may auto-init only if the behavior is explicitly configured or passed as a flag. Default v1 recommendation: `ingest` should fail with a clear message if no config/layout exists, while `init` remains easy.

This auto-init decision should be confirmed before implementation.

`reconcile` is included in v1 as a narrow recovery command for sources whose primary artifacts are ready but archive/reconcile did not complete.

`ingest-inbox` should process files directly under `_inbox/` one at a time and skip `_inbox/_done/`. Unsupported formats should be reported as per-file failures using normal ingest/quarantine behavior. It should return a batch JSON summary with per-source results and continue processing after recoverable per-file failures.

Future enhancement: add controlled parallelism for inbox ingestion, such as `--jobs`, or harness-level fan-out to multiple focused sub-agents. This should wait until the engine has explicit coordination for shared ledger writes, lock behavior, provider rate limits, and per-file reporting.

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
- Host/session-backed providers let an active agentic harness produce the same structured provider response through the current subscription-backed session.

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
- handoff contract for a sub-agent to provide structured provider output back to the engine
- CLI or wrapper mechanism for ingesting with externally supplied provider JSON
- Supa Code / T3 Code / Claude Code / Codex usage notes
- tests proving externally supplied provider JSON passes the same schema, renderer, signal, ledger, archive, and reconcile flow

Lead review:

- verify subscription-backed workflows do not require API keys
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

## User Guidance Needed

Ask the user before deciding:

- whether `ingest` should auto-init or require explicit `init`
- which real provider should be first
- whether remote provider use should default to disabled for privacy
- which host/session-backed provider path should be implemented first
- whether existing Hearst/Spelman corpora should be migrated, adopted read-only, or ignored for v1
- exact deterministic cleanup rules if the first fixtures expose ambiguity
- whether file modified date is acceptable as the v1 fallback effective date
- whether duplicate/no-op should complete unfinished archive/reconcile work automatically
- whether path discovery should use config walk-up from current working directory

## Suggested First Coding Session

Start with Milestone 1.

Concrete first tasks:

1. create Python packaging scaffold
2. add CLI with `init`, `ingest`, `doctor`, `status` stubs
3. add `pipeline.py` stub called by `cli.py`
4. add `errors.py` and `clock.py`
5. implement config model and path layout creation
6. add tests for `init`, error mapping, and deterministic clock behavior

Do not implement provider calls or artifact rendering before the package/config/path foundation is working.
