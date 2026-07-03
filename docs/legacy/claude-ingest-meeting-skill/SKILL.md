---
name: ingest-meeting
description: Ingest meeting transcripts (.docx/.vtt/.txt) from the project _inbox into structured markdown + a per-meeting append-only Layer-1 event log. Use when the user says "ingest the standup", "process these transcripts", or drops files in meetings/_inbox.
---

# ingest-meeting

Turns raw transcripts into structured per-meeting markdown + immutable Layer-1
events. Deterministic mechanics live in the `ingest_meeting` Python package;
this skill performs the one non-deterministic step — reading a transcript and
producing the narrative markdown + typed observations — under a strict contract.

## Model & context strategy (read first)

The LLM extraction step runs in a **Sonnet subagent** (`model: "sonnet"`),
dispatched per transcript. The parent session only orchestrates: lists the
inbox, dispatches subagents, collects short result dicts, and presents the
end-of-batch roster classification. This keeps parent context light and
dodges Opus endpoint overload, which is the most common cause of repeated
"retrying..." on this skill.

- **Sonnet is the default** for per-transcript extraction. The work has real
  judgment in it (observation `kind` classification, audience-fit detection,
  no-fabrication discipline on names) so Haiku is not the default. Haiku is
  an opt-in option for explicit large backfills where cost dominates.
- **Parent never reads transcript text or generated markdown into context.**
  The subagent reads/produces those; only short result dicts come back
  (meeting_id, paths, unresolved[]).
- **Never read generated artifacts back into context** (the large `.docx`,
  the `.md` you just wrote, rendered SVG/PNG). The library validates writes.
- **Never run two ingests racing the same inbox.**

## Workflow

1. Run `python -m ingest_meeting.cli ingest --project-root <root> --home ~ --dry-run`
   to list inbox files, detected dates/types, and unresolved people. Review.
   (The CLI is directly runnable — no `/tmp` wrapper needed.)
2. For each non-skipped transcript, dispatch a **Sonnet subagent** to do
   both the LLM extraction and the pipeline write. The parent never reads
   the transcript text or the generated markdown.
   ```
   Agent({
     subagent_type: "general-purpose",
     model: "sonnet",
     name: "ingest-<meeting_id_short>",
     prompt: <see Subagent contract below>,
     run_in_background: false   // see step 5 for parallel backfills
   })
   ```
   The subagent: calls `extract.extract_text(path)` for cleaned text, produces
   `{markdown, observations}` per the **LLM Extraction Contract**, then calls
   `pipeline.ingest_transcript(path, root, llm_extract, ingest_run_id=run,
   home=~)` with the extraction injected as `llm_extract`. It returns ONLY
   the result dict (`meeting_id`, `markdown_path`, `signals_path`,
   `unresolved[]`, `meeting_type`, `meeting_date`) — never the full markdown
   or observation text.
3. After the batch, present **all** collected unresolved/`tentative`/`conflicted`
   people in one **end-of-batch classification** prompt: for each, ask
   colleague (global) / client (project-local) / skip. Persist via
   `roster.Roster.classify(...)` + `.save()`.
4. After ingest, reconcile the inbox so processed originals don't accumulate:
   `python -m ingest_meeting.cli reconcile-inbox --project-root <root>` (dry-run)
   then `--apply`. It SHA-checks each `_inbox/` file against the ledger and
   **moves** (never deletes) confirmed-ingested originals into `_inbox/_done/`;
   un-ingested files are left in place and reported `[PENDING]`. The canonical
   copy already lives in `_processed/`, so nothing is lost.
5. **Large backfills (>5 transcripts in one batch):** same per-transcript
   subagent pattern, dispatched in parallel — one message containing multiple
   `Agent({...})` calls with `run_in_background: true`. Sonnet stays the
   default; `model: "haiku"` is acceptable here if cost dominates and the
   user has explicitly opted in. Each subagent writes only its own per-meeting
   files (disjoint — safe). Never race two batches on the same inbox.

## Subagent contract

The parent dispatches one Sonnet subagent per transcript with a prompt that
includes:

- Absolute `path` to the transcript file in `_inbox/`.
- Absolute `project_root` (e.g. `/Users/<user>/dev_projects/<project>/sandbox`).
- The `ingest_run_id` (parent generates, e.g. `ingest-YYYYMMDD-<short>`).
- The `home` path (for global roster lookup; default `~`).
- A pointer to **this SKILL.md** so the subagent can read the full LLM
  Extraction Contract section verbatim — do not paraphrase the contract in
  the prompt; tell the subagent to `Read` SKILL.md and follow §"LLM
  Extraction Contract" exactly.
- An explicit instruction to return ONLY the pipeline result dict (no
  markdown body, no observation text in the response). The parent uses the
  returned `unresolved[]` to build the end-of-batch classification.

## LLM Extraction Contract

`llm_extract(clean_text, meeting_type) -> {"markdown": str, "observations": [...]}`

- `markdown`: the human-readable meeting doc. For `meeting_type == "standup"`
  use the **standup variant** section set exactly (spec §4): TL;DR; Ken —
  Updates & Commitments; Team Updates; Client Voice — Mark & Dilip; Internal
  Leadership — JF & Josh; Decisions & Direction Changes; Action Items / Asks;
  North Star Signals; Communication Signals (by person); Cross-References.
  Any other type uses the **generic base** (drop the Internal-Leadership split;
  add Participants & Roles + Key Discussion).
- `observations`: list of objects, each:
  `{signal_id, speaker, person_id?, kind, text, meeting_id_ref?}`
  - `kind` ∈ stable-preference | time-bound | project-specific | contradiction
    | voice-correction | audience-fit | model-miss
  - emit **typed facets** as observations too (decisions/action_items/asks/
    topics → `kind: project-specific`, text prefixed `DECISION:` etc.)
  - `speaker` is the raw transcript name; leave `person_id` null unless certain.
- NO FABRICATION: only what the transcript supports. Garbled names stay raw in
  `speaker`; the roster/end-of-batch prompt resolves them — never invent IDs.
- Deployment terminology: never "production/UAT"; everything is develop.

## Boundaries

- This skill writes ONLY: per-meeting `.md`, `_signals/<meeting_id>.jsonl`,
  `_ledger.jsonl`, `_processed/`, the global `~/.claude/people/roster.json`,
  and (via `reconcile-inbox`) moves processed originals into `_inbox/_done/`.
- `reconcile-inbox` never deletes a source — it only relocates ledger-confirmed
  originals; `_processed/` retains the immutable canonical copy.
- It never builds projections or drafts messages (P2/P3).
- Never auto-commit/push.
