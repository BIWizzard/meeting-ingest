# meeting-ingest

`meeting-ingest` is a platform-agnostic meeting and transcript ingestion tool.

It is intended to turn raw meeting artifacts such as `.docx`, `.txt`, and `.vtt` files into structured project knowledge with a strong done process.

## Why

Meeting transcripts often contain real project value:

- decisions
- action items
- asks
- dependencies
- risks
- communication signals
- stakeholder intent

But raw transcripts are noisy and hard to reuse directly.

`meeting-ingest` exists to transform those artifacts into durable, structured project outputs that are consistent, idempotent, and easy to integrate into broader workflows.

## Product Direction

The first serious build is scoped around the maintainer's personal and professional workflows. Broader productization may come later, but early design should solve the real current workflow first.

The long-term target is a host-neutral engine that can work cleanly with:

- Codex
- Claude Code
- Codex via T3 harness
- Supa Code
- optionally Gemini CLI
- plain shell automation

The tool should support:

- project-local first-run initialization
- deterministic meeting IDs
- structured markdown outputs
- selectable output modes, including summary-only and summary-plus-verbatim
- structured signals / observations
- stakeholder communication signals
- source-ledger idempotency
- processed archives
- inbox reconciliation only after confirmed success

## Design Principles

- One engine, many wrappers
- Strong done process
- Provenance matters
- Idempotency by content hash, not filename
- Provider-backed extraction should be swappable
- Human-readable project artifacts remain important

## Relationship To iQ Context

`meeting-ingest` is separate from `iQ Context`.

- `meeting-ingest` = specialized artifact producer
- `iQ Context` = session/context operating system

They should integrate cleanly, but they should not be collapsed into one codebase prematurely.

## Repo Focus

This repo is for the ingestion tool itself.

It should stay focused on:

- transcript extraction
- structured meeting summarization
- signal extraction
- roster/identity resolution
- project-local ingest directories and config
- archive/ledger/reconcile behavior
- host-neutral CLI and provider model

## Current Status

Python CLI/library implementation with:

- project initialization
- single-file ingest
- sequential inbox batch ingest
- mock provider for local deterministic tests
- Anthropic provider adapter behind an explicit privacy gate
- session provider handoff for subscription-backed host sessions
- cleaned-verbatim transcript extraction for `.txt`, `.vtt`, and `.docx`
- markdown artifact rendering
- signal JSONL output
- append-only ledger
- archive/reconcile behavior
- doctor/status/reconcile commands

## Development

Run the current scaffold tests with:

```bash
python3 -m pytest
```

Initialize a project-local meetings layout with:

```bash
python3 -m meeting_ingest.cli init --root . --json
```

Ingest one source:

```bash
python3 -m meeting_ingest.cli ingest _local/project-context/meetings/_inbox/example.vtt --json
```

Ingest every direct file in `_inbox/`:

```bash
python3 -m meeting_ingest.cli ingest-inbox --json
```

## Providers

The default provider is `mock`, which never sends transcript content outside the local process.

Anthropic is available only when remote provider use is explicitly enabled:

```toml
[privacy]
allow_remote_provider = true
```

Set the API key in the environment:

```bash
export ANTHROPIC_API_KEY=...
```

Then request Anthropic explicitly:

```bash
python3 -m meeting_ingest.cli ingest _local/project-context/meetings/_inbox/example.vtt --provider anthropic --json
```

Quality aliases map to Anthropic models as follows:

- `fast`: `claude-haiku-4-5`
- `balanced`: `claude-sonnet-5`
- `deep`: `claude-opus-4-8`

Session-backed extraction is available only when the session provider privacy gate is enabled:

```toml
[privacy]
allow_session_provider = true
```

Use `provider-request` to create a transcript-bearing request for the active host session:

```bash
python3 -m meeting_ingest.cli provider-request _local/project-context/meetings/_inbox/example.vtt --provider session --quality balanced --json
```

The command returns `request_path` and `expected_response_path`. A dedicated extraction agent should read the request file and write the expected response envelope. The response envelope must use `provider.name: "session"` and place the structured meeting extraction under `response`:

```json
{
  "schema_version": "1.0",
  "handoff_type": "provider_response",
  "provider_contract": "meeting-ingest-provider-response-v1",
  "meeting_id": "mtg-20260703-abc12345",
  "ingest_run_id": "ingest-20260703-20260703T120000Z-abcd",
  "source_sha256": "...",
  "normalized_transcript_sha256": "...",
  "provider": {
    "name": "session",
    "host": "codex",
    "model_alias": "balanced",
    "model_id": "codex-session",
    "generated_at": "2026-07-03T12:00:00Z"
  },
  "response": {
    "title": "Example meeting",
    "tl_dr": "Short grounded summary.",
    "meeting_type": "unknown",
    "attendees": [],
    "topics": [],
    "decisions": [],
    "action_items": [],
    "stakeholder_asks": [],
    "dependencies_risks": [],
    "communication_signals": [],
    "open_questions": [],
    "cross_references": []
  }
}
```

Complete the ingest with the response file:

```bash
python3 -m meeting_ingest.cli ingest _local/project-context/meetings/_inbox/example.vtt --provider session --provider-response _local/project-context/meetings/_cache/provider-responses/ingest-20260703-20260703T120000Z-abcd.response.json --json
```

Phase 2 requires the persisted request file that matches the response `ingest_run_id`; arbitrary response-only ingests are rejected. The response path may be absolute or relative and does not have to live under `_cache/provider-responses`, though that cache path is the default. If `--mode` or `--quality` is supplied during phase 2 and differs from the persisted request, the engine uses the persisted request values and emits a warning.

For a reusable extraction sub-agent prompt, see [Session Provider Sub-Agent Prompt](docs/session-provider-subagent-prompt.md). For host-specific wrapper starting points, see [Session Provider Host Wrapper Snippets](docs/session-provider-host-wrappers.md). For the current agent-operated inbox workflow, see [Session Provider Inbox Agent Workflow](docs/session-provider-inbox-agent-workflow.md).

## Start Here

- [Context Primer](docs/context-primer.md)
- [Claude Code Review Prompt](docs/claude-code-review-prompt.md)
- [Personal Workflow Scope](docs/personal-workflow-scope.md)
- [Current Output Evaluation](docs/current-output-evaluation.md)
- [Design Proposal](docs/design-proposal.md)
- [Artifact Contract](docs/artifact-contract.md)
- [Implementation Plan](docs/implementation-plan.md)

The context primer is the agent-optimized starting point for architecture and roadmap exploration. The personal workflow scope captures the initial product requirements that should guide near-term design. The current output evaluation summarizes what to preserve and improve from real Claude skill outputs. The design proposal turns those findings into an initial implementation shape. The artifact contract defines the markdown, signal, ledger, and run-summary surfaces for implementation. The implementation plan translates those contracts into build milestones and agent work lanes.
