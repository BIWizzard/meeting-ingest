import json
from ingest_meeting import events, paths, schema

def _obs_payload():
    return {"signal_id": "s1", "person_id": "p1",
            "kind": "stable-preference", "text": "leads with the ask"}

def test_make_event_has_envelope_and_id():
    ev = events.make_event("observation", "2026-05-15",
        "2026-05-15T00:00:00Z", "meeting", {"project": "h", "source": "f"},
        "run1", _obs_payload())
    assert ev["event_id"] and ev["schema_version"] == schema.SCHEMA_VERSION
    assert schema.validate_event(ev) == []

def test_append_valid_event_per_meeting_file(tmp_path):
    ev = events.make_event("observation", "2026-05-15",
        "2026-05-15T00:00:00Z", "meeting", {"project": "h", "source": "f"},
        "run1", _obs_payload())
    log = events.append_events("2026-05-15-standup-abcd1234", [ev], tmp_path)
    assert log.name == "2026-05-15-standup-abcd1234.jsonl"
    assert log.parent.name == "_signals"
    lines = log.read_text().strip().splitlines()
    assert len(lines) == 1 and json.loads(lines[0])["event_id"] == ev["event_id"]

def test_invalid_event_is_quarantined_not_appended(tmp_path):
    bad = events.make_event("observation", "2026-05-15",
        "2026-05-15T00:00:00Z", "meeting", {"project": "h", "source": "f"},
        "run1", {"signal_id": "s1"})  # missing person_id/kind/text
    log = events.append_events("2026-05-15-standup-abcd1234", [bad], tmp_path)
    assert not log.exists()
    q = list((paths.project_paths(tmp_path)["quarantine"]).glob("*.json"))
    assert len(q) == 1
