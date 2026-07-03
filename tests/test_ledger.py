from pathlib import Path

import pytest

from meeting_ingest.errors import MeetingIngestError
from meeting_ingest.ledger import LedgerSnapshot, append_snapshot, read_records, read_records_with_issues


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
