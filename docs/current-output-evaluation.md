# Current Claude Skill Output Evaluation

## Scope Reviewed

Primary corpus reviewed:

- `/Users/kmgdev/dev_projects/hearst-client/HTV-IQ-DataAnalytics/_local/project-context/meetings`

Secondary sanity-check corpus:

- `/Users/kmgdev/dev_projects/spelman/_local/project-context/meetings`

The Hearst corpus is the better reference set because it contains sustained real use:

- 153 top-level markdown files
- 42 top-level verbatim markdown files
- 82 files in `_signals/`
- 81 ledger entries
- 81 processed source copies
- 80 files under `_inbox/_done`

## What Is Working Well

### 1. The summaries are useful work products

The better outputs are not generic meeting notes. They preserve:

- decisions
- action items
- owner commitments
- technical constraints
- stakeholder asks
- project-specific context
- communication signals
- cross-references into broader project memory

The strongest examples read like project operating artifacts, not passive summaries.

Good patterns to preserve:

- `TL;DR` at the top
- `Participants & Roles`
- `Key Discussion`
- `Decisions & Direction Changes`
- `Action Items / Asks`
- `North Star Signals`
- `Communication Signals`
- `Cross-References`

### 2. The output understands stakeholder value

Several files already capture the kind of communication intelligence the rebuild should preserve.

The standup summaries are especially strong at identifying:

- client voice vs internal leadership vs peer collaborators
- what a stakeholder cares about
- how they frame accountability
- how to communicate back to them
- which asks should be pinned to dates, sprints, deliverables, or review points

The `stakeholder-comms-playbook.md` file is strong evidence that this workflow is valuable and should become more first-class.

### 3. The source-ledger/archive model is directionally right

The current system already has:

- `_processed/`
- `_inbox/_done/`
- `_signals/`
- `_ledger.jsonl`
- source hashes
- deterministic-looking meeting IDs

This confirms the rebuild should preserve the strong done-process model rather than becoming a simple summarizer.

### 4. Separate signal output is valuable

The `_signals/*.jsonl` files contain useful durable observations. They make the meeting output machine-consumable and give a path toward stakeholder memory, project memory, and later retrieval.

The signal categories are already meaningful, including:

- project-specific observations
- stable preferences
- contradictions
- time-bound items
- asks
- actions

### 5. The Spelman output shows recent quality improvements

The Spelman summary is well structured and preserves stakeholder/business context effectively. Its verbatim file also includes front matter and a clear note about transcript cleaning.

This is a good candidate reference for the newer artifact style.

## What Is Less Than Ideal

### 1. File naming is the biggest product pain

The user specifically wants file names that identify:

- date
- meeting or conversation identity
- primary topic
- one-on-one counterpart when applicable

The corpus confirms why this matters.

There are 43 Hearst markdown files with `generic` in the name. Many of these files have strong semantic titles inside the document, but the filename stays low-signal.

Example pattern to avoid:

```text
2026-06-29-generic-f0792f97.md
```

The document title may clearly say the meeting was a Kushali AdBook validation explainer, but the filename does not.

Better target pattern:

```text
2026-06-29-kushali-adbook-dimension-validation-explainer.md
```

The rebuild should treat `generic-<hash>` as a fallback only. If it must fall back, it should emit a rename suggestion.

### 2. Verbatim output shape is inconsistent

The current corpus has multiple styles:

- separate summary file plus separate `-verbatim.md`
- one combined summary plus verbatim file
- at least one `.verbatim.md` suffix instead of `-verbatim.md`
- some verbatim files with front matter
- some verbatim files without front matter

The user preference is one file for `summary-plus-verbatim`:

1. templated smart summary
2. verbatim transcript

The combined file pattern already exists and should be formalized as an explicit output mode.

### 3. Headings are useful but not stable enough

Common summary sections are mostly consistent, but not fully stable.

Observed variations include:

- `Communication Signals`
- `Communication Signals (by person)`
- `Communication Signals by Person`
- `Participants & Roles`
- `Attendees`
- `Meeting recap`
- standup-specific formats
- one-off prep or draft artifacts mixed into the same directory

Some variation is appropriate by meeting type, but the rebuild should have stable templates by mode and meeting type so tools can parse the output reliably.

### 4. Metadata is inconsistent

Older standup files often have useful YAML front matter. Many later generated meeting summaries use bold markdown metadata instead. Verbatim files vary between front matter and inline metadata.

The rebuild should standardize metadata across generated artifacts.

Recommended baseline fields:

- meeting_id
- title
- date
- source file
- source hash
- ingest_run_id
- output mode
- provider/model, if applicable
- transcript cleanup policy

### 5. Signals are useful but under-structured

The JSONL records are valid and useful, but most signal meaning is embedded in `payload.text`.

Current shape is roughly:

- event
- event_id
- ingest_run_id
- origin
- payload.kind
- payload.person_id
- payload.signal_id
- payload.text
- provenance
- timestamps

Useful next-step fields:

- signal_type
- explicit_vs_inferred
- confidence
- quote_or_evidence
- stakeholder_equity
- action_owner
- due_date, when present
- recurrence marker
- source span or timestamp, when available

The text blob is good for humans but too coarse for reliable downstream communication assistance.

### 6. Ledger records are too thin

The current ledger confirms source-hash idempotency, but entries only include:

- source_sha256
- meeting_id
- ingest_run_id

For the rebuild, the ledger should also track:

- source path
- archived processed path
- generated artifact paths
- output mode
- status
- provider/model metadata
- timestamps
- error/quarantine state
- whether source reconciliation completed

This matters especially if one source can generate multiple output variants.

### 7. Directory hygiene needs tightening

The meeting root currently contains mixed artifact types:

- generated meeting summaries
- generated verbatim transcripts
- raw `.docx` files
- PDFs
- HTML files
- PNG/SVG/Mermaid flow artifacts
- a stakeholder playbook
- `.DS_Store`
- an empty `_signals/test.json`

The structure is useful but needs clearer boundaries.

Potential direction:

- generated meeting artifacts in one canonical location
- raw inbox files only under `_inbox/`
- canonical processed copies only under `_processed/`
- machine signals only under `_signals/`
- derived diagrams or non-meeting artifacts outside the meeting output root or under a typed `_attachments/` area
- playbooks under a deliberate `_derived/` or project-context area

### 8. Reconciliation appears directionally right but not perfectly clean

The Hearst corpus has 81 processed copies, 81 ledger entries, and 80 `_inbox/_done` files. There are also files still directly under `_inbox` and raw source files in the top-level meeting root.

This suggests the current done process is close but can leave residue. The rebuild should make the run summary and `doctor` command surface these states clearly.

## Things To Mimic

- Summary-first writing style.
- Short, useful TL;DR.
- Strong decision/action extraction.
- Explicit stakeholder/client voice sections when relevant.
- Communication signals by person.
- Cross-reference section.
- Roster/person normalization into stable person IDs.
- Source-hash idempotency.
- Processed source archive.
- JSONL signal output.
- Stakeholder playbook concept, but generated from better-structured signals.

## Things To Change

- Make filename/title inference a first-class pipeline step.
- Avoid `generic-<hash>` unless there is no confident title.
- Make output mode explicit.
- Make `summary-plus-verbatim` one canonical combined file by default.
- Standardize metadata and headings.
- Keep verbatim cleanup policy explicit.
- Strengthen the ledger schema.
- Separate generated artifacts from raw source files and derived/non-meeting assets.
- Add a `doctor` or `status` check for residual inbox files, missing signal files, empty files, and mismatched ledger/artifact counts.
- Make communication signals more structured without losing readable prose.

## Design Implications For The Rebuild

1. Add a `title_inference` phase that produces:
   - display title
   - filename slug
   - meeting type
   - primary topic
   - one-on-one counterpart, when applicable
   - confidence

2. Add stable output modes:
   - `summary`
   - `summary-plus-verbatim`
   - `verbatim`

3. Treat artifact rendering as deterministic:
   - provider returns structured content
   - renderer owns final markdown shape

4. Track output mode and artifact paths in the ledger.

5. Store communication signals as structured records with a human-readable text field, not only a text blob.

6. Keep stakeholder communication intelligence inside the ingestion/product-artifact boundary. Do not turn this repo into a full messaging assistant.

