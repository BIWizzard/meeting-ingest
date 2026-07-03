from datetime import UTC, datetime
import os
from pathlib import Path
import time

from meeting_ingest.clock import FrozenClock
from meeting_ingest.ledger import read_records
from meeting_ingest.paths import init_project
from meeting_ingest.pipeline import doctor, ingest, status


def test_status_reports_project_counts(tmp_path: Path) -> None:
    paths = init_project(tmp_path)

    summary = status(tmp_path)

    assert summary.status == "success"
    assert summary.exit_code == 0
    assert summary.details["project"] == {
        "meetings_root": str(paths.meetings_root),
        "ledger_records": 0,
        "known_sources": 0,
        "inbox_files": 0,
    }


def test_doctor_reports_clean_project_after_ingest(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")

    ingest(source, start=paths.inbox, clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)))
    summary = doctor(tmp_path)

    assert summary.status == "success"
    assert summary.exit_code == 0
    assert summary.details["issues"] == []
    assert summary.details["project"]["ledger_records"] == 2
    assert summary.details["project"]["known_sources"] == 1


def test_doctor_reports_inbox_residue(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "unprocessed.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")

    summary = doctor(tmp_path)

    assert summary.status == "issues_found"
    assert summary.exit_code == 1
    assert summary.details["issues"] == [
        {
            "code": "inbox_residue",
            "message": "Source file remains in inbox.",
            "path": "_inbox/unprocessed.txt",
        }
    ]


def test_doctor_reports_missing_ledger_artifact(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    result = ingest(source, start=paths.inbox, clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)))
    artifact = paths.meetings_root / result.artifacts[0]["path"]
    artifact.unlink()

    summary = doctor(tmp_path)
    records = read_records(paths.ledger)

    assert len(records) == 2
    assert summary.status == "issues_found"
    assert {
        "code": "missing_artifact",
        "message": "Ledger references a missing path.",
        "path": result.artifacts[0]["path"],
    } in summary.details["issues"]


def test_doctor_reports_missing_processed_copy(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    result = ingest(source, start=paths.inbox, clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)))
    processed = paths.meetings_root / result.details["archive"]["processed_path"]
    processed.unlink()

    summary = doctor(tmp_path)

    assert {
        "code": "missing_processed_source",
        "message": "Ledger references a missing path.",
        "path": result.details["archive"]["processed_path"],
    } in summary.details["issues"]


def test_doctor_reports_malformed_ledger_line(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    paths.ledger.write_text("{not-json\n", encoding="utf-8")

    summary = doctor(tmp_path)

    assert summary.status == "issues_found"
    assert summary.details["issues"] == [
        {
            "code": "malformed_ledger_json",
            "message": "Ledger line is not valid JSON: Expecting property name enclosed in double quotes",
            "path": "_ledger.jsonl:line:1",
        }
    ]


def test_doctor_reports_stale_provider_handoff_cache(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    request = paths.cache / "provider-requests" / "old.request.json"
    response = paths.cache / "provider-responses" / "old.response.json"
    request.parent.mkdir(parents=True)
    response.parent.mkdir(parents=True)
    request.write_text("{}", encoding="utf-8")
    response.write_text("{}", encoding="utf-8")
    old_time = time.time() - (8 * 24 * 60 * 60)
    os.utime(request, (old_time, old_time))
    os.utime(response, (old_time, old_time))

    summary = doctor(tmp_path)

    assert {
        "code": "stale_provider_request",
        "message": "Provider handoff cache file is stale.",
        "path": "_cache/provider-requests/old.request.json",
    } in summary.details["issues"]
    assert {
        "code": "stale_provider_response",
        "message": "Provider handoff cache file is stale.",
        "path": "_cache/provider-responses/old.response.json",
    } in summary.details["issues"]
