# Design Proposal

## Purpose

This document turns the current requirements and output evaluation into a proposed build plan for `meeting-ingest`.

The goal is not to freeze every detail. The goal is to define enough architecture and product shape that implementation can start without inheriting the old Claude skill's accidental inconsistencies.

## Product Defaults

Default output mode:

- `summary-plus-verbatim`

Why:

- the maintainer more often wants both a structured smart summary and a transcript record
- one-on-one and small-group sessions often contain detailed explanation, knowledge transfer, and build/design decisions where wording matters

Common override:

- `summary` for large structured meetings such as daily standups, broad status meetings, or recurring ceremonies where a transcript is less important

Other supported mode:

- `verbatim` for a cleaned transcript record without summary extraction

## Cleaned Verbatim Transcript

For this project, "cleaned verbatim" means:

- speaker-attributed
- chronological
- lightly cleaned for readability
- filler-only artifacts may be removed
- obvious transcription junk may be repaired or omitted
- substantive words, decisions, explanations, and technical detail must not be summarized away

The artifact should state the cleanup policy in metadata.

Raw extracted text may be cached internally for provenance and repair workflows, but the default user-facing transcript should be cleaned verbatim.

## Pipeline Shape

Proposed phases:

1. discover project config and initialize missing structure if allowed
2. read source and compute content hash
3. check ledger for existing source/mode artifacts
4. extract normalized transcript from source
5. infer title, topic, meeting type, and one-on-one counterpart when applicable
6. run provider-backed structured extraction when required by mode
7. render deterministic markdown artifact
8. write structured signals
9. write ledger entry/update with primary artifact and signal status
10. archive canonical processed copy
11. reconcile inbox source only after confirmed primary success
12. emit run summary and report primary artifacts ready
13. update rolling stakeholder playbook inputs or derived playbook as separately-statused post-output work

The provider should not own final markdown shape. The provider should return structured content; the renderer should produce stable markdown.

Output readiness should be prioritized. The meeting markdown and signal file should be produced and reported as ready before slower derived work blocks the user. Rolling stakeholder playbook updates should happen during the ingest workflow when possible, but they run as post-output work after the primary artifacts are available.

Confirmed primary success means:

- primary markdown artifact written
- signal file written, even if empty
- ledger updated
- processed archive copy written
- inbox reconciliation completed or explicitly skipped by configuration

Playbook update failure should not make the meeting ingest fail. It should be captured as derived-work status for `doctor` or `status` to surface.

## Artifact Modes

### `summary-plus-verbatim`

One canonical markdown file.

Structure:

1. front matter metadata
2. meeting overview
3. attendees and identity notes
4. key topics
5. decisions
6. commitments and action items
7. dependencies and risks
8. stakeholder asks
9. communication signals
10. open questions
11. verbatim transcript

The markdown should be optimized for agent consumption as well as human reading. Stable headings, predictable metadata, explicit identifiers, and structured tables/lists are preferred over prose-only summaries.

### `summary`

One canonical markdown file with the same summary sections, excluding the transcript.

Best fit:

- daily standups
- large recurring structured meetings
- broad status meetings

### `verbatim`

One canonical markdown file containing metadata and cleaned verbatim transcript only.

Best fit:

- transcript archive without model-heavy summarization
- later repair/regeneration workflows

## Filename And Title Inference

Meeting identity and display naming are separate.

The immutable `meeting_id` should not be the semantic slug. It should be stable even when the title or filename is repaired later.

Recommended shape:

```text
mtg-YYYYMMDD-<source-shorthash>
```

Example:

```text
mtg-20260612-71e6b28b
```

Filename inference should be a first-class pipeline phase.

It should produce:

- display title
- filename slug
- meeting type
- primary topic
- one-on-one counterpart, when applicable
- confidence
- fallback reason, when applicable

Target filename shape:

```text
YYYY-MM-DD-<counterpart-or-meeting>-<topic>.md
```

Examples:

```text
2026-06-12-kushali-adbook-fact-revenue-detail.md
2026-07-01-spelman-data-infrastructure-rfp-prep.md
2026-06-10-jim-haley-historical-revenue-dedup.md
```

Fallback names like `generic-<hash>` should be rare. If fallback naming is used, the run summary should include a rename suggestion if one can be inferred later.

Renaming after ingest is allowed through a controlled repair step that updates ledger references.

Rename repair must not change immutable IDs used by signals, ledger records, cross-references, or derived playbook entries.

## Project Directory Layout

Proposed project-local structure:

```text
_local/project-context/meetings/
  _inbox/
    _done/
  _processed/
  _quarantine/
  _signals/
  _derived/
  _cache/
  _ledger.jsonl
```

Generated meeting markdown may remain directly under `meetings/` for human convenience, but raw source files should not remain there after successful ingest.

Decision: generated markdown lives in the meeting root by default. This preserves easy scanning and sharing with agents. Directory hygiene should come from keeping raw inputs, processed copies, signals, cache files, quarantine records, and derived aggregate outputs in their own underscore-prefixed directories.

`_derived/` can hold rolling stakeholder playbooks and future aggregate outputs.

`_cache/` can hold normalized transcript text keyed by source hash if caching is enabled.

## Ledger Model

The ledger should be content-hash based and richer than the current implementation.

Proposed fields:

- source hash
- original source path
- processed archive path
- meeting ID
- ingest run ID
- mode-specific generated artifact paths
- per-artifact status
- signal paths
- derived artifact update status
- timestamps
- provider/model metadata per generated artifact
- schema version per generated artifact
- transcript cleanup policy
- title metadata
- reconcile status
- error/quarantine details, when applicable
- supersedes or related-source links, when duplicate or regenerated artifacts are identified

Open design choice:

- one ledger record per source hash with an artifacts map by mode
- or one ledger record per source hash plus output mode

Decision:

- one source-level record with mode-specific artifact entries, because the same source may later produce multiple output variants.

Plain-language explanation:

- source-level ledger means "this transcript source is known once, and here are the artifacts produced from it"
- source-plus-mode ledger means "summary and summary-plus-verbatim are treated like separate ingest records even if they came from the same source"

Source-level ledger is easier for user-facing idempotency: if the same transcript is dropped into the inbox again, the tool can say it already knows that source and list which artifact modes exist or are missing.

The append-only ledger should define a current-state rule, such as "last valid record wins per source hash." This allows state repair, regeneration, and derived-work status updates without rewriting history.

The ledger should support regeneration from the processed archive copy, because a source may be reconciled out of `_inbox` before a later artifact mode or renderer repair is requested.

## Provider Contract

Provider-backed extraction should return structured data.

Candidate response shape:

- title proposal
- participants
- meeting type
- topics
- decisions
- action items
- commitments
- dependencies
- risks
- stakeholder asks
- communication signals
- open questions
- summary narrative
- confidence notes

The engine should validate provider output before rendering or reconciling source files.

## Model Right-Sizing

Proposed quality modes:

- `fast`
- `balanced`
- `deep`

Default:

- `balanced`

Suggested behavior:

- deterministic phases use no model
- cleaned verbatim should use no model unless transcript repair needs it
- title inference may use lightweight extraction or the same structured extraction pass
- summary/signals use the configured balanced provider by default
- deep mode is reserved for long, high-value, or ambiguous meetings

## Agentic Harness Operation

The CLI/library is canonical, but normal use should work inside Supa Code and T3 Code through the active agent.

Practical requirement:

- the user can ask the agent to ingest a meeting without leaving the harness

Design implication:

- provide generic agent instructions
- optionally provide harness-specific wrapper instructions later
- wrappers should call the same engine
- wrappers should not manually implement ledger/archive/reconcile behavior
- wrappers may delegate to a focused sub-agent
- CLI output should include a machine-readable run summary with a stable JSON shape
- exit codes should distinguish success, partial success, duplicate/no-op, validation failure, provider failure, and filesystem/reconcile failure

## Rolling Stakeholder Playbook

Per-meeting communication signals should feed a rolling stakeholder playbook.

The playbook should accumulate:

- stakeholder priorities
- explicit asks
- recurring concerns
- communication style cues
- preferred level of detail
- useful framing
- commitments made by or to the stakeholder
- source-grounded evidence

Implementation should preserve provenance and distinguish explicit statements from inferred patterns.

Suggested approach:

1. generate structured per-meeting signals
2. report primary meeting artifacts as ready
3. update per-stakeholder derived profiles as post-output work
4. render a human-readable and agent-readable playbook under `_derived/`
5. keep enough source references to audit or regenerate

This remains inside the artifact-producer boundary. It should not become a full messaging assistant in this repo.

## Proposed Communication Signal Schema

Per-meeting signal records should be structured enough for a rolling playbook while still carrying readable text.

Suggested fields:

```json
{
  "schema_version": "1.0",
  "signal_id": "sig-20260612-001",
  "meeting_id": "mtg-20260612-71e6b28b",
  "ingest_run_id": "ingest-20260612-71e6b28b",
  "effective_at": "2026-06-12",
  "recorded_at": "2026-06-12T13:36:54Z",
  "signal_type": "explicit_ask",
  "stakeholder_id": "kushali-g",
  "stakeholder_name": "Kushali G",
  "summary": "Kushali wants the proper Decentrix source for AE and advertiser identity resolution rather than relying on history-derived fallbacks.",
  "evidence": {
    "kind": "paraphrase",
    "text": "Kushali pushed back that there should be a proper source for the mapping and planned to ask Decentrix.",
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

Why these fields:

- `signal_type` makes the record sortable and usable by agents
- `stakeholder_id` supports rolling profiles across meetings
- `summary` gives humans and agents a compact usable statement
- `evidence` keeps the signal grounded in the meeting
- `inference_level` separates what was said from what was inferred
- `confidence` prevents weak signals from being overused
- `topics` and `project_refs` help retrieval
- `recurrence` lets the playbook distinguish one-off comments from stable patterns
- `status` allows later superseded or stale signals without deleting history

V1 `signal_type` values:

- `explicit_ask`
- `stakeholder_priority`
- `decision_rationale`
- `commitment`
- `risk_or_concern`

Later candidate values:

- `dependency`
- `communication_style`
- `preferred_detail_level`
- `urgency_signal`
- `follow_up_expectation`
- `contradiction_or_tension`

Avoid `relationship_context` in v1 because it is more profiling-adjacent and harder to evidence cleanly.

Communication guidance should be generated during playbook derivation, not directly in per-meeting signal extraction. Per-meeting records should stay close to observed or well-grounded facts.

Candidate `inference_level` values:

- `explicit`
- `strong_inference`
- `weak_inference`

Candidate `confidence` values:

- `high`
- `medium`
- `low`

## Agent-Consumable Markdown Requirements

The generated markdown will often be handed to another agent for follow-on work. It should therefore be optimized for machine reading without becoming hostile to humans.

Requirements:

- stable front matter
- stable section headings
- explicit meeting ID and source metadata
- immutable IDs separate from mutable titles/slugs
- clear owner/action tables
- consistent person names and IDs where known
- short summaries before detailed discussion
- transcript section clearly delimited
- transcript is always the final section, with nothing after it
- no hidden meaning that only exists in prose
- important decisions and asks repeated in structured sections, even if also discussed narratively
- empty sections are emitted explicitly so agents can distinguish "none" from "missing"
- stable anchors for decisions and actions, such as `D1`, `A1`, and `ASK1`

Recommended front matter:

```yaml
schema_version: 1.0
meeting_id: mtg-20260612-71e6b28b
title: Kushali x Ken - AdBook fact_revenue detail design
slug: kushali-adbook-fact-revenue-detail
date: 2026-06-12
output_mode: summary-plus-verbatim
source_file: Call with G, Kushali (5).docx
source_sha256: 2d17...
ingest_run_id: ingest-20260612-71e6b28b
transcript_policy: cleaned-verbatim
provider: anthropic
model_alias: balanced
model_id: claude-sonnet-...
generated_by: meeting-ingest 0.1.0
```

## Future Communication Artifact Ingest

Stakeholder voice and commitments often appear outside meetings.

Potential future source types:

- email bodies
- email screenshots
- memos
- Teams messages or threads
- attachments containing stakeholder requests, decisions, or commitments

These artifacts do not need a transcript in the same way a meeting does. An email body is already a verbatim communication record. However, the same signal extraction model can identify:

- explicit asks
- commitments
- decisions
- stakeholder priorities
- communication style cues
- useful phrasing
- recurring concerns

Current stance:

- keep the first implementation meeting/transcript-first
- do not broaden the first build into a generic document ingestion platform
- design source metadata, signal records, and rolling stakeholder playbook updates so non-meeting communication artifacts can be added later without reworking the core model

Possible future mode:

```text
meeting-ingest ingest-communication path/to/email.md --source-type email
```

This may eventually justify either:

- expanding `meeting-ingest` into a broader communication-artifact ingest tool
- or extracting a sibling tool that shares the signal/playbook schema

That decision should wait until the meeting ingest engine is working and trusted.

## Initial Implementation Slice

Recommended first build slice:

1. package and CLI scaffold with JSON run summary and exit-code contract
2. project init, directory layout, and versioned config schema
3. content hashing and source-level ledger with per-artifact status
4. deterministic `.txt`, `.vtt`, and `.docx` extraction plus cleanup ruleset
5. deterministic markdown renderer from fixtures for `summary-plus-verbatim`
6. provider contract, mock provider, and one real adapter returning title proposal, summary sections, and minimal v1 signals
7. filename/title inference from provider output, with fallback and rename-suggestion rules
8. processed archive, reconcile behavior, and regenerate-from-processed path
9. basic `doctor` command for inbox residue, orphan artifacts, ledger/artifact mismatches, and stale derived work

After that:

1. rolling stakeholder playbook aggregation
2. summary and verbatim-only modes
3. rename-repair command
4. additional provider adapters
5. agent harness instructions
6. split-file derivatives
7. mode auto-selection
