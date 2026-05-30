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

## Working Assumptions

- The deterministic parts of the current engine are worth preserving.
- The Claude-specific orchestration and packaging boundaries are redesign targets.
- This repo should stay small enough to reason about and strong enough to trust.

## Decision Hygiene

Update this file when a meaningful product boundary, CLI, config, provider, or storage decision is made.
