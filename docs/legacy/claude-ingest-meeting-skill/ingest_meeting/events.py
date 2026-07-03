import json
from pathlib import Path

from ingest_meeting import SCHEMA_VERSION
from ingest_meeting import identity, paths, quarantine, schema


def make_event(
    event_type: str,
    effective_at: str,
    recorded_at: str,
    origin: str,
    provenance: dict,
    ingest_run_id: str,
    payload: dict,
) -> dict:
    """
    Build an enveloped event dict and stamp it with a deterministic event_id.

    The event_id is computed over the full envelope (excluding event_id itself)
    so it is stable across re-ingests of identical content.

    Args:
        event_type: One of schema.EVENTS ("observation", "supersession", "reclassification").
        effective_at: Date the signal was observed (YYYY-MM-DD).
        recorded_at: ISO 8601 UTC timestamp when the event was created.
        origin: Source context (one of schema.ORIGINS).
        provenance: Free-form dict describing the source artefact.
        ingest_run_id: Opaque run identifier for traceability.
        payload: Event-type-specific payload dict.

    Returns:
        Fully enveloped event dict with a populated event_id.
    """
    ev = {
        "event": event_type,
        "schema_version": SCHEMA_VERSION,
        "effective_at": effective_at,
        "recorded_at": recorded_at,
        "origin": origin,
        "provenance": provenance,
        "ingest_run_id": ingest_run_id,
        "payload": payload,
    }
    ev["event_id"] = identity.event_id(ev)
    return ev


def append_events(meeting_id: str, evs: list[dict], project_root: Path | str) -> Path:
    """
    Validate each event and append valid ones to the per-meeting JSONL log.

    One file per meeting under _signals/<meeting_id>.jsonl — disjoint by
    meeting_id, so concurrent writers on different meetings are parallel-safe.
    Invalid events are quarantined and never written to the log.

    Args:
        meeting_id: Meeting identifier (used as the JSONL filename stem).
        evs: List of event dicts to append.
        project_root: Project root passed to paths.project_paths.

    Returns:
        Path to the per-meeting JSONL file (may not exist if all events were invalid).
    """
    pp = paths.project_paths(project_root)
    log = pp["signals"] / f"{meeting_id}.jsonl"

    valid: list[dict] = []
    for ev in evs:
        errs = schema.validate_event(ev)
        if errs:
            quarantine.park(
                project_root,
                "event",
                ev.get("event_id", "noid"),
                "; ".join(errs),
                ev,
            )
        else:
            valid.append(ev)

    if valid:
        with open(log, "a", encoding="utf-8") as f:
            for ev in valid:
                f.write(json.dumps(ev, ensure_ascii=False, sort_keys=True) + "\n")

    return log
