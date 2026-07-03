from pathlib import Path

from meeting_ingest.ledger import read_records, read_records_with_issues


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
