import json
import hashlib
from pathlib import Path

import pytest

from meeting_ingest.errors import MeetingIngestError
from meeting_ingest.ledger import (
    LedgerSnapshot,
    append_snapshot,
    has_legacy_record_for_source,
    mint_ledger_identity,
    read_records,
    read_records_with_issues,
)
from meeting_ingest.provider_handoff import runtime_provenance_sha256
from meeting_ingest.ids import canonical_json
from meeting_ingest.locking import ProjectLock, lock_path


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


def test_read_records_requires_canonical_provenance_for_schema_2(tmp_path: Path) -> None:
    provenance = {
        "semantic_version": "0.1.0",
        "build_id": "meeting-ingest-test-approved",
        "source_commit": "a" * 40,
        "source_tree_sha256": "sha256:" + "b" * 64,
        "install_mode": "approved_frozen",
        "runtime_mode": "approved",
        "workflow_contract_version": "claude-code-session-v1",
        "development_override_reason": None,
    }
    base = {
        "schema_version": "2.0",
        "event": "ingest_completed",
        "source_sha256": "a" * 64,
        "meeting_id": "mtg-20260703-aaaaaaaa",
    }
    valid = {
        **base,
        "ingest_run_id": None,
        "source_record_sequence": 1,
        "runtime_provenance_schema": "1.0",
        "runtime_provenance_sha256": runtime_provenance_sha256(provenance),
        "runtime_provenance": provenance,
    }
    valid["ledger_record_id"] = "lr-" + hashlib.sha256(
        canonical_json(
            {
                "source_sha256": valid["source_sha256"],
                "source_record_sequence": 1,
                "event": valid["event"],
                "ingest_run_id": None,
            }
        ).encode("utf-8")
    ).hexdigest()[:32]
    ledger = tmp_path / "_ledger.jsonl"
    ledger.write_text(json.dumps(base) + "\n" + json.dumps(valid) + "\n", encoding="utf-8")

    records, issues = read_records_with_issues(ledger)

    assert records == [valid]
    assert [issue.code for issue in issues] == ["ledger_provenance_invalid"]


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


def test_ledger_identity_is_deterministic_unique_and_source_sequence_is_monotonic(
    tmp_path: Path,
) -> None:
    ledger = tmp_path / "_ledger.jsonl"
    cache = tmp_path / "_cache"
    source_sha256 = "a" * 64
    with ProjectLock(lock_path(cache)):
        first_id, first_sequence = mint_ledger_identity(
            ledger,
            source_sha256=source_sha256,
            event="primary_artifacts_ready",
            ingest_run_id="ingest-1",
        )
        retry_id, retry_sequence = mint_ledger_identity(
            ledger,
            source_sha256=source_sha256,
            event="primary_artifacts_ready",
            ingest_run_id="ingest-1",
        )
        assert (retry_id, retry_sequence) == (first_id, first_sequence)
        append_snapshot(
            ledger,
            LedgerSnapshot(
                event="primary_artifacts_ready",
                source_sha256=source_sha256,
                meeting_id="mtg-20260703-aaaaaaaa",
                ingest_run_id="ingest-1",
                source={},
                artifacts={},
                signals={},
                reconcile={},
                ledger_record_id=first_id,
                source_record_sequence=first_sequence,
            ),
        )
        second_id, second_sequence = mint_ledger_identity(
            ledger,
            source_sha256=source_sha256,
            event="ingest_completed",
            ingest_run_id="ingest-1",
        )
        append_snapshot(
            ledger,
            LedgerSnapshot(
                event="ingest_completed",
                source_sha256=source_sha256,
                meeting_id="mtg-20260703-aaaaaaaa",
                ingest_run_id="ingest-1",
                source={},
                artifacts={},
                signals={},
                reconcile={},
                ledger_record_id=second_id,
                source_record_sequence=second_sequence,
            ),
        )

    records = read_records(ledger)
    assert [record["source_record_sequence"] for record in records] == [1, 2]
    assert first_id != second_id
    assert first_id == "lr-" + hashlib.sha256(
        canonical_json(
            {
                "source_sha256": source_sha256,
                "source_record_sequence": 1,
                "event": "primary_artifacts_ready",
                "ingest_run_id": "ingest-1",
            }
        ).encode("utf-8")
    ).hexdigest()[:32]
