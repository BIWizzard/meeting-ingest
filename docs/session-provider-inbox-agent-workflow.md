# Session Provider Inbox Agent Workflow

## Purpose

This is the operator-facing workflow for agents processing Meeting Ingest inbox files in the maintainer's personal workflow.

The intended user experience is:

> "There are files in the Meeting Ingest inbox. Process them."

The user should not need to operate the CLI manually. The active agent should run the commands, perform the session-backed extraction step, and report the generated artifact paths.

## Default Assumption

Use `provider=session` by default.

Do not use `mock` for real workflow tests. Do not use an API-backed provider unless the user explicitly asks for it and the privacy gate is enabled.

Session-backed extraction is the default personal workflow because the active Codex, Claude Code, Supa Code, or T3 Code session can provide model judgment without a separate API call.

## Preconditions

Run from the Meeting Ingest project root.

Before processing, confirm `_local/project-context/meetings/meeting-ingest.toml` contains:

```toml
default_provider = "session"

[privacy]
allow_session_provider = true
```

If the config still uses `default_provider = "mock"` or `allow_session_provider = false`, update the local config before processing the inbox.

## Important Current Limitation

`meeting-ingest ingest-inbox` currently rejects `provider=session`.

That is intentional in the current engine because a session-provider ingest has two phases:

1. the engine creates a transcript-bearing provider request
2. the active agent or extraction sub-agent writes the provider response JSON
3. the engine completes validation, rendering, signals, ledger, archive, and reconcile

Until a first-class session inbox wrapper exists, agents should process inbox files by looping over direct files in `_inbox/` and running the two-phase flow for each file.

## Workflow

List direct inbox files:

```bash
find _local/project-context/meetings/_inbox -maxdepth 1 -type f -print
```

For each file, run phase 1:

```bash
uv run meeting-ingest provider-request "$SOURCE" --provider session --quality balanced --json
```

Read the JSON summary. It returns:

- `request_path`
- `expected_response_path`
- `meeting_id`
- `ingest_run_id`
- `source_sha256`
- `output_mode`
- `quality`

The returned handoff paths are relative to the meetings root. The meetings root is normally:

```text
_local/project-context/meetings
```

Read the provider request file. It contains the normalized transcript and identity fields the response must echo.

Write one provider response JSON file at the returned `expected_response_path`. The response must use:

```json
{
  "schema_version": "1.0",
  "handoff_type": "provider_response",
  "provider_contract": "meeting-ingest-provider-response-v1",
  "provider": {
    "name": "session",
    "host": "codex",
    "model_alias": "balanced",
    "model_id": "codex-session",
    "generated_at": "2026-07-03T12:00:00Z"
  },
  "response": {
    "title": "Required title",
    "tl_dr": "Required grounded summary.",
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

Also include the exact `meeting_id`, `ingest_run_id`, `source_sha256`, and `normalized_transcript_sha256` from the request.

Use the current host in `provider.host`:

- `codex`
- `claude-code`
- `supa-code`
- `t3-code`

Use the actual model identifier if the host exposes one. Otherwise use `<host>-session`, such as `codex-session` or `claude-code-session`.

Complete phase 2:

```bash
uv run meeting-ingest ingest "$SOURCE" --provider session --provider-response "$RESPONSE_PATH" --json
```

Confirm the summary includes:

- `status: "success"`
- `provider: "session"`
- `provider_host`
- markdown artifact path
- signal artifact path
- processed archive path
- reconcile status `completed`

Then process the next direct inbox file.

## Response Quality Requirements

The provider response should be useful as a durable project artifact. Extract:

- meeting title
- concise TL;DR
- meeting type
- attendees and role context
- key topics
- decisions
- action items and commitments
- stakeholder asks
- dependencies and risks
- communication signals
- open questions
- cross-references

Ground claims in the transcript. Omit uncertain claims instead of inventing them.

For standups, emphasize:

- status changes
- blocked or risky work
- owner commitments
- due dates and sprint pressure
- stakeholder direction
- carryover risk
- validation or readiness gates

For design/review meetings, emphasize:

- decisions and rationale
- alternatives discussed
- validation evidence
- unresolved questions
- stakeholder asks
- follow-up artifacts

## Do Not

- Do not manually write markdown meeting artifacts.
- Do not manually write enriched signal JSONL.
- Do not manually write ledger records.
- Do not manually move files to `_processed/` or `_inbox/_done/`.
- Do not reuse an old provider request for a new ingest attempt.
- Do not use `mock` when the user is testing the real workflow.

The engine owns all final side effects.

## Completion Message

After processing, report:

- each source processed
- each generated markdown path
- each signal path and count
- whether archive/reconcile completed
- whether any inbox files remain

If processing fails, report the engine error code and the phase that failed.
