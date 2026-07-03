---
name: meeting-ingest
description: Process Meeting Ingest transcript inbox files using the meeting-ingest CLI. Use when the user says there is a new transcript, asks to process the meeting inbox, ingest a transcript, or turn .vtt/.docx/.txt meeting files into structured meeting artifacts.
---

# meeting-ingest

Use this skill to process transcript files through the `meeting-ingest` CLI.

The CLI engine is the source of truth for transcript extraction, provider request/response validation, markdown rendering, signal enrichment, ledger writes, archive, and inbox reconcile behavior.

## Defaults

- Use `provider=session` unless the user explicitly asks for another provider.
- Do not use `mock` for real workflow tests.
- Do not use API-backed providers unless the user explicitly asks and the privacy gate is enabled.
- Run commands from the project root that contains `_local/project-context/meetings/`.
- Prefer `uv run meeting-ingest ...` in this repo.

Before processing, verify `_local/project-context/meetings/meeting-ingest.toml` contains:

```toml
default_provider = "session"

[privacy]
allow_session_provider = true
```

If those values are missing or set differently, update the local workflow config before processing.

## Process The Inbox

When the user says there are transcripts in the inbox, process every direct file in:

```text
_local/project-context/meetings/_inbox/
```

Ignore files already under `_inbox/_done/`.

`meeting-ingest ingest-inbox` does not currently complete session-provider work by itself. Use the two-phase session workflow for each direct inbox file.

Phase 1:

```bash
uv run meeting-ingest provider-request "$SOURCE" --provider session --quality balanced --json
```

Read the returned `request_path` and `expected_response_path`. They are relative to the meetings root.

Use the `meeting-ingest-session-provider` extraction agent when available. Do not use the generic `meeting-transcript-analyzer` agent for Meeting Ingest provider handoffs unless the specific session-provider agent is unavailable.

The session-provider agent should:

1. Read the request JSON.
2. Use the normalized transcript inside it.
3. Write exactly one provider response JSON envelope to the expected response path.
4. Return only a short completion summary.

The provider response must echo the request identity fields:

- `meeting_id`
- `ingest_run_id`
- `source_sha256`
- `normalized_transcript_sha256`

The provider envelope must use:

```json
{
  "schema_version": "1.0",
  "handoff_type": "provider_response",
  "provider_contract": "meeting-ingest-provider-response-v1",
  "provider": {
    "name": "session",
    "host": "claude-code",
    "model_alias": "balanced",
    "model_id": "claude-code-session",
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

Use `provider.host: "claude-code"` when running inside Claude Code. Use the actual model ID if available; otherwise use `claude-code-session`.

Phase 2:

```bash
uv run meeting-ingest ingest "$SOURCE" --provider session --provider-response "$RESPONSE_PATH" --json
```

Confirm the run summary reports:

- `status: "success"`
- `provider: "session"`
- markdown artifact path
- signal artifact path and count
- archive path
- reconcile status `completed`

Continue until no direct inbox files remain.

## Extraction Quality

Provider responses should be grounded in the transcript and include:

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

For standups, emphasize status changes, blockers, risks, owners, due dates, stakeholder direction, validation gates, and carryover risk.

For working sessions or design reviews, emphasize decisions, rationale, alternatives, unresolved questions, implementation risks, and follow-up artifacts.

Omit uncertain claims instead of inventing them.

## Do Not

- Do not manually write final markdown artifacts.
- Do not manually write enriched signal JSONL.
- Do not manually write ledger records.
- Do not manually move files to `_processed/` or `_inbox/_done/`.
- Do not reuse an old provider request for a new ingest attempt.
- Do not run the deprecated `ingest_meeting` package.

The `meeting-ingest` CLI owns final side effects.

## Completion Message

After processing, report:

- each source processed
- generated markdown path
- signal path and count
- archive/reconcile completion
- whether any direct inbox files remain

If processing fails, report the engine error phase and code.
