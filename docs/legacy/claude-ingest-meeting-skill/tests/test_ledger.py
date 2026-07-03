from ingest_meeting import ledger, paths


def test_record_then_already_ingested(tmp_path):
    paths.project_paths(tmp_path)
    assert ledger.already_ingested(tmp_path, "sha-abc") is None
    ledger.record(tmp_path, "sha-abc", "2026-05-15-standup-abcd1234", "run1")
    assert ledger.already_ingested(tmp_path, "sha-abc") == "2026-05-15-standup-abcd1234"


def test_idempotent_record_does_not_duplicate(tmp_path):
    paths.project_paths(tmp_path)
    ledger.record(tmp_path, "sha-x", "m1", "run1")
    ledger.record(tmp_path, "sha-x", "m1", "run2")  # re-run, different run id
    lines = paths.project_paths(tmp_path)["ledger"].read_text().strip().splitlines()
    assert len(lines) == 1  # keyed by sha, not run id
