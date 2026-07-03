import json
from pathlib import Path

import pytest

from meeting_ingest.errors import MeetingIngestError
from meeting_ingest.schema import ProviderValidationError, SignalEvidence, SignalRecord
from meeting_ingest.signals import write_signal_jsonl


def test_write_signal_jsonl_uses_contract_record_shape(tmp_path: Path) -> None:
    path = tmp_path / "_signals" / "mtg-20260703-f953bbd2.jsonl"
    signal = SignalRecord(
        signal_id="sig-20260703-001",
        meeting_id="mtg-20260703-f953bbd2",
        ingest_run_id="ingest-20260703-20260703T120000Z-abcd1234",
        effective_at="2026-07-03",
        recorded_at="2026-07-03T12:00:00Z",
        signal_type="explicit_ask",
        stakeholder_id="person-kushali",
        stakeholder_name="Kushali",
        summary="Asked for source clarity.",
        evidence=SignalEvidence(kind="paraphrase", text="Kushali asked for source clarity.", speaker="Kushali"),
        inference_level="explicit",
        confidence="high",
        topics=["identity-resolution"],
        project_refs=["AE SK"],
    )

    result = write_signal_jsonl(path, [signal])
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert result.count == 1
    assert payload["schema_version"] == "1.0"
    assert payload["meeting_id"] == "mtg-20260703-f953bbd2"
    assert payload["signal_type"] == "explicit_ask"
    assert payload["evidence"] == {
        "kind": "paraphrase",
        "speaker": "Kushali",
        "text": "Kushali asked for source clarity.",
        "timestamp": None,
    }
    assert payload["recurrence"] == "unknown"
    assert payload["status"] == "active"


def test_write_signal_jsonl_validates_records(tmp_path: Path) -> None:
    path = tmp_path / "signals.jsonl"
    signal = SignalRecord(
        signal_id="sig-20260703-001",
        meeting_id="mtg-20260703-f953bbd2",
        ingest_run_id="ingest-20260703-20260703T120000Z-abcd1234",
        effective_at="2026-07-03",
        recorded_at="2026-07-03T12:00:00Z",
        signal_type="unsupported",
        stakeholder_id=None,
        stakeholder_name="Project team",
        summary="Summary",
        evidence=SignalEvidence(kind="paraphrase", text="Evidence"),
        inference_level="explicit",
        confidence="high",
    )

    with pytest.raises(ProviderValidationError):
        write_signal_jsonl(path, [signal])


def test_write_signal_jsonl_wraps_write_failures(tmp_path: Path) -> None:
    path = tmp_path / "signals-as-directory"
    path.mkdir()

    with pytest.raises(MeetingIngestError) as exc:
        write_signal_jsonl(path, [])

    assert exc.value.phase == "signal_write"
    assert exc.value.code == "signal_write_failed"
    assert exc.value.exit_code == 7
