import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

import meeting_ingest.archive as archive_module
import meeting_ingest.pipeline as pipeline_module
from meeting_ingest.clock import FrozenClock
from meeting_ingest.cli import main
from meeting_ingest.errors import (
    EXIT_ARCHIVE_RECONCILE,
    EXIT_ARTIFACT_WRITE,
    EXIT_LEDGER_WRITE,
    EXIT_PROVIDER_FAILURE,
    EXIT_PROVIDER_VALIDATION,
    ConfigError,
    MeetingIngestError,
    UnsupportedSourceFormatError,
)
from meeting_ingest.hashing import sha256_file
from meeting_ingest.ledger import LedgerSnapshot, append_snapshot, read_records
from meeting_ingest.paths import init_project
from meeting_ingest.pipeline import ingest, ingest_inbox, reconcile
from meeting_ingest.schema import ProviderResponse


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
    assert ledger_records[-1]["source"] == {
        "original_path": "_inbox/2026-07-03-kushali-sync.txt",
        "processed_path": "_processed/bf3b2898-2026-07-03-kushali-sync.txt",
        "source_type": "txt",
    }
    assert ledger_records[-1]["artifacts"]["summary-plus-verbatim"]["path"] == "2026-07-03-kushali-sync.md"
    assert ledger_records[-1]["artifacts"]["summary-plus-verbatim"]["title"] == "Kushali Sync"
    assert ledger_records[-1]["artifacts"]["summary-plus-verbatim"]["slug"] == "kushali-sync"
    assert ledger_records[-1]["artifacts"]["summary-plus-verbatim"]["model_id"] == "none"
    assert ledger_records[-1]["signals"]["path"] == "_signals/mtg-20260703-bf3b2898.jsonl"
    assert ledger_records[-1]["reconcile"]["status"] == "completed"
    assert ledger_records[-1]["reconcile"]["path"] == "_inbox/_done/2026-07-03-kushali-sync.txt"


def test_pipeline_ingest_enriches_provider_signals_and_mirrors_markdown(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-kushali-signal.txt"
    source.write_text("Kushali: [mock-signal] Please clarify the source.\n", encoding="utf-8")

    summary = ingest(
        source,
        start=paths.inbox,
        clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)),
    )

    artifact = paths.meetings_root / summary.artifacts[0]["path"]
    signal_file = paths.meetings_root / summary.artifacts[1]["path"]
    signal_payload = json.loads(signal_file.read_text(encoding="utf-8"))
    markdown = artifact.read_text(encoding="utf-8")

    assert summary.artifacts[1]["count"] == 1
    assert signal_payload["signal_id"] == "sig-20260703-001"
    assert signal_payload["meeting_id"] == summary.meeting_id
    assert signal_payload["ingest_run_id"] == summary.ingest_run_id
    assert signal_payload["recorded_at"] == "2026-07-03T12:00:00Z"
    assert signal_payload["signal_type"] == "explicit_ask"
    assert signal_payload["evidence"]["kind"] == "paraphrase"
    assert "| `sig-20260703-001` | explicit_ask | Kushali | Asked for source clarity. | high |" in markdown


def test_ingest_inbox_processes_direct_inbox_sources_and_continues_after_failures(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    good = paths.inbox / "2026-07-03-kushali-sync.txt"
    good.write_text("Ken: Hello\nKushali: Hi\n", encoding="utf-8")
    bad = paths.inbox / "2026-07-03-unsupported.pdf"
    bad.write_text("not supported", encoding="utf-8")
    nested = paths.inbox / "nested"
    nested.mkdir()
    nested_source = nested / "2026-07-03-nested.txt"
    nested_source.write_text("Ken: Nested\n", encoding="utf-8")
    done_source = paths.inbox_done / "2026-07-03-done.txt"
    done_source.write_text("Ken: Done\n", encoding="utf-8")

    summary = ingest_inbox(
        tmp_path,
        clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)),
    )
    data = summary.to_dict()

    assert summary.status == "partial_success"
    assert summary.exit_code == 1
    assert data["processed"] == 2
    assert data["succeeded"] == 1
    assert data["failed"] == 1
    assert [result["source"] for result in data["results"]] == [
        "_inbox/2026-07-03-kushali-sync.txt",
        "_inbox/2026-07-03-unsupported.pdf",
    ]
    assert data["results"][0]["status"] == "success"
    assert data["results"][0]["artifacts"][0]["path"] == "2026-07-03-kushali-sync.md"
    assert data["results"][1]["status"] == "failed"
    assert data["results"][1]["errors"][0]["code"] == "unsupported_source_format"
    assert not good.exists()
    assert not bad.exists()
    assert nested_source.exists()
    assert done_source.exists()
    assert (paths.inbox_done / "2026-07-03-kushali-sync.txt").exists()
    assert list(paths.quarantine.glob("*.pdf"))


def test_ingest_inbox_empty_inbox_returns_no_op(tmp_path: Path) -> None:
    init_project(tmp_path)

    summary = ingest_inbox(tmp_path)
    data = summary.to_dict()

    assert summary.status == "no_op"
    assert summary.exit_code == 0
    assert data["processed"] == 0
    assert data["results"] == []


def test_ingest_inbox_reports_duplicate_sources_as_no_op(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-kushali-sync.txt"
    source.write_text("Ken: Hello\nKushali: Hi\n", encoding="utf-8")
    ingest(source, start=paths.inbox, clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)))
    redrop = paths.inbox / "2026-07-03-kushali-sync.txt"
    redrop.write_text("Ken: Hello\nKushali: Hi\n", encoding="utf-8")

    summary = ingest_inbox(
        tmp_path,
        clock=FrozenClock(datetime(2026, 7, 3, 12, 5, tzinfo=UTC)),
    )
    data = summary.to_dict()

    assert summary.status == "success"
    assert data["processed"] == 1
    assert data["succeeded"] == 1
    assert data["failed"] == 0
    assert data["results"][0]["status"] == "no_op"
    assert data["results"][0]["details"]["existing_artifacts"] == {"summary-plus-verbatim": "2026-07-03-kushali-sync.md"}


def test_artifact_write_failure_stops_before_ledger_archive_and_reconcile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-kushali-sync.txt"
    source.write_text("Ken: Hello\nKushali: Hi\n", encoding="utf-8")

    def fail_write_artifact(path: Path, markdown: str) -> None:
        raise MeetingIngestError(
            phase="artifact_write",
            code="artifact_write_failed",
            message="boom",
            exit_code=EXIT_ARTIFACT_WRITE,
            recoverable=True,
        )

    monkeypatch.setattr(pipeline_module, "_write_artifact", fail_write_artifact)

    with pytest.raises(MeetingIngestError) as exc:
        ingest(source, start=paths.inbox, clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)))

    assert exc.value.code == "artifact_write_failed"
    assert exc.value.exit_code == EXIT_ARTIFACT_WRITE
    assert source.exists()
    assert not (paths.inbox_done / source.name).exists()
    assert read_records(paths.ledger) == []
    assert list(paths.processed.iterdir()) == []
    assert list(paths.meetings_root.glob("*.md")) == []


def test_signal_write_failure_stops_before_artifact_ledger_archive_and_reconcile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-kushali-signal.txt"
    source.write_text("Kushali: [mock-signal] Please clarify the source.\n", encoding="utf-8")

    def fail_write_signal_jsonl(path: Path, signals: object) -> object:
        raise MeetingIngestError(
            phase="signal_write",
            code="signal_write_failed",
            message="boom",
            exit_code=EXIT_ARTIFACT_WRITE,
            recoverable=True,
        )

    monkeypatch.setattr(pipeline_module, "write_signal_jsonl", fail_write_signal_jsonl)

    with pytest.raises(MeetingIngestError) as exc:
        ingest(source, start=paths.inbox, clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)))

    assert exc.value.code == "signal_write_failed"
    assert exc.value.exit_code == EXIT_ARTIFACT_WRITE
    assert source.exists()
    assert not (paths.inbox_done / source.name).exists()
    assert read_records(paths.ledger) == []
    assert list(paths.processed.iterdir()) == []
    assert list(paths.meetings_root.glob("*.md")) == []


def test_provider_failure_records_ingest_failed_and_leaves_source_in_place(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-kushali-sync.txt"
    source.write_text("Ken: Hello\nKushali: Hi\n", encoding="utf-8")

    class FailingProvider:
        name = "mock"
        model_id = "none"

        def extract(self, request: object) -> ProviderResponse:
            raise RuntimeError("network timeout")

    monkeypatch.setattr(pipeline_module, "get_provider", lambda provider: FailingProvider())

    with pytest.raises(MeetingIngestError) as exc:
        ingest(source, start=paths.inbox, clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)))
    records = read_records(paths.ledger)

    assert exc.value.phase == "provider"
    assert exc.value.code == "provider_failed"
    assert exc.value.exit_code == EXIT_PROVIDER_FAILURE
    assert source.exists()
    assert not (paths.inbox_done / source.name).exists()
    assert list(paths.processed.iterdir()) == []
    assert list(paths.meetings_root.glob("*.md")) == []
    assert [record["event"] for record in records] == ["ingest_failed"]
    assert records[-1]["meeting_id"] == "mtg-20260703-bf3b2898"
    assert records[-1]["ingest_run_id"].startswith("ingest-20260703-20260703T120000Z-")
    assert records[-1]["error"]["code"] == "provider_failed"


def test_provider_validation_failure_records_ingest_failed_and_leaves_source_in_place(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-kushali-sync.txt"
    source.write_text("Ken: Hello\nKushali: Hi\n", encoding="utf-8")

    class InvalidProvider:
        name = "mock"
        model_id = "none"

        def extract(self, request: object) -> ProviderResponse:
            return ProviderResponse(title="", tl_dr="Summary")

    monkeypatch.setattr(pipeline_module, "get_provider", lambda provider: InvalidProvider())

    with pytest.raises(MeetingIngestError) as exc:
        ingest(source, start=paths.inbox, clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)))
    records = read_records(paths.ledger)

    assert exc.value.phase == "provider_validation"
    assert exc.value.code == "invalid_provider_output"
    assert exc.value.exit_code == EXIT_PROVIDER_VALIDATION
    assert source.exists()
    assert not (paths.inbox_done / source.name).exists()
    assert list(paths.processed.iterdir()) == []
    assert list(paths.meetings_root.glob("*.md")) == []
    assert [record["event"] for record in records] == ["ingest_failed"]
    assert records[-1]["meeting_id"] == "mtg-20260703-bf3b2898"
    assert records[-1]["error"]["code"] == "invalid_provider_output"


def test_primary_ledger_write_failure_leaves_source_unreconciled_with_orphan_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-kushali-sync.txt"
    source.write_text("Ken: Hello\nKushali: Hi\n", encoding="utf-8")

    def fail_append_snapshot(*args: object, **kwargs: object) -> None:
        raise MeetingIngestError(
            phase="ledger",
            code="ledger_write_failed",
            message="boom",
            exit_code=EXIT_LEDGER_WRITE,
            recoverable=True,
        )

    monkeypatch.setattr(pipeline_module, "append_snapshot", fail_append_snapshot)

    with pytest.raises(MeetingIngestError) as exc:
        ingest(source, start=paths.inbox, clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)))

    assert exc.value.code == "ledger_write_failed"
    assert exc.value.exit_code == EXIT_LEDGER_WRITE
    assert source.exists()
    assert not (paths.inbox_done / source.name).exists()
    assert read_records(paths.ledger) == []
    assert list(paths.processed.iterdir()) == []
    assert (paths.meetings_root / "2026-07-03-kushali-sync.md").exists()
    assert list(paths.signals.glob("*.jsonl"))


def test_archive_copy_failure_keeps_primary_ready_state_and_source_in_place(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-kushali-sync.txt"
    source.write_text("Ken: Hello\nKushali: Hi\n", encoding="utf-8")

    def fail_copy2(*args: object, **kwargs: object) -> None:
        raise OSError("copy failed")

    monkeypatch.setattr(archive_module.shutil, "copy2", fail_copy2)

    with pytest.raises(MeetingIngestError) as exc:
        ingest(source, start=paths.inbox, clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)))
    records = read_records(paths.ledger)

    assert exc.value.code == "archive_write_failed"
    assert exc.value.exit_code == EXIT_ARCHIVE_RECONCILE
    assert source.exists()
    assert not (paths.inbox_done / source.name).exists()
    assert list(paths.processed.iterdir()) == []
    assert [record["event"] for record in records] == ["primary_artifacts_ready"]
    assert records[-1]["reconcile"]["status"] == "pending"


def test_reconcile_move_failure_keeps_processed_copy_and_source_in_place(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-kushali-sync.txt"
    source.write_text("Ken: Hello\nKushali: Hi\n", encoding="utf-8")

    def fail_move(*args: object, **kwargs: object) -> None:
        raise OSError("move failed")

    monkeypatch.setattr(archive_module.shutil, "move", fail_move)

    with pytest.raises(MeetingIngestError) as exc:
        ingest(source, start=paths.inbox, clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)))
    records = read_records(paths.ledger)

    assert exc.value.code == "inbox_reconcile_failed"
    assert exc.value.exit_code == EXIT_ARCHIVE_RECONCILE
    assert source.exists()
    assert not (paths.inbox_done / source.name).exists()
    assert (paths.processed / "bf3b2898-2026-07-03-kushali-sync.txt").exists()
    assert [record["event"] for record in records] == ["primary_artifacts_ready"]
    assert records[-1]["reconcile"]["status"] == "pending"


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


def test_cli_ingest_uses_config_defaults_when_flags_are_omitted(tmp_path: Path, monkeypatch, capsys) -> None:
    paths = init_project(tmp_path)
    config_text = paths.config_path.read_text(encoding="utf-8")
    paths.config_path.write_text(config_text.replace('default_quality = "balanced"', 'default_quality = "fast"'), encoding="utf-8")
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    exit_code = main(["ingest", str(source), "--json"])

    captured = capsys.readouterr()
    summary = json.loads(captured.out)

    assert exit_code == 0
    assert summary["provider"] == "mock"
    assert summary["quality"] == "fast"
    artifact = paths.meetings_root / summary["artifacts"][0]["path"]
    assert "model_alias: fast" in artifact.read_text(encoding="utf-8")


def test_cli_provider_failure_returns_exit_5_and_records_ingest_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    class FailingProvider:
        name = "mock"
        model_id = "none"

        def extract(self, request: object) -> ProviderResponse:
            raise RuntimeError("network timeout")

    monkeypatch.setattr(pipeline_module, "get_provider", lambda provider: FailingProvider())

    exit_code = main(["ingest", str(source), "--json"])
    captured = capsys.readouterr()
    summary = json.loads(captured.out)
    records = read_records(paths.ledger)

    assert exit_code == EXIT_PROVIDER_FAILURE
    assert summary["status"] == "failed"
    assert summary["exit_code"] == EXIT_PROVIDER_FAILURE
    assert summary["errors"][0]["phase"] == "provider"
    assert summary["errors"][0]["code"] == "provider_failed"
    assert [record["event"] for record in records] == ["ingest_failed"]
    assert records[-1]["error"]["code"] == "provider_failed"
    assert source.exists()
    assert not (paths.inbox_done / source.name).exists()
    assert list(paths.processed.iterdir()) == []
    assert list(paths.meetings_root.glob("*.md")) == []


def test_cli_provider_validation_failure_returns_exit_6_and_records_ingest_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    class InvalidProvider:
        name = "mock"
        model_id = "none"

        def extract(self, request: object) -> ProviderResponse:
            return ProviderResponse(title="", tl_dr="Summary")

    monkeypatch.setattr(pipeline_module, "get_provider", lambda provider: InvalidProvider())

    exit_code = main(["ingest", str(source), "--json"])
    captured = capsys.readouterr()
    summary = json.loads(captured.out)
    records = read_records(paths.ledger)

    assert exit_code == EXIT_PROVIDER_VALIDATION
    assert summary["status"] == "failed"
    assert summary["exit_code"] == EXIT_PROVIDER_VALIDATION
    assert summary["errors"][0]["phase"] == "provider_validation"
    assert summary["errors"][0]["code"] == "invalid_provider_output"
    assert [record["event"] for record in records] == ["ingest_failed"]
    assert records[-1]["error"]["code"] == "invalid_provider_output"
    assert source.exists()
    assert not (paths.inbox_done / source.name).exists()
    assert list(paths.processed.iterdir()) == []
    assert list(paths.meetings_root.glob("*.md")) == []


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


def test_duplicate_external_source_no_op_does_not_append_repair_snapshot(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    source = tmp_path / "2026-07-03-external-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    first = ingest(source, start=tmp_path, clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)))

    second = ingest(source, start=tmp_path, clock=FrozenClock(datetime(2026, 7, 3, 12, 5, tzinfo=UTC)))
    ledger_records = read_records(paths.ledger)

    assert second.status == "no_op"
    assert second.meeting_id == first.meeting_id
    assert second.details["reconcile"]["status"] == "skipped"
    assert second.details["reconcile"]["archive_repaired"] == "false"
    assert [record["event"] for record in ledger_records] == ["primary_artifacts_ready", "ingest_completed"]


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
            source={
                "original_path": "_inbox/2026-07-03-kushali-sync.txt",
                "processed_path": None,
                "source_type": "txt",
            },
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


def test_ingest_allows_anthropic_when_privacy_gate_enabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths = init_project(tmp_path)
    config_text = paths.config_path.read_text(encoding="utf-8")
    paths.config_path.write_text(config_text.replace("allow_remote_provider = false", "allow_remote_provider = true"), encoding="utf-8")
    source = paths.inbox / "2026-07-03-synthetic.txt"
    source.write_text("Ken: Hello\nKushali: Please clarify the source.\n", encoding="utf-8")

    class SyntheticAnthropicProvider:
        name = "anthropic"
        model_id = "claude-sonnet-5"

        def extract(self, request: object) -> ProviderResponse:
            return ProviderResponse(title="Synthetic", tl_dr="Synthetic summary.")

    monkeypatch.setattr(pipeline_module, "get_provider", lambda provider: SyntheticAnthropicProvider())

    summary = ingest(
        source,
        start=paths.inbox,
        provider="anthropic",
        clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)),
    )
    artifact = paths.meetings_root / summary.artifacts[0]["path"]

    assert summary.status == "success"
    assert "provider: anthropic" in artifact.read_text(encoding="utf-8")
    assert "model_id: claude-sonnet-5" in artifact.read_text(encoding="utf-8")


def test_ingest_quarantines_unsupported_inbox_source_and_records_failure(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-meeting.pdf"
    source.write_text("not supported", encoding="utf-8")

    with pytest.raises(UnsupportedSourceFormatError) as exc:
        ingest(source, start=paths.inbox, clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)))
    records = read_records(paths.ledger)

    assert exc.value.code == "unsupported_source_format"
    assert not source.exists()
    quarantined = list(paths.quarantine.iterdir())
    assert len(quarantined) == 1
    assert records[-1]["event"] == "source_quarantined"
    assert records[-1]["meeting_id"] is None
    assert records[-1]["error"]["code"] == "unsupported_source_format"
    assert records[-1]["quarantine"]["status"] == "quarantined"
    assert records[-1]["quarantine"]["path"].startswith("_quarantine/")


def test_ingest_records_failed_external_source_without_quarantine(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    source = tmp_path / "2026-07-03-meeting.pdf"
    source.write_text("not supported", encoding="utf-8")

    with pytest.raises(UnsupportedSourceFormatError) as exc:
        ingest(source, start=tmp_path, clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)))
    records = read_records(paths.ledger)

    assert exc.value.code == "unsupported_source_format"
    assert source.exists()
    assert records[-1]["event"] == "ingest_failed"
    assert records[-1]["quarantine"] is None
    assert records[-1]["error"]["code"] == "unsupported_source_format"


def test_retry_after_failed_external_source_can_ingest_successfully(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    source = tmp_path / "2026-07-03-meeting.pdf"
    source.write_text("not supported", encoding="utf-8")

    with pytest.raises(UnsupportedSourceFormatError):
        ingest(source, start=tmp_path, clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)))
    source = tmp_path / "2026-07-03-meeting.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")

    summary = ingest(source, start=tmp_path, clock=FrozenClock(datetime(2026, 7, 3, 12, 5, tzinfo=UTC)))
    records = read_records(paths.ledger)

    assert summary.status == "success"
    assert [record["event"] for record in records] == ["ingest_failed", "primary_artifacts_ready", "ingest_completed"]
    assert records[-1]["artifacts"]["summary-plus-verbatim"]["status"] == "ready"


def test_reconcile_skips_failed_record_without_repairing_as_duplicate(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-meeting.pdf"
    source.write_text("not supported", encoding="utf-8")

    with pytest.raises(UnsupportedSourceFormatError):
        ingest(source, start=paths.inbox, clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)))
    retry_source = paths.inbox / "2026-07-03-meeting.pdf"
    retry_source.write_text("not supported", encoding="utf-8")

    summary = reconcile(tmp_path)

    assert summary.details["repaired"] == []
    assert summary.details["skipped"] == [
        {
            "path": "_inbox/2026-07-03-meeting.pdf",
            "reason": "source_not_in_ledger",
        }
    ]
    assert retry_source.exists()
