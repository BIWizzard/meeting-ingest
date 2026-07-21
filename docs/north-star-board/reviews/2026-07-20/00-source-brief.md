# North Star Review Board Source Brief

Review date: 2026-07-20

Repository: `meeting-ingest`

Review mode: read-only product-governance review. No implementation, roadmap replacement, commit, external-system change, or iQ Context mutation is authorized for independent reviewers.

## Exact Review Question

Does Meeting Ingest currently deliver a coherent, trustworthy, low-ceremony path from a real supported meeting transcript to useful durable project knowledge for its intended user, and if not, what is the smallest evidence-backed milestone that must be completed before the product can credibly claim that it “just works”?

The review must answer:

1. What was the original product vision?
2. What user and problem was it designed for?
3. What has actually been implemented?
4. What works reliably in real use?
5. Where do implementation, documentation, active state, and product claims disagree?
6. What has been completed, absorbed, deferred, superseded, or abandoned?
7. Is the current roadmap still the right roadmap?
8. What should the next milestone be?
9. What must be true before the product can credibly claim that it “just works”?

## Decision Standard

Judge the product against these standards:

- It can be explained in one human sentence.
- Its primary workflow is obvious.
- Behavior matches documentation and product claims.
- Failures preserve trust and provide recovery.
- Generated artifacts are useful, predictable, and inspectable.
- Reprocessing and retries behave safely.
- It removes more ceremony than it creates.
- A real meeting can travel from supported input to useful output without expert intervention.
- Dogfooding demonstrates the intended outcome outside a synthetic fixture.
- Current state, roadmap, implementation, and public truth agree.

## Original Vision And Product Principles

The repository begins with a simple public proposition: transform raw `.docx`, `.txt`, and `.vtt` meeting artifacts into structured project knowledge with a strong done process (`README.md:3-21`). The founding design principles are one engine with many wrappers, provenance, content-hash idempotency, swappable providers, and human-readable artifacts (`README.md:48-55`).

The first serious product was explicitly personal-workflow first: optimize for the maintainer's real professional workflow before a generic market, while staying host-neutral, frequent-use fast, trustworthy, configurable without heaviness, and easy to initialize (`docs/personal-workflow-scope.md:3-20`). The intended interaction is agentic: ask an active agent in a supported harness to ingest a meeting without leaving that harness; wrappers and extraction agents must delegate the done process to one engine (`docs/personal-workflow-scope.md:22-56`).

Consistency was intended to come from deterministic parsing, schemas, validation, and rendering, with provider judgment limited to phases that require it (`docs/personal-workflow-scope.md:58-83`). The default desired artifact was a single summary-plus-verbatim file with stable structure and provenance (`docs/personal-workflow-scope.md:85-158`). A second, longer-horizon vision was practical stakeholder communication memory: source-grounded, non-manipulative accumulated context that helps the maintainer communicate in their own voice (`docs/personal-workflow-scope.md:205-230`).

The durable decisions reinforce a CLI-first, host-neutral engine, explicit initialization, strong done semantics, content-hash idempotency, swappable providers, personal-workflow-first scope, and explicit output modes (`DECISIONS.md:5-116`). The engine, not a wrapper or provider, owns validation, rendering, signals, ledger, archive, and reconcile behavior (`AGENTS.md:54-63`; `DECISIONS.md:223-227`).

## Current Product Definitions

Public definition: “a platform-agnostic meeting and transcript ingestion tool” that creates durable structured project outputs (`README.md:1-21`).

Current internal definition: “a project-local meeting transcript ingestion engine for agent-operated workflows,” strongest for a technical owner using Codex, Claude Code, Supa Code, T3 Code, or CLI automation, and not yet a general self-serve product (`docs/product-status.md:9-24`).

Package definition: version `0.1.0`, “Project-local meeting transcript ingestion engine,” Python 3.11+, with no runtime dependencies and a `meeting-ingest` console script (`pyproject.toml:5-17`). There is no evidence in the repository of a published package release, semantic release process, end-user installer, or supported upgrade path. Outside this repository, project instructions describe a frozen local `uv tool` install refreshed from `main` (`AGENTS.md:136-146`).

## Target User And Job To Be Done

Primary user: the maintainer or a similarly technical project owner already working inside an agentic coding harness.

Primary job: place or identify a meeting transcript, ask the active agent to ingest it, and receive a useful, inspectable meeting artifact plus structured signals while the engine safely records provenance, prevents duplicate work, archives the source, and reconciles the inbox.

Desired experiential outcome: the user should not need to understand provider envelopes, ledger snapshots, request caches, recovery internals, or host-specific orchestration to get the useful output (`docs/personal-workflow-scope.md:39-56`).

Secondary job: derive an evidence-backed stakeholder briefing from accumulated signals. This grew from the original stakeholder-communication goal, but it is explicitly separate from source-ingest completion (`DECISIONS.md:149-179`, `DECISIONS.md:237-253`).

## Initial Roadmap And Current Roadmap

The initial build plan contained seven sequential milestones: scaffold/init, extraction/IDs, provider/renderer, signals/ledger/archive, run summary/doctor, first real provider, and host/session provider (`docs/implementation-plan.md:492-617`). Those foundations are substantially implemented.

The later layered roadmap covers V1 polish, output modes and repair/regenerate, session inbox automation, provider/wrapper hardening, stakeholder briefing/guidance, corpus adoption, broader communication sources, and iQ Context integration (`docs/implementation-plan.md:647-1094`).

The active product-status sequence still says to implement effective-date reliability, schema 1.1, provider contract updates, Layer 5A, and deterministic Stakeholder Briefing V1 (`docs/product-status.md:433-445`). Repository history and the same status file show that all of those except the last small Layer 5B hardening item have since landed or are implemented (`docs/product-status.md:329-366`; commits `4101cf2`, `67b9862`, `53de840`, `d996992`, `196592d`, `25b1ba9`, `11b3780`). This is direct roadmap truth drift.

The worktree contains an uncommitted `playbook cleanup-uncommitted` safety/recovery slice plus tests and contract/status edits. iQ Context says this was reviewed once, passes the suite, and awaits a focused follow-up review. This review does not approve, reject, or modify that implementation.

## Current Implementation Inventory

### Complete or demonstrated in code and tests

- Project initialization, config/path discovery, hashing, deterministic IDs, locking, typed errors, exit codes, and JSON summaries (`docs/product-status.md:93-107`).
- Deterministic `.txt`, `.vtt`, and `.docx` extraction and cleaned-verbatim normalization (`docs/product-status.md:108-123`).
- The single implemented renderer is summary-plus-verbatim with stable sections, provenance, signals, and transcript (`docs/product-status.md:125-137`; `src/meeting_ingest/pipeline.py:777-946`).
- Signal JSONL, schema 1.1 enrichment, append-only source ledger snapshots, archive, inbox reconcile, duplicate/no-op, and incomplete archive/reconcile repair (`docs/product-status.md:145-176`).
- Mock, Anthropic, and session-provider paths with privacy gates and shared validation (`docs/product-status.md:178-213`).
- Session provider request/response contract, preflight response validation, active-agent inbox planner, resume-safe scanning, and handoff health reporting (`README.md:170-236`; `docs/product-status.md:198-220`).
- Effective-date candidate selection, explicit override, controlled repair, and warnings for mtime fallback (`docs/product-status.md:119-123`, `docs/product-status.md:224-243`).
- Layer 5A generalized signal provenance/identity and most Layer 5B deterministic Stakeholder Briefing implementation, including immutable generations, review overlays, status/doctor, readers, evidence index, thresholds, and diagnostics (`docs/product-status.md:329-366`).

### Active

- One uncommitted Layer 5B cleanup/corruption-recovery slice in `src/meeting_ingest/playbook.py`, `src/meeting_ingest/cli.py`, tests, and contracts. It is not part of `origin/main`.
- North Star Review Board adoption and this review package.

### Planned

- Mechanical contradiction candidates after structured mutually exclusive source values exist (`docs/product-status.md:364-366`).
- Playbook Guidance V1.1 provider-assisted interpretation and review (`docs/product-status.md:368-375`).
- Corpus adoption, broader communication sources, and deeper iQ Context product integration (`docs/product-status.md:377-431`).
- Production-grade host adapters and a selected production remote-provider posture (`docs/product-status.md:287-313`).

### Absorbed into another outcome

- The original “sub-agent operation” requirement is absorbed into the session-provider request/response protocol plus host skills. The engine contract exists, but fully automatic host execution is not yet a productized adapter.
- iQ Context integration currently exists as agent instructions, artifact tracking, and post-ingest capture protocol rather than config-gated engine integration (`AGENTS.md:74-123`; `docs/product-status.md:416-431`).

### Deferred

- Global identity, targeted playbook rebuilds, output-mode expansion, title repair, regenerate, stale-handoff cleanup, additional providers, migration, non-meeting sources, and richer iQ Context integration.

### Superseded

- The prior Claude-skill implementation is a behavior reference and legacy artifact, not the architecture (`DECISIONS.md:17-21`; `docs/legacy/claude-ingest-meeting-skill/`).
- Source-ledger `derived` fields are compatibility data; the separate derivation ledger is authoritative for playbook state (`DECISIONS.md:165-179`).
- The former CodeRabbit review/autofix workflow is retired in favor of human-mediated read-only Claude Code review (`AGENTS.md:31-49`).

### Abandoned or cancelled

- No product feature is explicitly recorded as abandoned. CodeRabbit-based review automation and the obsolete autofix skill are explicitly retired process, not product scope.

## Current End-To-End Workflow

Direct/API path:

1. Initialize a project.
2. Put a supported source in `_inbox/` or pass a path.
3. Run `ingest` or `ingest-inbox` with a non-session provider.
4. The engine extracts, validates provider output, writes signals and markdown, appends `primary_artifacts_ready`, archives/reconciles, appends `ingest_completed`, and returns a run summary (`src/meeting_ingest/pipeline.py:777-946`).

Subscription-backed session path:

1. The local project must override the package defaults to `default_provider = "session"` and enable `privacy.allow_session_provider`.
2. `session-inbox` scans existing handoffs and either completes ready responses or creates requests.
3. An active agent or dedicated extraction sub-agent reads each request and writes provider-level JSON matching the embedded schema.
4. The engine validates and completes ingest with `ingest --provider session --provider-response ...`.
5. The operator/agent confirms the output and records one iQ Context capture per successful meeting (`AGENTS.md:74-123`; `docs/session-provider-inbox-agent-workflow.md`).

The CLI itself cannot invoke the active model session. Plain CLI therefore stops at `pending_provider_response`; the natural-language skill and host session supply the missing execution step.

## Distribution And First-Run State

- The package has a normal console entry point and no runtime dependencies (`pyproject.toml:5-17`).
- Default initialized config uses `mock`, disables session and remote providers, disables auto-init, and selects summary-plus-verbatim (`src/meeting_ingest/config.py:42-83`).
- The repository's own dogfood config intentionally changes the provider to `session` and enables session-provider privacy.
- README development examples use `python3 -m meeting_ingest.cli`, even though the package exposes `meeting-ingest`; no single “first real meeting” quick start is presented before the detailed provider material (`README.md:97-236`).
- CLI help enumerates commands but supplies little workflow guidance, defaults, examples, or next-step instruction (`src/meeting_ingest/cli.py:17-125`).
- Consumer distribution is a local frozen `uv tool` install from merged `main`, refreshed by repository-local hooks in this clone; this is operational tooling, not a documented general release channel (`AGENTS.md:136-146`).

## Validation And Test Evidence

Validation performed on 2026-07-20 from the repository root:

- `uv run pytest -q`: 231 passed in 0.76 seconds.
- `uv run meeting-ingest --help`, plus help for `init`, `ingest`, `session-inbox`, `doctor`, and `playbook`: exit 0.
- `uv run meeting-ingest status --root . --json`: exit 0; six known sources, twelve ledger records, no inbox files or handoffs, valid signal contract, missing playbook current state.
- `uv run meeting-ingest doctor --root . --json`: exit 1; one `playbook_state_missing` issue and three `low_confidence_meeting_date` issues.
- Git inspection: `main` equals `origin/main` at `3bc917d`, with pre-existing uncommitted Layer 5B implementation/docs/tests and iQ Context state.

The test suite provides broad deterministic coverage across extraction, pipeline ingest, providers, handoffs, identity, signals, ledger, archive/reconcile, repair, doctor/status, playbook generation/review/status, locking, and CLI scaffold. It does not by itself prove a non-expert, fresh consumer can complete the active-agent workflow.

The product-status evidence block is stale: it reports 133 tests on 2026-07-18 and lists older commits (`docs/product-status.md:447-464`).

## Real-World Dogfooding Evidence

The repository dogfood corpus contains six generated meeting Markdown artifacts, six signal files, six processed-source copies, six `_inbox/_done/` copies, and twelve source-ledger snapshots (primary-ready plus completed). Inputs cover `.docx`, `.vtt`, and `.txt`, and artifacts record both Codex and Claude Code session hosts.

This is evidence that supported real sources can traverse the engine and produce inspectable outputs. It is not clean evidence of an effortless first-run experience because the operator is the product maintainer and the session-provider path is agent-mediated.

The first recorded external consumer UAT on 2026-07-18 found strong failure atomicity and retry behavior: four invalid phase-2 attempts caused no partial side effects, safe retries worked, and the eventual ingest and capture succeeded. It also exposed an expert-intervention burden: the agent had to discover response-envelope schema requirements through sequential validation failures and inspect source code. Subsequent implementation embedded the exact JSON Schema and added aggregate validation plus `validate-response` (`.iq-context/workstreams/default/captures.jsonl`, capture `cap_20260718T220148Z_a28fa2b4`; commit `67b9862`). No recorded post-fix external UAT proves that remediation closed the onboarding loop.

The same UAT exposed mtime date uncertainty, stale handoffs without cleanup, and mid-word slug truncation. Date warnings/override/repair and response-contract discoverability were addressed. Stale-handoff cleanup and word-boundary slug quality remain unproven or unresolved.

## Known Failures And Trust Gaps

- Three of six local dogfood artifacts still have low-confidence mtime-derived dates. Because meeting IDs include the effective date, repair changes artifact metadata/path while preserving originally minted identity; this is safe by contract but can remain cognitively surprising.
- `doctor` treats advisories as issues and exits 1. The active iQ Context briefing explicitly asks whether `low_confidence_meeting_date` should be advisory without forcing failure.
- The dogfood project has no reviewed people in the identity registry and no current playbook generation, so the implemented Stakeholder Briefing value is not demonstrated in the repository's own live state.
- `summary` and `verbatim` are documented product modes but are not implemented; the pipeline always calls the summary-plus-verbatim renderer (`docs/product-status.md:138-143`; `src/meeting_ingest/pipeline.py:819-840`).
- The primary personal workflow still depends on an agent correctly executing a multi-step handoff. There is no fully automatic host adapter and no recorded fresh-consumer proof after the response-contract fix.
- Archive/reconcile has explicit repair, but the write sequence can intentionally leave primary artifacts and a pending ledger state if archive/reconcile fails; recovery is available but still requires diagnosis and retry.
- Playbook implementation has advanced faster than live product proof: status reports `playbook.status = missing`, zero profiles, zero reviewed people, and ten identity candidates in this repository.
- README, product status, current questions, and active iQ state contain different ages and levels of truth. `CURRENT-QUESTIONS.md` still presents several decided or implemented matters under “Open Questions.”

## Truth Drift Summary

- `docs/product-status.md:26-36` says the Stakeholder Playbook is design/contract work and no schema 1.1 or profile code has shipped; later sections in the same file correctly describe Layer 5A and most of 5B as implemented (`docs/product-status.md:315-366`).
- The recommended next product slice describes already completed work (`docs/product-status.md:433-445`).
- The status evidence cites 133 tests versus today's 231 (`docs/product-status.md:460-464`).
- README advertises selectable output modes as direction, but current status and pipeline show only summary-plus-verbatim is implemented (`README.md:36-46`; `docs/product-status.md:138-143`; `src/meeting_ingest/pipeline.py:819-840`).
- README says the default provider is `mock` (`README.md:141-143`), while project instructions say normal personal inbox processing must assume `session` and repair local config if needed (`AGENTS.md:74-89`). Both are technically true at different layers but create product-definition ambiguity.
- iQ Context says Layer 5B cleanup is implemented and ready for follow-up review, while committed `main` does not contain it.
- The implemented playbook surface is broad, but the live repository status is missing a usable playbook generation. Technical presence has not yet become demonstrated user value.

## Prior Decisions And Unresolved Questions

Binding decisions include personal-workflow-first, host-neutral CLI engine, explicit init, strong done semantics, content-hash identity, swappable providers, engine-owned completion, separate playbook derivation, reviewed identity, immutable playbook generations, and factual source observations (`DECISIONS.md`).

Unresolved product choices with current evidence:

- Whether `doctor` should distinguish advisory findings from failures.
- The true occurrence dates for the Nitesh follow-up, Wide Orbit orchestration, Fable 5 review, and a referenced external HTV artifact.
- Whether the next milestone should finish Layer 5B/5C, return to the incomplete core output-mode/repair experience, or freeze expansion for a first-run “just works” proof.
- Which single host/harness should be the first production-grade personal workflow.
- What release audience and channel version 0.1.0 actually commits to support.
- Whether stale handoff cleanup and slug quality are release blockers or bounded follow-up work.
- What minimum live Stakeholder Briefing demonstration is required before that surface is called part of the product.

## Repository Status At Review Start

Branch: `main`, aligned with `origin/main` at `3bc917d`.

Pre-existing modified tracked files:

- `.iq-context/workstreams/default/resume-state.json`
- `.iq-context/workstreams/default/state.json`
- `docs/artifact-contract.md`
- `docs/implementation-plan.md`
- `docs/product-status.md`
- `src/meeting_ingest/cli.py`
- `src/meeting_ingest/playbook.py`
- `tests/test_playbook_status.py`

Pre-existing untracked files:

- `docs/sessions/2026-07-20T04-16-18-940Z-default.md`
- `tests/test_playbook_cleanup.py`

The board artifacts under `docs/north-star-board/` are the only review files intentionally added by this review before synthesis. Independent reviewers must not edit any file or update git/iQ Context state.

## Required Independent Report Structure

Each seat must return findings only, with file and line references wherever practical:

1. Verdict
2. Evidence
3. What is working
4. Gaps and risks
5. Recommendations in priority order
6. What to stop, defer, or simplify
7. Release decision
8. Confidence and unresolved questions

If no issue exists in an examined area, state that explicitly. Separate demonstrated value from plausible value, and label interpretation as interpretation.
