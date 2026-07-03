import json
from ingest_meeting import quarantine, paths


def test_park_writes_blob_and_reason(tmp_path):
    paths.project_paths(tmp_path)
    p = quarantine.park(tmp_path, kind="event", name="bad1",
                         reason="unknown schema_version 9.9", blob={"x": 1})
    assert p.exists()
    rec = json.loads(p.read_text())
    assert rec["reason"] == "unknown schema_version 9.9"
    assert rec["kind"] == "event" and rec["blob"] == {"x": 1}
