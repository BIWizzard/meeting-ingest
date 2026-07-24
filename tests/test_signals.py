import json
from dataclasses import replace
from pathlib import Path

import pytest

from meeting_ingest.errors import MeetingIngestError
from meeting_ingest.ids import observation_identity_hash
from meeting_ingest.schema import ProviderValidationError, SignalEvidence, SignalRecord
from meeting_ingest.signals import (
    assign_deterministic_signal_ids,
    is_deprecated_signal_event_jsonl,
    read_signal_jsonl,
    write_signal_jsonl,
)


FIXTURES = Path(__file__).parent / "fixtures" / "signals"


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
    path.write_text("existing\n", encoding="utf-8")
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
    assert path.read_text(encoding="utf-8") == "existing\n"


def test_write_signal_jsonl_wraps_write_failures(tmp_path: Path) -> None:
    path = tmp_path / "signals-as-directory"
    path.mkdir()

    with pytest.raises(MeetingIngestError) as exc:
        write_signal_jsonl(path, [])

    assert exc.value.phase == "signal_write"
    assert exc.value.code == "signal_write_failed"
    assert exc.value.exit_code == 7


def test_read_signal_jsonl_accepts_schema_1_0_and_1_1() -> None:
    legacy = read_signal_jsonl(FIXTURES / "schema-1.0-meeting.jsonl")
    generalized = read_signal_jsonl(FIXTURES / "schema-1.1-meeting.jsonl")

    assert legacy[0].schema_version == "1.0"
    assert legacy[0].source is None
    assert generalized[0].schema_version == "1.1"
    assert generalized[0].source is not None
    assert generalized[0].source.source_id == "src-a1b2c3d4e5f6"
    assert generalized[0].stakeholder_name_raw == "G, Kushali"


def test_deprecated_signal_event_detection_requires_the_exact_legacy_shape(tmp_path: Path) -> None:
    path = tmp_path / "legacy-events.jsonl"
    event = {
        "schema_version": "1.0",
        "event": "stakeholder_signal_recorded",
        "event_id": "event-1",
        "ingest_run_id": "ingest-20260518-batch1",
        "effective_at": "2026-05-04",
        "recorded_at": "2026-05-18T03:06:15Z",
        "origin": "meeting",
        "payload": {},
        "provenance": {},
    }
    path.write_text(json.dumps(event) + "\n", encoding="utf-8")

    assert is_deprecated_signal_event_jsonl(path) is True

    event["unexpected"] = True
    path.write_text(json.dumps(event) + "\n", encoding="utf-8")
    assert is_deprecated_signal_event_jsonl(path) is False


def test_deprecated_signal_event_detection_fails_closed_for_mixed_and_empty_files(tmp_path: Path) -> None:
    path = tmp_path / "mixed.jsonl"
    event = {
        "schema_version": "1.0",
        "event": "stakeholder_signal_recorded",
        "event_id": "event-1",
        "ingest_run_id": "ingest-20260518-batch1",
        "effective_at": "2026-05-04",
        "recorded_at": "2026-05-18T03:06:15Z",
        "origin": "meeting",
        "payload": {},
        "provenance": {},
    }
    path.write_text(json.dumps(event) + "\n{}\n", encoding="utf-8")
    assert is_deprecated_signal_event_jsonl(path) is False

    path.write_text("", encoding="utf-8")
    assert is_deprecated_signal_event_jsonl(path) is False


def test_schema_1_1_rejects_unknown_source_kind(tmp_path: Path) -> None:
    payload = json.loads((FIXTURES / "schema-1.1-meeting.jsonl").read_text(encoding="utf-8"))
    payload["source"]["source_kind"] = "calendar_event"
    path = tmp_path / "invalid.jsonl"
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    with pytest.raises(MeetingIngestError, match="source_kind") as exc:
        read_signal_jsonl(path)
    assert exc.value.code == "signal_invalid"


def test_schema_1_1_accepts_collision_suffix_ordinals_above_nine(tmp_path: Path) -> None:
    payload = json.loads((FIXTURES / "schema-1.1-meeting.jsonl").read_text(encoding="utf-8"))
    payload["signal_id"] = f"{payload['signal_id']}-10"
    path = tmp_path / "collision-10.jsonl"
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    assert read_signal_jsonl(path)[0].signal_id.endswith("-10")


def test_locator_based_signal_identity_survives_provider_paraphrase() -> None:
    original = read_signal_jsonl(FIXTURES / "schema-1.1-meeting.jsonl")[0]
    paraphrased = replace(
        original,
        signal_id="pending",
        summary="A differently worded summary.",
        evidence=replace(original.evidence, text="Different provider wording for the same located evidence."),
    )
    first = assign_deterministic_signal_ids([replace(original, signal_id="pending")]).signals[0]
    second = assign_deterministic_signal_ids([paraphrased]).signals[0]

    assert first.signal_id == second.signal_id


def test_deterministic_signal_identity_collapses_exact_duplicates() -> None:
    signal = replace(read_signal_jsonl(FIXTURES / "schema-1.1-meeting.jsonl")[0], signal_id="pending")

    result = assign_deterministic_signal_ids([signal, signal])

    assert len(result.signals) == 1
    assert result.warnings == [f"collapsed 1 exact duplicate signal(s) for {result.signals[0].signal_id}"]


def test_deterministic_signal_identity_suffixes_same_locator_content_collisions() -> None:
    signal = replace(read_signal_jsonl(FIXTURES / "schema-1.1-meeting.jsonl")[0], signal_id="pending")
    changed = replace(signal, summary="Conflicting structured content at the same locator.")

    result = assign_deterministic_signal_ids([signal, changed])
    reordered = assign_deterministic_signal_ids([changed, signal])

    assert len(result.signals) == 2
    assert result.signals[1].signal_id == f"{result.signals[0].signal_id}-2"
    assert result.warnings == [f"assigned deterministic collision suffixes for {result.signals[0].signal_id}"]
    assert {item.summary: item.signal_id for item in result.signals} == {
        item.summary: item.signal_id for item in reordered.signals
    }


def test_observation_identity_normalizes_none_scheme_before_using_evidence() -> None:
    first = observation_identity_hash(
        signal_type="explicit_ask",
        actor_name="Kushali",
        locator={"scheme": " NONE ", "value": None},
        evidence_text="First evidence",
    )
    second = observation_identity_hash(
        signal_type="explicit_ask",
        actor_name="Kushali",
        locator={"scheme": "none", "value": None},
        evidence_text="First evidence",
    )

    assert first == second
    assert first != observation_identity_hash(
        signal_type="explicit_ask",
        actor_name="Kushali",
        locator={"scheme": "none", "value": None},
        evidence_text="Second evidence",
    )


def test_observation_identity_hash_matches_frozen_contract_inputs() -> None:
    assert observation_identity_hash(
        signal_type="explicit_ask",
        actor_name="  G,  Kushali ",
        locator={"scheme": "none", "value": None},
        evidence_text="  Asked   for source clarity. ",
    ) == "a7f76d04d0d238ebc99151076c3b1f50ba2ac975117be13e6ca12c83c0b168b2"
    assert observation_identity_hash(
        signal_type="explicit_ask",
        actor_name="  G,  Kushali ",
        locator={"scheme": "timestamp", "value": " 09:18 "},
        evidence_text="ignored",
    ) == "a800b55854b4e59fb1750d849c0c1c0e3ec0620064a9b83d3d3c14f2c3a3932f"


def test_signal_reader_rejects_non_string_required_fields(tmp_path: Path) -> None:
    payload = json.loads((FIXTURES / "schema-1.1-meeting.jsonl").read_text(encoding="utf-8"))
    payload["signal_type"] = 42
    path = tmp_path / "wrong-types.jsonl"
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    with pytest.raises(MeetingIngestError, match="signal_type must be a string") as exc:
        read_signal_jsonl(path)
    assert exc.value.code == "signal_invalid"


def test_signal_reader_wraps_undecodable_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "signals.jsonl"
    path.write_bytes(b"\xff\xfe\x00")

    with pytest.raises(MeetingIngestError) as exc:
        read_signal_jsonl(path)
    assert exc.value.code == "signal_read_failed"


def test_schema_1_1_allows_unknown_occurrence_without_processing_time_substitution(tmp_path: Path) -> None:
    payload = json.loads((FIXTURES / "schema-1.1-meeting.jsonl").read_text(encoding="utf-8"))
    payload["timing"]["occurred"].update(
        {"value": None, "precision": "unknown", "source": "unavailable", "confidence": "low"}
    )
    path = tmp_path / "unknown-occurrence.jsonl"
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    assert read_signal_jsonl(path)[0].timing.occurred.value is None
