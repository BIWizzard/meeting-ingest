from ingest_meeting import SCHEMA_VERSION

KINDS = {"stable-preference", "time-bound", "project-specific", "contradiction",
         "voice-correction", "audience-fit", "model-miss"}
EVENTS = {"observation", "supersession", "reclassification"}
ORIGINS = {"meeting", "cc", "sample", "draft", "bootstrap"}
TIERS = {"self", "colleague", "client"}
_ENVELOPE = ["event_id", "event", "schema_version", "effective_at",
             "recorded_at", "origin", "provenance", "ingest_run_id"]


def _err(msg: str, errs: list[str]) -> None:
    errs.append(msg)


def validate_event(ev: dict) -> list[str]:
    errs: list[str] = []
    for f in _ENVELOPE:
        if f not in ev:
            _err(f"missing envelope field: {f}", errs)
    if errs:
        return errs
    if ev["schema_version"] != SCHEMA_VERSION:
        _err(f"unknown schema_version: {ev['schema_version']}", errs)
    if ev["event"] not in EVENTS:
        _err(f"bad event type: {ev['event']}", errs)
    if ev["origin"] not in ORIGINS:
        _err(f"bad origin: {ev['origin']}", errs)
    if not isinstance(ev.get("provenance"), dict):
        _err("provenance must be an object", errs)
    p = ev.get("payload")
    if not isinstance(p, dict):
        _err("missing payload", errs)
        return errs
    et = ev["event"]
    if et == "observation":
        for f in ("signal_id", "person_id", "kind", "text"):
            if f not in p:
                _err(f"observation payload missing {f}", errs)
        if "kind" in p and p["kind"] not in KINDS:
            _err(f"bad kind: {p['kind']}", errs)
    elif et == "supersession":
        if not isinstance(p.get("supersedes"), list) or not p.get("by"):
            _err("supersession payload requires supersedes[] and by", errs)
    elif et == "reclassification":
        for f in ("person_id", "from_tier", "to_tier"):
            if f not in p:
                _err(f"reclassification payload missing {f}", errs)
        if "to_tier" in p and p["to_tier"] not in TIERS:
            _err(f"bad to_tier: {p['to_tier']}", errs)
    return errs
