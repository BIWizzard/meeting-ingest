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

## Current Session Batch Behavior

`meeting-ingest ingest-inbox --provider session --json` performs batch phase 1 for direct inbox files.

A session-provider ingest still has two phases:

1. the engine creates a transcript-bearing provider request
2. the active agent or extraction sub-agent writes the provider response JSON
3. the engine completes validation, rendering, signals, ledger, archive, and reconcile

For session batches, `ingest-inbox` creates one provider request per direct inbox file and returns per-file `request_path` and `expected_response_path` values. It does not perform the model extraction or phase-2 ingest by itself.

Complete pending phase-2 ingests before rerunning the batch, or expect regenerated request paths. Fresh request creation does not write the ledger, but duplicate/no-op files may be reconciled to `_inbox/_done/`, and source-read failures may be quarantined using normal ingest behavior.

## Workflow

Run the session inbox wrapper:

```bash
uv run meeting-ingest session-inbox --quality balanced --json
```

The CLI wrapper prepares the same handoff files as `ingest-inbox --provider session`.
Because a plain CLI process cannot invoke the active model session by itself, it reports
`pending_provider_response` entries until the active agent writes the expected response
files and runs phase 2.

The reusable automation hook for host wrappers is `meeting_ingest.session_inbox.process_session_inbox`.
Pass an extractor callback that reads the request payload and writes the response envelope
to the expected response path. The wrapper then calls phase 2 for each completed response
and reports markdown, signals, archive, and reconcile paths.

For interruption recovery, `session-inbox` first scans existing provider request files
under `_cache/provider-requests/`. If a matching response file already exists, it runs
phase 2 before creating new requests. If an existing request is still waiting for a
response, it reports that pending handoff and skips fresh phase 1 so the wrapper does
not mint a second request for the same inbox file.

If an existing request cannot be safely rebound to a direct inbox source, the wrapper
reports `status: "stale_handoff"` with a cleanup hint rather than failing the batch.
This can happen for old retained failure pairs, requests for external sources, missing
inbox files, or hash mismatches. Complete those manually with the lower-level phase-2
command when appropriate, or remove stale request/response files after confirming they
are no longer needed.

Use `uv run meeting-ingest status --json` to inspect pending, stale, and invalid
session handoffs without running the wrapper. Use `uv run meeting-ingest doctor --json`
to surface those handoffs as hygiene issues.

Lower-level phase 1:

```bash
uv run meeting-ingest ingest-inbox --provider session --quality balanced --json
```

Read the JSON summary. Each result with `status: "pending_provider_response"` returns these fields under `details`:

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

For each pending result, read the provider request file. It contains the normalized transcript and identity fields the response must echo.

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

Complete phase 2 for the same source:

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

Then process the next pending result.

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
