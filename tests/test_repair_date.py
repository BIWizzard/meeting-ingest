from pathlib import Path
import json
import os

import pytest

from meeting_ingest import pipeline
from meeting_ingest.errors import EXIT_ARTIFACT_WRITE, MeetingIngestError
from meeting_ingest.ledger import read_records


MEETINGS_RELATIVE = Path("_local/project-context/meetings")


def _ingest_mtime_dated_standup(tmp_path: Path) -> tuple[Path, str]:
    pipeline.initialize(tmp_path)
    meetings_root = tmp_path / MEETINGS_RELATIVE
    source = meetings_root / "_inbox" / "Daily Stand Up - Post-MVP (41).vtt"
    source.write_text(
        "WEBVTT\n\n"
        "7f3a2c9e-4b1d-4e8a-9c5f-1a2b3c4d5e6f/1-0\n"
        "00:00:03.120 --> 00:00:06.480\n"
        "<v Graham, Ken (Contractor)>Please capture this request. [mock-signal]</v>\n",
        encoding="utf-8",
    )
    os.utime(source, (1784160000, 1784160000))  # 2026-07-16, download date
    summary = pipeline.ingest(source, start=tmp_path, provider="mock")
    assert summary.status == "success"
    return meetings_root, summary.meeting_id


def test_repair_date_renames_artifact_rewrites_metadata_and_appends_ledger(tmp_path: Path) -> None:
    meetings_root, meeting_id = _ingest_mtime_dated_standup(tmp_path)

    summary = pipeline.repair_date(meeting_id, date="2026-07-10", start=tmp_path)

    assert summary.status == "success"
    assert summary.exit_code == 0
    assert summary.meeting_id == meeting_id  # meeting_id unchanged, still embeds 20260716

    records = read_records(meetings_root / "_ledger.jsonl")
    repaired = [r for r in records if r["event"] == "date_repaired"]
    assert len(repaired) == 1
    record = repaired[0]
    assert record["meeting_id"] == meeting_id
    assert record["ingest_run_id"] is None
    assert record["repair"]["previous_date"] == "2026-07-16"
    assert record["repair"]["previous_date_source"] == "file_mtime"
    assert record["repair"]["date"] == "2026-07-10"

    (mode_entry,) = record["artifacts"].values()
    new_path = meetings_root / mode_entry["path"]
    assert mode_entry["path"].startswith("2026-07-10-")
    assert new_path.exists()
    content = new_path.read_text(encoding="utf-8")
    assert "date: 2026-07-10" in content
    assert "date_confidence: manual" in content
    assert "date_source: repair" in content
    assert f"meeting_id: {meeting_id}" in content  # unchanged

    old_paths = list(meetings_root.glob("2026-07-16-*.md"))
    assert old_paths == []

    signal_path = meetings_root / "_signals" / f"{meeting_id}.jsonl"
    assert signal_path.exists()
    signal_lines = [json.loads(line) for line in signal_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert signal_lines
    assert all(line["effective_at"] == "2026-07-10" for line in signal_lines)
    assert all(line["meeting_id"] == meeting_id for line in signal_lines)
    assert all(line["timing"]["occurred"]["precision"] == "date" for line in signal_lines)
    assert all(line["timing"]["occurred"]["source"] == "repair" for line in signal_lines)
    assert all(line["source"]["artifact_path"] == mode_entry["path"] for line in signal_lines)
    assert record["signals"]["fingerprint"].startswith("sha256:")


def test_repair_date_accepts_source_sha_selector(tmp_path: Path) -> None:
    meetings_root, meeting_id = _ingest_mtime_dated_standup(tmp_path)
    records = read_records(meetings_root / "_ledger.jsonl")
    source_sha = records[-1]["source_sha256"]

    summary = pipeline.repair_date(source_sha, date="2026-07-10", start=tmp_path)

    assert summary.status == "success"
    assert summary.meeting_id == meeting_id


def test_repair_date_is_a_no_op_when_date_already_matches(tmp_path: Path) -> None:
    meetings_root, meeting_id = _ingest_mtime_dated_standup(tmp_path)
    pipeline.repair_date(meeting_id, date="2026-07-10", start=tmp_path)
    before = (meetings_root / "_ledger.jsonl").read_text(encoding="utf-8")

    summary = pipeline.repair_date(meeting_id, date="2026-07-10", start=tmp_path)

    assert summary.status == "no_op"
    assert summary.exit_code == 0
    assert (meetings_root / "_ledger.jsonl").read_text(encoding="utf-8") == before


def test_repair_date_fails_for_unknown_selector(tmp_path: Path) -> None:
    _ingest_mtime_dated_standup(tmp_path)

    with pytest.raises(MeetingIngestError) as excinfo:
        pipeline.repair_date("mtg-20990101-deadbeef", date="2026-07-10", start=tmp_path)

    assert excinfo.value.code == "repair_target_not_found"


def test_repair_date_fails_without_ledger_append_when_artifact_missing(tmp_path: Path) -> None:
    meetings_root, meeting_id = _ingest_mtime_dated_standup(tmp_path)
    for artifact in meetings_root.glob("2026-07-16-*.md"):
        artifact.unlink()
    before = (meetings_root / "_ledger.jsonl").read_text(encoding="utf-8")

    with pytest.raises(MeetingIngestError) as excinfo:
        pipeline.repair_date(meeting_id, date="2026-07-10", start=tmp_path)

    assert excinfo.value.code == "repair_artifact_missing"
    assert (meetings_root / "_ledger.jsonl").read_text(encoding="utf-8") == before


def test_repair_date_fails_without_ledger_append_or_file_mutation_when_signal_missing(tmp_path: Path) -> None:
    meetings_root, meeting_id = _ingest_mtime_dated_standup(tmp_path)
    signal_path = meetings_root / "_signals" / f"{meeting_id}.jsonl"
    signal_path.unlink()
    ledger_before = (meetings_root / "_ledger.jsonl").read_text(encoding="utf-8")
    artifact_paths = list(meetings_root.glob("2026-07-16-*.md"))
    artifact_contents = {path: path.read_text(encoding="utf-8") for path in artifact_paths}

    with pytest.raises(MeetingIngestError) as excinfo:
        pipeline.repair_date(meeting_id, date="2026-07-10", start=tmp_path)

    assert excinfo.value.code == "repair_artifact_missing"
    assert excinfo.value.phase == "repair"
    assert excinfo.value.exit_code == EXIT_ARTIFACT_WRITE
    assert excinfo.value.details == {"path": f"_signals/{meeting_id}.jsonl"}
    assert (meetings_root / "_ledger.jsonl").read_text(encoding="utf-8") == ledger_before
    assert list(meetings_root.glob("2026-07-10-*.md")) == []
    assert all(path.exists() and path.read_text(encoding="utf-8") == content for path, content in artifact_contents.items())


def test_reingest_after_repair_is_still_a_no_op(tmp_path: Path) -> None:
    meetings_root, meeting_id = _ingest_mtime_dated_standup(tmp_path)
    pipeline.repair_date(meeting_id, date="2026-07-10", start=tmp_path)
    processed = next((meetings_root / "_processed").iterdir())

    summary = pipeline.ingest(processed, start=tmp_path, provider="mock")

    assert summary.status == "no_op"


def test_repair_date_normalizes_unknown_occurrence_to_known_date(tmp_path: Path) -> None:
    meetings_root, meeting_id = _ingest_mtime_dated_standup(tmp_path)
    signal_path = meetings_root / "_signals" / f"{meeting_id}.jsonl"
    payload = json.loads(signal_path.read_text(encoding="utf-8"))
    payload["timing"]["occurred"].update(
        {"value": None, "precision": "unknown", "source": "unavailable", "confidence": "low"}
    )
    signal_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    pipeline.repair_date(meeting_id, date="2026-07-10", start=tmp_path)

    repaired = json.loads(signal_path.read_text(encoding="utf-8"))
    assert repaired["timing"]["occurred"] == {
        "value": "2026-07-10",
        "end_value": None,
        "precision": "date",
        "timezone": None,
        "source": "repair",
        "confidence": "manual",
    }
