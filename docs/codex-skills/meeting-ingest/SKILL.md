---
name: meeting-ingest
description: Process Meeting Ingest transcript inbox files using the meeting-ingest CLI. Use when the user says there is a new transcript, asks to process the meeting inbox, ingest a transcript, or turn .vtt/.docx/.txt meeting files into structured meeting artifacts.
---

# meeting-ingest

Use this skill to process transcript files through the `meeting-ingest` CLI.

The CLI engine is the source of truth for transcript extraction, provider request/response validation, markdown rendering, signal enrichment, ledger writes, archive, and inbox reconcile behavior.

## Reference-Host Boundary

Claude Code is the reference host for the approved Meeting Ingest runtime. Codex is not a reference host. Codex runs are development/non-release evidence only until separately approved. A Codex run must not claim approved-runtime, `Ready`, or approved-client status. Label all Codex results as development/non-release evidence in the completion output.

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

`meeting-ingest session-inbox --json` is the active-agent wrapper surface. In plain CLI use it creates session-provider requests for each direct inbox file and reports `pending_provider_response` entries because the CLI cannot invoke the active model session by itself.

It scans existing provider requests first, completes ready responses before creating fresh requests, and skips fresh phase 1 while unresolved handoffs remain.

It reports old or out-of-scope request files as non-failing `stale_handoff` results with a cleanup hint. Legacy or invalid runtime bindings instead block the wrapper with exit `12`, skip extraction and fresh phase 1, and require restoring the reviewed request or explicitly abandoning it before reminting.

To abandon after review, use the exact `details.request_path` and `details.expected_response_path` from `status --json`, remove only that named pair, and rerun `session-inbox`. Never delete the whole provider cache.

`meeting-ingest ingest-inbox --provider session --json` is the lower-level phase-1 command. It also creates session-provider requests for each direct inbox file. It does not complete the model extraction or phase-2 ingest by itself.

Phase 1:

```bash
uv run meeting-ingest session-inbox --quality balanced --json
```

For each result with `status: "pending_provider_response"`, read the returned `details.request_path` and `details.expected_response_path`. They are relative to the meetings root.

Before extraction, inspect `details.effective_date` (or the request's `date_confidence`). If confidence is `low`, do not write a response or run phase 2. Confirm the occurrence date with the user, then create a fresh request for that source with:

```bash
uv run meeting-ingest provider-request "$SOURCE" --provider session --quality balanced --meeting-date YYYY-MM-DD --json
```

Use only the fresh request and response paths. Never allow an unconfirmed low-confidence date to mint the final meeting artifact.

## Session Provider Extraction

The session-provider extraction step must produce provider-level JSON only.

If a focused sub-agent facility is available, use a dedicated extraction sub-agent and instruct it to:

1. Read the request JSON.
2. Use the normalized transcript inside it.
3. Write exactly one provider response JSON envelope to the expected response path.
4. Return only a short completion summary.

If no focused sub-agent is available, the active Codex agent may perform this extraction itself, but it must still write only the provider response envelope and must not bypass the engine.

The provider response must echo the request identity fields:

- `meeting_id`
- `ingest_run_id`
- `source_sha256`
- `normalized_transcript_sha256`
- `runtime_provenance_sha256`

Every request contains `response_contract.json_schema`, which is the complete request-bound response contract. Follow it directly: its `const` values contain the exact identity fields and model alias for this handoff, and its nested schemas list required field names and allowed enum values.

Use the request's `response_contract.preflight_command` for validation. Development-mode requests include the exact escaped `--development-override` reason required to preserve the runtime binding.

The provider envelope must use:

```json
{
  "schema_version": "1.1",
  "handoff_type": "provider_response",
  "provider_contract": "meeting-ingest-provider-response-v1",
  "meeting_id": "copy from request",
  "ingest_run_id": "copy from request",
  "source_sha256": "copy from request",
  "normalized_transcript_sha256": "copy from request",
  "runtime_provenance_sha256": "copy from request",
  "provider": {
    "name": "session",
    "host": "codex",
    "model_alias": "copy request quality",
    "model_id": "actual model ID or codex-session",
    "generated_at": "current UTC timestamp"
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

Exact array item fields:

- `attendees`: `person_id`, `display_name`, `raw_labels`, `role_context`, `confidence`
- `topics`: `id`, `topic`, `summary`, `evidence`
- `decisions`: `id`, `decision`, `owner_decider`, `evidence`, optional `status`
- `action_items`: `id`, `owner`, `action`, `due_timing`, `evidence`, optional `status`
- `stakeholder_asks`: `id`, `stakeholder`, `ask`, `directed_to`, `evidence`, optional `status`
- `dependencies_risks`: `id`, `type`, `description`, `owner_related_party`, `impact`, optional `status`
- `communication_signals`: `signal_type`, optional `stakeholder_id`, `stakeholder_name`, `summary`, `evidence`, `inference_level`, `confidence`, optional `topics`, `project_refs`, `recurrence`, `status`; `evidence` uses `kind`, `text`, optional `speaker`, `timestamp`
- `open_questions`: `id`, `question`, `owner_next_step`, `evidence`, optional `status`
- `cross_references`: strings

Use `provider.host: "codex"` when running inside Codex. Use the actual model ID if available; otherwise use `codex-session`.

Validate the completed response before phase 2:

```bash
uv run meeting-ingest validate-response "$RESPONSE_PATH" --source "$SOURCE" --json
```

Proceed only when it reports `status: "success"`, `provider_response.status: "valid"`, and `runtime_readiness.verdict` is not `blocked`. For provider-validation failures, correct every entry in `errors[0].details.issues`; for a `source_read` failure, correct the `--source` path. A blocked readiness verdict uses exit `12` even when the response payload itself is valid. Then re-run the preflight. The preflight has no ledger, artifact, archive, reconcile, or cache-cleanup side effects.

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

## Post-Ingest Capture

After each successfully processed meeting (ledger and signal writes confirmed), record it in iQ Context from the repo root — one capture per meeting, not per intermediate artifact:

```bash
iq-context capture \
  --file _local/project-context/meetings/<final-meeting-doc>.md \
  --note "Processed meeting: <title> (<meeting date>). Key outcomes: <1-2 line takeaways>. Decisions: <ids or 'none'>."
```

Lead the note with the meeting title and effective date, summarize outcomes in one or two lines, and name decisions or action items explicitly — those are what future sessions search for.

## Completion Message

After processing, report:

- each source processed
- generated markdown path
- signal path and count
- archive/reconcile completion
- whether any direct inbox files remain
- that these results are Codex development/non-release evidence, not approved-runtime output

If processing fails, report the engine error phase and code.
