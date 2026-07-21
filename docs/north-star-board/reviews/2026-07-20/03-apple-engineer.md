# Apple Engineer Seat

## 1. Verdict

Meeting Ingest has a credible engineering core, but it is not ready to claim that it just works or to ship as a trustworthy self-serve product.

The strongest parts are deterministic extraction, request-bound provider validation, content-hash identity, typed failures, coarse project locking, append-only state, and explicit archive/reconcile recovery.

The trust boundary remains incomplete:

- the primary workflow requires orchestration the CLI cannot perform;
- several done-state writes are not transactional;
- `doctor` does not verify important content against recorded integrity metadata;
- exposed behavioral/privacy config is not honored;
- stale-lock recovery is manual;
- remote-provider reliability is unproven.

Engineering judgment: freeze broader expansion until one supported host passes fresh-project, real-meeting, failure-injection, retry, integrity, and recovery gates.

## 2. Evidence

### Architecture and correctness

- One pipeline centralizes extraction, provider validation, rendering, signals, ledger, archive, and reconcile (`src/meeting_ingest/pipeline.py:576-946`).
- Content identity is computed before extraction; duplicates repair archive/reconcile instead of regenerating (`src/meeting_ingest/pipeline.py:949-977`, `src/meeting_ingest/pipeline.py:1328-1410`).
- Session responses are bound to persisted meeting/run/source/transcript hashes, and run-ID path traversal is rejected (`src/meeting_ingest/provider_handoff.py:62-97`, `src/meeting_ingest/provider_handoff.py:168-196`).
- Provider parsing aggregates structural errors and rejects provider-supplied enriched identity fields (`src/meeting_ingest/provider_json.py:24-177`).
- Signals use temporary replacement, but meeting artifacts use direct `write_text` (`src/meeting_ingest/signals.py:40-64`; `src/meeting_ingest/pipeline.py:1314-1325`).
- Signals and Markdown are written before the primary-ready ledger append; archive/reconcile and completed append follow (`src/meeting_ingest/pipeline.py:801-899`).
- A primary ledger failure intentionally leaves orphan Markdown/signals; archive or reconcile failure leaves a recoverable pending snapshot (`tests/test_pipeline_ingest.py:502-580`).
- Date repair mutates artifact and signals before appending its ledger event; interruption after partial mutation is not covered (`src/meeting_ingest/pipeline.py:283-331`; `tests/test_repair_date.py:108-138`).

### Data integrity and observability

- Ledger reads tolerate malformed lines and report issues; appends do not explicitly flush/fsync (`src/meeting_ingest/ledger.py:57-108`).
- Signal state records a fingerprint, but `doctor` does not compare it with current bytes; meeting artifacts have no content fingerprint (`src/meeting_ingest/pipeline.py:843-868`; `src/meeting_ingest/doctor.py:91-196`).
- `doctor` checks many important states, but advisories and corruption share one exit-1 issue class (`src/meeting_ingest/doctor.py:54-117`, `src/meeting_ingest/pipeline.py:1063-1074`).
- Typed phases, codes, exit codes, recoverability, warnings, and JSON paths are strong. No issue was found with the basic error taxonomy.

### Failure recovery

- Lock acquisition is atomic (`src/meeting_ingest/locking.py:46-59`).
- Stale lock detection exists, but acquisition rejects every existing lock and no guarded recovery command is present (`src/meeting_ingest/locking.py:52-55`, `src/meeting_ingest/locking.py:81-104`).
- Session handoff files survive validation failure and are deleted only after success (`src/meeting_ingest/pipeline.py:721-774`).
- Stale responses for already-ingested sources are not consumed, which is safe but can leave residue (`tests/test_pipeline_ingest.py:1465-1484`).
- The uncommitted playbook cleanup work appears guarded but is not released capability.

### Security and privacy

- Remote and session gates are separate. No issue was found with that separation (`src/meeting_ingest/config.py:27-30`).
- Request binding and response-path containment are sound in the examined envelope path.
- `auto_init`, `cache_normalized_transcript`, and `reconcile_after_success` are parsed/documented but repository search shows no runtime consumer. Session requests persist transcripts and success always archives/reconciles (`src/meeting_ingest/config.py:42-83`; `src/meeting_ingest/pipeline.py:663-681`, `src/meeting_ingest/pipeline.py:870-899`). This is a direct contract gap.
- Configured paths are joined and created without containment validation (`src/meeting_ingest/paths.py:31-48`, `src/meeting_ingest/paths.py:99-115`).
- Provider scalar strings lack control-character/newline constraints, while YAML quoting escapes only double quotes (`src/meeting_ingest/provider_json.py:51-56`; `src/meeting_ingest/render.py:59-83`, `src/meeting_ingest/render.py:242-244`).
- Extractors have no input/expanded-size limits (`src/meeting_ingest/extract.py:94-156`).
- Transcript-bearing requests, verbatim artifacts, archives, and signals have no documented product retention model.

### Portability and provider risk

- Basic Python packaging is portable and dependency-light (`pyproject.toml:5-17`). No issue was found there.
- No published-package, upgrade, or clean consumer-install evidence exists.
- The Anthropic adapter has one fixed request with no retry, backoff, rate-limit handling, or live acceptance evidence (`src/meeting_ingest/providers/anthropic.py:16-69`).

## 3. What is working

- Deterministic extraction for all three formats has typed failures.
- Request-side hashes prevent responses from applying to changed sources.
- Provider failures occur before primary artifacts; tests show no archive/reconcile side effects.
- Signal writes are individually atomic and schema-validated.
- Pending archive/reconcile state is explicitly recoverable.
- Duplicate inputs are content-based and safely reconcile re-dropped inbox files.
- Successful session completion adopts persisted request identity and cleans handoffs only after completion.
- Playbook generations, fingerprints, append-only derivation, atomic index writes, and index repair are technically strong, though live product value is unproven.
- Unhappy-path test breadth is meaningful evidence of engineering quality.

## 4. Gaps and risks

1. **High — Done is not atomic.** Artifact writing is non-atomic, primary ledger failure leaves untracked outputs, and date repair mutates multiple files before durable commit.
2. **High — Integrity claims exceed verification.** Signal fingerprints are not checked and artifacts lack recorded fingerprints.
3. **High — Exposed config is inert.** Behavioral and retention-looking keys do not change runtime behavior.
4. **High — Primary workflow is not autonomous.** A protocol exists, not a finished host adapter.
5. **Medium-high — Crash recovery can deadlock behind a stale lock.**
6. **Medium — Provider content can break artifact structure.**
7. **Medium — Diagnostic severity is not modeled.**
8. **Medium — Project-local path safety is assumed.**
9. **Medium — Remote provider robustness is below production posture.**
10. **Low-medium — Resource bounds and privacy lifecycle are undefined.**
11. **Medium — Dirty-worktree capability must not be represented as released.**

## 5. Recommendations in priority order

1. Define and pass a **Core Trust Gate** on one host/install/provider path across real `.txt`, `.vtt`, and `.docx`, including capture, duplicate redrop, and retry with no source inspection or JSON repair.
2. Make ingest and date repair interruption-safe using staged outputs, validation, documented commit/recovery semantics, and failure injection after every mutation/append.
3. Add integrity verification to `doctor`: artifact hashes, signal fingerprint checks, front-matter/ledger identity checks, and modified/malformed/untracked distinctions.
4. Remove, implement, or explicitly mark inert config; audit all three inactive keys. Privacy-looking controls must not be aspirational.
5. Provide safe stale-lock recovery with ownership/liveness checks and an explicit guarded command.
6. Harden provider-to-artifact boundaries with scalar normalization/validation, safe YAML serialization, limits, and hostile-input tests.
7. Introduce diagnostic severity and documented exit thresholds.
8. Constrain configured paths to the project/meetings root unless explicitly opted out.
9. Select a provider posture: session-only for the bounded release, or harden/UAT the remote adapter.
10. Document privacy and retention for every raw, cached, archived, generated, and transmitted artifact.
11. Complete review and commit cleanup recovery before claiming it.

## 6. What to stop, defer, or simplify

- Stop expanding Stakeholder Briefing and Guidance until the core trust gate passes.
- Defer broader sources, extra providers, global identity, deeper iQ integration, and extra modes unless explicitly part of the chosen first workflow.
- Stop advertising config keys with no effect.
- Simplify release to one user, host, provider path, three inputs, and one output mode.
- Treat playbook as experimental until live reviewed profiles exist.
- Do not count the uncommitted cleanup slice as complete.
- Build one coherent recovery model before adding more isolated recovery commands.

## 7. Release decision

**No-go** for general release or a just-works claim.

**Conditional go** for maintainer dogfood/engineering preview with explicit limits: technical owner, one active-agent host, operator-mediated session flow, summary-plus-verbatim only, local retention responsibility, no health severity model, and possible manual recovery after interruption.

Minimum engineering exit gate:

1. Fresh consumer install succeeds.
2. One host completes all three formats without source inspection.
3. Invalid output has no primary side effects and corrects in one validation cycle.
4. Failure injection at every commit boundary yields no visible state or diagnosed one-command recovery.
5. Duplicate redrop and repeated phase two are safe no-ops.
6. `doctor` distinguishes advisories and reports no trust-invalidating state after success.
7. Artifact and signal bytes verify against committed integrity metadata.
8. Privacy/cache controls match documentation.
9. Killed processes do not leave unrecoverable locks.
10. One post-fix external UAT passes.

## 8. Confidence and unresolved questions

Confidence is high based on direct code, tests, package, worktree, and history inspection.

Unresolved questions:

- What exactly should `cache_normalized_transcript` control?
- Is `reconcile_after_success = false` supported or obsolete?
- Is project config fully trusted or clone-provided/untrusted?
- Are meeting artifacts intentionally user-editable after ingest? If yes, byte integrity needs a different contract.
- What is today's supported stale-lock recovery?
- Which host and adapter are the first production target?
- What transcript size, cost, and duration limits are acceptable?
- Should `doctor` fail for dates and missing optional playbook state?
- Is the immutable old-date meeting ID after date repair the intended user-facing model?
