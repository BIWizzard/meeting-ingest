# Artifact Contract

## Purpose

This document defines the first stable artifact contract for `meeting-ingest`.

The contract is optimized for:

- agent consumption
- human readability
- deterministic rendering
- source-grounded provenance
- safe regeneration and rename repair

The first meeting-artifact implementation target was `summary-plus-verbatim`; `summary` and `verbatim` follow the same identity, metadata, signal, ledger, and run-summary rules. Stakeholder Briefing V1 is a separate deterministic derived-artifact contract over validated signals.

## Contract Principles

1. Identity is immutable.
2. Titles, slugs, and filenames are mutable display metadata.
3. Markdown is deterministic renderer output, not provider-written freeform output.
4. Every important fact needed by an agent appears in a structured section.
5. Empty sections are explicit.
6. The verbatim transcript is always the final section.
7. Signal records stay factual and evidence-backed.
8. Playbook guidance is derived later from signals, not embedded directly in per-meeting signal records.
9. Stakeholder profiles are rebuildable materializations; sources, validated observations, reviewed identity, and review events are canonical inputs.
10. Source ingest and corpus-derived playbook history use separate authoritative ledgers.

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
- Meeting signals, ledger entries, and meeting cross-references key against `meeting_id`, not filename. Generalized observations also carry communication-neutral `source_id`; playbook entries key to reviewed person identity and canonical `(source_id, signal_id)` observation references.

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

Use this mode for one-on-ones, design/build conversations, knowledge-transfer sessions, decisions, technical explanations, and other meetings where the transcript itself remains useful project memory.

### `summary`

Produces one canonical markdown file containing the same structured summary sections without transcript.

Use this mode for large structured meetings, recurring status meetings, standups, and broad planning conversations where the structured extraction is more valuable than preserving the full transcript in the primary artifact.

### `verbatim`

Produces one canonical markdown file containing metadata and cleaned verbatim transcript only.

Use this mode when the user wants a normalized transcript record without summary extraction.

Default `verbatim` behavior is deterministic and should avoid provider calls. A future provider-assisted speaker-repair option may be added, but it must be explicit in CLI/config, must preserve `output_mode: verbatim`, and must record provider usage in front matter, ledger, and run summary.

### Multiple Modes For One Source

Rules:

- One `source_sha256` may have `summary`, `summary-plus-verbatim`, and `verbatim` artifacts at the same time.
- The source-level ledger snapshot is the current-state authority for all mode artifacts.
- Rendering a missing mode for an already-known source must not change unrelated mode artifacts.
- Regenerating one mode must not delete or rewrite unrelated mode artifacts.
- Signals are keyed by `meeting_id`, not by mode. A regenerate command may refresh signals only when the selected mode uses provider-backed summary/signal extraction and the caller has requested or accepted signal refresh.
- The default mode remains `summary-plus-verbatim`.

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

Required fields for all meeting markdown artifacts:

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
provider_host: codex
```

Rules:

- `meeting_id` must not change on rename.
- `title` and `slug` may change on repair.
- `model_alias` is the configured quality tier.
- `model_id` is the resolved provider model identifier.
- `provider_host` is optional and should be present when `provider: session` and the active harness is known.
- If no provider was used, set `provider: none` and `model_id: none`.
- `schema_version` must be quoted as a string in YAML.
- `meeting_type` is free-form in v1, but recommended values are `one-on-one`, `small-group`, `standup`, `status`, `discovery`, `design-review`, and `unknown`.
- `output_mode` must match the artifact mode.
- `transcript_policy` is required for `summary-plus-verbatim` and `verbatim`; for `summary`, use `none` unless a later summary mode stores transcript excerpts under a documented policy.
- `title_confidence` and `filename_confidence` values are `high`, `medium`, `low`, or `manual`. Use `manual` only for user-directed repair.

## Required Markdown Structures

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

`summary` must use this top-level section order:

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
```

Rules:

- All summary sections use the same contracts as `summary-plus-verbatim`.
- `## Verbatim Transcript` must not be present.
- Front matter must set `output_mode: summary`.
- Front matter should set `transcript_policy: none`.
- Provider-backed extraction is expected unless a future deterministic summary extractor is explicitly documented.

`verbatim` must use this top-level section order:

```markdown
# <Title>

## Meeting Overview

## Attendees And Identity

## Cross-References

## Verbatim Transcript
```

Rules:

- `## Verbatim Transcript` must be the final section.
- No structured summary sections may be present: `## Key Topics`, `## Decisions`, `## Commitments And Action Items`, `## Stakeholder Asks`, `## Dependencies And Risks`, `## Communication Signals`, and `## Open Questions` are omitted.
- `## Meeting Overview` is limited to provenance, meeting type/date when known, source, output mode, transcript policy, and explicit notes about low-confidence title/date inference.
- `## Attendees And Identity` should be derived from transcript speaker labels and any deterministic identity normalization available without provider extraction.
- `## Cross-References` may be `None identified.` unless deterministic source metadata links known project artifacts.
- Front matter must set `output_mode: verbatim`.
- Front matter must set `transcript_policy: cleaned-verbatim`.
- If no provider was used, set `provider: none`, `model_alias: none`, and `model_id: none`.

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

Mode-specific rules:

- `summary-plus-verbatim` includes a TL;DR and provenance table.
- `summary` includes the same TL;DR and provenance table, with `Output Mode` set to `summary`.
- `verbatim` omits the TL;DR unless it can be generated deterministically from source metadata; it must still include the provenance table.

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

## Signal JSONL Contracts

### Schema 1.0 Meeting Signals

Schema 1.0 remains a supported compatibility contract for existing meeting signal files.

Signals are written to:

```text
_signals/<meeting_id>.jsonl
```

Example:

```text
_signals/mtg-20260612-71e6b28b.jsonl
```

Schema 1.0 meeting signal files must be keyed by immutable `meeting_id`, never by mutable slug or filename.

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

### Schema 1.1 Generalized Signals

Schema 1.1 is additive and supports meeting and non-meeting communication sources. New playbook-facing signal work should write schema 1.1 while readers continue to accept schema 1.0.

Signal paths:

```text
_signals/<meeting_id>.jsonl     # meeting compatibility path
_signals/<source_id>.jsonl      # non-meeting communication path
```

Meeting signals retain the meeting-keyed path through schema 1.x. Non-meeting signals use communication-neutral `source_id`.

Required schema 1.1 shape:

```json
{
  "schema_version": "1.1",
  "signal_id": "sig-a1b2c3d4e5f6-91aa2c80b731",
  "meeting_id": "mtg-20260612-71e6b28b",
  "ingest_run_id": "ingest-20260612-20260703T120000Z-a1b2",
  "effective_at": "2026-06-12",
  "recorded_at": "2026-07-03T12:00:00Z",
  "source": {
    "source_id": "src-a1b2c3d4e5f6",
    "source_kind": "meeting_transcript",
    "source_sha256": "a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890",
    "meeting_id": "mtg-20260612-71e6b28b",
    "artifact_path": "2026-06-12-kushali-adbook.md",
    "channel": "teams",
    "evidence_locator_scheme": "timestamp"
  },
  "timing": {
    "occurred": {
      "value": "2026-06-12",
      "end_value": null,
      "precision": "date",
      "timezone": null,
      "source": "transcript_header",
      "confidence": "high"
    },
    "acquired": {
      "value": "2026-07-03T11:45:00-04:00",
      "end_value": null,
      "precision": "datetime",
      "timezone": "America/Detroit",
      "source": "filesystem_mtime",
      "confidence": "low"
    },
    "recorded": {
      "value": "2026-07-03T12:00:00Z",
      "end_value": null,
      "precision": "datetime",
      "timezone": "UTC",
      "source": "system_clock",
      "confidence": "high"
    }
  },
  "signal_type": "explicit_ask",
  "stakeholder_id": "person-kushali-g",
  "stakeholder_name": "Kushali G",
  "stakeholder_name_raw": "G, Kushali",
  "audience_id": null,
  "audience_name": null,
  "summary": "Kushali wants source-of-truth clarity for AE and advertiser identity mapping.",
  "evidence": {
    "kind": "paraphrase",
    "text": "Kushali said she wanted to ask Decentrix where the correct names come from.",
    "speaker": "G, Kushali",
    "timestamp": "09:18",
    "locator": {
      "scheme": "timestamp",
      "value": "09:18"
    }
  },
  "inference_level": "explicit",
  "confidence": "high",
  "topics": ["adbook", "identity-resolution", "decentrix"],
  "project_refs": ["fact_revenue_adbook", "AE SK"],
  "recurrence": "unknown",
  "status": "active"
}
```

Compatibility mirrors:

- Schema 1.1 meeting signals continue to emit top-level `meeting_id`, `effective_at`, and `recorded_at` through the 1.x compatibility window.
- Top-level `meeting_id` is required and non-null when `source.source_kind` is `meeting_transcript`; non-meeting schema 1.1 signals emit `meeting_id: null`.
- Schema 1.0 readers map `meeting_id` to the current source-ledger record and derive `source_id` from that record's `source_sha256`.
- A schema 1.0 signal whose meeting identity cannot be mapped to a valid source-ledger hash is reported by `doctor` and excluded from playbook derivation; the engine must not invent a generalized source identity.

Allowed `source.source_kind` values:

- `meeting_transcript`
- `email`
- `chat_thread`
- `text_thread`
- `document`
- `screenshot`
- `social_post`
- `social_profile`

Unknown source kinds fail validation. Schema 1.1 freezes complete required metadata for `meeting_transcript`. Email and document metadata become required through the Phase 4 communication-ingest contract; image and social requirements remain unsupported until their source-specific contracts land.

For `meeting_transcript`, `source_id`, `source_kind`, `source_sha256`, non-null `meeting_id`, `artifact_path`, `channel` (nullable), and `evidence_locator_scheme` are required. For non-meeting sources, `source.meeting_id` is `null`.

`source_kind` describes the communication artifact. The source ledger's existing `source.source_type` continues to describe file format such as `docx`, `vtt`, or `txt`.

Allowed timing precision values:

- `datetime`
- `date`
- `range`
- `unknown`

Timing rules:

- `occurred` is required. Unknown occurrence uses `value: null`, `precision: "unknown"`, and low confidence rather than silently substituting processing time.
- `acquired` may be `null` only when acquisition is indistinguishable from processing and the source-kind contract permits it.
- `meeting_transcript` requires non-null `acquired`; the current file-based ingest records the source file modification time as the best available acquisition time and does not promote it to occurrence without the low-confidence warning below.
- `recorded` is required and uses the engine clock.
- `end_value` is required only for `range` and otherwise is `null`.
- File modification time normally describes acquisition for downloaded Teams transcripts. If it is the only occurrence fallback, it remains low confidence and the run summary warns that it may be the download date.

Allowed evidence locator schemes:

- `timestamp`
- `message_id`
- `line_range`
- `document_anchor`
- `image_region`
- `url_element`
- `none`

Schema 1.1 meeting signals may use `timestamp` or `none`. Deterministic validation verifies locator shape and scheme membership. It verifies source existence only for addressable schemes whose source-kind contract supports lookup; transcript timestamp text is not guaranteed to be a machine-resolvable address.

Allowed schema 1.1 `signal_type` values:

- `explicit_ask`
- `stakeholder_priority`
- `decision_rationale`
- `commitment`
- `risk_or_concern`
- `communication_preference`
- `communication_behavior`
- `interaction_response`

Signal-type rules:

- `communication_preference` records a stated preference about format, detail, sequence, channel, timing, supporting evidence, or interaction structure.
- `communication_behavior` records an observable event behavior without turning it into a person-level trait.
- `interaction_response` records an observable response linked to a specific antecedent communication approach and requires the typed extension below.
- `communication_style` is not a source signal type. It is permitted only as derived pattern vocabulary under the Playbook Guidance V1.1 contract.
- Providers do not set recurrence. The engine writes `recurrence: "unknown"`; playbook derivation computes recurrence across observations.

The current provider payload contract does not yet permit the three new playbook-facing types or the `interaction_response` extension. Providers must not emit them until `docs/provider-handoff-contract.md`, provider payload validation, extraction prompts, repo-maintained skills, and installed skill copies are amended together.

Identity rules:

- `stakeholder_name_raw` is required for every person-directed schema 1.1 signal and preserves the best available source/provider label.
- `stakeholder_name` is the normalized display value emitted for the observation.
- `stakeholder_id` may contain an exact reviewed registry match or an extraction-time hint. It is never authoritative during playbook derivation.
- Derivation resolves `stakeholder_name_raw` through the current reviewed registry and ignores stored IDs as identity shortcuts.
- Schema 1.0 derivation treats `stakeholder_name` as the best available legacy raw label and records the provider-normalization caveat.
- Group-directed observations use `audience_id` and `audience_name`; they do not mint a fake person.

#### Interaction Response Extension

An `interaction_response` signal keeps every common schema 1.1 field and adds:

```json
{
  "interaction": {
    "antecedent": {
      "source_id": "src-a1b2c3d4e5f6",
      "evidence_locator": {
        "scheme": "message_id",
        "value": "msg-14"
      },
      "approach_tags": ["recommendation_first", "supporting_detail"],
      "approach_label": null,
      "summary": "The update led with a recommendation and then supporting evidence."
    },
    "response": {
      "source_id": "src-a1b2c3d4e5f6",
      "evidence_locator": {
        "scheme": "message_id",
        "value": "msg-15"
      },
      "response_kind": "explicit_approval",
      "valence": "positive",
      "summary": "The stakeholder explicitly approved the recommendation."
    },
    "antecedent_at": "2026-07-10T14:03:00-04:00",
    "response_at": "2026-07-10T14:07:00-04:00",
    "link_confidence": "high",
    "causal_confidence": "unknown"
  }
}
```

Allowed response kinds:

- `explicit_approval`
- `adoption_or_action`
- `requested_continuation`
- `accepted_with_revision`
- `requested_clarification`
- `explicit_rejection`
- `abandoned_or_reversed`
- `polite_acknowledgment`
- `emoji_reaction`
- `response_timing`
- `unclear`

Allowed valence values:

- `positive`
- `negative`
- `neutral`
- `mixed`
- `unclear`

Allowed approach tags for the initial contract:

- `recommendation_first`
- `context_first`
- `risk_first`
- `mitigation_first`
- `summary_then_detail`
- `detail_first`
- `supporting_detail`
- `source_lineage`
- `example_driven`
- `visual_artifact`
- `one_page_summary`
- `async_pre_read`
- `direct_ask`
- `options_with_recommendation`
- `custom`

`approach_label` is required when `custom` is present and otherwise is `null`.

Interaction-response evidence rules:

- Explicit approval is a valid observation but does not by itself establish a context-general pattern.
- Adoption or action is strong evidence when linked to the proposal, but causation remains unknown unless explicit.
- A request to continue, repeat, expand, or reuse an approach is strong preference evidence.
- Timing, emoji, thanks, politeness, and sentiment are corroborating evidence only and cannot independently support durable positive-response guidance.
- No response is not a source observation in schema 1.1.
- `causal_confidence` defaults to `unknown` and never inherits `link_confidence`.
- `accepted_with_revision` normally maps to `mixed` unless the evidence explicitly supports another valence.
- `requested_clarification` normally maps to `neutral` or `unclear`; it is not negative without explicit evidence.

### Schema 1.1 Source And Signal Identity

`source_id` format:

```text
src-<first-12-lowercase-hex-of-source_sha256>
```

New signal ID format:

```text
sig-<source-12-hex>-<observation-12-hex>[-<collision-suffix>]
```

Observation identity input is canonical JSON containing:

- `signal_type`
- normalized `stakeholder_name_raw`, or normalized `audience_name` when no person is directed
- canonical evidence locator when its scheme is not `none`
- normalized evidence text only when the locator scheme is `none`

Canonicalization rules:

- Unicode text is normalized to NFC.
- Actor names are trimmed, internal whitespace is collapsed, and case-folding is applied.
- Evidence text is trimmed and internal whitespace is collapsed without case-folding.
- Locator objects use sorted keys and source-kind-specific normalized values.
- Canonical JSON uses UTF-8, sorted keys, and no insignificant whitespace.
- The observation hash is SHA-256 over the canonical JSON; the ID uses the first 12 lowercase hexadecimal characters.

Within one source:

- Identical canonical structured observations collapse as duplicates.
- If two non-identical observations produce the same truncated ID, sort their full structured-content SHA-256 values lexicographically. The first keeps the unsuffixed ID; subsequent observations receive deterministic suffixes `-2`, `-3`, and so on.
- Collision collapse or suffixing is reported in the run summary warnings.

The canonical observation reference is `(source_id, signal_id)`. Existing schema 1.0 IDs remain valid without migration.

### Signal Regeneration And Supersession

Refreshing signals for an existing source may supersede prior observations.

Rules:

- Locator-based IDs remain stable when signal type, raw actor, and source locator remain stable.
- Observations that cannot retain identity explicitly supersede the prior signal set for that source.
- The source-ledger signal block records the current signal-set fingerprint and the regeneration event records the prior fingerprint. A signal-set fingerprint is SHA-256 over the exact signal JSONL file bytes after the file is fully written and validated, stored as `sha256:<64-lowercase-hex>`.
- Playbook rebuild reports review events that reference observations no longer present.
- `doctor` reports suppressed content that re-emerges under a new signal ID when source ID, signal type, raw actor, and locator match.
- Signal suppression must never disappear silently because provider evidence wording changed.
- Regeneration fixtures must cover paraphrase drift, locator change, duplicates, truncated-ID collision behavior, supersession, and suppression re-emergence.

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

## Title Repair Contract

Controlled title repair uses this CLI shape:

```text
meeting-ingest repair-title <meeting-id-or-source-sha> --title "<title>" [--slug "<slug>"] [--json]
```

Rules:

- `repair-title` updates mutable display metadata only: title, slug, and mode-specific artifact paths.
- It must not change `meeting_id`, `source_sha256`, signal IDs, processed archive path, original source identity, or transcript content.
- If `--slug` is omitted, the engine derives a slug from `--title` using the normal filename slug rules.
- The repair applies to all ready markdown mode artifacts for the selected source unless a future `--mode` option is explicitly added.
- Existing markdown files are moved to their repaired filenames in place. The old path is not preserved as a stub or redirect in v1; ledger history is the source of old-path provenance.
- Filename collisions use the same numeric suffix rule as initial ingest and must be reported in warnings.
- The command appends a complete `title_repaired` ledger snapshot containing every known mode artifact entry with repaired title/slug/path metadata.
- The command returns `status: "success"` and exit `0` when at least one artifact path or title metadata changed.
- If the requested title/slug already matches current state, the command returns `status: "no_op"` and exit `0` without appending a ledger record.
- If any expected artifact file cannot be moved, the command must fail without appending `title_repaired`; partially moved files must be surfaced as a repair-required error for `doctor` rather than silently normalized.

Minimum `title_repaired` ledger fields:

```json
{
  "schema_version": "1.0",
  "event": "title_repaired",
  "source_sha256": "2d17d59a230107b3e5a1df1528eacd3328d40b4746cfbcab99d86242158cfd5a",
  "meeting_id": "mtg-20260612-71e6b28b",
  "ingest_run_id": null,
  "artifacts": {
    "summary-plus-verbatim": {
      "status": "ready",
      "path": "2026-06-12-kushali-adbook-revenue-design.md",
      "schema_version": "1.0",
      "title": "Kushali x Ken - AdBook revenue design",
      "slug": "kushali-adbook-revenue-design",
      "title_confidence": "manual",
      "filename_confidence": "manual"
    }
  },
  "repair": {
    "previous_title": "Kushali x Ken - AdBook fact_revenue detail design",
    "previous_slug": "kushali-adbook-fact-revenue-detail",
    "changed_modes": ["summary-plus-verbatim"]
  },
  "recorded_at": "2026-07-03T12:00:00Z"
}
```

## Meeting Occurrence And Date Repair Contract

### Occurrence Candidate Selection

Effective-date inference is candidate-based and deterministic. Before minting
`meeting_id`, `ingest_run_id`, or a provider request, the engine gathers every
available occurrence candidate and selects by fixed precedence:

1. operator override via `--meeting-date` — confidence `manual`, source `override`
2. transcript content export stamp or human date header — confidence `high`, source `content`
3. filename date — confidence `high`, source `filename`
4. file modification time — confidence `low`, source `file_mtime`

Rules:

- Selection is precedence-ordered, never content-weighted. The first available
  candidate wins.
- Contextual date evidence (weekday names, relative-date phrases, nearby
  absolute-date references inside dialogue) is explicitly out of scope for v1
  candidate selection and must not influence the chosen date.
- When two or more non-`file_mtime` candidates disagree, the engine still
  selects by precedence and appends a run-summary warning listing every
  non-`file_mtime` candidate as `source=value` pairs.
- An operator override always wins, including over conflicting high-confidence
  evidence; the conflict warning still fires so the operator sees the
  disagreement.
- Whenever the selected source is `file_mtime`, `ingest` and `provider-request`
  must append a prominent run-summary warning stating that the date may be a
  download/acquisition time rather than the meeting occurrence, and naming both
  escape hatches: `--meeting-date` before ingest, `repair-date` after.

### Manual Meeting-Date Override

CLI shape:

```text
meeting-ingest ingest <source> --meeting-date YYYY-MM-DD [...]
meeting-ingest provider-request <source> --meeting-date YYYY-MM-DD [...]
```

Rules:

- `--meeting-date` accepts only a real calendar date in `YYYY-MM-DD` form.
  Anything else fails with config error code `invalid_meeting_date` and the
  usage/config exit code before any extraction or minting happens.
- The override participates in candidate selection as the highest-precedence
  candidate; the chosen effective date records confidence `manual` and source
  `override` in artifacts, provider requests, and run summaries.
- Batch commands (`ingest-inbox`, `session-inbox`) do not accept
  `--meeting-date` in v1: one date across many sources is an error amplifier,
  not an escape hatch. Per-source overrides go through single-source `ingest`
  or `provider-request`.
- For session-provider work the override applies at phase 1: the persisted
  provider request carries the overridden `effective_date`,
  `date_confidence`, and `date_source`, and phase 2 adopts them through the
  normal persisted-request rebinding rules.

### Date Repair Contract

Controlled date repair uses this CLI shape:

```text
meeting-ingest repair-date <meeting-id-or-source-sha> --date YYYY-MM-DD [--root <path>] [--json]
```

Rules:

- `<meeting-id-or-source-sha>` is an exact `meeting_id` or an exact full
  `source_sha256`. Prefix matching is not supported in v1.
- `repair-date` updates mutable occurrence metadata only: artifact filename
  date prefixes (file renames), artifact front-matter `date`,
  `date_confidence`, and `date_source` fields, and signal-record
  `effective_at` values.
- Repaired metadata records confidence `manual` and source `repair`.
- It must not change `meeting_id`, `ingest_run_id` values on existing records,
  `signal_id` values, signal counts, `source_sha256`, the processed archive
  path, original source identity, or transcript content. The date segments
  embedded in `meeting_id` and `signal_id` are minting provenance, not current
  occurrence, and are documented as such.
- The signal JSONL file path is keyed by `meeting_id` and therefore does not
  move; its records are rewritten in place with only `effective_at` changed.
- Artifact renames replace the leading `YYYY-MM-DD` filename prefix and keep
  the existing slug. Filename collisions use the same numeric suffix rule as
  initial ingest and must be reported in warnings.
- The repair applies to all ready markdown mode artifacts for the selected
  source.
- The command appends a complete `date_repaired` ledger snapshot containing
  every known mode artifact entry with repaired path metadata, only after all
  file renames and rewrites have succeeded.
- A `date_repaired` snapshot carries current primary-artifact state: duplicate
  detection, no-op summaries, and doctor current-state checks must treat it
  exactly like `ingest_completed` when it is the latest record for a source.
- The command returns `status: "success"` and exit `0` when at least one date
  field or artifact path changed.
- If the requested date already matches current state, the command returns
  `status: "no_op"` and exit `0` without appending a ledger record.
- If the target cannot be resolved from the ledger, the command fails with
  error code `repair_target_not_found`. If an expected artifact or signal file
  is missing or cannot be moved, it fails with `repair_artifact_missing` (or
  the underlying write error) without appending `date_repaired`; partial
  states are surfaced by `doctor` as missing-path issues rather than silently
  normalized.

Minimum `date_repaired` ledger fields:

```json
{
  "schema_version": "1.0",
  "event": "date_repaired",
  "source_sha256": "63d2e8690b7ba09d51e80cc1d3be40fa530c5479b15e33bd2535e0881bccaf55",
  "meeting_id": "mtg-20260703-63d2e869",
  "ingest_run_id": null,
  "artifacts": {
    "summary-plus-verbatim": {
      "status": "ready",
      "path": "2026-07-10-nitesh-follow-up-interview-debrief.md",
      "schema_version": "1.0",
      "title": "Nitesh Follow-Up Interview Debrief",
      "slug": "nitesh-follow-up-interview-debrief"
    }
  },
  "repair": {
    "previous_date": "2026-07-03",
    "previous_date_confidence": "low",
    "previous_date_source": "file_mtime",
    "date": "2026-07-10",
    "changed_modes": ["summary-plus-verbatim"]
  },
  "recorded_at": "2026-07-18T12:00:00Z"
}
```

### Low-Confidence Date Doctor Check

- `doctor` reports advisory issue code `low_confidence_meeting_date` for every
  current ready artifact whose front matter records `date_source: file_mtime`.
- The check is read-only and never mutates project files.
- A successful `repair-date` clears the condition because the repaired front
  matter records `date_source: repair`.

## Regeneration Contract

Regeneration uses this CLI shape:

```text
meeting-ingest regenerate <meeting-id-or-source-sha> --mode summary|summary-plus-verbatim|verbatim [--provider mock|anthropic|session] [--quality fast|balanced|deep] [--json]
```

Rules:

- `_processed/` is the durable source of truth for regeneration.
- `_cache/` may be used only as an optimization. Missing cache entries must not block regeneration when the processed source exists.
- Regeneration creates a new `ingest_run_id`.
- Regeneration overwrites the current artifact for the selected mode by replacing it atomically with deterministic renderer output. It does not create timestamped public replacements in v1.
- The old artifact path is retained in the append-only ledger history; no stub or redirect file is created.
- Regeneration of one mode must preserve the current ledger entries for all other modes.
- If regeneration changes the selected mode's title or slug through provider output, the engine may update that mode's artifact path but must report the change in warnings. User-directed cross-mode title repair should still use `repair-title`.
- `summary` and `summary-plus-verbatim` regeneration may use the configured provider because they need summary/signal extraction.
- `verbatim` regeneration is deterministic by default and should use `provider: none`; if a future provider-assisted repair option is used, that provider usage must be explicit and recorded.
- `regenerate --provider session` starts a fresh phase-1 provider request with the new `ingest_run_id`. It must not reuse old request/response files. Phase 2 must verify the fresh persisted request exactly as normal session ingest does.
- The command appends a complete `artifact_regenerated` ledger snapshot after the regenerated markdown and any refreshed signal file are ready.
- If regeneration fails before the replacement artifact is ready, the current artifact remains the current state and the command appends `ingest_failed` only when it has enough identity to write a valid failure snapshot.

Minimum `artifact_regenerated` ledger fields:

```json
{
  "schema_version": "1.0",
  "event": "artifact_regenerated",
  "source_sha256": "2d17d59a230107b3e5a1df1528eacd3328d40b4746cfbcab99d86242158cfd5a",
  "meeting_id": "mtg-20260612-71e6b28b",
  "ingest_run_id": "ingest-20260612-20260703T130000Z-c3d4",
  "regeneration": {
    "mode": "summary",
    "source_path": "_processed/2d17d59a-Call with G, Kushali (5).docx",
    "replaced_path": "2026-06-12-kushali-adbook-revenue-design.md"
  },
  "artifacts": {
    "summary": {
      "status": "ready",
      "path": "2026-06-12-kushali-adbook-revenue-design-summary.md",
      "schema_version": "1.0",
      "title": "Kushali x Ken - AdBook revenue design",
      "slug": "kushali-adbook-revenue-design-summary"
    },
    "summary-plus-verbatim": {
      "status": "ready",
      "path": "2026-06-12-kushali-adbook-revenue-design.md",
      "schema_version": "1.0",
      "title": "Kushali x Ken - AdBook revenue design",
      "slug": "kushali-adbook-revenue-design"
    }
  },
  "signals": {
    "status": "ready",
    "path": "_signals/mtg-20260612-71e6b28b.jsonl",
    "count": 5,
    "fingerprint": "sha256:91aa2c80b731...",
    "previous_fingerprint": "sha256:80aa1b70a620...",
    "refreshed": true
  },
  "recorded_at": "2026-07-03T13:00:00Z"
}
```

### Ledger Events

Recommended v1 event values:

- `primary_artifacts_ready`
- `ingest_completed`
- `reconcile_repaired`
- `ingest_failed`
- `source_quarantined`
- `artifact_regenerated`
- `title_repaired`
- `date_repaired`

Write timing:

1. After markdown and signal files are written, append `primary_artifacts_ready`.
2. After processed archive copy and inbox reconciliation complete or are explicitly skipped, append `ingest_completed`.
3. If a duplicate/no-op run repairs a missing processed copy or reconciles a re-dropped source, append `reconcile_repaired`.
4. If ingest fails before primary artifacts are ready, append `ingest_failed` or `source_quarantined` when possible.

`derived_updated` is deprecated as a source-ledger event. Existing records remain readable compatibility history. New playbook rebuilds append to `_playbook-state/derivation-ledger.jsonl` and never rewrite or fan out corpus-derived state into source snapshots.

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
    "processed_path": "_processed/2d17d59a-Call with G, Kushali (5).docx",
    "source_type": "docx"
  },
  "artifacts": {
    "summary-plus-verbatim": {
      "status": "ready",
      "path": "2026-06-12-kushali-adbook-fact-revenue-detail.md",
      "schema_version": "1.0",
      "title": "Kushali x Ken - AdBook fact_revenue detail design",
      "slug": "kushali-adbook-fact-revenue-detail",
      "title_confidence": "high",
      "filename_confidence": "high",
      "provider": "anthropic",
      "model_alias": "balanced",
      "model_id": "claude-sonnet-placeholder",
      "provider_host": null
    }
  },
  "signals": {
    "status": "ready",
    "path": "_signals/mtg-20260612-71e6b28b.jsonl",
    "count": 5,
    "fingerprint": "sha256:91aa2c80b731..."
  },
  "derived": {
    "playbook_input_status": "pending"
  },
  "error": null,
  "quarantine": null,
  "reconcile": {
    "status": "completed",
    "path": "_inbox/_done/Call with G, Kushali (5).docx",
    "processed_path": "_processed/2d17d59a-Call with G, Kushali (5).docx"
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

- `pending`
- `completed`
- `skipped`
- `failed`

Playbook input status values:

- `not_applicable`
- `pending`

`derived.playbook_input_status` is an ingest-time hint only. It is never updated later in the source ledger. Current, stale, failed, or missing playbook state is computed from signal, registry, ruleset, and review fingerprints against the playbook derivation ledger and index.

Use `pending` when the source produced at least one validated playbook-eligible observation. Use `not_applicable` when it produced no eligible observation, including a valid empty signal file.

Existing `derived.playbook_update_status` values remain readable compatibility data but are not authoritative for new behavior.

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

## Stakeholder Briefing V1 Artifact Contract

Stakeholder Briefing V1 is deterministic and uses validated signal JSONL, reviewed identity state, versioned rules, and append-only review events. It does not call a provider.

### Storage Authority And Paths

All paths are relative to the meetings root.

Durable reviewed state:

```text
_playbook-state/
  stakeholders.toml
  derivation-ledger.jsonl
  overrides.jsonl
```

Rebuildable materializations:

```text
_derived/
  playbook-index.json
  generations/
    <derivation-run-id>/
      identity-candidates.json
      stakeholders/
        <person-id>/
          profile.json
          briefing.md
```

Rules:

- `_playbook-state/` is durable human-reviewed state and must never be removed by cache or derived-output cleanup.
- `_derived/` is rebuildable and may be removed when no derivation is running.
- Readers resolve current artifacts only through `playbook-index.json`; they never select the lexically or chronologically newest generation directory.
- A generation may be pruned when it is not current in the index and is not required to recover the current generation.
- Project-local ignored storage is not a backup. User documentation should recommend an approved local or encrypted backup for `_playbook-state/`.
- Profiles and briefings are concentrated sensitive artifacts. iQ Context and other capture integrations must not copy profile bodies or concentrated evidence by default.

### Stakeholder Registry

`_playbook-state/stakeholders.toml` is human-owned and must not be silently written by extraction or derivation.

Minimum shape:

```toml
schema_version = "1.0"

[[people]]
person_id = "person-kushali-g"
display_name = "Kushali G"
aliases = ["Kushali", "G, Kushali", "Kushali G"]
status = "reviewed"
```

Rules:

- `person_id` uses lowercase ASCII letters, numbers, and hyphens and is immutable after use.
- `status` is `reviewed` in V1.
- Display-name and alias edits do not change `person_id`.
- Alias comparison uses Unicode NFC normalization, trimmed/collapsed whitespace, and case-folding.
- Normalized aliases must be injective. The same alias under two people is ambiguous, resolves to neither person, and is reported by `doctor`.
- Resolution order is exact reviewed external identifier when later supported, exact reviewed alias, exact unambiguous normalized display name, candidate, then unresolved.
- Fuzzy similarity never auto-merges people.
- Provider-proposed IDs and stored signal IDs are advisory only. Derivation resolves raw labels through the current registry.
- Registry redirects and external identifiers are deferred until their contract is added; merges in V1 use reviewed alias edits and rebuild.

Unresolved names and suggested registry entries are written only to the current generation's `identity-candidates.json`:

```json
{
  "schema_version": "1.0",
  "generated_at": "2026-07-10T18:00:00Z",
  "candidates": [
    {
      "raw_name": "Presenter",
      "normalized_name": "Presenter",
      "signal_count": 4,
      "source_count": 1,
      "suggested_person_id": null,
      "reason": "generic_or_ambiguous_label"
    }
  ]
}
```

### Briefing Ruleset

The default deterministic ruleset ID is:

```text
briefing-rules-v1
```

Default values:

- minimum distinct source events for recurrent qualification: `2`
- tracked ask or commitment verify-after interval: `30` days
- priority or concern stale-after interval: `60` days
- communication preference, behavior, or interaction response stale-after interval: `90` days

Project config may override permitted numeric values. The effective values and ruleset fingerprint are stored in every derivation-ledger record and index.

Rules:

- One explicit high-confidence communication preference may appear as a current preference but is not labeled recurrent.
- Weak-inference observations appear only under unresolved or low-confidence observations and cannot independently qualify recurrence.
- A deterministic rollup confidence may not exceed the lowest-confidence supporting observation; contradicting evidence may lower it further.
- Distinct source count is not necessarily distinct communication-event count. Cross-representation event identity is required before image and forwarded-source inputs can promote patterns together.
- Stale items remain visible with a stale or verify-before-citing marker; derivation does not delete them automatically.

### Input Fingerprint

An eligible signal file:

- is a discovered `_signals/*.jsonl` file whose nonblank lines all validate against a supported signal schema
- contains at least one signal record after schema normalization; empty or whitespace-only files are excluded
- has resolvable generalized source identity, including successful schema 1.0 meeting-to-source-ledger mapping

Malformed, unsupported, or identity-unmappable files are excluded and reported by `doctor`. Signal suppression does not make a file ineligible because the override ledger is a separate fingerprint input. A meeting whose signal file is empty uses `derived.playbook_input_status: "not_applicable"`; adding an empty signal file does not make a current briefing stale.

The derivation input fingerprint is SHA-256 over canonical JSON containing:

- sorted eligible signal paths, expressed relative to the meetings root with `/` separators, and each file's SHA-256 over exact bytes
- stakeholder registry SHA-256
- review-overlay ledger SHA-256
- effective ruleset ID and values
- supported schema versions
- renderer version

Canonical JSON uses UTF-8, sorted keys, and no insignificant whitespace. The stored value uses:

```text
sha256:<64-lowercase-hex>
```

### Derivation Run And Generation IDs

Derivation run IDs use:

```text
derive-YYYYMMDD-<UTC-timestamp>-<short-suffix>
```

Example:

```text
derive-20260710-20260710T180000Z-a1b2
```

The immutable generation directory name equals the derivation run ID.

### Derivation Ledger

`_playbook-state/derivation-ledger.jsonl` is append-only. One line is one run outcome.

Successful commit record:

```json
{
  "schema_version": "1.0",
  "event": "briefing_derivation_completed",
  "derivation_run_id": "derive-20260710-20260710T180000Z-a1b2",
  "status": "success",
  "trigger": "explicit_cli",
  "input_fingerprint": "sha256:...",
  "registry_fingerprint": "sha256:...",
  "overrides_fingerprint": "sha256:...",
  "ruleset": {
    "id": "briefing-rules-v1",
    "fingerprint": "sha256:...",
    "values": {
      "min_recurrent_source_events": 2,
      "tracked_verify_after_days": 30,
      "priority_concern_stale_after_days": 60,
      "preference_behavior_response_stale_after_days": 90
    }
  },
  "provider": "none",
  "generation_path": "_derived/generations/derive-20260710-20260710T180000Z-a1b2",
  "profiles": [
    {
      "person_id": "person-kushali-g",
      "profile_path": "_derived/generations/derive-20260710-20260710T180000Z-a1b2/stakeholders/person-kushali-g/profile.json",
      "briefing_path": "_derived/generations/derive-20260710-20260710T180000Z-a1b2/stakeholders/person-kushali-g/briefing.md"
    }
  ],
  "unresolved_identity_count": 1,
  "warnings": [],
  "errors": [],
  "recorded_at": "2026-07-10T18:00:00Z"
}
```

Failure record uses `event: "briefing_derivation_failed"`, `status: "failed"`, `generation_path: null`, an empty `profiles` array, and at least one structured error. A failed record never commits a generation.

Malformed or unsupported derivation-ledger lines are ignored for commit-state calculation and reported by `doctor`.

Allowed Briefing V1 `trigger` values are `explicit_cli` and `agent_wrapper`. Future scheduled or provider-guidance triggers require a contract amendment rather than free-form values.

### Playbook Index

`_derived/playbook-index.json` is an atomic pointer to the latest committed generation and is rebuildable from the derivation ledger and generation outputs.

```json
{
  "schema_version": "1.0",
  "status": "current",
  "derivation_run_id": "derive-20260710-20260710T180000Z-a1b2",
  "generation_path": "_derived/generations/derive-20260710-20260710T180000Z-a1b2",
  "input_fingerprint": "sha256:...",
  "registry_fingerprint": "sha256:...",
  "overrides_fingerprint": "sha256:...",
  "ruleset_id": "briefing-rules-v1",
  "ruleset_fingerprint": "sha256:...",
  "profiles": {
    "person-kushali-g": {
      "profile_path": "_derived/generations/derive-20260710-20260710T180000Z-a1b2/stakeholders/person-kushali-g/profile.json",
      "briefing_path": "_derived/generations/derive-20260710-20260710T180000Z-a1b2/stakeholders/person-kushali-g/briefing.md"
    }
  },
  "identity_candidates_path": "_derived/generations/derive-20260710-20260710T180000Z-a1b2/identity-candidates.json",
  "unresolved_identity_count": 1,
  "committed_at": "2026-07-10T18:00:00Z"
}
```

The stored index `status` is commit-time state and is always `current` when the index is written for a committed generation. `status --json` computes live freshness by comparing the stored fingerprints with current eligible inputs and may report `stale`, `missing`, or `failed` without rewriting the index; readers must not treat the stored field as a live health result.

### Review Overlay Ledger

`_playbook-state/overrides.jsonl` is append-only. Current review state is computed by folding valid events in recorded order.

Common fields:

```json
{
  "schema_version": "1.0",
  "review_event_id": "review-20260710T181500Z-a1b2",
  "action": "resolve",
  "target": {},
  "reason": null,
  "note": "Confirmed delivered in the July 10 review.",
  "actor": "user",
  "recorded_at": "2026-07-10T18:15:00Z"
}
```

Briefing V1 actions:

- `reject_entry`
- `restore_entry`
- `resolve_tracked_item`
- `suppress_signal`
- `unsuppress_signal`

Target shapes:

```json
{"entry_id": "entry-person-kushali-g-commitment-06c55ee04dba"}
```

Resolve target:

```json
{
  "entry_id": "entry-person-kushali-g-commitment-06c55ee04dba",
  "resolution_state": "resolved"
}
```

```json
{"source_id": "src-a1b2c3d4e5f6", "signal_id": "sig-a1b2c3d4e5f6-91aa2c80b731"}
```

Rules:

- Reject and suppress actions require `reason`.
- Resolve requires `note` and `resolution_state` in the target with value `explicitly_outstanding`, `resolved`, `withdrawn`, or `superseded`.
- Restore and unsuppress require `note` explaining the reversal.
- `actor` is required free-form text in V1 and should identify the human or authorized agent context that made the change.
- Malformed events are ignored and reported by `doctor`.
- Orphaned events remain in history and are reported; they are never silently deleted.
- Pattern/guidance review actions are added by the Guidance V1.1 contract.

### Profile JSON

Each current stakeholder has one canonical profile in the committed generation.

Top-level shape:

```json
{
  "schema_version": "1.0",
  "profile_kind": "stakeholder_briefing",
  "stakeholder": {
    "person_id": "person-kushali-g",
    "display_name": "Kushali G",
    "aliases": ["Kushali", "G, Kushali"],
    "identity_status": "reviewed"
  },
  "derivation_run_id": "derive-20260710-20260710T180000Z-a1b2",
  "generated_at": "2026-07-10T18:00:00Z",
  "input_fingerprint": "sha256:...",
  "coverage": {
    "source_count": 6,
    "source_kinds": {"meeting_transcript": 6},
    "first_observed_at": "2026-01-15",
    "last_observed_at": "2026-07-09"
  },
  "tracked_asks": [],
  "tracked_commitments_by_stakeholder": [],
  "tracked_commitments_to_stakeholder": [],
  "priorities": [],
  "concerns_and_risks": [],
  "decision_rationales": [],
  "communication_preferences": [],
  "communication_behaviors": [],
  "interaction_responses": [],
  "patterns": {
    "status": "not_available_in_briefing_v1",
    "items": []
  },
  "guidance": {
    "status": "not_available_in_briefing_v1",
    "items": []
  },
  "recent_changes": [],
  "contradiction_candidates": [],
  "unresolved_observations": [],
  "stale_items": []
}
```

Every deterministic entry uses:

```json
{
  "entry_id": "entry-person-kushali-g-priority-ba5a32787229",
  "entry_kind": "priority",
  "statement": "Source-of-truth clarity is a recurring priority.",
  "scope": {
    "project_refs": ["fact_revenue_adbook"],
    "topics": ["identity-resolution"],
    "channel": null
  },
  "confidence": "high",
  "confidence_rationale": "Two explicit observations from two meeting sources.",
  "supporting_observations": [
    {"source_id": "src-a1b2c3d4e5f6", "signal_id": "sig-a1b2c3d4e5f6-91aa2c80b731"},
    {"source_id": "src-b2c3d4e5f607", "signal_id": "sig-b2c3d4e5f607-a2bb3d91c842"}
  ],
  "contradicting_observations": [],
  "distinct_source_count": 2,
  "first_observed_at": "2026-06-12",
  "last_observed_at": "2026-07-09",
  "lifecycle_state": "active",
  "review_state": "unreviewed",
  "freshness_state": "current"
}
```

Allowed deterministic entry states:

- `lifecycle_state`: `active`, `superseded`
- `review_state`: `unreviewed`, `rejected`, `restored`
- `freshness_state`: `current`, `verify_before_citing`, `stale`

Each `recent_changes` item references a current `entry_id` and carries one or more `change_kinds`: `first_observed`, `lifecycle_state_changed`, `review_state_changed`, or `freshness_state_changed`. State-change items include the prior and current value for each changed state; they do not duplicate the full entry.

Tracked asks and commitments additionally use:

- `originating_observation`
- `observed_at`
- `age_days`
- `last_lifecycle_evidence_at`
- `resolution_state`
- `resolution_source`

Allowed resolution states:

- `unknown`
- `explicitly_outstanding`
- `resolved`
- `withdrawn`
- `superseded`

Only explicit lifecycle evidence or a reviewed override may assign a value other than `unknown`.

Briefing text must say:

> Committed on June 12; no evidence of resolution since.

It must not infer:

> Open since June 12.

Entry lineage:

- Briefing V1 entry IDs use `entry-<person-id>-<entry-kind>-<anchor-12-hex>`.
- The anchor hash is the first 12 lowercase hexadecimal characters of SHA-256 over canonical JSON containing `person_id`, `entry_kind`, originating `source_id`, and originating `signal_id`. Canonical JSON uses UTF-8, sorted keys, and no insignificant whitespace. Hashing the full tuple prevents two sources with matching observation hashes or locators from sharing a review target and also supports legacy signal-ID shapes.
- Tracked asks, commitments, and single-observation facts use their originating observation as the anchor.
- Deterministic multi-observation rollups use the earliest qualifying observation as the anchor. Earliest is determined by normalized `occurred.value`, falling back to legacy `effective_at`; known times sort before unknown times, and ties are broken by sorted `(source_id, signal_id)`.
- Later supporting, resolution, or contradicting evidence does not change an anchored Briefing V1 entry ID.
- If the anchor observation is suppressed, superseded, or otherwise no longer qualifies, the rebuilt entry receives a new ID. Rebuild and `doctor` report orphaned review events with a nearest-successor hint based on stakeholder, entry kind, compatible scope, and overlapping observations; review state never transfers silently.
- Provider wording never participates in entry identity.
- Pattern and guidance lineage is defined in the Guidance V1.1 contract.

### Briefing Markdown

The Markdown renderer mirrors profile JSON and uses this stable section order:

```markdown
# Stakeholder Briefing: <Display Name>

## Identity And Evidence Coverage

## Tracked Asks

## Commitments By The Stakeholder

## Commitments To The Stakeholder

## Current Priorities

## Concerns And Risks

## Decision Rationale History

## Explicit Communication Preferences

## Observed Communication Behaviors

## Interaction Responses

## Communication Cues

## Emerging And Established Patterns

## Recent Changes

## Contradictions And Cautions

## Unresolved Or Low-Confidence Observations

## Evidence Index
```

Rules:

- Empty deterministic sections use `None identified.`
- `Communication Cues` and `Emerging And Established Patterns` use `Not available in Briefing V1.`
- Every displayed entry includes its stable `entry_id` and compact source/signal citations.
- The renderer never adds facts absent from profile JSON.
- Stale or verify-before-citing state is visible next to the entry.
- The evidence index maps compact citations to source artifact path, observation ID, evidence kind, minimal excerpt, speaker, and locator.
- `Recent Changes` compares the current profile with the previously committed generation and includes entries first observed or whose lifecycle, review, or freshness state changed. On the first successful build, or when no qualifying change exists, it renders `None identified.`

### Deterministic Rebuild And Commit

Briefing rebuild holds the project lock while it:

1. discovers and hashes eligible signal, registry, ruleset, and override inputs
2. normalizes schema 1.0 and 1.1 signals
3. resolves reviewed identities and surfaces unresolved candidates
4. applies signal suppression and tracked-item resolution events
5. derives the complete profile set
6. writes and validates a new immutable generation without changing the index
7. appends `briefing_derivation_completed`, which commits the generation
8. atomically rewrites `playbook-index.json` to the committed generation

Failure semantics:

- A crash before the ledger commit leaves an uncommitted generation that never becomes current.
- A successful ledger commit followed by index-write failure leaves a committed generation; `doctor` reports the mismatch and an explicit repair command may rebuild the index.
- Failed derivation appends a failure record when possible and does not replace the current index.
- Full rebuild is the only V1 update mode. Targeted refresh is deferred.

### Briefing CLI

Mutating commands:

```text
meeting-ingest playbook update [--json]
meeting-ingest playbook reject <entry-id> --reason <text> [--json]
meeting-ingest playbook restore <entry-id> --note <text> [--json]
meeting-ingest playbook resolve <entry-id> --state explicitly_outstanding|resolved|withdrawn|superseded --note <text> [--json]
meeting-ingest playbook suppress-signal <source-id> <signal-id> --reason <text> [--json]
meeting-ingest playbook unsuppress-signal <source-id> <signal-id> --note <text> [--json]
```

Read commands:

```text
meeting-ingest playbook show <person-id-or-alias> [--format markdown|json]
meeting-ingest playbook brief <person-id-or-alias> [--format markdown|json]
```

Mutating commands use `--json` for the standard run summary. Read commands use `--format` for the returned payload and do not add a second `--json` flag.

`playbook show` returns the complete committed `profile.json` or `briefing.md` payload selected through the current index. `playbook brief` returns a deterministic concise projection containing identity/coverage, tracked asks, commitments, current priorities, concerns, explicit preferences, recent behaviors/responses, freshness warnings, and compact citations. It omits the full evidence appendix but never removes the citations needed to audit a displayed statement. The concise projection is generated from the current profile and is not a separate durable artifact in V1.

Successful `playbook update --json` summary:

```json
{
  "schema_version": "1.0",
  "status": "success",
  "exit_code": 0,
  "source_sha256": null,
  "meeting_id": null,
  "ingest_run_id": null,
  "artifacts": [
    {
      "kind": "playbook_index",
      "status": "ready",
      "path": "_derived/playbook-index.json"
    }
  ],
  "warnings": [],
  "errors": [],
  "command": "playbook_update",
  "derivation_run_id": "derive-20260710-20260710T180000Z-a1b2",
  "generation_path": "_derived/generations/derive-20260710-20260710T180000Z-a1b2",
  "input_fingerprint": "sha256:...",
  "profiles_written": 4,
  "unresolved_identity_count": 1
}
```

Review mutation summaries add:

- `review_event_id`
- `action`
- `target`
- `changed`

No-op review commands return `status: "no_op"`, exit `0`, and do not append duplicate events.

### Briefing Status And Doctor

`status --json` adds:

```json
{
  "playbook": {
    "status": "current",
    "derivation_run_id": "derive-20260710-20260710T180000Z-a1b2",
    "input_fingerprint": "sha256:...",
    "current_input_fingerprint": "sha256:...",
    "profile_count": 4,
    "unresolved_identity_count": 1,
    "rejected_or_suppressed_count": 2,
    "guidance_status": "not_available_in_briefing_v1",
    "latest_attempt_status": "success"
  }
}
```

Allowed playbook status values:

- `current`
- `stale`
- `missing`
- `failed`

`failed` means no usable committed generation exists and the latest derivation attempt failed. When an older committed generation remains usable after a later failed attempt, `status` is `current` or `stale` according to fingerprints and `latest_attempt_status` is `failed`.

Additional doctor issue codes:

- `playbook_state_missing`
- `identity_registry_invalid`
- `identity_alias_ambiguous`
- `signal_identity_invalid`
- `signal_suppression_reemerged`
- `derivation_ledger_malformed`
- `derivation_generation_uncommitted`
- `derivation_index_mismatch`
- `playbook_profile_missing`
- `playbook_profile_invalid`
- `playbook_stale`
- `review_event_malformed`
- `review_event_orphaned`
- `evidence_locator_invalid`

`doctor` detects and reports. It does not rebuild the index, delete generations, edit the registry, or rewrite review events. Repair commands require separate explicit contracts.

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
      "count": 5,
      "fingerprint": "sha256:91aa2c80b731..."
    }
  ],
  "derived": {
    "playbook_input_status": "pending"
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

`derived.playbook_input_status` reports whether the completed ingest produced eligible playbook inputs. It does not claim that a profile rebuild ran. Existing `derived.playbook_update_status` run-summary fields remain compatibility data only.

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
  "source": {
    "path": "_inbox/Call with G, Kushali (5).docx",
    "source_type": "docx",
    "known_original_path": "_inbox/Call with G, Kushali (5).docx"
  },
  "existing_artifacts": {
    "summary-plus-verbatim": "2026-06-12-kushali-adbook-fact-revenue-detail.md"
  },
  "existing_artifact_details": {
    "summary-plus-verbatim": {
      "status": "ready",
      "path": "2026-06-12-kushali-adbook-fact-revenue-detail.md",
      "schema_version": "1.0",
      "title": "Kushali x Ken - AdBook fact_revenue detail design",
      "slug": "kushali-adbook-fact-revenue-detail"
    }
  },
  "archive": {
    "processed_path": "_processed/2d17d59a-Call with G, Kushali (5).docx"
  },
  "reconcile": {
    "status": "completed",
    "path": "_inbox/_done/Call with G, Kushali (5).docx",
    "processed_path": "_processed/2d17d59a-Call with G, Kushali (5).docx",
    "reason": "source_already_ingested"
  },
  "repair": {
    "changed": true,
    "ledger_event": "reconcile_repaired"
  }
}
```

A duplicate/no-op run may still perform repair work when the ledger shows an otherwise-ingested source has incomplete archive or reconcile state. In that case, keep `status: "no_op"` and exit `0`, include the repair action in `warnings`, and append a complete `reconcile_repaired` ledger snapshot reflecting the repaired archive/reconcile state. If no archive or reconcile state changed, do not append a repair snapshot.

The `existing_artifacts` map is the backward-compatible mode-to-path summary. `existing_artifact_details` carries the current ledger artifact entries for agents that need provider, title, slug, or schema metadata. `repair.changed` indicates whether the no-op run performed archive/reconcile repair; `repair.ledger_event` is `reconcile_repaired` only when a repair snapshot was appended, otherwise `null`.

`reconcile --json` reports duplicate inbox repair work without re-ingesting sources. Repaired entries include:

- `path`: reconciled inbox done path when reconciliation completed.
- `source_sha256`
- `meeting_id`
- `status`
- `reason`
- `processed_path`
- `changed`

Skipped entries include:

- `path`
- `source_sha256`
- `meeting_id`, usually `null`
- `reason`

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

### Doctor And Status JSON

`doctor --json` reports project hygiene without mutating project files. It exits `0` when no issues are found and `1` when issues are found.

Example clean doctor summary:

```json
{
  "schema_version": "1.0",
  "status": "success",
  "exit_code": 0,
  "source_sha256": null,
  "meeting_id": null,
  "ingest_run_id": null,
  "artifacts": [],
  "warnings": [],
  "errors": [],
  "command": "doctor",
  "project": {
    "meetings_root": "_local/project-context/meetings",
    "ledger_records": 2,
    "known_sources": 1,
    "inbox_files": 0,
    "session_handoffs": {
      "total": 0,
      "pending": 0,
      "stale": 0,
      "failed": 0
    }
  },
  "issues": []
}
```

Example doctor summary with issues:

```json
{
  "schema_version": "1.0",
  "status": "issues_found",
  "exit_code": 1,
  "source_sha256": null,
  "meeting_id": null,
  "ingest_run_id": null,
  "artifacts": [],
  "warnings": [],
  "errors": [],
  "command": "doctor",
  "project": {
    "meetings_root": "_local/project-context/meetings",
    "ledger_records": 1,
    "known_sources": 1,
    "inbox_files": 1,
    "session_handoffs": {
      "total": 0,
      "pending": 0,
      "stale": 0,
      "failed": 0
    }
  },
  "issues": [
    {
      "code": "incomplete_reconcile",
      "message": "Primary artifacts are ready but archive/reconcile did not complete.",
      "path": "_inbox/2026-07-03-team-sync.txt"
    }
  ]
}
```

Doctor issue records use:

- `code`: stable machine-readable issue code.
- `message`: concise human-readable issue description.
- `path`: project-meetings-root-relative path when applicable, otherwise `null`.

Current issue codes:

- `malformed_ledger_json`
- `invalid_ledger_record`
- `stale_lock`
- `stale_provider_request`
- `stale_provider_response`
- `session_handoff_pending`
- `session_handoff_stale`
- `session_handoff_invalid`
- `inbox_residue`
- `missing_artifact`
- `missing_signal_file`
- `missing_processed_source`
- `incomplete_reconcile`

`status --json` uses the same shared summary keys and `project` object, but does not include `issues` and exits `0` when it can read project state.

For session-backed workflows, `status --json` also includes:

```json
{
  "session_handoffs": {
    "counts": {
      "total": 1,
      "pending": 1,
      "stale": 0,
      "failed": 0
    },
    "results": []
  }
}
```

`session_handoffs.results` uses the same per-handoff records described in `docs/provider-handoff-contract.md`. It may contain `pending_provider_response`, `stale_handoff`, or `failed` records. `doctor --json` maps those records into the `session_handoff_pending`, `session_handoff_stale`, and `session_handoff_invalid` issue codes.

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
| 10 | Lock/concurrency conflict or stale two-phase inputs |
| 11 | Reserved; legacy blocking-derived-work code |

Rules:

- Exit `0` when primary success is complete or when duplicate/no-op is successful.
- Duplicate/no-op uses exit `0` with `status: "no_op"` in JSON.
- Primary ingest does not run blocking playbook derivation. It reports only `derived.playbook_input_status`.
- An explicitly invoked playbook command is the primary operation and uses the applicable provider, validation, artifact-write, ledger-write, lock, CLI/config, or general failure code.
- Exit `10` JSON errors must distinguish `lock_conflict` from `stale_inputs`. A lock conflict is retryable after the competing operation finishes; `stale_inputs` invalidates the old phase-1 request and requires a fresh phase 1.
- Exit `11` is reserved and must not be emitted by new playbook behavior.
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
- signal records validate against a supported schema 1.0 or 1.1 signal JSONL contract

## Explicitly Deferred

Not required for the currently frozen contracts:

- Playbook Guidance V1.1 provider request and response contract
- provider-derived semantic pattern, contradiction, and guidance entry schemas
- split-file derivative artifacts
- non-meeting communication ingest contract
- screenshot/OCR evidence-region contract
- social-source provenance and privacy contract
- cross-project identity contract
- corpus migration contract
