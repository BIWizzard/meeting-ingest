from ingest_meeting import identity


def test_source_sha256_is_content_not_name(tmp_path):
    a = tmp_path / "a.txt"
    a.write_text("hello world")
    b = tmp_path / "renamed.txt"
    b.write_text("hello world")
    c = tmp_path / "c.txt"
    c.write_text("different")
    assert identity.source_sha256(a) == identity.source_sha256(b)
    assert identity.source_sha256(a) != identity.source_sha256(c)
    assert len(identity.source_sha256(a)) == 64


def test_meeting_id_deterministic_and_slugged():
    mid = identity.meeting_id("a" * 64, "2026-05-15", "standup")
    assert mid == identity.meeting_id("a" * 64, "2026-05-15", "standup")
    assert mid.startswith("2026-05-15-standup-")
    assert len(mid.split("-")[-1]) == 8  # short hash suffix


def test_event_id_deterministic_and_excludes_itself():
    ev = {"event": "observation", "effective_at": "2026-05-15", "payload": {"x": 1}}
    e1 = identity.event_id(ev)
    e2 = identity.event_id({**ev, "event_id": "ignored"})
    assert e1 == e2 and len(e1) == 16


def test_now_iso_utc():
    s = identity.now_iso()
    assert s.endswith("Z") and "T" in s
