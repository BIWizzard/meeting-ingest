"""
Single-transcript orchestration.

Wires the deterministic ingest steps together for one transcript:
identity → ledger dedup → text extraction → header/type detection →
LLM extraction (injected) → participant resolution → per-meeting events
+ markdown write → ledger record → processed copy.

The LLM step is injected as ``llm_extract`` so it can be stubbed in tests;
SKILL.md supplies the real implementation at runtime. The pipeline is
idempotent (keyed by source content SHA256, not filename) and supports a
dry-run mode that previews without writing anything. Unresolved participants
are collected on the result, never written to a global file (spec §5.6/§5.7/
§7/§9).
"""

from pathlib import Path
from typing import Any, Callable

from ingest_meeting import (extract, identity, events, ledger, roster,
                            paths, quarantine)

# (clean_text, meeting_type) -> {"markdown": str, "observations": [ ... ]}
LlmExtract = Callable[[str, str], dict]


def ingest_transcript(path: Path | str, project_root: Path | str,
                      llm_extract: LlmExtract, *,
                      dry_run: bool = False, ingest_run_id: str,
                      home: Path | str | None = None) -> dict[str, Any]:
    """
    Ingest a single transcript end to end.

    Args:
        path: Transcript file (.txt/.vtt/.docx).
        project_root: Project root passed to paths.project_paths.
        llm_extract: Injected LLM step. Receives (clean_text, meeting_type),
            returns {"markdown": str, "observations": [...]}.
        dry_run: When True, resolve and count events but write nothing
            (no markdown, no events, no ledger, no processed copy).
        ingest_run_id: Opaque run identifier for provenance/traceability.
        home: Override for the global ~/.claude home (roster lookup).

    Returns:
        Result dict. Always carries source_sha256, dry_run, skipped. When a
        new transcript is ingested: meeting_id, meeting_type, meeting_date,
        unresolved[]. On a real write: markdown_path, signals_path. On dry
        run: preview_event_count. On dedup hit / quarantine: skipped True.
    """
    path = Path(path)
    sha = identity.source_sha256(path)

    existing = ledger.already_ingested(project_root, sha)
    if existing:
        return {"skipped": True, "meeting_id": existing,
                "source_sha256": sha, "dry_run": dry_run}

    try:
        text = extract.extract_text(path)
    except extract.UnsupportedFormat as e:
        if not dry_run:
            quarantine.park(project_root, "transcript", path.name, str(e),
                            {"path": str(path)})
        return {"skipped": True, "quarantined": True, "source_sha256": sha,
                "dry_run": dry_run}

    hdr = extract.parse_header(text)
    mtype = extract.detect_type(text, hdr.get("title", ""))
    mdate = hdr.get("meeting_date") or "0000-00-00"
    mid = identity.meeting_id(sha, mdate, mtype)

    llm = llm_extract(text, mtype)
    r = roster.Roster.load(project_root, home=home)
    recorded = identity.now_iso()
    evs: list[dict] = []
    unresolved: list[dict] = []
    for obs in llm.get("observations", []):
        raw = obs.get("speaker", "")
        if obs.get("person_id"):
            pid, status = obs.get("person_id"), "matched"
        else:
            pid, status = r.resolve(raw)
        if pid is None or status != "matched":
            unresolved.append({"raw": raw, "status": status})
            continue
        payload = {"signal_id": obs["signal_id"], "person_id": pid,
                   "kind": obs["kind"], "text": obs["text"]}
        if obs.get("meeting_id_ref"):
            payload["meeting_id"] = mid
        evs.append(events.make_event(
            "observation", mdate, recorded, "meeting",
            {"project": Path(project_root).name, "source": path.name},
            ingest_run_id, payload))

    result: dict[str, Any] = {
        "meeting_id": mid, "source_sha256": sha, "dry_run": dry_run,
        "skipped": False, "unresolved": unresolved,
        "meeting_type": mtype, "meeting_date": mdate}

    if dry_run:
        result["preview_event_count"] = len(evs)
        return result

    md_path = paths.project_paths(project_root)["base"] / \
        f"{mdate}-{mtype}-{mid.split('-')[-1]}.md"
    md_path.write_text(llm["markdown"], encoding="utf-8")
    log = events.append_events(mid, evs, project_root)
    ledger.record(project_root, sha, mid, ingest_run_id)
    proc = paths.project_paths(project_root)["processed"] / \
        f"{sha[:12]}-{ingest_run_id}-{path.name}"
    proc.write_bytes(path.read_bytes())
    result["markdown_path"] = str(md_path)
    result["signals_path"] = str(log)
    return result
