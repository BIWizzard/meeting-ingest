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
- Invoke the CLI only through the approved executable set in the next section. Do not use `uv run meeting-ingest` or ambient PATH resolution.

Before processing, verify `_local/project-context/meetings/meeting-ingest.toml` contains:

```toml
default_provider = "session"

[privacy]
allow_session_provider = true
```

If those values are missing or set differently, update the local workflow config before processing.

## Approved Executable

Set the approved executable once per session and use it for every `meeting-ingest` command in this skill:

```bash
MEETING_INGEST="{{MEETING_INGEST_APPROVED_EXECUTABLE}}"
```

This is the canonical executable recorded in the consumer pin for the maintainer-only private-alpha channel. Every command below runs as `"$MEETING_INGEST" <args>`. Never substitute `uv run meeting-ingest`, an editable checkout, or ambient PATH resolution.

## Step 0: Runtime Readiness Gate

Before any natural-language inbox processing, check runtime readiness:

```bash
"$MEETING_INGEST" readiness --host claude-code --json
```

Read `verdict` from the JSON and continue only as follows:

- `ready` or `ready_with_history_warnings`: proceed with the workflow.
- `development_override`: proceed only when the user has explicitly authorized the override reason in this session. Pass `--development-override "<reason>"` on every mutating command (`session-inbox`, `provider-request`, `ingest`), using the exact authorized reason, and state in the completion message that the results are development-marked.
- `blocked` (exit `12`): stop and report the findings. Do not process the inbox. Read-only commands (`status`, `doctor`, `readiness`, `runtime inspect`) remain usable while blocked.

Keep the readiness JSON for the completion report. It carries `running_build`, `runtime_provenance`, and `verdict`, which the completion message must echo.

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
"$MEETING_INGEST" session-inbox --quality balanced --json
```

For each result with `status: "pending_provider_response"`, read the returned `details.request_path` and `details.expected_response_path`. They are relative to the meetings root.

Before extraction, inspect `details.effective_date` (or the request's `date_confidence`). If confidence is `low`, do not write a response or run phase 2. Confirm the occurrence date with the user, then create a fresh request for that source with:

```bash
"$MEETING_INGEST" provider-request "$SOURCE" --provider session --quality balanced --meeting-date YYYY-MM-DD --json
```

Use only the fresh request and response paths. Never allow an unconfirmed low-confidence date to mint the final meeting artifact.

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
  "semantic_guidance_version": "copy from request",
  "provider": {
    "name": "session",
    "host": "claude-code",
    "model_alias": "copy request quality",
    "model_id": "actual model ID or claude-code-session",
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
- `communication_signals`: `signal_type`, optional `stakeholder_id`, `stakeholder_name`, `summary`, `evidence`, `inference_level`, `confidence`, optional `topics`, `project_refs`, `recurrence`, `status`; `evidence` uses `kind`, `text`, `speaker`, and optional `timestamp`. `speaker` is required whenever the transcript has speaker labels — the generated response contract lists it in `evidence.required` and enum-binds it to the grounding set. `timestamp` may be omitted or null
- `open_questions`: `id`, `question`, `owner_next_step`, `evidence`, optional `status`
- `cross_references`: strings

Use `provider.host: "claude-code"` when running inside Claude Code. Use the actual model ID if available; otherwise use `claude-code-session`.

Raw labels, evidence speakers, and evidence timestamps must satisfy the request's `transcript_grounding` exactly, and the extraction must obey the request's `semantic_guidance_rules`. See `Grounding And Semantic Guidance` below before writing the response.

Validate the completed response before phase 2:

```bash
"$MEETING_INGEST" validate-response "$RESPONSE_PATH" --source "$SOURCE" --json
```

Proceed only when it reports `status: "success"`, `provider_response.status: "valid"`, and `runtime_readiness.verdict` is not `blocked`. For provider-validation failures, correct every entry in `errors[0].details.issues`; for a `source_read` failure, correct the `--source` path. A blocked readiness verdict uses exit `12` even when the response payload itself is valid. Then re-run the preflight. The preflight has no ledger, artifact, archive, reconcile, or cache-cleanup side effects.

Phase 2:

```bash
"$MEETING_INGEST" ingest "$SOURCE" --provider session --provider-response "$RESPONSE_PATH" --json
```

Confirm the run summary reports:

- `status: "success"`
- `provider: "session"`
- markdown artifact path
- signal artifact path and count
- archive path
- reconcile status `completed`

Continue until no direct inbox files remain.

## Grounding And Semantic Guidance

Every request carries `transcript_grounding`, the engine's index of `normalized_transcript`, holding `speaker_labels` and `timestamps` in first-seen order and deduplicated. It is the only authority for attendee raw labels and signal evidence locators, and the engine re-checks every one of them before any durable write.

- Every `attendees[].raw_labels[]` entry is an exact copy of one `transcript_grounding.speaker_labels` entry. Raw labels are source labels, not normalized display names and not inferred affiliations.
- Never add, remove, or edit a parenthetical qualifier, and never recase or repunctuate. `Opeyemi, Baba` and `Opeyemi, Baba (Contractor)` are two different labels; neither may stand in for the other, and a qualifier on one label says nothing about a person whose label lacks it.
- Copy verbatim. The engine's check is set membership after collapsing repeated whitespace, so whitespace runs are the only tolerated difference; capitalization, punctuation, comma order, and qualifiers are all compared as-is and any other departure fails.
- Every `communication_signals[].evidence.speaker` is an exact copy of one `transcript_grounding.speaker_labels` entry. It is the transcript utterer of the evidence, not its audience or directed-to party, and it is required for every person-directed signal. If no speaker can be grounded, omit the signal instead of substituting the display-oriented `stakeholder_name`.
- `communication_signals[].evidence.timestamp` is `null` or an exact copy of one `transcript_grounding.timestamps` entry. Do not reconstruct a timestamp from the transcript body.
- `display_name` and `role_context` may summarize grounded evidence, but they must not alter a raw label or assert an alias, affiliation, or shared identity the transcript does not state.
- When `speaker_labels` is empty, `attendees[].raw_labels` and `communication_signals` must both be empty. When `timestamps` is empty, every evidence timestamp must be `null`.

Every request also carries `semantic_guidance_version` and `semantic_guidance_rules`. The rules array is the exact published text for the bound version. Obey it rather than a remembered prompt revision, and echo `semantic_guidance_version` into the response envelope unchanged. A persisted request that predates the field is the one exception: omit `semantic_guidance_version` from the response, or send `"legacy"`. Never invent a version the request did not bind. For version `"1.0"` the rules are:

1. Preserve nearby time context. Do not add AM/PM unless it is explicit or unambiguously established by phrases such as "last run of the night."
2. Separate observations, hypotheses, and confirmed causes. Do not use "caused by," "traced to," or equivalent causal language when root cause remains open.
3. Record a proposal as a decision only when the transcript shows acceptance. Record an action only when an owner accepts it or a direction is acknowledged.
4. Never carry a rejected or infeasible proposal into open actions.
5. Do not merge people from nickname similarity alone. Conflicting or incomplete alias evidence stays unresolved and receives low confidence.
6. Keep the TL;DR consistent with the detailed topics, decisions, risks, actions, and open questions.

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

- readiness verdict (`verdict` from step 0)
- build ID (`running_build` from the readiness JSON)
- runtime mode (`runtime_provenance.runtime_mode` from the readiness JSON)
- each source processed
- generated markdown path
- signal path and count
- archive/reconcile completion
- whether any direct inbox files remain

If the run used a development override, state that the results are development-marked and include the override reason.

If processing fails, report the engine error phase and code.
