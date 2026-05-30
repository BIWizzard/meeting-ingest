# Context Primer — meeting-ingest

## Why This Repo Exists

`meeting-ingest` is the platform-agnostic rebuild of a meeting and transcript ingestion workflow originally developed as a user-level Claude Code skill.

It solves a real workflow problem:

- teams and solo builders accumulate meeting artifacts quickly
- those artifacts contain project decisions, action items, constraints, risks, and communication signals
- raw transcripts are too noisy to be directly useful
- ingest needs a strong done process, not ad hoc summarization

This repo exists to turn that working but Claude-first workflow into a host-neutral ingestion engine that can be used from:

- Codex
- Claude Code
- Codex via T3 harness
- optionally Gemini CLI
- plain shell / automation

## Existing Implementation Reference

This rebuild is not starting from zero. The current working implementation lives as a user-level Claude skill here:

- `~/.claude/skills/ingest-meeting/`

That skill contains the current Python ingestion engine, CLI, path model, bootstrap logic, ledger behavior, and the Claude-specific orchestration contract.

Important: this repo (`meeting-ingest`) is now the rebuild target, but the existing skill directory remains the primary reference source for current behavior.

## Source Files To Read First From The Existing Skill

When exploring or migrating, start with these files in the existing skill:

- `~/.claude/skills/ingest-meeting/SKILL.md`
- `~/.claude/skills/ingest-meeting/ingest_meeting/cli.py`
- `~/.claude/skills/ingest-meeting/ingest_meeting/pipeline.py`
- `~/.claude/skills/ingest-meeting/ingest_meeting/extract.py`
- `~/.claude/skills/ingest-meeting/ingest_meeting/identity.py`
- `~/.claude/skills/ingest-meeting/ingest_meeting/ledger.py`
- `~/.claude/skills/ingest-meeting/ingest_meeting/roster.py`
- `~/.claude/skills/ingest-meeting/ingest_meeting/bootstrap.py`
- `~/.claude/skills/ingest-meeting/ingest_meeting/paths.py`
- `~/.claude/skills/ingest-meeting/ingest_meeting/events.py`

These files collectively show:

- the current ingestion contract
- the deterministic engine behavior
- the source-ledger/archive/reconcile model
- the current global path assumptions
- the split between core engine logic and Claude-specific orchestration

## What The Existing Workflow Already Does Well

The current workflow already has meaningful product shape:

- transcript extraction from `.docx`, `.txt`, and `.vtt`
- meeting date and type detection
- deterministic meeting ID generation
- structured markdown meeting summary generation
- structured observations / signal extraction
- roster-based person resolution
- append-only project-local signal/event output
- source-ledger idempotency keyed by file content hash
- canonical processed-copy archive behavior
- inbox reconciliation only after ledger-confirmed success

The durable asset is the ingest engine, not the old Claude wrapper.

## What To Preserve From The Existing Implementation

The rebuild should assume the following are valuable unless a strong reason emerges to change them:

- content-hash idempotency
- deterministic meeting identity
- structured markdown output
- structured signals / observations output
- archive copy behavior
- reconcile-only-after-success discipline
- clear separation between deterministic mechanics and LLM extraction step
- roster-based identity resolution as a concept

## Rebuild Goal

Build one normal package/CLI/library that preserves the workflow semantics but removes host lock-in.

The rebuilt tool should:

- work consistently across hosts
- support project-local first-run setup
- remain idempotent and provenance-aware
- keep the done process strong
- expose a host-neutral extraction/provider boundary

## What To Replace Or Redesign

The rebuild should assume the following are likely redesign targets:

- skill/package location under `~/.claude/...`
- global roster assumptions under Claude-owned directories
- orchestration primarily described in `SKILL.md`
- CLI stub extraction path that is not fully self-sufficient for real ingest
- host-specific model assumptions
- conceptual identity of the product as “a Claude skill” instead of “an ingest engine with adapters”

## Recommended Product Boundary

This repo should remain focused on the meeting ingestion tool itself.

It should not turn into a generic “agentic tools” repo unless multiple mature tools later prove that a shared runtime truly exists.

For now:

- this repo = ingestion engine
- `iQ Context` = separate session/context OS

They should integrate, not merge.

## Core Requirements

### 1. First-Run Project Setup

If invoked in a new project, the tool should be able to initialize missing structure safely.

That likely means:

- project-local config
- meetings root
- `_inbox/`
- `_processed/`
- `_signals/`
- `_quarantine/`
- `_done/` or equivalent reconciled-source area
- ledger file

Exact structure is open to design, but the experience should be low-friction and portable.

### 2. Strong Done Process

Ingest should mean:

1. read source
2. normalize transcript text
3. produce structured markdown
4. produce structured signals/events
5. record ledger entry
6. archive canonical processed copy
7. reconcile source only after success is confirmed
8. emit a clear run summary

### 3. Idempotency

Duplicate ingest protection should be keyed by content hash, not filename.

### 4. Provider Abstraction

The extraction step should be provider-backed and host-neutral.

Likely providers:

- Anthropic
- OpenAI
- Gemini
- mock/testing provider

### 5. Identity / Roster Boundary

People resolution should not be hardwired to `~/.claude/...`.

Preferred direction:

- optional user-global roster
- optional project-local overrides
- deterministic resolution order
- unresolved identities surfaced cleanly

### 6. Provenance

Every important output should preserve provenance:

- source file
- meeting ID
- ingest run ID
- effective date
- speaker/person info where available
- certainty boundaries where useful

## Relationship To iQ Context

`meeting-ingest` and `iQ Context` are separate but complementary.

- `meeting-ingest` produces structured project artifacts
- `iQ Context` can later track, embed, retrieve, and surface those artifacts
- `meeting-ingest` should not depend on `iQ Context`
- `iQ Context` may optionally recognize or initialize meeting-ingest project structure

The right mental model is:

- `iQ Context` = session/context OS
- `meeting-ingest` = specialized artifact producer

## Candidate CLI Shape

Likely command family:

- `meeting-ingest init`
- `meeting-ingest ingest`
- `meeting-ingest reconcile`
- `meeting-ingest doctor`
- `meeting-ingest status`

Hosts should wrap this CLI or its library API instead of reimplementing the behavior.

## Questions To Explore In This Repo

1. What should the project-local directory and config layout be?
2. Should `ingest` auto-init missing structure, or should init be explicit?
3. What should the extraction contract look like?
4. How should provider plugins be modeled?
5. How should roster state be split between global and project-local scopes?
6. How should failures, quarantine, and partial writes be handled?
7. How should tests cover deterministic ingest behavior vs provider-backed extraction?
8. What is the cleanest migration path from the current Claude-first implementation?

## Non-Goals

This repo is not trying to become:

- a generic note-taking app
- a full session operating system
- a broad knowledge platform
- an all-purpose agent framework

It is a specific ingestion pipeline that should be done well.

## Migration Stance

This repo should treat the old skill directory as:

- the behavior reference
- the source of reusable engine code
- the source of current constraints and path assumptions

It should not preserve Claude-specific packaging or orchestration boundaries unless there is a strong reason to do so.
