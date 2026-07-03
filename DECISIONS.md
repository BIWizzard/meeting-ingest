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

Likely provider targets:
- Anthropic
- OpenAI
- Gemini
- mock/testing provider

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

### 12. Output filenames must be scannable

Generated meeting filenames should identify the date, meeting/conversation identity, and primary topic.

For one-on-one meetings, the filename should usually include the counterpart's name or stable short identifier.

Low-signal fallback names like `generic-<hash>` should be avoided unless the tool cannot confidently infer a better title. When fallback naming is necessary, the output should surface a rename suggestion.

Filename/title repair after ingest is acceptable when transcript-derived context produces a better meeting identity.

Meeting identity must remain separate from title, slug, and filename. `meeting_id` should be immutable and content/date-derived so rename repair does not break ledger records, signals, cross-references, or derived playbook entries.

Signal files should be keyed by immutable `meeting_id`, not mutable slug or filename.

If inferred filenames collide, append a numeric suffix and surface a warning in the run summary.

### 13. Stakeholder communication should accumulate into a rolling playbook

Per-meeting communication signals should feed a durable stakeholder playbook over time.

The playbook should help the maintainer understand stakeholder priorities, communication patterns, recurring asks, and useful framing guidance across meetings. This should remain grounded in source provenance and should support communication memory rather than becoming a separate messaging product.

### 14. Generated markdown lives in the meetings root by default

Generated meeting markdown should live directly under the project meeting root for easy scanning and sharing with agents.

Directory hygiene should come from keeping raw inputs, processed copies, signals, cache files, quarantine records, and derived aggregate outputs in their own underscore-prefixed directories.

### 15. Primary meeting artifacts are ready before derived playbook work blocks the user

The ingest workflow should prioritize producing the meeting markdown and signal output, then notifying the user those outputs are ready.

Rolling stakeholder playbook updates should happen during ingest when possible, but slower derived playbook maintenance should not delay access to the primary meeting output.

Playbook update failure should not make the primary meeting ingest fail. It should be tracked as separately-statused derived work.

### 16. Markdown should be optimized for agent consumption

Generated markdown should remain human-readable, but the primary downstream consumer is often another agent.

Artifacts should use stable metadata, stable headings, explicit identifiers, clear tables/lists, and predictable transcript delimiters so agents can consume them reliably.

### 17. Ledger records are source-level with mode-specific artifacts

The ledger should track each source content hash once and attach generated artifacts by output mode.

This matches the user's mental model: a transcript source is known once, and the tool can list which artifact variants exist or are missing.

This is preferred over separate ledger rows for every source-plus-mode pair.

Ledger entries should track per-artifact status, provider/model/schema metadata, derived-work status, and support regeneration from processed archive copies.

The append-only ledger should define a current-state rule such as "last valid record wins per source hash."

Ledger records should be complete current-state snapshots, not partial deltas. V1 ledger events should distinguish primary artifact readiness, completed ingest, failed ingest, quarantine, regeneration, title repair, and derived updates.

### 18. V1 signal extraction should stay factual and minimal

V1 per-meeting signals should use a small taxonomy:

- explicit ask
- stakeholder priority
- decision rationale
- commitment
- risk or concern

Every signal should include evidence, inference level, and confidence.

Communication guidance should be generated during playbook derivation rather than extracted directly into per-meeting signal records.

Duplicate/no-op ingest is a success-class outcome: JSON should use `status: "no_op"` and exit code `0`.

Derived playbook failure should default to exit code `0` after primary artifact success unless the caller explicitly asks derived work to be blocking.

### 19. Communication artifact ingest is a valuable future extension, not the first build target

Emails, memos, Teams messages/threads, screenshots of communications, and related attachments may provide valuable stakeholder voice, commitments, decisions, and requests.

The first implementation should stay focused on meeting/transcript ingestion. However, the architecture should avoid assuming that all future sources are meetings with transcripts. The signal schema, source ledger, and rolling stakeholder playbook should be general enough to later support other communication artifact types.

## Working Assumptions

- The deterministic parts of the current engine are worth preserving.
- The Claude-specific orchestration and packaging boundaries are redesign targets.
- This repo should stay small enough to reason about and strong enough to trust.
- Consistency should come from stable schemas and renderers, not from asking a model to invent final document structure.
- Model/provider use should be right-sized by task, output mode, and quality requirements.
- The default transcript record should be cleaned verbatim: speaker-attributed and lightly cleaned for readability while preserving substantive content.
- Python is the preferred implementation language unless later technical constraints argue otherwise.

## Decision Hygiene

Update this file when a meaningful product boundary, CLI, config, provider, or storage decision is made.
