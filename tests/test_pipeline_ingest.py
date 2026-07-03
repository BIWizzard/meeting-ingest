import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from meeting_ingest.clock import FrozenClock
from meeting_ingest.cli import main
from meeting_ingest.errors import ConfigError
from meeting_ingest.hashing import sha256_file
from meeting_ingest.ledger import LedgerSnapshot, append_snapshot, read_records
from meeting_ingest.paths import init_project
from meeting_ingest.pipeline import ingest, reconcile


def test_pipeline_ingest_writes_mock_markdown_artifact(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-kushali-sync.txt"
    source.write_text("Ken: Hello\nKushali: Hi\n", encoding="utf-8")

    summary = ingest(
        source,
        start=paths.inbox,
        clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)),
    )

    artifact = paths.meetings_root / summary.artifacts[0]["path"]
    signal_file = paths.meetings_root / summary.artifacts[1]["path"]
    done_file = paths.inbox_done / source.name
    markdown = artifact.read_text(encoding="utf-8")
    ledger_records = read_records(paths.ledger)

    assert summary.status == "success"
    assert summary.meeting_id == "mtg-20260703-bf3b2898"
    assert summary.ingest_run_id.startswith("ingest-20260703-20260703T120000Z-")
    assert summary.artifacts == [
        {
            "kind": "markdown",
            "mode": "summary-plus-verbatim",
            "status": "ready",
            "path": "2026-07-03-kushali-sync.md",
        },
        {
            "kind": "signals",
            "status": "ready",
            "path": "_signals/mtg-20260703-bf3b2898.jsonl",
            "count": 0,
        },
    ]
    assert artifact.exists()
    assert signal_file.exists()
    assert signal_file.read_text(encoding="utf-8") == ""
    assert not source.exists()
    assert done_file.exists()
    assert (paths.meetings_root / summary.details["archive"]["processed_path"]).exists()
    assert "# Kushali Sync" in markdown
    assert "## Verbatim Transcript" in markdown
    assert markdown.endswith("<!-- transcript:end -->")
    assert [record["event"] for record in ledger_records] == ["primary_artifacts_ready", "ingest_completed"]
    assert ledger_records[0]["reconcile"]["status"] == "pending"
    assert ledger_records[-1]["artifacts"]["summary-plus-verbatim"]["path"] == "2026-07-03-kushali-sync.md"
    assert ledger_records[-1]["signals"]["path"] == "_signals/mtg-20260703-bf3b2898.jsonl"
    assert ledger_records[-1]["reconcile"]["status"] == "completed"
    assert ledger_records[-1]["reconcile"]["path"] == "_inbox/_done/2026-07-03-kushali-sync.txt"


def test_cli_ingest_json_from_nested_project_directory(tmp_path: Path, monkeypatch, capsys) -> None:
    paths = init_project(tmp_path)
    nested = paths.inbox / "nested"
    nested.mkdir()
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    monkeypatch.chdir(nested)

    exit_code = main(
        [
            "ingest",
            str(source),
            "--json",
        ]
    )

    captured = capsys.readouterr()
    summary = json.loads(captured.out)

    assert exit_code == 0
    assert summary["status"] == "success"
    assert summary["artifacts"][0]["path"] == "2026-07-03-team-sync.md"
    assert summary["artifacts"][1]["path"].startswith("_signals/mtg-20260703-")
    assert (paths.meetings_root / summary["artifacts"][0]["path"]).exists()
    assert (paths.inbox_done / source.name).exists()


def test_pipeline_ingest_archives_but_skips_reconcile_for_external_source(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    source = tmp_path / "2026-07-03-external-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")

    summary = ingest(
        source,
        start=tmp_path,
        clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)),
    )
    ledger_records = read_records(paths.ledger)

    assert source.exists()
    assert (paths.meetings_root / summary.details["archive"]["processed_path"]).exists()
    assert summary.details["reconcile"] == {
        "status": "skipped",
        "reason": "source_not_in_inbox",
        "processed_path": summary.details["archive"]["processed_path"],
    }
    assert ledger_records[-1]["reconcile"]["status"] == "skipped"


def test_pipeline_ingest_duplicate_source_returns_no_op_and_reconciles_inbox(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-kushali-sync.txt"
    source.write_text("Ken: Hello\nKushali: Hi\n", encoding="utf-8")
    first = ingest(
        source,
        start=paths.inbox,
        clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)),
    )
    redrop = paths.inbox / "2026-07-03-kushali-sync.txt"
    redrop.write_text("Ken: Hello\nKushali: Hi\n", encoding="utf-8")

    second = ingest(
        redrop,
        start=paths.inbox,
        clock=FrozenClock(datetime(2026, 7, 3, 12, 5, tzinfo=UTC)),
    )
    ledger_records = read_records(paths.ledger)

    assert second.status == "no_op"
    assert second.exit_code == 0
    assert second.meeting_id == first.meeting_id
    assert second.ingest_run_id is None
    assert second.details["existing_artifacts"] == {"summary-plus-verbatim": "2026-07-03-kushali-sync.md"}
    assert second.details["reconcile"]["status"] == "completed"
    assert second.details["reconcile"]["reason"] == "source_already_ingested"
    assert second.details["archive"]["processed_path"].startswith("_processed/bf3b2898-")
    assert not redrop.exists()
    assert (paths.inbox_done / "2026-07-03-kushali-sync-2.txt").exists()
    assert len(ledger_records) == 3
    assert ledger_records[-1]["event"] == "reconcile_repaired"
    assert ledger_records[-1]["reconcile"]["status"] == "completed"


def test_reconcile_repairs_duplicate_inbox_sources_only(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-kushali-sync.txt"
    source.write_text("Ken: Hello\nKushali: Hi\n", encoding="utf-8")
    ingest(source, start=paths.inbox, clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)))
    duplicate = paths.inbox / "duplicate-name.txt"
    duplicate.write_text("Ken: Hello\nKushali: Hi\n", encoding="utf-8")
    unknown = paths.inbox / "unknown.txt"
    unknown.write_text("Different content\n", encoding="utf-8")

    summary = reconcile(tmp_path)

    assert summary.status == "success"
    assert summary.details["repaired"] == [
        {
            "path": "_inbox/_done/duplicate-name.txt",
            "status": "completed",
            "reason": "source_already_ingested",
            "processed_path": "_processed/bf3b2898-duplicate-name.txt",
        }
    ]
    assert summary.details["skipped"] == [
        {
            "path": "_inbox/unknown.txt",
            "reason": "source_not_in_ledger",
        }
    ]
    assert not duplicate.exists()
    assert unknown.exists()


def test_reingest_after_primary_snapshot_repairs_archive_and_reconcile(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-kushali-sync.txt"
    source.write_text("Ken: Hello\nKushali: Hi\n", encoding="utf-8")
    source_sha256 = sha256_file(source)
    meeting_id = "mtg-20260703-bf3b2898"
    artifact = paths.meetings_root / "2026-07-03-kushali-sync.md"
    artifact.write_text("# Kushali Sync\n", encoding="utf-8")
    signal = paths.signals / f"{meeting_id}.jsonl"
    signal.write_text("", encoding="utf-8")
    append_snapshot(
        paths.ledger,
        LedgerSnapshot(
            event="primary_artifacts_ready",
            source_sha256=source_sha256,
            meeting_id=meeting_id,
            ingest_run_id="ingest-20260703-20260703T120000Z-abcd1234",
            source_path=str(source),
            artifacts={
                "summary-plus-verbatim": {
                    "kind": "markdown",
                    "status": "ready",
                    "path": "2026-07-03-kushali-sync.md",
                }
            },
            signals={"status": "ready", "path": f"_signals/{meeting_id}.jsonl", "count": 0},
            reconcile={"status": "pending"},
        ),
        clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)),
    )

    summary = ingest(source, start=paths.inbox, clock=FrozenClock(datetime(2026, 7, 3, 12, 5, tzinfo=UTC)))
    ledger_records = read_records(paths.ledger)

    assert summary.status == "no_op"
    assert summary.details["archive"]["processed_path"] == "_processed/bf3b2898-2026-07-03-kushali-sync.txt"
    assert (paths.processed / "bf3b2898-2026-07-03-kushali-sync.txt").exists()
    assert not source.exists()
    assert (paths.inbox_done / "2026-07-03-kushali-sync.txt").exists()
    assert [record["event"] for record in ledger_records] == ["primary_artifacts_ready", "reconcile_repaired"]
    assert ledger_records[-1]["reconcile"]["status"] == "completed"
    assert ledger_records[-1]["reconcile"]["processed_path"] == "_processed/bf3b2898-2026-07-03-kushali-sync.txt"


def test_ingest_rejects_remote_provider_when_privacy_gate_disabled(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")

    with pytest.raises(ConfigError) as exc:
        ingest(source, start=paths.inbox, provider="anthropic")

    assert exc.value.code == "remote_provider_disabled"
