# Current Questions — meeting-ingest

## Purpose

This file tracks the highest-value open questions for the `meeting-ingest` rebuild.

The goal is to keep design exploration focused on decisions that materially shape the engine and its usability across hosts and projects.

## Open Questions

### 1. What should the project-local directory and config layout be?

Likely concerns:
- meetings root
- `_inbox/`
- `_processed/`
- `_signals/`
- `_quarantine/`
- `_done/`
- ledger
- project config

Why it matters:
- this defines the operating model
- first-run usability depends on it

### 2. Should `ingest` auto-init missing structure, or should init be explicit?

Why it matters:
- affects user friction
- affects predictability
- shapes CLI philosophy

Good answer characteristics:
- low-friction
- safe
- easy to reason about

### 3. What should the stable CLI surface be?

Candidate commands:
- `meeting-ingest init`
- `meeting-ingest ingest`
- `meeting-ingest reconcile`
- `meeting-ingest doctor`
- `meeting-ingest status`

Why it matters:
- this becomes the canonical interface
- hosts should wrap this, not invent different semantics

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

Why it matters:
- determines portability across hosts and models

### 6. What should be user-global vs project-local identity state?

Examples:
- global roster
- project-local overrides
- aliases
- uncertain matches

Why it matters:
- affects cross-project portability
- affects operational clarity

### 7. How should failure handling and quarantine work?

Need to decide:
- unsupported formats
- extraction failure
- partial write handling
- bad or ambiguous identity resolution
- corrupt source input

Why it matters:
- ingest reliability depends on this

### 8. What is the migration path from the existing Claude-first implementation?

Need to decide:
- what code to port directly
- what to rewrite
- what behavior to preserve exactly
- what packaging/orchestration assumptions to discard

Why it matters:
- preserves momentum without freezing old architecture into place

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

## Already Decided

- this repo stays focused on the ingestion engine
- product direction is CLI-first and host-neutral
- first-run project setup is required
- strong done-process semantics are required
- idempotency stays content-hash based
- `iQ Context` is separate but complementary

## Not In Scope Right Now

- broad generic ingestion types beyond the current meeting/transcript focus
- collapsing into a generic agentic-toolbox repo
- premature rebranding into a larger product family
- dashboard-first design

## How To Use This File

When starting a new exploration thread, pick 1-3 questions from this file and drive them toward concrete architecture proposals or decisions. Avoid trying to answer everything in a single pass.
