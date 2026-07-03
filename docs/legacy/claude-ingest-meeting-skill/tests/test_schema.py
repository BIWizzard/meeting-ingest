from ingest_meeting import schema

ENV = dict(event_id="a"*16, event="observation", schema_version=schema.SCHEMA_VERSION,
           effective_at="2026-05-15", recorded_at="2026-05-15T00:00:00Z",
           origin="meeting", provenance={"project": "hearst", "source": "f.docx"},
           ingest_run_id="run1")

def test_valid_observation():
    ev = {**ENV, "payload": {"signal_id": "s1", "person_id": "p1",
          "kind": "stable-preference", "text": "x"}}
    assert schema.validate_event(ev) == []

def test_missing_envelope_field_fails():
    ev = {**ENV, "payload": {"signal_id": "s1", "person_id": "p1",
          "kind": "stable-preference", "text": "x"}}
    del ev["effective_at"]
    assert any("effective_at" in e for e in schema.validate_event(ev))

def test_bad_kind_fails():
    ev = {**ENV, "payload": {"signal_id": "s1", "person_id": "p1",
          "kind": "not-a-kind", "text": "x"}}
    assert any("kind" in e for e in schema.validate_event(ev))

def test_supersession_payload():
    ev = {**ENV, "event": "supersession",
          "payload": {"supersedes": ["s1"], "by": "s2", "reason": "r"}}
    assert schema.validate_event(ev) == []

def test_reclassification_payload():
    ev = {**ENV, "event": "reclassification",
          "payload": {"person_id": "p1", "from_tier": "client",
                      "to_tier": "colleague", "reason": "r"}}
    assert schema.validate_event(ev) == []

def test_unknown_schema_version_flagged():
    ev = {**ENV, "schema_version": "9.9",
          "payload": {"signal_id": "s1", "person_id": "p1",
                      "kind": "stable-preference", "text": "x"}}
    assert any("schema_version" in e for e in schema.validate_event(ev))
