# Extraction Model Evaluation — Decision Brief

**Date:** 2026-07-24
**Origin:** agent-orchestration workstream (`~/.claude`), meeting-ingest inheritance analysis
**Decision owner:** this project (meeting-ingest)
**Board:** not warranted — an experiment answers this; treat as a cheap consult, not a convening.

## Question

Is Sonnet 5 the right model for Meeting Ingest session-provider extraction, and should the CLI's `quality` alias map to different model tiers instead of one fixed pin?

## Background

The global orchestration policy (`~/.claude/CLAUDE.md`) routes work through a role registry (orchestrator / claude-implementer / codex-workhorse). Analysis on 2026-07-24 found Meeting Ingest's extraction path does not pass through that routing: the `meeting-ingest` skill hard-names the `meeting-ingest-session-provider` agent, whose definition pinned `model: sonnet` — a bare alias that silently floated across model generations (it rode Sonnet 4 → Sonnet 5 with no review). The generic `meeting-transcript-analyzer` agent had the same bare pin.

## Already decided and done (mechanism half, in `~/.claude`)

These are in effect now and are not this project's decision:

- Both extraction agents are hard-pinned to `claude-sonnet-5` — the model that was already running, so behavior is unchanged.
- A `meeting-extraction` row in the global role registry names both agent files as the swap point; future generation changes are deliberate one-line edits, not silent drift.
- The global pin lint now fails bare model aliases in agent definitions.

## This project's decisions (product half)

### 1. Run the comparison experiment

Pick one to three already-ingested transcripts of different meeting types (a standup, a working session). Re-run extraction on the same normalized transcripts at the claude-implementer tier (Opus 4.8) and diff the provider envelopes against the shipped Sonnet 5 outputs. Structural validity is CLI-enforced and will not differ; compare the judgment-flavored fields:

- topic/decision/action-item recall and precision against the transcript
- communication-signal quality and `inference_level` calibration
- stakeholder-ask and dependency/risk extraction
- grounding — does either model invent or omit?

### 2. Decide the model policy

Choose one, on the experiment's evidence:

- **Keep Sonnet 5 as the sole pin** — if Opus shows no material lift, cheapest and simplest.
- **Switch the pin to Opus 4.8** — if the lift is material across all meeting types.
- **Map the `quality` alias to tiers** — `balanced` → Sonnet 5, `high` → Opus 4.8, chosen per meeting at ingest time. Before adopting, verify how `quality` flows into the request's `response_contract` const values and runtime provenance — establish whether a tier map is purely agent-side (parent session picks the agent/model by requested quality) or needs CLI awareness.

### 3. Reaffirm or amend the privacy stance

Transcript content currently stays session-side by architecture: the session provider exists for this, and API-backed providers sit behind the privacy gate in `meeting-ingest.toml`. Routing extraction to codex-workhorse (OpenAI) would subvert that gate, so it is off the table unless explicitly ruled otherwise here. Note the boundary: this is a data-plane rule — repo *code* work may still route to codex under the global policy (`AGENTS.md` already contemplates Codex agents in this repo).

## Constraints

- Refer to roles, never concrete model names, in any durable project doc; the registry in `~/.claude/CLAUDE.md` is the single swap point.
- Any pin change lands as an edit to the agent files named in the registry row and fires the global pin-lint check-in (OB-003-3) in `~/.claude` — route that edit back through an agent-orchestration session or make it and run `scripts/claude-md-lint.sh` there.
- The provider response's `provider.model_id` field records the actual model — the envelopes already carry the provenance needed to compare runs.

## Deliverable

A recorded decision (DECISIONS.md and/or iq-context capture) covering: the model policy chosen, the evidence (envelope diffs), the privacy reaffirmation, and — if the quality→tier map is adopted — a scoped work item for the agent/skill/CLI changes, with the pin edits routed back to `~/.claude`.

---

## Context prime (paste into a meeting-ingest session)

> Start with /iq-go, then read docs/plans/2026-07-24-extraction-model-evaluation.md — a decision brief handed off from the agent-orchestration workstream. Execute it: (1) select 1–3 already-processed meetings of different types and re-run session-provider extraction on their normalized transcripts at the claude-implementer tier (Opus 4.8), without touching ledgers, archives, or reconcile state — provider envelopes only, written to a scratch location, never the expected response paths; (2) diff those envelopes against the shipped Sonnet 5 outputs on the judgment fields named in the brief; (3) decide among keep-Sonnet / switch-to-Opus / quality→tier mapping, verifying first how `quality` flows into the response contract if the mapping is on the table; (4) reaffirm or amend the transcript privacy stance; (5) record the decision in DECISIONS.md, capture it with iq-context, and if any agent-pin change is needed, emit a work item routed back to ~/.claude rather than editing pins from this repo.
