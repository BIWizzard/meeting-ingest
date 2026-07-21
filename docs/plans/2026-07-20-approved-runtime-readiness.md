# Just Works Continuity Track 1: Approved Runtime And Pre-Meeting Readiness Implementation Plan

**Status:** Approved for implementation by owner direction on 2026-07-20.

**Goal:** Before a transcript is processed, identify the exact Meeting Ingest build and Claude Code workflow that will run, compare them with the consumer's approved immutable pin, block unsafe or ambiguous client execution, and preserve reconstructable runtime provenance through every output.

**Milestone placement:** This is Track 1 of Just Works Continuity and precedes further release-quality HTV dogfooding and the Track 3 Semantic Integrity Guardrails plan. It does not adopt or mutate HTV/Spelman history, implement Stakeholder Briefing, broaden the reference host, or silently upgrade a consumer.

**Approved policy basis:** The owner has already approved one exact immutable consumer build tied to a reviewed commit and packaged build, explicit updates, Claude Code as the reference host, a maintainer-only private alpha, block-by-default editable client execution, and an explicit visibly marked development override. See `docs/north-star-board/reviews/2026-07-20-reconvened/09-owner-decisions.md`.

**Architecture:** Build from an exact Git archive, inject immutable source identity into the wheel, and emit an external build receipt containing the final wheel digest. A consumer runtime pin records the approved build, receipt, executable, channel, and Claude workflow hashes. Runtime inspection detects executable/module paths, install mode, package integrity, editable source commit and dirty state, and workflow compatibility. `readiness` combines that result with project config, privacy, active handoff/integrity health, and separately classified history warnings. Every write-capable engine entry point calls the same guard before acquiring the project lock or writing files. A deliberate development override allows work but marks the run, handoff, artifact, ledger, and derived output as development-generated.

**Dogfood evidence:** Capture `cap_20260720T165222Z_593ed953` proves the current ambiguity. `/Users/kmgdev/.local/bin/meeting-ingest` is a frozen snapshot matching commit `3bc917de8c6072239848ed190c4c45889d6cf227` but is silently replaced when `main` moves; HTV `.venv/bin/meeting-ingest` is editable and imports the live Meeting Ingest working tree. The Claude skill currently runs `uv run meeting-ingest`, which selects the HTV editable executable. Both identify only as `0.1.0`.

## Approved Outcomes

- One immutable approval unit consists of an embedded build identity plus an external receipt binding it to one exact wheel SHA-256.
- Each consumer records one exact approved runtime pin; a channel may announce a newer approved build but never changes that pin or installation.
- Claude Code invokes the canonical approved executable explicitly, never through ambiguous `uv run` or ambient PATH resolution.
- Readiness reports `Ready`, `Ready with history warnings`, `Development override`, or `Blocked` with stable JSON reasons.
- A fresh ingest is allowed with history warnings only when runtime, workflow, privacy, active handoff, and current-write integrity are safe and the excluded historical scope is explicit. Such a result does not satisfy the full Continuity exit gate.
- Editable or otherwise unverifiable client execution is blocked unless the operator supplies an explicit non-empty development-override reason.
- Development execution is never reported as Ready and cannot produce output indistinguishable from an approved build.
- Phase 1 and phase 2 of a session handoff must run under the same build, workflow contract, and runtime mode.
- Updates are build, review, publish, install, and pin operations performed explicitly; Git hooks never reinstall consumer tooling.

## Non-Goals And Boundaries

- Do not mutate, repair, regenerate, adopt, or clean HTV/Spelman meeting history in this track.
- Do not make all legacy doctor findings next-meeting blockers.
- Do not treat semantic version `0.1.0`, PATH order, a Git branch name, editable metadata, or a clone-local hook as immutable identity.
- Do not embed the final wheel SHA-256 inside the wheel; that is self-referential. Bind the embedded identity to the wheel digest through the external receipt.
- Do not add automatic install/update behavior to `readiness`, `status`, `doctor`, agent skills, shell startup, or Git hooks.
- Do not require network access, a public registry, signing infrastructure, or multi-user release administration for the private-alpha implementation.
- Do not delete the HTV virtual environment. The eventual cutover removes only its editable `meeting-ingest` distribution after rollback evidence is recorded.
- Do not claim the historical corpus is qualified merely because readiness permits a safe fresh ingest.

## Approval Unit And File Contracts

### Embedded build identity

Every packaged build contains immutable generated metadata:

```json
{
  "schema_version": "1.0",
  "semantic_version": "0.1.0",
  "build_id": "meeting-ingest-0.1.0-g3bc917de8c60-s0123456789ab",
  "source_commit": "3bc917de8c6072239848ed190c4c45889d6cf227",
  "source_tree_sha256": "sha256:...",
  "workflow_contract_version": "claude-code-session-v1",
  "build_kind": "approved-candidate"
}
```

`source_tree_sha256` uses a frozen algorithm over sorted POSIX paths and bytes from the exact Git archive. It includes `pyproject.toml`, packaged Python sources, the durable Claude skill, the durable Claude session-provider agent, and their governing handoff/workflow contracts. It excludes `.iq-context`, generated artifacts, untracked files, local runtime state, and build timestamps.

`build_id` is deterministic: `meeting-ingest-{semantic_version}-g{first 12 source-commit hex}-s{first 12 source-tree-sha256 hex}`. It contains no wall-clock value, build-machine value, random value, or receipt-derived value. `SOURCE_DATE_EPOCH` is the selected commit timestamp and affects archive/wheel normalization only, not identity derivation.

An editable source checkout carries committed development defaults (`build_id = "development"`, no approved commit/tree claim). Runtime inspection supplements those defaults with live Git commit and dirty state; it never promotes them to an approved build identity.

### External approved-build receipt

The build command emits a receipt after the wheel exists:

```json
{
  "schema_version": "1.0",
  "build": {
    "semantic_version": "0.1.0",
    "build_id": "meeting-ingest-0.1.0-g3bc917de8c60-s0123456789ab",
    "source_commit": "3bc917de8c6072239848ed190c4c45889d6cf227",
    "source_tree_sha256": "sha256:...",
    "wheel_filename": "meeting_ingest-0.1.0-py3-none-any.whl",
    "wheel_sha256": "sha256:..."
  },
  "workflow": {
    "contract_version": "claude-code-session-v1",
    "claude_skill_template_sha256": "sha256:...",
    "claude_agent_sha256": "sha256:..."
  },
  "verification": {
    "source_commit_reviewed": true,
    "full_suite_passed": true,
    "reproducible_wheel_verified": true
  },
  "approved_by": "owner",
  "approved_at": "2026-07-20T00:00:00Z"
}
```

Approval is refused if the commit is not exact, tests are not recorded green, the wheel is not reproducible, required workflow files are missing, or the receipt does not match the wheel and embedded metadata. The receipt has its own external SHA-256 recorded by channel and consumer pin; it does not contain its own digest.

### Consumer runtime pin

Each consumer stores `_local/project-context/meetings/meeting-ingest-runtime.toml`:

```toml
schema_version = "1.0"
channel = "private-alpha"
approved_build_id = "meeting-ingest-0.1.0-g3bc917de8c60-s0123456789ab"
approved_source_commit = "3bc917de8c6072239848ed190c4c45889d6cf227"
approved_source_tree_sha256 = "sha256:..."
approved_wheel_sha256 = "sha256:..."
approved_receipt_sha256 = "sha256:..."
approved_executable = "/Users/kmgdev/.local/bin/meeting-ingest"
workflow_contract_version = "claude-code-session-v1"
claude_skill_template_sha256 = "sha256:..."
installed_claude_skill_sha256 = "sha256:..."
claude_agent_sha256 = "sha256:..."
approved_at = "2026-07-20T00:00:00Z"
```

The separate pin file can be loaded even when the normal project configuration is missing or invalid. `approved_executable` is intentionally machine-local in the maintainer-only alpha. The durable skill remains a portable template containing exactly one strict approved-executable marker, `{{MEETING_INGEST_APPROVED_EXECUTABLE}}`. Installation renders that marker to the consumer's absolute executable path; the receipt hashes the durable template and the consumer pin hashes both the template and rendered installed copy. No other template substitution is permitted. Portability beyond this controlled rendering is deferred.

### Local private-alpha channel

The explicit publish command maintains a local channel manifest under the Meeting Ingest application-data directory. It names the latest approved receipt/build but does not install it or rewrite consumer pins. Readiness may report `update_available: true` when the channel is newer than the consumer pin. Missing/unreadable channel metadata is advisory when the running build matches the pin; it is never permission to switch builds.

## Readiness Contract

CLI surface:

```text
meeting-ingest runtime inspect [--root <path>] [--json]
meeting-ingest readiness [--root <path>] [--host claude-code] [--development-override <reason>] [--json]
meeting-ingest runtime pin --receipt <path> --root <path> [--json]
meeting-ingest runtime update-check --root <path> [--json]
```

Read-only `runtime inspect`, `readiness`, `runtime update-check`, `status`, and `doctor` never require an approved pin and never mutate install, consumer, corpus, cache, or iQ state.

### Runtime inspection fields

- resolved command/executable path;
- Python executable and imported `meeting_ingest` module path;
- semantic version, build ID, source commit, source-tree digest, workflow-contract version;
- install mode: `approved_frozen`, `frozen_unapproved`, `editable`, or `unknown`;
- distribution metadata and `direct_url.json` classification;
- installed distribution `RECORD` integrity status;
- editable source root, live Git commit, dirty state, and Git inspection status when applicable;
- build receipt path/hash and whether it matches embedded metadata;
- consumer pin path/hash and every field comparison;
- installed Claude skill/agent paths, hashes, and compatibility;
- channel and update availability;
- runtime mode: `approved`, `development`, or `unverified`.

Unknown install mode, inaccessible editable Git state, invalid package `RECORD`, or mismatched receipt is fail-closed for client writes.

### Verdicts

- `Ready` / JSON `ready`: exact frozen runtime, receipt, executable, consumer pin, workflow, privacy/config, active state, and current-write integrity all match; no history warnings.
- `Ready with history warnings` / JSON `ready_with_history_warnings`: the same next-meeting safety gates pass, while explicitly enumerated legacy/history/adoption issues remain excluded.
- `Development override` / JSON `development_override`: a non-empty reason explicitly authorizes this invocation; client approval is not claimed and all resulting provenance is development-marked.
- `Blocked` / JSON `blocked`: one or more next-meeting safety gates fail and no valid development override authorizes the write.

`Ready`, `Ready with history warnings`, and an explicitly requested `Development override` return exit `0`. `Blocked` uses a new stable runtime-readiness exit code. Human output leads with the verdict and the single most actionable remediation; JSON preserves all categorized findings.

### Finding categories

**Runtime blockers:** executable mismatch, build/pin/receipt mismatch, editable without override, unknown install mode, dirty/uninspectable development source, package integrity failure, workflow hash/contract mismatch.

**Project blockers:** invalid/missing runtime pin for write operations, invalid normal config, disabled required privacy gate, active conflicting lock, invalid/pending response that must be resolved, provenance-aware/current-era corruption that can affect the next write, or unsafe path configuration.

**History warnings:** legacy ledger/signal formats outside the current write set, low-confidence historical dates, historical identity gaps, missing optional playbook outputs, and unqualified/adoption-pending corpus classes.

**Advisories:** newer approved channel build available, channel unavailable, optional provider absent, or other non-blocking information.

Every finding has stable `code`, `category`, `severity`, `message`, `path` when relevant, and `remediation` fields. Readiness must not dump one issue per legacy record in normal human output; it groups counts and provides detailed JSON.

## Runtime Enforcement Contract

- All write-capable public pipeline/playbook entry points call one shared runtime guard before lock acquisition or side effects; CLI-only enforcement is insufficient.
- Write-capable operations include `init`, `provider-request`, `ingest`, `ingest-inbox`, `session-inbox`, `repair-date`, `reconcile`, playbook rebuild/mutations/repair/cleanup, and future regeneration/migration commands.
- Approved bootstrap is two explicit operations: `runtime pin --receipt <path> --root <path>` may create only the runtime-pin parent and pin, then `init --root <path>` creates normal project configuration under that verified pin. `init` does not accept or interpret receipts. Editable `init` requires a development override.
- Unit tests inject an approved frozen runtime descriptor through fixtures; production code never trusts `PYTEST_CURRENT_TEST`, a generic environment toggle, or caller-controlled “testing” metadata.
- A development override is a global CLI option with a required non-empty reason and an equivalent typed API value. It is invocation-scoped, not a persistent config escape hatch.
- The override does not bypass malformed configuration, unsafe paths, response/source identity mismatch, package corruption, or other integrity failures unrelated to install approval.
- No-op and failure summaries still report runtime mode/build so the attempted execution is reconstructable.

### Session handoff binding

Phase 1 provider requests persist a canonical runtime-provenance object and its SHA-256. The response contract requires the provider response to echo the provenance hash. Phase 2 recomputes current runtime provenance and requires exact equality for build ID, source/tree identity, workflow contract, install/runtime mode, and development-override identity.

If the approved build changes while a handoff is pending, phase 2 returns `runtime_handoff_mismatch` before rendering or cleanup. The operator must finish with the original approved build or explicitly abandon the handoff and mint a fresh request under the new build. Phase 2 never silently adopts a newer runtime.

## Durable Provenance Contract

Use one canonical `RuntimeProvenance` payload across surfaces:

```json
{
  "semantic_version": "0.1.0",
  "build_id": "meeting-ingest-0.1.0-g3bc917de8c60-s0123456789ab",
  "source_commit": "3bc917de8c6072239848ed190c4c45889d6cf227",
  "source_tree_sha256": "sha256:...",
  "install_mode": "approved_frozen",
  "runtime_mode": "approved",
  "workflow_contract_version": "claude-code-session-v1",
  "development_override_reason": null
}
```

Persist it in:

- every run summary, including read-only checks, no-ops, and failures;
- provider request/response handoffs;
- meeting artifact front matter;
- source-ledger snapshots;
- playbook derivation ledger, generation manifest, index, profiles, and briefings;
- repair/regeneration snapshots when those commands later ship.

Signals remain reconstructably bound through `ingest_run_id`, `meeting_id`, source identity, a provenance-reference hash, and the source ledger rather than duplicating the full runtime-provenance payload into every signal record. The artifact contract must state this indirection explicitly and doctor must report a missing, ambiguous, or mismatched provenance link for provenance-aware signals.

### Provenance-era boundary

Existing records cannot be separated safely by dates or file location, and historical signals already use signal schema `1.1` while historical ledger records use ledger schema `1.0`. Track 1 therefore freezes an explicit structural cutover:

- provenance-aware ledger snapshots use ledger schema `2.0` and require `runtime_provenance_schema = "1.0"` plus the canonical payload;
- ledger schema `1.0` records are legacy-readable and missing runtime provenance is a history warning;
- provenance-aware signals use signal schema `1.2` and require `runtime_provenance_ref` containing the producing ledger-record ID and producer runtime-provenance SHA-256; that reference must resolve to exactly one ledger `2.0` producer snapshot;
- signal schemas `1.0` and `1.1` remain legacy-readable. A missing ledger link for those legacy schemas is a history warning unless independent provenance-aware evidence proves current corruption;
- artifact and derived-output contracts receive explicit provenance-aware schema/version markers; missing provenance is a blocker only when that marker or a linked ledger `2.0` snapshot declares the output current;
- no existing file is rewritten merely to add a marker. Adoption or regeneration is a later, separately approved operation.

Write-time validation must confirm every just-written signal `1.2` record resolves to its pre-minted producer ledger `2.0` snapshot before the run can report success. A later complete snapshot that did not modify signals carries the prior producer reference without becoming a second producer. A repair that rewrites signal bytes mints a new producer reference. Standing doctor starts from each source's latest valid manifest and follows its producer reference in both directions. This catches current orphans without treating historical snapshots as competing producers or an unlinked legacy signal `1.0`/`1.1` as current.

This discriminator is structural and immutable. Timestamps, semantic package versions, and “file existed before deployment” heuristics are not accepted as provenance-era evidence.

Development output uses `runtime_mode: development` and preserves the override reason. It may never carry `approved_frozen`, `Ready`, or an approved-client claim.

## Task 1: Freeze Approved Runtime, Readiness, And Provenance Contracts

**Files:**

- Modify: `docs/artifact-contract.md`
- Modify: `docs/provider-handoff-contract.md`
- Modify: `docs/implementation-plan.md`
- Modify: `DECISIONS.md`
- Modify: `CURRENT-QUESTIONS.md`

- [x] Freeze the embedded build, receipt, consumer pin, channel manifest, runtime inspection, readiness verdict/finding, development override, handoff binding, and durable provenance shapes above.
- [x] Freeze the source-tree fingerprint algorithm and included path set.
- [x] Freeze deterministic `build_id` derivation and the rule that it contains no wall-clock or machine-local input.
- [x] Freeze the new runtime-readiness exit code and stable blocker codes.
- [x] Record the decision that safe fresh ingest may be `Ready with history warnings` only when excluded history is explicit and no next-write gate depends on it; this does not satisfy the Continuity exit gate.
- [x] Freeze signal schema `1.2` as a compact ledger-linked provenance reference rather than duplicating the runtime payload in each signal.
- [x] Freeze the provenance-era boundary: ledger schema `2.0` and signal schema `1.2` are provenance-required; ledger `1.0` and signal `1.0`/`1.1` are legacy-readable.
- [x] Freeze separate operation and signal-generation provenance: later complete snapshots carry the existing producer reference, while any operation that rewrites signals mints a new producer ledger record.
- [x] Freeze the portable Claude skill-template marker and controlled installed-skill rendering contract.
- [x] Remove resolved runtime-policy questions from `CURRENT-QUESTIONS.md`; retain corpus adoption and generated-output mutation questions.

**Contract checkpoint:** Approved on 2026-07-20 after independent review and resolution of the materialization-producer lineage issue. Later tasks must not invent alternate field names, identity algorithms, override behavior, readiness categories, or producer-lineage semantics.

## Task 2: Produce Reproducible Approved Builds And Receipts

**Files:**

- Create: `src/meeting_ingest/_build_info.py` with development defaults
- Create: `src/meeting_ingest/runtime_build.py`
- Create: `scripts/build-approved-runtime.py`
- Create: `tests/test_runtime_build.py`
- Modify: `pyproject.toml`
- Modify: `.gitignore`

- [x] Build from `git archive <exact-commit>` in a validated temporary staging directory; never copy the dirty working tree.
- [x] Begin with a determinism feasibility spike against the current setuptools backend: build the same minimal archived commit twice in isolated paths and compare wheel bytes, `RECORD` ordering, modes, and ZIP metadata. Record the result before implementing downstream runtime tasks.

**Determinism spike (2026-07-21):** Two isolated `git archive` builds of commit `3bc917de8c6072239848ed190c4c45889d6cf227`, with `SOURCE_DATE_EPOCH=1784517600`, produced byte-identical wheels with SHA-256 `829cd26c071410fb63c3e47b6c55069d75f2d80f6468b7c97296ca987ccb7fbc`. Both wheels contained 38 entries in the same order, a final 38-row `RECORD`, the same regular-file modes (`0644` and setuptools-generated `0664` for `RECORD`), and one normalized ZIP timestamp (`2026-07-20T03:20:00Z`). This same-machine, same-toolchain spike proves timestamp and staging normalization for the maintainer-only alpha; it does not claim cross-platform or cross-toolchain reproducibility. Generated build identity is not part of this baseline spike and is verified by the implementation below.
- [x] Compute the frozen source-tree digest before injecting generated build metadata.
- [x] Use `SOURCE_DATE_EPOCH` from the commit timestamp and normalize wheel inputs so two builds of the same commit produce identical wheel SHA-256 values.
- [x] Inject build identity and workflow contract metadata only into the staging tree.
- [x] Run the full test suite against the exact staged source before approving the receipt.
- [x] Build the wheel, inspect its metadata/contents, verify embedded identity, compute wheel SHA-256, and emit the receipt.
- [x] Build twice in isolated directories and require identical wheel hashes before `reproducible_wheel_verified: true`.
- [x] If byte-identical wheels cannot be demonstrated with normalized setuptools inputs, stop before Tasks 3-10 and return to the owner with evidence and a revised build-backend or approval-unit proposal; never weaken the receipt silently. The stop path is implemented; the feasibility and end-to-end rehearsals did not trigger it.
- [x] Refuse uncommitted commit identifiers, missing tracked inputs, unexpected archive paths, unreviewed/test-failed status, or receipt/wheel mismatch.
- [x] Keep wheels/receipts out of routine source control; commit only release/channel metadata intentionally approved by the owner.

**Implementation verification (2026-07-21):** After independent review and failure-path hardening, the focused suite passed with 37 tests and the full working-tree suite passed with 268 tests. A separate end-to-end rehearsal created a synthetic exact Git commit, ran the full suite from its injected archive, built twice in isolated directories, verified both wheels, and emitted a matching receipt successfully. The output contained only the final wheel and receipt with no pending residue. The rehearsal artifacts remained under `/tmp` and are not release or approval artifacts.

**Focused verification:**

```bash
uv run pytest tests/test_runtime_build.py -q
```

## Task 3: Inspect Runtime, Install Mode, Integrity, And Dirty State

**Files:**

- Create: `src/meeting_ingest/runtime.py`
- Modify: `src/meeting_ingest/__init__.py`
- Modify: `src/meeting_ingest/errors.py`
- Modify: `src/meeting_ingest/run_summary.py`
- Modify: `src/meeting_ingest/cli.py`
- Test: create `tests/test_runtime.py`
- Test: modify `tests/test_cli_scaffold.py`

- [x] Implement frozen dataclasses for build identity, install evidence, workflow evidence, consumer pin, runtime provenance, readiness finding, and readiness result.
- [x] Read installed distribution metadata and `direct_url.json` without assuming `pip` or `uv` generated it.
- [x] Verify installed files against distribution `RECORD` hashes when available; missing/invalid integrity evidence is blocked for approved mode.
- [x] Detect editable installs from standards metadata and confirm imported module location.
- [x] For editable installs, resolve the source repository, full commit, dirty state including untracked files, and inspection errors without modifying Git state.
- [x] Report the resolved invoked command, Python, module, distribution, receipt, pin, and workflow paths.
- [x] Implement `runtime inspect` as read-only and usable outside an initialized Meeting Ingest project.
- [x] Add tests for approved wheel, non-editable local-directory install, editable clean/dirty, missing Git, mismatched module/distribution, corrupted `RECORD`, missing receipt, unknown mode, and human/JSON output.

**Implementation verification (2026-07-21):** After independent review and follow-up hardening, focused runtime/CLI coverage passed with 32 tests and the full repository-root suite passed with 292 tests. Inspection was also exercised directly against the live editable installation and an uninitialized consumer root, returning development evidence and structured blockers without creating project state. A full-suite invocation from the `tests/` working directory reached one unrelated pre-existing cwd-sensitive golden-fixture path in `test_provider_render.py`; the normal repository-root suite remains green.

## Task 4: Load Consumer Pins, Publish Channels, And Check Updates Explicitly

**Files:**

- Create: `src/meeting_ingest/runtime_config.py`
- Create: `src/meeting_ingest/runtime_release.py`
- Create: `scripts/publish-approved-runtime.py`
- Modify: `src/meeting_ingest/cli.py`
- Test: create `tests/test_runtime_config.py`
- Test: create `tests/test_runtime_release.py`

- [x] Strictly parse the separate runtime pin before normal project config; reject unknown keys, malformed hashes, partial identity, and relative approved-executable paths.
- [x] `runtime pin --receipt` verifies the receipt, wheel hash when the wheel is present, current embedded build, installed receipt, executable, and workflow files before atomically writing the pin.
- [x] Permit `runtime pin --receipt` to bootstrap only the runtime-pin parent directory and pin in an otherwise uninitialized root; it must not create normal config, corpus, inbox, cache, ledger, or iQ state.
- [x] Publishing copies an approved wheel/receipt into the local private-alpha release store and atomically advances the channel manifest; it never installs or pins a consumer.
- [x] `runtime update-check` compares channel, consumer pin, installed build, and receipt without mutating any of them.
- [x] A newer channel build is advisory when the current approved pin still matches.
- [x] Add explicit rollback metadata so the prior build receipt/wheel remains available after publishing or installing a newer approved build. No separate rollback verb is required: approved rollback explicitly reinstalls the retained prior wheel and reruns `runtime pin` with its retained receipt; editable rollback follows the recorded install command and is necessarily development-marked.

**Implementation verification (2026-07-21):** Strict pin/channel parsing, immutable publication, rendered-skill pinning, read-only update comparison, and three-generation retained rollback coverage passed 57 focused tests and 317 full tests. Publication uses a per-channel exclusion lock, unique pending files, file and directory durability syncs, immutable hard-link placement, and atomic manifest replacement. Independent read-only review reached commit-ready after rendered-template verification, stable runtime error codes, human advisory output, symlink/path binding, and lock descriptor ownership were corrected.

## Task 5: Classify Readiness And Enforce It Before Writes

**Files:**

- Create: `src/meeting_ingest/readiness.py`
- Modify: `src/meeting_ingest/cli.py`
- Modify: `src/meeting_ingest/pipeline.py`
- Modify: `src/meeting_ingest/session_inbox.py`
- Modify: `src/meeting_ingest/playbook.py`
- Modify: `src/meeting_ingest/config.py`
- Test: create `tests/test_readiness.py`
- Test: modify `tests/test_pipeline_ingest.py`
- Test: modify `tests/test_session_inbox.py`
- Test: modify playbook mutation/rebuild tests

- [ ] Implement the four verdicts and categorized findings without duplicating raw doctor output.
- [ ] Separate next-meeting blockers from history warnings using explicit issue-code classification and the frozen provenance-era boundary; unknown issue codes fail closed until classified.
- [ ] Check normal config, required privacy gate, current handoffs, lock/active state, path safety, and current-write integrity.
- [ ] Add the global `--development-override <reason>` option and typed API authorization.
- [ ] Call the shared guard from every public write-capable engine entry point before lock acquisition or writes.
- [ ] Preserve read-only access to inspect/readiness/status/doctor even when blocked.
- [ ] Ensure development override bypasses only approval/install-mode blockers, never source, config, privacy, path, handoff-identity, package-integrity, or corruption blockers.
- [ ] Add an autouse test fixture that injects an approved runtime inspector; add dedicated tests proving production defaults do not trust test environment variables.
- [ ] Test Ready, Ready with history warnings, Development override, Blocked, unknown issue fail-closed, grouped human output, full JSON details, and zero side effects.

## Task 6: Bind Runtime Across Session Handoffs

**Files:**

- Modify: `src/meeting_ingest/provider_contract.py`
- Modify: `src/meeting_ingest/provider_handoff.py`
- Modify: `src/meeting_ingest/pipeline.py`
- Modify: `src/meeting_ingest/session_handoffs.py`
- Modify: `src/meeting_ingest/session_inbox.py`
- Test: modify `tests/test_pipeline_ingest.py`
- Test: modify `tests/test_session_inbox.py`

- [ ] Persist canonical runtime provenance plus fingerprint in every new request.
- [ ] Bind the response echo through the request-specific response contract.
- [ ] Verify the persisted request provenance against current runtime in preflight and phase 2.
- [ ] Refuse approved/development mode changes, override-reason changes, build changes, workflow changes, or tampered provenance.
- [ ] Preserve legacy handoff readability for doctor/status, but do not complete an unpinned legacy handoff as an approved client run.
- [ ] Keep mismatched handoffs for explicit recovery; never delete them on validation failure.
- [ ] Test update-during-handoff, dirty-state change during development handoff, tampering, legacy handoff, retry under original build, and fresh remint under a new build.

## Task 7: Persist Runtime Provenance In Artifacts, Ledgers, And Derived Outputs

**Files:**

- Modify: `src/meeting_ingest/render.py`
- Modify: `src/meeting_ingest/ledger.py`
- Modify: `src/meeting_ingest/schema.py`
- Modify: `src/meeting_ingest/pipeline.py`
- Modify: `src/meeting_ingest/playbook.py`
- Modify: `src/meeting_ingest/doctor.py`
- Modify: `tests/fixtures/expected_markdown/summary_plus_verbatim_basic.md`
- Test: modify `tests/test_provider_render.py`
- Test: modify `tests/test_ledger.py`
- Test: modify signal schema/JSONL tests
- Test: modify `tests/test_doctor_status.py`
- Test: modify playbook tests

- [ ] Add canonical runtime provenance to all run summaries and durable surfaces listed in the contract.
- [ ] Make session artifacts adopt the phase-1 bound provenance after phase-2 equality succeeds.
- [ ] Mark development artifacts prominently in front matter and the rendered overview; do not hide the mode in machine-only fields.
- [ ] Record development override reason in provenance while escaping it safely for JSON/YAML/Markdown.
- [ ] Add doctor checks for missing, malformed, contradictory, or unresolvable runtime provenance on ledger `2.0` and other explicitly provenance-aware artifacts and derived outputs.
- [ ] Emit signal schema `1.2` with a compact producer-ledger/runtime reference; distinguish operation provenance from carried signal-generation provenance; enforce write-time producer linkage and latest-state standing-doctor linkage with ledger `2.0`.
- [ ] Preserve legacy readability: absent runtime provenance on ledger `1.0` and other explicitly legacy records is a history warning, not automatic current-write corruption.
- [ ] Test approved, development, no-op, failure, repair, reconcile, and playbook derivation provenance.

## Task 8: Replace Ambiguous Claude Commands And Silent Global Refresh

**Files:**

- Modify: `docs/claude-skills/meeting-ingest/SKILL.md`
- Modify: `docs/claude-agents/meeting-ingest-session-provider.md`
- Modify: `docs/codex-skills/meeting-ingest/SKILL.md` for truthful non-reference-host status
- Modify: installed `~/.claude/skills/meeting-ingest/SKILL.md`
- Modify: installed `~/.claude/agents/meeting-ingest-session-provider.md`
- Modify: installed `~/.codex/skills/meeting-ingest/SKILL.md`
- Modify: `AGENTS.md`
- Modify: `scripts/git-hooks/refresh-global-tool.sh`
- Modify or remove: `scripts/git-hooks/post-commit`, `scripts/git-hooks/post-merge`
- Modify: `README.md`

- [ ] Replace every Claude Code `uv run meeting-ingest` instruction with the canonical absolute approved executable used by the maintainer-only channel.
- [ ] Start every natural-language inbox workflow with `readiness --host claude-code --json`; continue only for Ready/Ready-with-history-warnings or an explicitly user-authorized development override.
- [ ] Make the skill report build ID, runtime mode, and readiness verdict in completion output.
- [ ] Require the session-provider agent to echo request-bound runtime provenance without interpreting or rewriting it.
- [ ] Hash the portable durable skill template in the build receipt; render only its strict approved-executable marker during consumer installation; hash the rendered installed skill in the consumer pin; verify the installed agent byte-for-byte when it requires no machine-local substitution.
- [ ] Retire hook-based `uv tool install --reinstall` completely. Hooks may emit an informational reminder that a candidate exists, but they cannot build, publish, install, pin, or update.
- [ ] Document the explicit release flow and reference-host boundary; Codex remains development/non-release evidence until separately approved.

## Task 9: Cut HTV Over With Rollback Preserved

**Scope:** This task is authorized only after Tasks 1-8 pass review and an approved wheel/receipt exists. It changes runtime installation/configuration but does not mutate meeting corpus content.

- [ ] Record the existing HTV editable distribution metadata, executable/module paths, source target, Git state, and environment package snapshot for rollback.
- [ ] Build, review, approve, publish, and explicitly install the selected frozen wheel into the canonical global tool location.
- [ ] Verify global runtime identity and package integrity before writing the HTV pin.
- [ ] Pin HTV to the exact receipt/build/executable/workflow.
- [ ] Render the approved executable into the installed Claude skill's strict marker, then verify its hash against the consumer pin; hash-verify the extraction agent against the receipt/pin contract.
- [ ] Uninstall only `meeting-ingest` from the explicit HTV `.venv` interpreter. Do not delete or recreate the virtual environment.
- [ ] Verify the editable `.pth`, distribution metadata, and local console script are gone and no activated/`uv run` path can import the Meeting Ingest working tree.
- [ ] Run read-only runtime inspection and readiness. Expected verdict is `Ready with history warnings` until historical qualification is complete.
- [ ] Run `status` and `doctor` through the pinned executable and confirm legacy findings are categorized, not silently repaired.
- [ ] Keep the prior approved wheel/receipt and the recorded editable-install instructions as rollback evidence; rollback is explicit and development-marked.
- [ ] Do not process a real transcript until the cutover checklist and review pass.

## Task 10: Fresh Reference-Host Proof And Product-Truth Reconciliation

**Files after evidence exists:**

- Modify: `docs/product-status.md`
- Modify: `docs/implementation-plan.md`
- Modify: `README.md`
- Modify: `CURRENT-QUESTIONS.md`
- Create: dated session/acceptance evidence under `docs/sessions/`

- [ ] From HTV, submit one normal Claude Code request with one new non-synthetic transcript.
- [ ] Require the skill to show readiness and build identity without source, PATH, package, ledger, or cache inspection.
- [ ] Complete phase 1/extraction/phase 2 using the same bound runtime and workflow.
- [ ] Confirm completion reports artifact, signals, ledger, archive, reconcile, provider, host, effective date/confidence, build ID, runtime mode, and workflow contract.
- [ ] Confirm the output surfaces preserve the same provenance and post-run readiness remains safe.
- [ ] Exercise explicit update availability without installing it, then an approved update/repin in a disposable consumer before touching HTV.
- [ ] Record elapsed time, interventions, failures, rollback evidence, and human trust assessment.
- [ ] Update product truth only with demonstrated claims; Track 1 completion does not claim semantic guardrails or qualified history.

## Required Test Matrix

| Case | Expected result |
|---|---|
| Frozen wheel + matching receipt/pin/executable/workflow | Ready |
| Same semantic version, different build ID | Blocked |
| Same commit, different unapproved wheel digest/receipt | Blocked |
| Approved build selected through wrong executable | Blocked |
| Editable clean source without override | Blocked |
| Editable dirty source without override | Blocked |
| Editable source with explicit reason | Development override; outputs marked |
| Unknown/uninspectable install mode | Blocked |
| Corrupted installed package file/RECORD | Blocked |
| Missing or malformed runtime pin for write | Blocked |
| Invalid normal project config/privacy gate | Blocked |
| Runtime safe plus classified legacy findings | Ready with history warnings |
| Unknown health issue code | Blocked until classified |
| Newer channel build available | Current pin remains Ready; advisory only |
| Missing channel manifest | Current matching pin remains Ready; advisory |
| Phase 2 build/workflow/mode differs from phase 1 | Blocked; handoff retained |
| Legacy unpinned handoff | Visible but not completable as approved run |
| Development output | Runtime mode and reason visible everywhere |
| Ledger `2.0`/provenance-aware output missing provenance | Doctor current-integrity blocker |
| Ledger `1.0` legacy output missing provenance | History warning |
| Legacy signal `1.1` with no resolvable legacy ledger link | History warning |
| Signal `1.2` with no unique matching producer ledger `2.0` reference | Write-time failure and doctor current-integrity blocker |
| Later reconcile snapshot carries prior signal generation | Valid when producer reference/fingerprint/count remain unchanged and `produced_in_this_record` is false |
| Repair rewrites signal bytes | New producer ledger record/reference; prior generation remains history |
| Latest ledger `2.0` signal manifest missing or mismatching signal `1.2` | Write-time failure and doctor current-integrity blocker |
| Git commit/merge on main | Does not install or repin consumer tool |
| HTV `.venv` activated after cutover | Cannot import editable Meeting Ingest |
| Readiness/status/doctor while blocked | Read-only commands still work |

## Verification Commands

Focused suites are specified per task. Final verification requires:

```bash
uv run pytest -q
git diff --check
```

Also require:

- an initial setuptools determinism spike recorded before downstream runtime implementation;
- two isolated builds of the approved commit with identical wheel SHA-256;
- receipt-to-wheel and receipt-to-embedded-identity verification;
- durable skill-template hash, controlled rendered-skill hash, and byte-for-byte agent verification;
- a disposable-consumer install/pin/update/rollback drill;
- the read-only HTV cutover checks;
- one fresh Claude Code meeting proof only after readiness is safe;
- independent review with all findings resolved or explicitly deferred.

## Completion Gate

Track 1 is complete only when:

1. One reviewed commit and reproducible wheel are bound by an approved receipt.
2. HTV pins that exact immutable build, executable, and workflow.
3. The editable HTV Meeting Ingest distribution is removed without disturbing the rest of its environment.
4. Claude Code no longer uses ambiguous `uv run` resolution.
5. Git hooks cannot silently install or update consumer tooling.
6. Runtime inspection and readiness require no source/PATH/package investigation by the user.
7. Every write-capable entry point fails closed on unapproved runtime unless development override is explicit.
8. Development execution is unmistakable in every required provenance surface.
9. Session phase 1 and phase 2 are build/workflow/mode bound.
10. Safe fresh ingest can distinguish history warnings from current blockers without mutating history.
11. A fresh non-synthetic Claude Code ingest succeeds through the pinned runtime and reports complete provenance.
12. Full tests, reproducible-build verification, disposable update/rollback drill, and independent review pass.

## Suggested Commit Sequence

1. `docs: freeze approved runtime and readiness contract`
2. `feat: build reproducible runtime receipts`
3. `feat: inspect installed runtime identity`
4. `feat: add consumer runtime pins and update checks`
5. `feat: gate writes on pre-meeting readiness`
6. `feat: bind runtime provenance across handoffs`
7. `feat: persist runtime provenance in outputs`
8. `docs: switch Claude workflow to approved runtime`
9. `chore: retire automatic global tool refresh`
10. `docs: record HTV approved-runtime proof`

Commits must exclude unrelated pre-existing working-tree changes, generated wheels/receipts unless explicitly approved release metadata, client corpus data, and volatile `.iq-context` runtime files.
