from pathlib import Path
import json
import os

import pytest

from meeting_ingest import pipeline
from meeting_ingest.errors import MeetingIngestError
from meeting_ingest.hashing import sha256_file
from meeting_ingest.ledger import read_records
from meeting_ingest.readiness import assess_readiness
from meeting_ingest.signals import read_signal_jsonl


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


def _rewrite_signals_as_legacy(meetings_root: Path, meeting_id: str, schema_version: str) -> Path:
    signal_path = meetings_root / "_signals" / f"{meeting_id}.jsonl"
    payloads = [
        json.loads(line)
        for line in signal_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    for payload in payloads:
        payload["schema_version"] = schema_version
        payload.pop("runtime_provenance_ref")
        if schema_version == "1.0":
            for key in (
                "source",
                "timing",
                "stakeholder_name_raw",
                "audience_id",
                "audience_name",
            ):
                payload.pop(key)
            payload["evidence"].pop("locator")
    signal_path.write_text(
        "".join(json.dumps(payload) + "\n" for payload in payloads),
        encoding="utf-8",
    )
    fingerprint = f"sha256:{sha256_file(signal_path)}"
    ledger_path = meetings_root / "_ledger.jsonl"
    ledger_records = [
        json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines()
    ]
    for record in ledger_records:
        manifest = record["signals"]
        manifest["schema_version"] = schema_version
        manifest["fingerprint"] = fingerprint
        manifest.pop("producer_ledger_record_id", None)
        manifest.pop("producer_runtime_provenance_sha256", None)
        manifest.pop("produced_in_this_record", None)
    ledger_path.write_text(
        "".join(json.dumps(record) + "\n" for record in ledger_records),
        encoding="utf-8",
    )
    return signal_path


def test_repair_date_renames_artifact_rewrites_metadata_and_appends_ledger(tmp_path: Path) -> None:
    meetings_root, meeting_id = _ingest_mtime_dated_standup(tmp_path)
    before_records = read_records(meetings_root / "_ledger.jsonl")
    before_signals = before_records[-1]["signals"]
    signal_path = meetings_root / "_signals" / f"{meeting_id}.jsonl"
    signal_bytes = signal_path.read_bytes()

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

    assert signal_path.exists()
    assert signal_path.read_bytes() != signal_bytes
    repaired_signal = json.loads(signal_path.read_text(encoding="utf-8"))
    assert repaired_signal["effective_at"] == "2026-07-10"
    assert repaired_signal["runtime_provenance_ref"]["producer_ledger_record_id"] == record["ledger_record_id"]
    assert record["signals"]["fingerprint"] != before_signals["fingerprint"]
    assert record["signals"]["count"] == before_signals["count"]
    assert record["signals"]["schema_version"] == before_signals["schema_version"]
    assert record["signals"]["producer_ledger_record_id"] == record["ledger_record_id"]
    assert record["signals"]["produced_in_this_record"] is True
    assert mode_entry["producer_ledger_record_id"] == record["ledger_record_id"]
    assert f"runtime_provenance_ledger_record_id: {record['ledger_record_id']}" in content
    prior_producers = [
        item
        for item in records
        if item["ledger_record_id"] != record["ledger_record_id"]
        and item["signals"].get("produced_in_this_record") is True
    ]
    assert len(prior_producers) == 1
    assert prior_producers[0]["signals"]["producer_ledger_record_id"] == prior_producers[0]["ledger_record_id"]


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

    assert excinfo.value.code == "missing_artifact"
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

    assert excinfo.value.code == "current_signal_link_invalid"
    assert excinfo.value.phase == "readiness"
    assert excinfo.value.exit_code == 12
    assert (meetings_root / "_ledger.jsonl").read_text(encoding="utf-8") == ledger_before
    assert list(meetings_root.glob("2026-07-10-*.md")) == []
    assert all(path.exists() and path.read_text(encoding="utf-8") == content for path, content in artifact_contents.items())


def test_reingest_after_repair_is_still_a_no_op(tmp_path: Path) -> None:
    meetings_root, meeting_id = _ingest_mtime_dated_standup(tmp_path)
    pipeline.repair_date(meeting_id, date="2026-07-10", start=tmp_path)
    processed = next((meetings_root / "_processed").iterdir())

    summary = pipeline.ingest(processed, start=tmp_path, provider="mock")

    assert summary.status == "no_op"


def test_repair_date_rewrites_existing_signal_observation_time(tmp_path: Path) -> None:
    meetings_root, meeting_id = _ingest_mtime_dated_standup(tmp_path)
    signal_path = meetings_root / "_signals" / f"{meeting_id}.jsonl"
    payload = json.loads(signal_path.read_text(encoding="utf-8"))
    payload["timing"]["occurred"].update(
        {"value": None, "precision": "unknown", "source": "unavailable", "confidence": "low"}
    )
    signal_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    fingerprint = f"sha256:{sha256_file(signal_path)}"
    ledger_path = meetings_root / "_ledger.jsonl"
    ledger_records = [
        json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines()
    ]
    for record in ledger_records:
        record["signals"]["fingerprint"] = fingerprint
    ledger_path.write_text(
        "".join(json.dumps(record) + "\n" for record in ledger_records),
        encoding="utf-8",
    )

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


@pytest.mark.parametrize("legacy_schema", ["1.0", "1.1"])
def test_repair_date_migrates_legacy_signal_generation_to_schema_1_2(
    tmp_path: Path,
    legacy_schema: str,
) -> None:
    meetings_root, meeting_id = _ingest_mtime_dated_standup(tmp_path)
    signal_path = _rewrite_signals_as_legacy(meetings_root, meeting_id, legacy_schema)

    before = assess_readiness(tmp_path)
    assert before.verdict == "ready_with_history_warnings"
    assert "legacy_signal_link_missing" in {finding.code for finding in before.findings}

    pipeline.repair_date(meeting_id, date="2026-07-10", start=tmp_path)

    records = read_records(meetings_root / "_ledger.jsonl")
    repaired_record = records[-1]
    repaired_signals = read_signal_jsonl(signal_path)
    assert repaired_signals
    assert repaired_record["signals"]["schema_version"] == "1.2"
    assert all(signal.schema_version == "1.2" for signal in repaired_signals)
    assert all(signal.source is not None for signal in repaired_signals)
    assert all(signal.timing is not None for signal in repaired_signals)
    assert all(
        signal.source is not None
        and signal.source.source_sha256 == repaired_record["source_sha256"]
        and signal.source.artifact_path
        == repaired_record["artifacts"]["summary-plus-verbatim"]["path"]
        for signal in repaired_signals
    )
    assert all(
        signal.timing is not None
        and signal.timing.occurred.value == "2026-07-10"
        and signal.timing.recorded.value == signal.recorded_at
        for signal in repaired_signals
    )
    assert all(
        signal.runtime_provenance_ref is not None
        and signal.runtime_provenance_ref.producer_ledger_record_id
        == repaired_record["ledger_record_id"]
        and signal.runtime_provenance_ref.sha256
        == repaired_record["runtime_provenance_sha256"]
        for signal in repaired_signals
    )
    if legacy_schema == "1.0":
        assert all(
            signal.evidence.locator is not None
            and (
                (
                    signal.evidence.locator.scheme == "timestamp"
                    and signal.evidence.locator.value == signal.evidence.timestamp
                )
                if signal.evidence.timestamp
                else (
                    signal.evidence.locator.scheme == "none"
                    and signal.evidence.locator.value is None
                )
            )
            and signal.stakeholder_name_raw == signal.stakeholder_name
            and signal.timing is not None
            and signal.timing.acquired is not None
            and signal.timing.acquired.precision == "unknown"
            for signal in repaired_signals
        )
    doctor_codes = {
        issue["code"] for issue in pipeline.doctor(tmp_path).details["issues"]
    }
    assert "current_signal_link_invalid" not in doctor_codes
    after = assess_readiness(tmp_path)
    assert after.verdict == "ready"
    assert "current_signal_link_invalid" not in {
        finding.code for finding in after.findings
    }


@pytest.mark.parametrize("legacy_schema", ["1.0", "1.1"])
def test_untouched_legacy_signal_generation_remains_a_history_warning(
    tmp_path: Path,
    legacy_schema: str,
) -> None:
    meetings_root, meeting_id = _ingest_mtime_dated_standup(tmp_path)
    _rewrite_signals_as_legacy(meetings_root, meeting_id, legacy_schema)

    result = assess_readiness(tmp_path)

    assert result.verdict == "ready_with_history_warnings"
    legacy = [
        finding
        for finding in result.findings
        if finding.code == "legacy_signal_link_missing"
    ]
    assert len(legacy) == 1
    assert (legacy[0].category, legacy[0].severity) == ("history", "warning")
