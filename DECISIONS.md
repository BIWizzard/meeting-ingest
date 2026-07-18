# Decisions — meeting-ingest

## Current Decisions

### 1. This repo stays focused on the meeting ingestion tool

`meeting-ingest` is intended to remain a specific ingestion engine, not a generic family-of-tools repo.

If a broader shared runtime emerges later, it should be extracted deliberately instead of broadening this repo prematurely.

### 2. The product direction is host-neutral and CLI-first

The canonical product should be a normal package/CLI/library.

Claude Code, Codex, Codex via T3 harness, and other hosts should be thin wrappers over the same engine.

### 3. The existing Claude skill is the behavior reference, not the final architecture

The current implementation under `~/.claude/skills/ingest-meeting/` contains the best current behavior reference.

This repo is the rebuild target and should preserve what works while removing Claude-specific packaging and orchestration assumptions.

### 4. First-run project setup is required

The rebuilt tool should be able to initialize missing project structure safely, either explicitly or as part of normal ingest behavior.

This is a core usability requirement, not a stretch goal.

### 5. Strong done-process semantics are required

This tool is not “summarize a transcript somehow.”

It must preserve a strong operational done process:

- normalized source read
- structured markdown output
- structured signal output
- ledger write
- archive write
- reconcile only after confirmed success

### 6. Idempotency must remain content-hash based

Deduplication should be based on source content hash, not filename.

### 7. Provider-backed extraction should be swappable

The extraction step should not be hardwired to one host or one model provider.

Provider targets include both API-backed and host/session-backed options.

API-backed providers are required for portability, automation, and broader productization:
- Anthropic
- OpenAI
- Gemini
- mock/testing provider

Host/session-backed providers are required for the maintainer's personal workflow, where Supa Code, T3 Code, Claude Code, or Codex may already be running in a subscription-backed active session. These should allow a dedicated extraction sub-agent to create structured provider output without requiring a separate paid API call when the active harness can perform the model judgment.

Host/session-backed providers should keep large transcript/model-extraction context out of the main session when practical. They must still return the same validated structured response shape as API providers. They should not bypass deterministic engine behavior, artifact rendering, signal enrichment, ledger writes, archive, or reconcile.

The host/session-backed handoff should use engine-created request JSON and sub-agent-created response JSON. The response envelope carries identity metadata, while the nested `response` payload maps directly to `ProviderResponse`; the engine verifies identity fields against the persisted request, adopts identity from the request rather than the response, and routes that payload through the same validation and ingest path as API-backed provider output.

The canonical provider name for this path is `session`. Session-backed extraction should have its own privacy gate, such as `privacy.allow_session_provider`, because active-harness subscription workflows and direct API-backed providers have different trust profiles.

### 8. `iQ Context` is separate but complementary

Relationship:

- `meeting-ingest` produces structured project artifacts
- `iQ Context` may later track, embed, retrieve, and surface those artifacts
- `meeting-ingest` should not depend on `iQ Context`

### 9. Initial scope is personal-workflow first

The first serious build should optimize for the maintainer's current personal and professional workflows.

This includes:

- Supa Code and T3 Code as primary harnesses
- Claude and Codex as common operating contexts
- fast and consistent ingestion
- easy project-local setup
- selectable output depth
- stakeholder communication signals

Broader productization can happen later, but it should not dilute the first build.

### 10. Output modes should be explicit

The rebuild should not leave the final artifact shape to ad hoc prompting.

Initial output modes should include:

- smart summary
- summary plus verbatim transcript
- verbatim-only normalized transcript

Default mode should be summary plus verbatim because the maintainer more often wants both a smart summary and a transcript record.

For summary plus verbatim, the preferred output is one markdown file with the structured summary first and the transcript second. Summary-only remains important for large structured meetings such as daily standups.

### 11. Sub-agent operation remains desirable

The current sub-agent interaction model is valuable and should be preserved through host wrappers.

The engine should remain a normal CLI/library, while Claude, Codex, Supa Code, and T3 Code wrappers can delegate ingestion work to a focused sub-agent that calls the same underlying engine.

Normal use should work from inside the active agentic harness. The user should not need to exit Supa Code or T3 Code into a raw CLI session to ingest meeting documents.

For subscription-backed harnesses, normal use should also support a path where a delegated extraction sub-agent performs the model extraction step through the current session rather than requiring an Anthropic/OpenAI API key. This keeps transcript-heavy context out of the main session. This is separate from API-backed provider adapters, which remain important for portability and marketability.

The dedicated extraction sub-agent should return provider-level JSON only. It must not produce markdown artifacts, enriched signal records, ledger snapshots, archive copies, or reconcile moves.

Host/session-backed extraction is a two-phase flow. The engine must not hold a project lock while the sub-agent performs model extraction; phase 2 reacquires the lock, rechecks duplicate/no-op state, verifies the response against the cached request, and then continues normal ingest side effects.

### 12. Output filenames must be scannable

Generated meeting filenames should identify the date, meeting/conversation identity, and primary topic.

For one-on-one meetings, the filename should usually include the counterpart's name or stable short identifier.

Low-signal fallback names like `generic-<hash>` should be avoided unless the tool cannot confidently infer a better title. When fallback naming is necessary, the output should surface a rename suggestion.

Filename/title repair after ingest is acceptable when transcript-derived context produces a better meeting identity.

Meeting identity must remain separate from title, slug, and filename. `meeting_id` should be immutable and content/date-derived so rename repair does not break ledger records, signals, cross-references, or derived playbook entries.

Meeting signal files should remain keyed by immutable `meeting_id`, not mutable slug or filename. Generalized non-meeting signal files should be keyed by communication-neutral `source_id`.

If inferred filenames collide, append a numeric suffix and surface a warning in the run summary.

### 13. Stakeholder communication should accumulate into a rolling playbook

Per-meeting communication signals should feed a durable stakeholder playbook over time.

The playbook should help the maintainer prepare for interactions by surfacing stakeholder priorities, tracked asks and commitments, observed communication preferences and behaviors, recurring patterns, contradictions, freshness, and useful framing guidance across sources.

The playbook is evidence-grounded communication memory, not a personality dossier, relationship score, persuasion engine, or autonomous messaging product. Source observations remain distinct from derived patterns and guidance. Every profile entry must preserve provenance, uncertainty, and review state.

The durable design baseline is `docs/stakeholder-playbook-design.md`.

### 14. Generated markdown lives in the meetings root by default

Generated meeting markdown should live directly under the project meeting root for easy scanning and sharing with agents.

Directory hygiene should come from keeping raw inputs, processed copies, signals, cache files, quarantine records, and derived aggregate outputs in their own underscore-prefixed directories.

### 15. Playbook derivation is explicit and never part of primary ingest completion

The ingest workflow should prioritize producing the meeting markdown and signal output, then notifying the user those outputs are ready.

Source ingest marks playbook inputs pending and completes without running a blocking profile rebuild. Stakeholder Briefing V1 uses an explicit deterministic rebuild command. `status` and `doctor` report whether the current playbook is stale.

Agent wrappers may offer or invoke the explicit rebuild after primary ingest, but that is a separate engine operation. Provider-assisted guidance always uses its own two-phase derivation workflow and never holds the project lock during model judgment.

Playbook failure cannot make the primary meeting ingest fail because playbook derivation is not part of primary ingest completion.

### 16. Markdown should be optimized for agent consumption

Generated markdown should remain human-readable, but the primary downstream consumer is often another agent.

Artifacts should use stable metadata, stable headings, explicit identifiers, clear tables/lists, and predictable transcript delimiters so agents can consume them reliably.

### 17. Source and playbook derivation use separate authoritative ledgers

The source ledger should track each source content hash once and attach generated artifacts by output mode.

This matches the user's mental model: a transcript source is known once, and the tool can list which artifact variants exist or are missing.

This is preferred over separate ledger rows for every source-plus-mode pair.

Source-ledger entries should track per-artifact status, provider/model/schema metadata, an ingest-time playbook-input hint, and regeneration from processed archive copies.

The append-only ledger should define a current-state rule such as "last valid record wins per source hash."

Source-ledger records should be complete current-state snapshots, not partial deltas. Source-ledger events should distinguish primary artifact readiness, completed ingest, reconcile repair, failed ingest, quarantine, regeneration, and title repair.

Corpus-derived playbook history does not belong in every source snapshot. `_playbook-state/derivation-ledger.jsonl` is authoritative for playbook rebuild history, provider provenance, committed generations, and failure state. `_derived/playbook-index.json` is a rebuildable pointer to the current committed generation. Existing source-ledger and ingest-run-summary `derived_updated` or `derived.playbook_update_status` values remain compatibility data but are superseded for new playbook behavior.

### 18. Signal extraction stays factual and uses narrow observation types

V1 per-meeting signals should use a small taxonomy:

- explicit ask
- stakeholder priority
- decision rationale
- commitment
- risk or concern

The playbook foundation adds three source-grounded observation types:

- communication preference
- communication behavior
- interaction response

`communication_style` is derived pattern vocabulary only. It must not be emitted as a source observation or used for trait labeling.

Every signal should include evidence, inference level, and confidence.

Communication guidance should be generated during playbook derivation rather than extracted directly into per-meeting signal records.

Providers do not set recurrence. Extraction records recurrence as unknown; playbook derivation computes recurrence across qualified observations.

Duplicate/no-op ingest is a success-class outcome: JSON should use `status: "no_op"` and exit code `0`.

Exit code `11` is reserved rather than used for blocking playbook work. An explicitly invoked playbook command is the primary operation and reports the applicable provider, validation, write, ledger, lock, stale-input, CLI, or general failure category.

### 19. Communication artifact ingest follows the meeting-derived briefing foundation

Emails, memos, Teams messages/threads, screenshots of communications, and related attachments may provide valuable stakeholder voice, commitments, decisions, and requests.

Stakeholder Briefing V1 should first prove identity resolution, generalized signal provenance, deterministic rebuilds, review overlays, and meeting-derived profiles. Plain-text email or pasted-message ingest is the first non-meeting pilot after that foundation. Image-based and public/social sources follow only after their provenance, privacy, attribution, and evidence-location contracts are reviewed.

### 20. Stakeholder profiles require a reviewed project-local identity registry

Playbook derivation uses a small, human-owned project-local registry under `_playbook-state/`. It stores immutable person IDs, reviewed display names, and reviewed aliases.

Canonical observations preserve raw stakeholder labels. Provider-proposed IDs and extraction-time deterministic slugs are advisory only. Derivation always resolves raw labels through the current registry; ambiguous aliases remain unresolved and fuzzy matching never auto-merges people.

Cross-project/global roster behavior, automatic candidate promotion, and fuzzy identity resolution remain deferred.

### 21. The CLI is a thin adapter over a reusable pipeline API

The ingest workflow should live in a library-level orchestrator such as `pipeline.py`.

`cli.py` should parse commands, call the pipeline, print summaries, and map exit codes. It should not own the done-process sequencing.

### 22. Duplicate/no-op may repair incomplete reconcile state

If a duplicate source is detected but the ledger shows incomplete archive or reconcile work, v1 may complete the missing archive/reconcile work instead of returning a passive no-op.

This is intended to prevent inbox residue from becoming permanent workflow debt.

Repair work should append a complete `reconcile_repaired` snapshot when archive or reconcile state changes.

### 23. The playbook ships as Stakeholder Briefing V1 and Playbook Guidance V1.1

Stakeholder Briefing V1 is a complete deterministic milestone. It produces canonical profile JSON and human/agent-readable briefing Markdown with tracked asks and commitments, priorities, concerns, rationales, preferences, behaviors, interaction responses, freshness, evidence coverage, and unresolved identity.

Playbook Guidance V1.1 adds provider-assisted semantic clustering, contextual scope, contradiction confirmation, positive-response patterns, and practical communication cues after review controls exist.

The primary consumption surface is a concise pre-interaction briefing. The profile file is its substrate, not the end of the product experience.

### 24. Playbook profiles use full rebuilds and immutable generations

Validated source observations, the identity registry, versioned rules, and append-only review overlays are canonical playbook inputs. Profiles and briefings are rebuildable materializations.

Briefing V1 uses a full deterministic rebuild. Targeted refresh is deferred until corpus size justifies its additional equivalence and concurrency surface.

Each rebuild writes a new immutable generation under `_derived/generations/<derivation-run-id>/`. The derivation-ledger append is the commit point, and `_derived/playbook-index.json` is atomically rewritten to point to the committed generation. Readers use the index and never infer current state from generation timestamps.

Human-reviewed state lives under `_playbook-state/` and must not be deleted by derived-output or cache cleanup. `_derived/` remains safely rebuildable.

### 25. Communication provenance distinguishes source kind, file format, and three time semantics

Generalized signal provenance uses communication-neutral `source_id` and `source_kind`. `source_kind` describes the communication artifact, while the source ledger's `source_type` continues to describe file formats such as `docx`, `vtt`, and `txt`.

Signal timing distinguishes:

- occurrence: when the meeting or communication happened
- acquisition: when the source was downloaded, copied, or captured
- recording: when Meeting Ingest processed the observation

File modification time normally describes acquisition for downloaded Teams transcripts. When used as an occurrence fallback, it remains low confidence and must be reported as such.

Schema 1.1 adds generalized source, timing, and raw stakeholder-label fields while keeping tolerant reads for schema 1.0 meeting signals.

### 26. Signal identity and review lineage must survive ordinary evidence evolution

New signal IDs combine source identity with a deterministic observation identity. Stable source locators are preferred over provider wording so paraphrase changes do not unnecessarily remint observations.

Signal regeneration explicitly supersedes observations it cannot preserve. Rebuild and `doctor` report orphaned overrides and suppressed content that re-emerges under a new signal ID.

Tracked asks, commitments, and single-observation facts anchor review lineage to their originating observation. Pattern and guidance lineage excludes contradicting evidence and provider wording. Review decisions never transfer silently when a pattern's supporting basis materially changes.

### 27. Playbook synthesis has stricter provider and privacy boundaries than source extraction

Deterministic Briefing V1 uses no provider. Provider-assisted guidance may group, scope, confirm, or phrase qualified observations, but it may not mint source facts, raise observation confidence, remove contradictions, resurrect disqualified evidence, or assign reviewed identity.

Guidance synthesis uses dedicated default-false privacy gates for API-backed and session-backed providers. Meeting extraction permission does not imply permission to send concentrated cross-source playbook evidence for synthesis.

Session-backed guidance uses a persisted two-phase derivation request. Phase 1 fingerprints inputs under the project lock, provider judgment runs without the lock, and phase 2 rechecks the complete fingerprint before publishing. Changed inputs produce a typed `stale_inputs` result and require a fresh phase 1.

### 28. Human review and evidence discipline are part of the playbook contract

Briefing V1 supports rejecting a derived entry, resolving a tracked ask or commitment, suppressing a bad source observation, and correcting identity through the registry. Guidance V1.1 adds accept, reject, and tombstone controls for inferred guidance.

Review events are append-only, audited, and applied during rebuild without mutating source observations. Absence of closure evidence never means an ask or commitment is open; the briefing states that no resolution evidence was found.

The playbook must not infer or store protected traits, diagnoses, intelligence ratings, personality types, hidden motives, emotional vulnerabilities, manipulation opportunities, or relationship scores. Guidance is framed as communication accommodation and always cites qualified evidence.

Profiles and briefings remain in ignored project-local storage. iQ Context and other capture integrations must not copy profile bodies or concentrated evidence by default.

### 29. Occurrence selection and date repair preserve immutable minting provenance (2026-07-18)

- Occurrence selection is precedence-based (override > content > filename > file mtime); contextual dialogue evidence deferred from v1.
- `--meeting-date` exists on single-source commands only; batch commands excluded deliberately.
- `meeting_id` and `signal_id` date segments are immutable minting provenance; `repair-date` rewrites only mutable occurrence metadata (artifact filename prefix, front-matter date fields, signal `effective_at`).
- Signal files are rewritten in place because downstream briefing layers sequence on `effective_at`; leaving stale values would poison Layer 5+.

## Working Assumptions

- The deterministic parts of the current engine are worth preserving.
- The Claude-specific orchestration and packaging boundaries are redesign targets.
- This repo should stay small enough to reason about and strong enough to trust.
- Consistency should come from stable schemas and renderers, not from asking a model to invent final document structure.
- Model/provider use should be right-sized by task, output mode, and quality requirements.
- The default transcript record should be cleaned verbatim: speaker-attributed and lightly cleaned for readability while preserving substantive content.
- Python is the preferred implementation language unless later technical constraints argue otherwise.
- V1 should use injectable clock/ID hooks so renderer and run-summary tests remain deterministic.

## Decision Hygiene

Update this file when a meaningful product boundary, CLI, config, provider, or storage decision is made.
