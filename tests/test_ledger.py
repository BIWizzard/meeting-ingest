import json
from pathlib import Path

import pytest

from meeting_ingest.errors import MeetingIngestError
from meeting_ingest.ledger import (
    LedgerSnapshot,
    append_snapshot,
    has_legacy_record_for_source,
    read_records,
    read_records_with_issues,
)


def test_read_records_ignores_malformed_and_invalid_lines(tmp_path: Path) -> None:
    ledger = tmp_path / "_ledger.jsonl"
    ledger.write_text(
        "\n".join(
            [
                '{"schema_version": "1.0", "event": "ingest_completed", "source_sha256": "abc", "meeting_id": "mtg-1"}',
                "{not-json",
                '{"schema_version": "1.0", "event": "ingest_completed"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    records, issues = read_records_with_issues(ledger)

    assert read_records(ledger) == records
    assert records == [
        {
            "schema_version": "1.0",
            "event": "ingest_completed",
            "source_sha256": "abc",
            "meeting_id": "mtg-1",
        }
    ]
    assert [issue.code for issue in issues] == ["malformed_ledger_json", "invalid_ledger_record"]


def test_read_records_classifies_only_the_exact_deprecated_shape_as_legacy(tmp_path: Path) -> None:
    ledger = tmp_path / "_ledger.jsonl"
    legacy = {
        "source_sha256": "a" * 64,
        "meeting_id": "2026-05-04-generic-d01638d8",
        "ingest_run_id": "20260518T030615Z",
    }
    invalid_lookalike = {**legacy, "source_sha256": "not-a-sha256"}
    ledger.write_text(
        "\n".join(json.dumps(record) for record in (legacy, invalid_lookalike)) + "\n",
        encoding="utf-8",
    )

    records, issues = read_records_with_issues(ledger)

    assert records == []
    assert [issue.code for issue in issues] == ["legacy_ledger_record", "invalid_ledger_record"]


def test_has_legacy_record_for_source_matches_valid_legacy_record(tmp_path: Path) -> None:
    ledger = tmp_path / "_ledger.jsonl"
    matching_sha256 = "a" * 64
    legacy = {
        "source_sha256": matching_sha256,
        "meeting_id": "2026-05-04-generic-d01638d8",
        "ingest_run_id": "20260518T030615Z",
    }
    ledger.write_text(json.dumps(legacy) + "\n", encoding="utf-8")

    assert has_legacy_record_for_source(ledger, matching_sha256)


@pytest.mark.parametrize(
    "line",
    [
        json.dumps(
            {
                "source_sha256": "b" * 64,
                "meeting_id": "2026-05-04-generic-d01638d8",
                "ingest_run_id": "20260518T030615Z",
            }
        ),
        "{not-json",
        json.dumps(
            {
                "schema_version": "1.0",
                "event": "ingest_completed",
                "source_sha256": "a" * 64,
                "meeting_id": "mtg-20260504-aaaaaaaa",
                "ingest_run_id": "ingest-20260504-20260518T030615Z-abcd1234",
                "source": {},
                "artifacts": {},
                "signals": {},
                "reconcile": {},
            }
        ),
        json.dumps(
            {
                "source_sha256": "not-a-sha256",
                "meeting_id": "2026-05-04-generic-d01638d8",
                "ingest_run_id": "20260518T030615Z",
            }
        ),
        json.dumps(
            {
                "source_sha256": "a" * 64,
                "meeting_id": "2026-05-04-generic-d01638d8",
                "ingest_run_id": "bad-run-id",
            }
        ),
    ],
)
def test_has_legacy_record_for_source_ignores_nonmatches(tmp_path: Path, line: str) -> None:
    ledger = tmp_path / "_ledger.jsonl"
    ledger.write_text(line + "\n", encoding="utf-8")

    assert not has_legacy_record_for_source(ledger, "a" * 64)


def test_append_snapshot_wraps_write_failures(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger-as-directory"
    ledger_path.mkdir()

    with pytest.raises(MeetingIngestError) as exc:
        append_snapshot(
            ledger_path,
            LedgerSnapshot(
                event="ingest_completed",
                source_sha256="abc",
                meeting_id="mtg-20260703-abcdef12",
                ingest_run_id="ingest-20260703-20260703T120000Z-abcd1234",
                source={},
                artifacts={},
                signals={},
                reconcile={},
            ),
        )

    assert exc.value.phase == "ledger"
    assert exc.value.code == "ledger_write_failed"
    assert exc.value.exit_code == 8
