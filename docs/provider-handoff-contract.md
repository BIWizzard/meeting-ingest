# Provider Handoff Contract

## Purpose

This document defines how host/session-backed provider extraction hands structured model output back to the Meeting Ingest engine.

The goal is to support subscription-backed agentic harnesses such as Claude Code, Codex, Supa Code, and T3 Code without fragmenting product behavior. A host wrapper may use the active session to obtain model judgment, but the engine remains responsible for source extraction, provider-output validation, deterministic rendering, signal enrichment, ledger writes, archive, reconcile, and run summaries.

## Roles

### Engine

The engine owns:

- project discovery, config, privacy gates, and locking
- source hashing and duplicate/no-op detection
- source text extraction and normalized transcript generation
- `meeting_id` and `ingest_run_id` minting
- provider request file creation for host/session-backed extraction
- provider response JSON parsing into `ProviderResponse`
- provider request/response identity verification
- `validate_provider_response`
- stable person identity normalization
- conversion of `ProviderSignal` candidates into enriched `SignalRecord` records
- markdown rendering
- signal JSONL writing
- ledger snapshots
- processed archive copy and inbox reconcile
- JSON run summary and exit code

### Host Wrapper

A host wrapper owns:

- invoking the engine CLI/library
- invoking a dedicated extraction sub-agent when `provider=session` or equivalent host/session mode is requested
- passing request and response file paths between the engine and the sub-agent
- reporting the engine run summary to the user

The wrapper must not implement artifact rendering, signal enrichment, ledger writes, archive, reconcile, or duplicate/no-op behavior.

### Extraction Sub-Agent

The extraction sub-agent owns only:

- reading the provider request JSON file
- using the normalized transcript in that request to produce structured extraction
- writing one provider response JSON file

The sub-agent must not write meeting artifacts, signal JSONL, ledger records, archive files, or reconciled inbox files.

The canonical provider name for this path is `session`. Config validation, front matter, ledger artifact state, and run summaries should use `provider: session` for host/session-backed extraction.

Session-backed extraction has a different trust profile than direct API-backed providers. It should be controlled by its own privacy gate, recommended as `privacy.allow_session_provider`, rather than being implicitly enabled by `privacy.allow_remote_provider`. This lets local workflows enable active-harness extraction while keeping direct remote API providers disabled.

## Request File

The engine should write a provider request JSON file for host/session-backed extraction. This file is transient project runtime state and should live under cache/runtime storage, not durable docs.

Recommended path shape:

```text
<meetings_root>/_cache/provider-requests/<ingest_run_id>.request.json
```

Required fields:

```json
{
  "schema_version": "1.0",
  "handoff_type": "provider_request",
  "provider_contract": "meeting-ingest-provider-response-v1",
  "source_name": "Call with G, Kushali (5).docx",
  "source_sha256": "2d17d59a230107b3e5a1df1528eacd3328d40b4746cfbcab99d86242158cfd5a",
  "normalized_transcript_sha256": "3d3f0f6c0d8c8b9d4b91d9e6df0c0c1f1b4e7f2a63ed5e8a2f1c0f54e3d6a7b8",
  "meeting_id": "mtg-20260612-71e6b28b",
  "ingest_run_id": "ingest-20260612-20260703T120000Z-a1b2",
  "effective_date": "2026-06-12",
  "quality": "balanced",
  "output_mode": "summary-plus-verbatim",
  "normalized_transcript": "Speaker: Transcript text..."
}
```

Rules:

- `normalized_transcript` is the engine-normalized transcript, not raw source bytes.
- `normalized_transcript_sha256` binds the response to the exact transcript text the sub-agent received.
- `meeting_id`, `ingest_run_id`, `source_sha256`, `normalized_transcript_sha256`, and `effective_date` are copy-through requirements for the sub-agent; the sub-agent must not remint or alter them.
- The request file may include future optional helper fields such as allowed enum values, source format, duration, or date confidence.
- The request file should be treated as sensitive transcript-bearing runtime data.
- A provider request is runtime state only. It should not append a ledger record by itself.

## Response File

The sub-agent writes a provider response JSON file. The engine reads this file, parses it into `ProviderResponse`, and runs the same validation used for API-backed providers.

Recommended path shape:

```text
<meetings_root>/_cache/provider-responses/<ingest_run_id>.response.json
```

The cache path above is the default handoff location, not a hard trust boundary. The CLI may accept an absolute path or a relative path outside `_cache/provider-responses` when a wrapper writes responses elsewhere. Regardless of location, phase 2 must still locate and verify the persisted request file under `_cache/provider-requests/` for the response envelope's `ingest_run_id`.

Required top-level envelope:

```json
{
  "schema_version": "1.0",
  "handoff_type": "provider_response",
  "provider_contract": "meeting-ingest-provider-response-v1",
  "meeting_id": "mtg-20260612-71e6b28b",
  "ingest_run_id": "ingest-20260612-20260703T120000Z-a1b2",
  "source_sha256": "2d17d59a230107b3e5a1df1528eacd3328d40b4746cfbcab99d86242158cfd5a",
  "normalized_transcript_sha256": "3d3f0f6c0d8c8b9d4b91d9e6df0c0c1f1b4e7f2a63ed5e8a2f1c0f54e3d6a7b8",
  "provider": {
    "name": "session",
    "host": "codex",
    "model_alias": "balanced",
    "model_id": "codex-session",
    "generated_at": "2026-07-03T12:00:00Z"
  },
  "response": {
    "title": "Kushali x Ken - AdBook fact_revenue detail design",
    "tl_dr": "Short grounded meeting summary.",
    "meeting_type": "one-on-one",
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

The `response` object is the provider payload. It maps directly to `ProviderResponse`.

Rules:

- The sub-agent must return JSON only.
- All required response keys must be present, even when arrays are empty.
- Claims must be grounded in the transcript.
- The sub-agent should omit uncertain facts rather than inventing them.
- IDs inside response arrays should be short, stable local IDs such as `T1`, `D1`, `A1`, and `Q1`.
- `communication_signals` must contain provider-level signal candidates only. The sub-agent must not include engine-enriched fields such as `signal_id`, `recorded_at`, `meeting_id`, or `ingest_run_id` inside individual signals.
- `meeting_id`, `ingest_run_id`, `source_sha256`, and `normalized_transcript_sha256` in the envelope must match the persisted request file. A mismatch is a provider validation failure.
- The response envelope's identity fields are not authoritative. The engine uses them to locate and verify the persisted request file, then adopts identity only from the verified request.
- `schema_version` governs the envelope shape. `provider_contract` governs the nested provider payload shape.

## Provider Provenance

The engine should stamp artifact front matter, ledger artifact state, and run summary fields from request-side engine config when there is a conflict.

Rules:

- `provider.name` must be `session`.
- `provider.model_alias` must match request `quality`; otherwise validation fails.
- The host wrapper and sub-agent should honor request `quality` by mapping it to the harness's available model, effort, or prompt-depth controls. If the harness cannot vary behavior by quality, it should still echo the request value in `provider.model_alias`.
- `provider.host` should identify the harness, such as `codex`, `claude-code`, `supa-code`, or `t3-code`.
- `provider.model_id` should contain the actual session model when the harness exposes it. If it cannot be discovered, use `<host>-session`, such as `codex-session`.
- `provider.generated_at` records when the sub-agent produced the extraction. It is audit metadata for the handoff and must not replace renderer `generated_at`.
- Artifact front matter and ledger artifact state should preserve `provider: session`, `model_alias`, `model_id`, and optional `provider_host` when available.

## Provider Payload Shape

The response payload must use the current `ProviderResponse` shape:

```json
{
  "title": "Required non-empty string",
  "tl_dr": "Required non-empty string",
  "meeting_type": "unknown",
  "attendees": [
    {
      "person_id": null,
      "display_name": "Kushali G",
      "raw_labels": ["Kushali"],
      "role_context": "Unknown",
      "confidence": "medium"
    }
  ],
  "topics": [
    {
      "id": "T1",
      "topic": "Topic label",
      "summary": "Grounded topic summary.",
      "evidence": "Transcript quote or paraphrase."
    }
  ],
  "decisions": [
    {
      "id": "D1",
      "decision": "Decision text.",
      "owner_decider": "Owner or decider.",
      "evidence": "Transcript quote or paraphrase.",
      "status": "active"
    }
  ],
  "action_items": [
    {
      "id": "A1",
      "owner": "Owner",
      "action": "Action text.",
      "due_timing": "Timing or unknown.",
      "evidence": "Transcript quote or paraphrase.",
      "status": "open"
    }
  ],
  "stakeholder_asks": [
    {
      "id": "ASK1",
      "stakeholder": "Stakeholder",
      "ask": "Ask text.",
      "directed_to": "Recipient or unknown.",
      "evidence": "Transcript quote or paraphrase.",
      "status": "open"
    }
  ],
  "dependencies_risks": [
    {
      "id": "R1",
      "type": "risk",
      "description": "Risk or dependency text.",
      "owner_related_party": "Party or unknown.",
      "impact": "Impact text.",
      "status": "active"
    }
  ],
  "communication_signals": [
    {
      "signal_type": "explicit_ask",
      "stakeholder_id": null,
      "stakeholder_name": "Kushali G",
      "summary": "Signal summary.",
      "evidence": {
        "kind": "paraphrase",
        "text": "Evidence text.",
        "speaker": "Kushali G",
        "timestamp": "09:18"
      },
      "inference_level": "explicit",
      "confidence": "high",
      "topics": ["adbook"],
      "project_refs": ["fact_revenue_adbook"],
      "recurrence": "unknown",
      "status": "active"
    }
  ],
  "open_questions": [
    {
      "id": "Q1",
      "question": "Open question text.",
      "owner_next_step": "Owner or next step.",
      "evidence": "Transcript quote or paraphrase.",
      "status": "open"
    }
  ],
  "cross_references": []
}
```

Signal enums are defined in `src/meeting_ingest/schema.py` and mirrored in `docs/artifact-contract.md`.

Provider-supplied `person_id` and `communication_signals[].stakeholder_id` are advisory. The sub-agent should set them to `null` unless the request includes a known ID. The engine should normalize stable person IDs from names and raw labels instead of trusting LLM-minted durable identity.

## Engine Ingest Flow

The host/session-backed ingest flow is two-phase. The second phase is not a standalone ingest; it is the completion of a previously created provider request.

Phase 1:

1. Engine loads config, validates options, acquires the project lock, hashes source, and checks for duplicate/no-op state.
2. Engine extracts normalized transcript and mints `meeting_id` and `ingest_run_id`.
3. Engine writes a provider request file under `_cache/provider-requests/`.
4. Engine releases the project lock and returns request path plus expected response path to the host wrapper.

Phase 2:

1. Host wrapper invokes a dedicated extraction sub-agent with the request path and expected response path.
2. Sub-agent writes the response envelope with the `ProviderResponse` payload.
3. Engine acquires the project lock again.
4. Engine rehashes the source and re-runs duplicate/no-op detection before consuming the response.
5. Engine reads the response envelope and locates the persisted request file keyed by the envelope `ingest_run_id`.
6. Engine verifies response identity fields against the persisted request and current source hash.
7. Engine adopts `meeting_id`, `ingest_run_id`, `effective_date`, `quality`, and `output_mode` from the verified request, not from the response.
8. Engine parses `response` into `ProviderResponse`.
9. Engine runs `validate_provider_response`.
10. Engine continues through the existing pipeline: signal enrichment, signal JSONL, markdown rendering, ledger snapshots, archive, reconcile, and run summary.

An externally supplied provider response must enter the pipeline before signal enrichment and rendering. It must not enter as rendered markdown or enriched signal records.

If the source is already ingested by the time phase 2 starts, phase 2 should return the normal duplicate/no-op summary and must not render new artifacts from the stale response. If phase 2 fails before primary artifacts are ready, retry must start from a new phase-1 provider request with a new `ingest_run_id`; the old request/response pair must not be reused for a new ingest attempt.

If phase 2 is invoked with CLI `--mode` or `--quality` values that differ from the persisted request, the engine must not reinterpret the response. It should use the verified request's `output_mode` and `quality` values, then include warnings in the run summary so callers can detect a stale or inconsistent command line. Today only `summary-plus-verbatim` is supported, so `--mode` mismatch warnings are mainly a forward-compatibility rule.

## CLI And Library Shape

Implementation should prefer a reusable library primitive first, then expose it through CLI/wrappers.

Recommended library shape:

```python
complete_session_ingest(source, provider_response=Path(...))
```

Recommended CLI shape:

```text
meeting-ingest provider-request SOURCE --provider session --json
meeting-ingest ingest SOURCE --provider session --provider-response PATH --json
```

`ingest --provider-response` is phase 2 of this flow and hard-requires the matching persisted request file. It must not accept an arbitrary provider response envelope without the corresponding request file.

`PATH` may be absolute or relative. Relative paths are resolved first from the current working directory and then from the meetings root when needed. Wrappers should prefer the engine-returned `expected_response_path` under `_cache/provider-responses/`, but alternate response locations are valid as long as the envelope and persisted request verify.

For fully managed host/session operation, a wrapper may hide the two commands from the user:

```text
meeting-ingest provider-request SOURCE --provider session --json
meeting-ingest ingest SOURCE --provider session --provider-response PATH --json
```

The exact command names may change during implementation, but the contract should preserve these boundaries:

- request generation is engine-owned
- model extraction is sub-agent-owned
- response validation and all ingest side effects are engine-owned

For a generic extraction sub-agent prompt template, see `docs/session-provider-subagent-prompt.md`.

## Failure Behavior

Milestone 7 depends on provider failure semantics being implemented first: a typed provider failure error, exit code `5`, provider-validation exit code `6`, and `ingest_failed` ledger recording before primary artifacts are ready.

Failures before primary artifacts are ready should use the provider/provider-validation failure path:

- missing response file: provider failure
- invalid JSON: provider failure
- wrong envelope type or unsupported contract: provider validation failure
- missing persisted request file for the envelope `ingest_run_id`: provider validation failure
- identity mismatch with request/source: provider validation failure
- payload cannot parse into `ProviderResponse`: provider validation failure
- `validate_provider_response` failure: provider validation failure

The source should remain unreconciled on provider or provider-validation failure. If possible, the ledger should append `ingest_failed` with the same error block used by API-backed providers.

## Privacy And Source Control

Provider request and response files contain transcript-derived sensitive data. They are runtime files and should not be committed by default.

Rules:

- `init` should ensure the configured cache directory is ignored by source control.
- Successful phase 2 should delete the matching request and response files after artifacts, ledger, archive, and reconcile complete.
- Failed phase 2 may retain request and response files for diagnosis.
- `doctor` should report stale provider request/response files older than the configured retention window; v1 may use a fixed 7-day warning threshold.
- Durable docs may record the contract and anonymized examples.
- Durable project memory should not capture full transcripts unless the user intentionally asks to preserve that artifact.
