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
- `validate_provider_response`
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
- `meeting_id`, `ingest_run_id`, `source_sha256`, and `effective_date` are informational constraints for the sub-agent; the sub-agent must not remint or alter them.
- The request file may include future optional helper fields such as allowed enum values, source format, duration, or date confidence.
- The request file should be treated as sensitive transcript-bearing runtime data.

## Response File

The sub-agent writes a provider response JSON file. The engine reads this file, parses it into `ProviderResponse`, and runs the same validation used for API-backed providers.

Recommended path shape:

```text
<meetings_root>/_cache/provider-responses/<ingest_run_id>.response.json
```

Required top-level envelope:

```json
{
  "schema_version": "1.0",
  "handoff_type": "provider_response",
  "provider_contract": "meeting-ingest-provider-response-v1",
  "meeting_id": "mtg-20260612-71e6b28b",
  "ingest_run_id": "ingest-20260612-20260703T120000Z-a1b2",
  "source_sha256": "2d17d59a230107b3e5a1df1528eacd3328d40b4746cfbcab99d86242158cfd5a",
  "provider": {
    "name": "session",
    "host": "codex",
    "model_alias": "balanced",
    "model_id": "host-session",
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
- `meeting_id`, `ingest_run_id`, and `source_sha256` in the envelope must match the request file. A mismatch is a provider validation failure.

## Provider Payload Shape

The response payload must use the current `ProviderResponse` shape:

```json
{
  "title": "Required non-empty string",
  "tl_dr": "Required non-empty string",
  "meeting_type": "unknown",
  "attendees": [
    {
      "person_id": "person-kushali",
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

## Engine Ingest Flow

The host/session-backed ingest flow should be:

1. Engine loads config, validates options, acquires project lock, hashes source, and checks for duplicate/no-op state.
2. Engine extracts normalized transcript and mints `meeting_id` and `ingest_run_id`.
3. Engine writes a provider request file.
4. Host wrapper invokes a dedicated extraction sub-agent with the request path and expected response path.
5. Sub-agent writes the response envelope with the `ProviderResponse` payload.
6. Engine reads the response file and verifies envelope identity fields.
7. Engine parses `response` into `ProviderResponse`.
8. Engine runs `validate_provider_response`.
9. Engine continues through the existing pipeline: signal enrichment, signal JSONL, markdown rendering, ledger snapshots, archive, reconcile, and run summary.

An externally supplied provider response must enter the pipeline before signal enrichment and rendering. It must not enter as rendered markdown or enriched signal records.

## CLI And Library Shape

Implementation should prefer a reusable library primitive first, then expose it through CLI/wrappers.

Recommended library shape:

```python
ingest(source, provider="session", external_provider_response=Path(...))
```

Recommended CLI shape:

```text
meeting-ingest ingest SOURCE --provider session --provider-response PATH --json
```

For fully managed host/session operation, the wrapper may call a two-phase helper instead:

```text
meeting-ingest provider-request SOURCE --provider session --json
meeting-ingest ingest SOURCE --provider session --provider-response PATH --json
```

The exact command names may change during implementation, but the contract should preserve these boundaries:

- request generation is engine-owned
- model extraction is sub-agent-owned
- response validation and all ingest side effects are engine-owned

## Failure Behavior

Failures before primary artifacts are ready should use the existing provider/provider-validation failure path:

- missing response file: provider failure
- invalid JSON: provider failure
- wrong envelope type or unsupported contract: provider validation failure
- identity mismatch with request/source: provider validation failure
- payload cannot parse into `ProviderResponse`: provider validation failure
- `validate_provider_response` failure: provider validation failure

The source should remain unreconciled on provider or provider-validation failure. If possible, the ledger should append `ingest_failed` with the same error block used by API-backed providers.

## Privacy And Source Control

Provider request and response files contain transcript-derived sensitive data. They are runtime files and should not be committed by default.

Durable docs may record the contract and anonymized examples. Durable project memory should not capture full transcripts unless the user intentionally asks to preserve that artifact.
