# Artifact Contract

## Purpose

This document defines the first stable artifact contract for `meeting-ingest`.

The contract is optimized for:

- agent consumption
- human readability
- deterministic rendering
- source-grounded provenance
- safe regeneration and rename repair

The first implementation target is `summary-plus-verbatim`. Other modes should follow the same identity, metadata, signal, ledger, and run-summary rules.

## Contract Principles

1. Identity is immutable.
2. Titles, slugs, and filenames are mutable display metadata.
3. Markdown is deterministic renderer output, not provider-written freeform output.
4. Every important fact needed by an agent appears in a structured section.
5. Empty sections are explicit.
6. The verbatim transcript is always the final section.
7. Signal records stay factual and evidence-backed.
8. Playbook guidance is derived later from signals, not embedded directly in per-meeting signal records.

## Identity

### Meeting ID

`meeting_id` is immutable.

It must not be derived from the semantic title or filename.

Recommended format:

```text
mtg-YYYYMMDD-<source_shorthash>
```

Example:

```text
mtg-20260612-71e6b28b
```

Rules:

- `YYYYMMDD` is the effective meeting date.
- `<source_shorthash>` is a stable short prefix from the source content hash or ingest source identity.
- `meeting_id` is minted once during first ingest from the best-known effective date at that time.
- If the effective date is corrected later, update `date` metadata but do not change `meeting_id`; after minting, treat the embedded date as opaque identity text.
- Rename repair must not change `meeting_id`.
- Signals, ledger entries, cross-references, and playbook entries must key against `meeting_id`, not filename.

### Ingest Run ID

`ingest_run_id` identifies a specific ingest attempt.

Recommended format:

```text
ingest-YYYYMMDD-<run_suffix>
```

Example:

```text
ingest-20260612-20260703T120000Z-a1b2
```

Rules:

- `ingest_run_id` must be unique per ingest attempt.
- Retries must receive a new `ingest_run_id`.
- Do not use only the source shorthash as the run suffix.
- A timestamp plus short random or monotonic suffix is acceptable.

## Filename Contract

Generated markdown lives directly under the project meetings root.

Filename shape:

```text
YYYY-MM-DD-<counterpart-or-meeting>-<topic>.md
```

Examples:

```text
2026-06-12-kushali-adbook-fact-revenue-detail.md
2026-07-01-spelman-data-infrastructure-rfp-prep.md
2026-06-10-jim-haley-historical-revenue-dedup.md
```

Rules:

- Include date.
- Include meeting identity or one-on-one counterpart when clear.
- Include primary topic.
- Do not include a full attendee list.
- Avoid `generic-<hash>` except as a low-confidence fallback.
- If fallback naming is used, include a rename suggestion in the run summary when possible.
- Rename repair updates artifact paths and title metadata, not immutable IDs.
- Slugs should use lowercase ASCII letters, numbers, and hyphens.
- Slugs should collapse repeated separators and trim leading/trailing separators.
- Recommended maximum slug length is 80 characters before date and extension.
- If a filename collision occurs, append a numeric suffix such as `-2`, `-3`, and include a warning in the run summary.

## Output Modes

### `summary-plus-verbatim`

Default mode.

Produces one canonical markdown file containing:

1. structured summary
2. cleaned verbatim transcript

### `summary`

Produces one canonical markdown file containing the same structured summary sections without transcript.

### `verbatim`

Produces one canonical markdown file containing metadata and cleaned verbatim transcript only.

## Cleaned Verbatim Policy

The default transcript record is `cleaned-verbatim`.

Meaning:

- speaker-attributed
- chronological
- lightly cleaned for readability
- filler-only artifacts may be removed
- obvious transcription junk may be repaired or omitted
- substantive words, decisions, explanations, and technical details must not be summarized away

The artifact must include `transcript_policy: cleaned-verbatim` in front matter.

If provider-assisted transcript repair is used, the artifact must include that fact in front matter or transcript notes.

## Markdown Front Matter

All generated markdown artifacts must start with YAML front matter.

Required fields for `summary-plus-verbatim`:

```yaml
---
schema_version: "1.0"
artifact_type: meeting
meeting_id: mtg-20260612-71e6b28b
ingest_run_id: ingest-20260612-20260703T120000Z-a1b2
output_mode: summary-plus-verbatim
title: Kushali x Ken - AdBook fact_revenue detail design
slug: kushali-adbook-fact-revenue-detail
date: 2026-06-12
date_confidence: high
date_source: content
meeting_type: one-on-one
source_file: Call with G, Kushali (5).docx
source_sha256: 2d17d59a230107b3e5a1df1528eacd3328d40b4746cfbcab99d86242158cfd5a
transcript_policy: cleaned-verbatim
provider: anthropic
model_alias: balanced
model_id: claude-sonnet-placeholder
generated_by: meeting-ingest 0.1.0
generated_at: 2026-07-03T12:00:00Z
---
```

Recommended optional fields:

```yaml
title_confidence: high
filename_confidence: high
counterpart_person_id: kushali-g
counterpart_name: Kushali G
duration: PT16M12S
source_started_at: 2026-06-12T04:42:00-04:00
timezone: America/Detroit
project: htv-iq-dataanalytics
```

Rules:

- `meeting_id` must not change on rename.
- `title` and `slug` may change on repair.
- `model_alias` is the configured quality tier.
- `model_id` is the resolved provider model identifier.
- If no provider was used, set `provider: none` and `model_id: none`.
- `schema_version` must be quoted as a string in YAML.
- `meeting_type` is free-form in v1, but recommended values are `one-on-one`, `small-group`, `standup`, `status`, `discovery`, `design-review`, and `unknown`.

## Required Markdown Structure

`summary-plus-verbatim` must use this top-level section order:

```markdown
# <Title>

## Meeting Overview

## Attendees And Identity

## Key Topics

## Decisions

## Commitments And Action Items

## Stakeholder Asks

## Dependencies And Risks

## Communication Signals

## Open Questions

## Cross-References

## Verbatim Transcript
```

Rules:

- All required headings must be present.
- Empty sections must contain `None identified.` or an equivalent explicit empty marker.
- `## Verbatim Transcript` must be the final section in `summary-plus-verbatim`.
- No content may appear after the transcript section.
- Downstream agents must be able to split the transcript by heading.

## Section Contracts

### `# <Title>`

The H1 is the human display title.

It may differ from filename and from immutable `meeting_id`.

### `## Meeting Overview`

Required contents:

- short TL;DR
- meeting type
- effective date
- source/provenance summary
- output mode

Recommended shape:

```markdown
## Meeting Overview

**TL;DR:** Kushali and Ken confirmed the AdBook fact_revenue detail-to-summary design and identified unresolved Decentrix identity mapping questions.

| Field | Value |
|---|---|
| Meeting ID | `mtg-20260612-71e6b28b` |
| Date | 2026-06-12 |
| Type | one-on-one |
| Source | `Call with G, Kushali (5).docx` |
| Output Mode | `summary-plus-verbatim` |
```

### `## Attendees And Identity`

Required table:

```markdown
| Person ID | Display Name | Raw Speaker Labels | Role / Context | Confidence |
|---|---|---|---|---|
| `kushali-g` | Kushali G | G, Kushali | Data engineer | high |
| `ken-graham` | Ken Graham | Graham, Ken (Contractor) | Contractor / orchestration | high |
```

Rules:

- Use stable person IDs when known.
- Preserve raw speaker labels.
- Mark uncertain identity resolution with `medium` or `low` confidence.
- Do not silently collapse uncertain speakers.

### `## Key Topics`

Required table:

```markdown
| ID | Topic | Summary | Evidence |
|---|---|---|---|
| T1 | AdBook fact_revenue two-table design | Detail table feeds compressed fact table. | Kushali described detail rows and compression plan. |
```

Rules:

- Topic IDs are local to the artifact.
- Topics should be concise and agent-scannable.

### `## Decisions`

Required table:

```markdown
| ID | Decision | Owner / Decider | Evidence | Status |
|---|---|---|---|---|
| D1 | Use detail table plus compressed fact table for AdBook fact_revenue. | Ken / Kushali | Confirmed in discussion of detail-to-summary flow. | active |
```

Rules:

- Decision IDs use `D1`, `D2`, etc.
- If no decisions are identified, emit `None identified.`
- Do not bury decisions only in narrative prose.

### `## Commitments And Action Items`

Required table:

```markdown
| ID | Owner | Commitment / Action | Due / Timing | Evidence | Status |
|---|---|---|---|---|---|
| A1 | Kushali G | Ask Decentrix about AE name mapping and advertiser GUID source. | Tomorrow morning | Kushali said she would reach out. | open |
```

Rules:

- Action IDs use `A1`, `A2`, etc.
- Owner may be `Unassigned` if unclear.
- Due may be `Unspecified`.
- Status values should start with `open`, `done`, `deferred`, or `unknown`.

### `## Stakeholder Asks`

Required table:

```markdown
| ID | Stakeholder | Ask | Directed To | Evidence | Status |
|---|---|---|---|---|---|
| ASK1 | Kushali G | Clarify the proper source for AE and advertiser identity resolution. | Decentrix / project team | Kushali rejected fallback matching as insufficient. | open |
```

Rules:

- Ask IDs use `ASK1`, `ASK2`, etc.
- Include explicit asks only.
- Inferred priorities belong in `Communication Signals`, not here.

### `## Dependencies And Risks`

Required table:

```markdown
| ID | Type | Description | Owner / Related Party | Impact | Status |
|---|---|---|---|---|---|
| R1 | risk | AE nickname mapping may block SK joins. | Kushali / Decentrix | Could prevent reliable AE dimension matching. | active |
```

Allowed `Type` values:

- `dependency`
- `risk`
- `constraint`
- `blocker`

### `## Communication Signals`

This section summarizes the signal records generated for the meeting.

Required table:

```markdown
| Signal ID | Type | Stakeholder | Summary | Confidence |
|---|---|---|---|---|
| `sig-20260612-001` | explicit_ask | Kushali G | Wants source-of-truth clarity for identity mapping. | high |
```

Rules:

- This table should mirror `_signals/<meeting_id>.jsonl`.
- Guidance or recommended messaging should not appear here in v1.
- If no signals are generated, emit `None identified.`

### `## Open Questions`

Required table:

```markdown
| ID | Question | Owner / Next Step | Evidence | Status |
|---|---|---|---|---|
| Q1 | Where does Decentrix get canonical AE names? | Kushali to ask Decentrix. | AE nicknames differ from canonical names. | open |
```

### `## Cross-References`

Required contents:

- related project artifacts, if known
- related prior meeting IDs, if known
- related files or systems

If none:

```markdown
None identified.
```

### `## Verbatim Transcript`

This must be final.

Recommended header:

```markdown
## Verbatim Transcript

<!-- transcript:begin policy=cleaned-verbatim -->

**Kushali G** (00:03): So this is the one that we loaded...

**Ken Graham** (01:00): I didn't know that. That's good to know.

<!-- transcript:end -->
```

Rules:

- Transcript section is final.
- Use fixed sentinel comments.
- Preserve chronological order.
- Preserve speaker labels.
- Mark uncertain speakers as `Unknown Speaker` or `Uncertain: <label>`.
- Do not add analysis inside the transcript section.

## V1 Signal JSONL Contract

Signals are written to:

```text
_signals/<meeting_id>.jsonl
```

Example:

```text
_signals/mtg-20260612-71e6b28b.jsonl
```

Signal files must be keyed by immutable `meeting_id`, never by mutable slug or filename.

Each line is one JSON object.

Required fields:

```json
{
  "schema_version": "1.0",
  "signal_id": "sig-20260612-001",
  "meeting_id": "mtg-20260612-71e6b28b",
  "ingest_run_id": "ingest-20260612-20260703T120000Z-a1b2",
  "effective_at": "2026-06-12",
  "recorded_at": "2026-07-03T12:00:00Z",
  "signal_type": "explicit_ask",
  "stakeholder_id": "kushali-g",
  "stakeholder_name": "Kushali G",
  "summary": "Kushali wants source-of-truth clarity for AE and advertiser identity mapping.",
  "evidence": {
    "kind": "paraphrase",
    "text": "Kushali said she wanted to ask Decentrix where the correct names come from.",
    "speaker": "Kushali G",
    "timestamp": "09:18"
  },
  "inference_level": "explicit",
  "confidence": "high",
  "topics": ["adbook", "identity-resolution", "decentrix"],
  "project_refs": ["fact_revenue_adbook", "AE SK"],
  "recurrence": "unknown",
  "status": "active"
}
```

V1 `signal_type` values:

- `explicit_ask`
- `stakeholder_priority`
- `decision_rationale`
- `commitment`
- `risk_or_concern`

Allowed `evidence.kind` values:

- `quote`
- `paraphrase`
- `timestamp_only`

Allowed `inference_level` values:

- `explicit`
- `strong_inference`
- `weak_inference`

Allowed `confidence` values:

- `high`
- `medium`
- `low`

Allowed `recurrence` values:

- `one_off`
- `recurring`
- `unknown`

Rules:

- Every signal must include evidence.
- `stakeholder_id` may be `null` when unresolved, group-directed, or not person-specific.
- `stakeholder_name` may be a group label such as `Project team` when appropriate.
- V1 extraction should set `recurrence: "unknown"`; recurrence should be promoted to `one_off` or `recurring` during playbook derivation.
- `communication_guidance` is not part of v1 signal records.
- Relationship/profiling-adjacent claims should be avoided in v1 unless directly evidenced and necessary.
- Signals may be empty; an empty signal file is valid and should still be recorded.

## Ledger Artifact Contract

The ledger is append-only JSONL.

Current state is computed as:

```text
last valid record wins per source_sha256
```

Ledger paths are relative to the meetings root unless otherwise stated.

Every ledger record must be a complete current-state snapshot for that `source_sha256`, not a partial delta. If a later run adds a new output mode, the new ledger record must include previously known artifact modes as well as the new mode.

A valid record is a parseable JSON object that:

- has a supported `schema_version`
- has a known `event`
- has `source_sha256`
- has `meeting_id` when a meeting identity has been minted
- passes event-specific validation

Malformed, unsupported-version, or incomplete records are ignored for current-state calculation and should be reported by `doctor`.

### Ledger Events

Recommended v1 event values:

- `primary_artifacts_ready`
- `ingest_completed`
- `reconcile_repaired`
- `ingest_failed`
- `source_quarantined`
- `artifact_regenerated`
- `title_repaired`
- `derived_updated`

Write timing:

1. After markdown and signal files are written, append `primary_artifacts_ready`.
2. After processed archive copy and inbox reconciliation complete or are explicitly skipped, append `ingest_completed`.
3. If a duplicate/no-op run repairs a missing processed copy or reconciles a re-dropped source, append `reconcile_repaired`.
4. If ingest fails before primary artifacts are ready, append `ingest_failed` or `source_quarantined` when possible.
5. Playbook updates append `derived_updated` and must not rewrite prior ingest records.

A source-level ledger record should include mode-specific artifacts.

Example:

```json
{
  "schema_version": "1.0",
  "event": "ingest_completed",
  "source_sha256": "2d17d59a230107b3e5a1df1528eacd3328d40b4746cfbcab99d86242158cfd5a",
  "meeting_id": "mtg-20260612-71e6b28b",
  "ingest_run_id": "ingest-20260612-20260703T120000Z-a1b2",
  "source": {
    "original_path": "_inbox/Call with G, Kushali (5).docx",
    "processed_path": "_processed/2d17d59a2301-ingest-20260612-20260703T120000Z-a1b2-Call with G, Kushali (5).docx",
    "source_type": "docx"
  },
  "artifacts": {
    "summary-plus-verbatim": {
      "status": "ready",
      "path": "2026-06-12-kushali-adbook-fact-revenue-detail.md",
      "schema_version": "1.0",
      "title": "Kushali x Ken - AdBook fact_revenue detail design",
      "slug": "kushali-adbook-fact-revenue-detail",
      "provider": "anthropic",
      "model_alias": "balanced",
      "model_id": "claude-sonnet-placeholder"
    }
  },
  "signals": {
    "status": "ready",
    "path": "_signals/mtg-20260612-71e6b28b.jsonl",
    "count": 5
  },
  "derived": {
    "playbook_update_status": "pending"
  },
  "error": null,
  "quarantine": null,
  "reconcile": {
    "status": "completed",
    "done_path": "_inbox/_done/Call with G, Kushali (5).docx"
  },
  "recorded_at": "2026-07-03T12:00:00Z"
}
```

Artifact status values:

- `ready`
- `pending`
- `failed`
- `stale`
- `superseded`
- `quarantined`

Reconcile status values:

- `completed`
- `skipped`
- `failed`

Derived playbook status values:

- `not_applicable`
- `pending`
- `ready`
- `failed`
- `stale`

Error block shape when present:

```json
{
  "phase": "provider_validation",
  "code": "invalid_provider_output",
  "message": "Provider output did not include required decisions array.",
  "recoverable": true
}
```

Quarantine block shape when present:

```json
{
  "status": "quarantined",
  "path": "_quarantine/2d17d59a2301-Call with G, Kushali (5).docx",
  "reason": "unsupported_source_format"
}
```

## JSON Run Summary Contract

The CLI should support a machine-readable run summary for agent harnesses.

Recommended flag:

```text
--json
```

Example successful run summary:

```json
{
  "schema_version": "1.0",
  "status": "success",
  "exit_code": 0,
  "meeting_id": "mtg-20260612-71e6b28b",
  "ingest_run_id": "ingest-20260612-20260703T120000Z-a1b2",
  "source_sha256": "2d17d59a230107b3e5a1df1528eacd3328d40b4746cfbcab99d86242158cfd5a",
  "output_mode": "summary-plus-verbatim",
  "artifacts": [
    {
      "kind": "markdown",
      "mode": "summary-plus-verbatim",
      "status": "ready",
      "path": "_local/project-context/meetings/2026-06-12-kushali-adbook-fact-revenue-detail.md"
    },
    {
      "kind": "signals",
      "status": "ready",
      "path": "_local/project-context/meetings/_signals/mtg-20260612-71e6b28b.jsonl",
      "count": 5
    }
  ],
  "derived": {
    "playbook_update_status": "pending"
  },
  "title": {
    "value": "Kushali x Ken - AdBook fact_revenue detail design",
    "slug": "kushali-adbook-fact-revenue-detail",
    "confidence": "high",
    "rename_suggestion": null
  },
  "reconcile": {
    "status": "completed"
  },
  "warnings": [],
  "errors": []
}
```

Duplicate/no-op summary:

```json
{
  "schema_version": "1.0",
  "status": "no_op",
  "exit_code": 0,
  "reason": "source_already_ingested",
  "source_sha256": "2d17d59a230107b3e5a1df1528eacd3328d40b4746cfbcab99d86242158cfd5a",
  "meeting_id": "mtg-20260612-71e6b28b",
  "ingest_run_id": null,
  "artifacts": [],
  "warnings": [],
  "errors": [],
  "existing_artifacts": {
    "summary-plus-verbatim": "2026-06-12-kushali-adbook-fact-revenue-detail.md"
  }
}
```

A duplicate/no-op run may still perform repair work when the ledger shows an otherwise-ingested source has incomplete archive or reconcile state. In that case, keep `status: "no_op"` and exit `0`, include the repair action in `warnings`, and append a complete `reconcile_repaired` ledger snapshot reflecting the repaired archive/reconcile state. If no archive or reconcile state changed, do not append a repair snapshot.

Failure summary:

```json
{
  "schema_version": "1.0",
  "status": "failed",
  "exit_code": 6,
  "reason": "provider_output_validation_failed",
  "source_sha256": "2d17d59a230107b3e5a1df1528eacd3328d40b4746cfbcab99d86242158cfd5a",
  "meeting_id": "mtg-20260612-71e6b28b",
  "ingest_run_id": "ingest-20260612-20260703T120000Z-a1b2",
  "phase": "provider_validation",
  "artifacts": [],
  "warnings": [],
  "errors": [
    {
      "code": "missing_required_field",
      "message": "Provider response omitted required field: decisions",
      "recoverable": true
    }
  ],
  "quarantine": {
    "status": "skipped",
    "path": null,
    "reason": null
  }
}
```

Required shared keys for all JSON summaries:

- `schema_version`
- `status`
- `exit_code`
- `source_sha256`
- `artifacts`
- `warnings`
- `errors`

Optional fields may be `null` when not applicable, but the shared keys should remain present for agent parsing.

## Exit Codes

Recommended v1 exit codes:

| Code | Meaning |
|---:|---|
| 0 | Success |
| 1 | General failure |
| 2 | Invalid CLI usage or config |
| 3 | Unsupported source format |
| 4 | Source read/extraction failure |
| 5 | Provider failure |
| 6 | Provider output validation failure |
| 7 | Artifact write or render failure |
| 8 | Ledger write failure |
| 9 | Archive or reconcile failure |
| 10 | Lock or concurrency conflict |
| 11 | Derived work failed while caller requested derived work to block |

Rules:

- Exit `0` when primary success is complete, when duplicate/no-op is successful, or when primary success is complete but non-blocking derived work fails.
- Duplicate/no-op uses exit `0` with `status: "no_op"` in JSON.
- Playbook failure after primary success defaults to exit `0` with `derived.playbook_update_status: "failed"` in JSON.
- Use exit `11` only when the caller explicitly asks for derived work to be blocking.
- JSON summary must include enough detail for an agent to report artifact paths to the user.

## Validation Rules

Before reporting primary success, the engine must verify:

- front matter is present
- `meeting_id` is present and immutable-format compliant
- required headings are present
- required empty sections use explicit empty markers
- transcript section exists for `summary-plus-verbatim`
- transcript section is final
- transcript begin/end sentinels are present for `summary-plus-verbatim`
- ledger update succeeded
- processed archive copy exists
- signal file exists, even if empty
- signal records validate against the v1 signal JSONL contract

## Explicitly Deferred

Not required for v1 artifact contract:

- rolling playbook document schema
- rename repair command semantics
- split-file derivative artifacts
- `summary` and `verbatim` full section contracts
- communication artifact ingest contract
- corpus migration contract
