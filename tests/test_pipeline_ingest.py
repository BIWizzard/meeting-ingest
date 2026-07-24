import json
import os
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from conftest import approved_runtime_inspection
import meeting_ingest.archive as archive_module
import meeting_ingest.pipeline as pipeline_module
from meeting_ingest.clock import FrozenClock
from meeting_ingest.cli import main
from meeting_ingest.errors import (
    EXIT_ARCHIVE_RECONCILE,
    EXIT_ARTIFACT_WRITE,
    EXIT_GENERAL_FAILURE,
    EXIT_LEDGER_WRITE,
    EXIT_PROVIDER_FAILURE,
    EXIT_PROVIDER_VALIDATION,
    EXIT_RUNTIME_READINESS,
    ConfigError,
    MeetingIngestError,
    UnsupportedSourceFormatError,
)
from meeting_ingest.hashing import sha256_file
from meeting_ingest.ledger import LedgerSnapshot, append_snapshot, read_records
from meeting_ingest.paths import init_project
from meeting_ingest.pipeline import ingest, ingest_inbox, provider_request, reconcile
from meeting_ingest.provider_contract import response_contract_for_request
from meeting_ingest.readiness import DevelopmentOverride
from meeting_ingest.runtime import ReadinessFinding
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
    assert signal_payload["schema_version"] == "1.1"
    assert signal_payload["signal_id"].startswith(f"sig-{summary.source_sha256[:12]}-")
    assert signal_payload["meeting_id"] == summary.meeting_id
    assert signal_payload["ingest_run_id"] == summary.ingest_run_id
    assert signal_payload["recorded_at"] == "2026-07-03T12:00:00Z"
    assert signal_payload["signal_type"] == "explicit_ask"
    assert signal_payload["evidence"]["kind"] == "paraphrase"
    assert f"| `{signal_payload['signal_id']}` | explicit_ask | Kushali | Asked for source clarity. | high |" in markdown
    assert signal_payload["stakeholder_name_raw"] == "Kushali"
    assert signal_payload["source"]["source_id"] == f"src-{summary.source_sha256[:12]}"
    assert signal_payload["source"]["source_kind"] == "meeting_transcript"
    assert signal_payload["source"]["channel"] is None
    assert signal_payload["timing"]["occurred"]["value"] == "2026-07-03"
    assert signal_payload["timing"]["recorded"]["value"] == "2026-07-03T12:00:00Z"


def test_ingest_reports_rename_suggestion_for_low_signal_title(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-kushali-adbook-validation-explainer.txt"
    source.write_text("Ken: Hello\nKushali: Hi\n", encoding="utf-8")

    class GenericTitleProvider:
        name = "mock"
        model_id = "none"

        def extract(self, request: object) -> ProviderResponse:
            return ProviderResponse(title="Generic", tl_dr="Summary.")

    monkeypatch.setattr(pipeline_module, "get_provider", lambda provider: GenericTitleProvider())

    summary = ingest(
        source,
        start=paths.inbox,
        clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)),
    )
    records = read_records(paths.ledger)

    assert summary.artifacts[0]["path"] == "2026-07-03-generic.md"
    assert summary.details["title"] == {
        "value": "Generic",
        "slug": "generic",
        "confidence": "low",
        "rename_suggestion": "2026-07-03-kushali-adbook-validation-explainer.md",
    }
    assert records[-1]["artifacts"]["summary-plus-verbatim"]["title_confidence"] == "low"
    assert records[-1]["artifacts"]["summary-plus-verbatim"]["filename_confidence"] == "low"


def test_ingest_uses_null_rename_suggestion_when_no_filename_suggestion_is_possible(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-generic.txt"
    source.write_text("Ken: Hello\nKushali: Hi\n", encoding="utf-8")

    class GenericTitleProvider:
        name = "mock"
        model_id = "none"

        def extract(self, request: object) -> ProviderResponse:
            return ProviderResponse(title="Generic", tl_dr="Summary.")

    monkeypatch.setattr(pipeline_module, "get_provider", lambda provider: GenericTitleProvider())

    summary = ingest(
        source,
        start=paths.inbox,
        clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)),
    )

    assert summary.details["title"]["confidence"] == "low"
    assert summary.details["title"]["rename_suggestion"] is None


def test_ingest_warns_when_artifact_filename_collides(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    existing = paths.meetings_root / "2026-07-03-kushali-sync.md"
    existing.write_text("# Existing\n", encoding="utf-8")
    source = paths.inbox / "2026-07-03-kushali-sync.txt"
    source.write_text("Ken: Hello\nKushali: Hi\n", encoding="utf-8")

    summary = ingest(
        source,
        start=paths.inbox,
        clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)),
    )

    assert summary.artifacts[0]["path"] == "2026-07-03-kushali-sync-2.md"
    assert summary.warnings == ["artifact filename collision; wrote 2026-07-03-kushali-sync-2.md"]
    assert existing.read_text(encoding="utf-8") == "# Existing\n"
    assert (paths.meetings_root / "2026-07-03-kushali-sync-2.md").exists()


def test_ingest_warns_when_effective_date_comes_from_file_mtime(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "Daily Stand Up - Post-MVP (41).vtt"
    source.write_text(
        (Path(__file__).parent / "fixtures" / "teams-vtt" / "Daily Stand Up - Post-MVP (41).vtt").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    os.utime(source, (1784160000, 1784160000))

    summary = pipeline_module.ingest(source, start=tmp_path, provider="mock")

    assert summary.status == "success"
    assert any("file modification time" in warning for warning in summary.warnings)
    assert summary.meeting_id is not None and summary.meeting_id.startswith("mtg-20260716-")


def test_ingest_warns_when_content_and_filename_dates_conflict(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-02-standup.txt"
    source.write_text(
        "Team Standup-20260701_090000-Meeting Transcript\n"
        "Ken: Hello team.\n",
        encoding="utf-8",
    )

    summary = pipeline_module.ingest(source, start=tmp_path, provider="mock")

    warning = next(
        warning for warning in summary.warnings if warning.startswith("conflicting meeting date evidence (")
    )
    assert "content=2026-07-01" in warning
    assert "filename=2026-07-02" in warning
    assert summary.meeting_id is not None and summary.meeting_id.startswith("mtg-20260701-")


def test_ingest_meeting_date_override_mints_ids_from_override(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "Daily Stand Up - Post-MVP (41).vtt"
    source.write_text(
        (Path(__file__).parent / "fixtures" / "teams-vtt" / "Daily Stand Up - Post-MVP (41).vtt").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    os.utime(source, (1784160000, 1784160000))

    summary = pipeline_module.ingest(
        source,
        start=tmp_path,
        provider="mock",
        meeting_date="2026-07-10",
    )

    assert summary.status == "success"
    assert summary.meeting_id is not None and summary.meeting_id.startswith("mtg-20260710-")
    assert summary.details["effective_date"] == {
        "value": "2026-07-10",
        "confidence": "manual",
        "source": "override",
    }
    assert not any("file modification time" in warning for warning in summary.warnings)
    artifact_path = tmp_path / "_local/project-context/meetings" / summary.artifacts[0]["path"]
    front_matter = artifact_path.read_text(encoding="utf-8")
    assert "date: 2026-07-10" in front_matter
    assert "date_confidence: manual" in front_matter
    assert "date_source: override" in front_matter


def test_ingest_rejects_invalid_meeting_date(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "meeting.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")

    with pytest.raises(ConfigError) as excinfo:
        pipeline_module.ingest(
            source,
            start=tmp_path,
            provider="mock",
            meeting_date="2026-13-40",
        )

    assert excinfo.value.code == "invalid_meeting_date"


def test_provider_request_warns_when_effective_date_comes_from_file_mtime(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "Daily Stand Up - Post-MVP (42).vtt"
    source.write_text(
        (Path(__file__).parent / "fixtures" / "teams-vtt" / "Daily Stand Up - Post-MVP (42).vtt").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    os.utime(source, (1784160000, 1784160000))

    summary = pipeline_module.provider_request(source, start=tmp_path)

    assert summary.status == "success"
    assert any("file modification time" in warning for warning in summary.warnings)


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
    assert second.details["source"] == {
        "path": "_inbox/2026-07-03-kushali-sync.txt",
        "source_type": "txt",
        "known_original_path": "_inbox/2026-07-03-kushali-sync.txt",
    }
    assert second.details["existing_artifacts"] == {"summary-plus-verbatim": "2026-07-03-kushali-sync.md"}
    assert second.details["existing_artifact_details"]["summary-plus-verbatim"]["status"] == "ready"
    assert second.details["existing_artifact_details"]["summary-plus-verbatim"]["path"] == "2026-07-03-kushali-sync.md"
    assert second.details["repair"] == {
        "changed": True,
        "ledger_event": "reconcile_repaired",
    }
    assert second.details["reconcile"]["status"] == "completed"
    assert second.details["reconcile"]["reason"] == "source_already_ingested"
    assert second.details["archive"]["processed_path"].startswith("_processed/bf3b2898-")
    assert not redrop.exists()
    assert (paths.inbox_done / "2026-07-03-kushali-sync-2.txt").exists()
    assert len(ledger_records) == 3
    assert ledger_records[-1]["event"] == "reconcile_repaired"
    assert ledger_records[-1]["reconcile"]["status"] == "completed"


def test_ingest_fails_closed_for_legacy_only_source_without_side_effects(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-legacy-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    source_sha256 = sha256_file(source)
    _append_legacy_record(paths.ledger, source_sha256)
    before = _file_snapshot(paths.meetings_root)

    with pytest.raises(MeetingIngestError) as exc:
        ingest(source, start=paths.inbox)

    assert exc.value.phase == "ledger"
    assert exc.value.code == "legacy_source_unresolved"
    assert exc.value.exit_code == EXIT_RUNTIME_READINESS
    assert exc.value.recoverable is False
    assert exc.value.details == {
        "source_path": str(source),
        "source_sha256": source_sha256,
    }
    assert source.name in exc.value.message
    assert "cannot be re-ingested" in exc.value.message
    assert _file_snapshot(paths.meetings_root) == before


def test_provider_request_fails_closed_for_legacy_only_source_without_minting_request(
    tmp_path: Path,
) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-legacy-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    source_sha256 = sha256_file(source)
    _append_legacy_record(paths.ledger, source_sha256)
    before = _file_snapshot(paths.meetings_root)

    with pytest.raises(MeetingIngestError) as exc:
        provider_request(source, start=paths.inbox)

    assert exc.value.phase == "ledger"
    assert exc.value.code == "legacy_source_unresolved"
    assert exc.value.exit_code == EXIT_RUNTIME_READINESS
    assert exc.value.recoverable is False
    assert exc.value.details == {
        "source_path": str(source),
        "source_sha256": source_sha256,
    }
    assert _file_snapshot(paths.meetings_root) == before
    assert list((paths.cache / "provider-requests").glob("*.request.json")) == []


def test_session_phase2_fails_closed_for_legacy_only_source_without_side_effects(
    tmp_path: Path,
) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-legacy-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    request_summary = provider_request(source, start=paths.inbox)
    request_path = paths.meetings_root / request_summary.details["request_path"]
    response_path = paths.meetings_root / request_summary.details["expected_response_path"]
    _write_session_response(request_path, response_path)
    _append_legacy_record(paths.ledger, request_summary.source_sha256)
    before = _file_snapshot(paths.meetings_root)

    with pytest.raises(MeetingIngestError) as exc:
        ingest(
            source,
            start=paths.inbox,
            provider="session",
            provider_response=response_path,
        )

    assert exc.value.phase == "ledger"
    assert exc.value.code == "legacy_source_unresolved"
    assert exc.value.exit_code == EXIT_RUNTIME_READINESS
    assert exc.value.recoverable is False
    assert exc.value.details == {
        "source_path": str(source),
        "source_sha256": request_summary.source_sha256,
    }
    assert _file_snapshot(paths.meetings_root) == before


def test_reconcile_fails_closed_for_legacy_only_source_without_side_effects(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-legacy-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    source_sha256 = sha256_file(source)
    _append_legacy_record(paths.ledger, source_sha256)
    before = _file_snapshot(paths.meetings_root)

    with pytest.raises(MeetingIngestError) as exc:
        reconcile(tmp_path)

    assert exc.value.code == "legacy_source_unresolved"
    assert exc.value.exit_code == EXIT_RUNTIME_READINESS
    assert _file_snapshot(paths.meetings_root) == before


def test_reconcile_preflights_legacy_sources_before_repairing_duplicates(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-kushali-sync.txt"
    source.write_text("Ken: Hello\nKushali: Hi\n", encoding="utf-8")
    ingest(source, start=paths.inbox)
    duplicate = paths.inbox / "a-duplicate.txt"
    duplicate.write_text("Ken: Hello\nKushali: Hi\n", encoding="utf-8")
    legacy = paths.inbox / "z-legacy.txt"
    legacy.write_text("Legacy content\n", encoding="utf-8")
    _append_legacy_record(paths.ledger, sha256_file(legacy))
    ledger_before = paths.ledger.read_bytes()

    with pytest.raises(MeetingIngestError) as exc:
        reconcile(tmp_path)

    assert exc.value.code == "legacy_source_unresolved"
    assert duplicate.exists()
    assert not (paths.inbox_done / duplicate.name).exists()
    assert paths.ledger.read_bytes() == ledger_before
    assert all(record["event"] != "reconcile_repaired" for record in read_records(paths.ledger))


def test_current_primary_record_wins_over_matching_legacy_record(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-legacy-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    first = ingest(source, start=paths.inbox)
    _append_legacy_record(paths.ledger, first.source_sha256)
    redrop = paths.inbox / source.name
    redrop.write_text("Ken: Hello\n", encoding="utf-8")

    summary = ingest(redrop, start=paths.inbox)

    assert summary.status == "no_op"
    assert summary.meeting_id == first.meeting_id
    assert summary.details["reconcile"]["reason"] == "source_already_ingested"


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
    assert second.details["repair"] == {
        "changed": False,
        "ledger_event": None,
    }
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
            "source_sha256": "bf3b289874ef561e3862f909101eebd430adf1c2f30eefba602a0c55f4c034e2",
            "meeting_id": "mtg-20260703-bf3b2898",
            "status": "completed",
            "reason": "source_already_ingested",
            "processed_path": "_processed/bf3b2898-duplicate-name.txt",
            "changed": True,
        }
    ]
    assert summary.details["skipped"] == [
        {
            "path": "_inbox/unknown.txt",
            "source_sha256": "006d57abf92bac83541e6b4732dbbb5adc338ff80b8ef0781511dcc16b9b7dd8",
            "meeting_id": None,
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
    assert summary.details["source"] == {
        "path": "_inbox/2026-07-03-kushali-sync.txt",
        "source_type": "txt",
        "known_original_path": "_inbox/2026-07-03-kushali-sync.txt",
    }
    assert summary.details["repair"] == {
        "changed": True,
        "ledger_event": "reconcile_repaired",
    }
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

    with pytest.raises(MeetingIngestError) as exc:
        ingest(source, start=paths.inbox, provider="anthropic")

    assert exc.value.code == "readiness_privacy_blocked"
    assert exc.value.exit_code == 12


def test_ingest_reports_unknown_provider_before_remote_privacy(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")

    with pytest.raises(ConfigError) as exc:
        ingest(source, start=paths.inbox, provider="sesion")

    assert exc.value.code == "provider_not_implemented"
    assert exc.value.exit_code == 2


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


def test_session_provider_request_requires_privacy_gate(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")

    with pytest.raises(MeetingIngestError) as exc:
        provider_request(source, start=paths.inbox)

    assert exc.value.code == "readiness_privacy_blocked"
    assert exc.value.exit_code == 12


def test_provider_response_requires_session_provider(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")

    with pytest.raises(ConfigError) as exc:
        ingest(source, start=paths.inbox, provider="mock", provider_response=paths.cache / "response.json")

    assert exc.value.code == "invalid_provider_response_provider"


def test_session_provider_request_writes_persisted_envelope(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")

    summary = provider_request(
        source,
        start=paths.inbox,
        clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)),
    )
    request_path = paths.meetings_root / summary.details["request_path"]
    response_path = paths.meetings_root / summary.details["expected_response_path"]
    request_payload = json.loads(request_path.read_text(encoding="utf-8"))

    assert summary.status == "success"
    assert summary.meeting_id.startswith("mtg-20260703-")
    assert request_payload["handoff_type"] == "provider_request"
    assert request_payload["schema_version"] == "1.1"
    assert request_payload["provider_contract"] == "meeting-ingest-provider-response-v1"
    assert request_payload["meeting_id"] == summary.meeting_id
    assert request_payload["source_sha256"] == summary.source_sha256
    assert request_payload["quality"] == "balanced"
    assert request_payload["output_mode"] == "summary-plus-verbatim"
    assert request_payload["normalized_transcript"] == "Ken: Hello\n"
    response_schema = request_payload["response_contract"]["json_schema"]
    assert request_payload["response_contract"]["identity_copy_fields"] == [
        "meeting_id",
        "ingest_run_id",
        "source_sha256",
        "normalized_transcript_sha256",
        "runtime_provenance_sha256",
    ]
    assert request_payload["runtime_provenance_schema"] == "1.0"
    assert request_payload["runtime_provenance"] == summary.runtime_provenance
    assert request_payload["runtime_provenance_sha256"].startswith("sha256:")
    assert response_schema["properties"]["meeting_id"] == {"const": summary.meeting_id}
    assert response_schema["properties"]["provider"]["properties"]["model_alias"] == {"const": "balanced"}
    risk_schema = response_schema["properties"]["response"]["properties"]["dependencies_risks"]["items"]
    assert "owner_related_party" in risk_schema["required"]
    signal_schema = response_schema["properties"]["response"]["properties"]["communication_signals"]["items"]
    assert "stakeholder_name" in signal_schema["required"]
    assert signal_schema["not"] == {
        "anyOf": [
            {"required": ["signal_id"]},
            {"required": ["meeting_id"]},
            {"required": ["ingest_run_id"]},
            {"required": ["recorded_at"]},
            {"required": ["effective_at"]},
            {"required": ["schema_version"]},
        ]
    }
    assert set(response_schema["properties"]["response"]["required"]) == {
        "title",
        "tl_dr",
        "meeting_type",
        "attendees",
        "topics",
        "decisions",
        "action_items",
        "stakeholder_asks",
        "dependencies_risks",
        "communication_signals",
        "open_questions",
        "cross_references",
    }
    assert summary.details["source"] == {
        "path": "_inbox/2026-07-03-team-sync.txt",
        "source_type": "txt",
    }
    assert summary.details["provider_request"] == {
        "status": "ready",
        "path": summary.details["request_path"],
        "contract": "meeting-ingest-provider-response-v1",
    }
    assert summary.details["provider_response"] == {
        "status": "pending",
        "path": summary.details["expected_response_path"],
    }
    assert summary.details["normalized_transcript_sha256"] == request_payload["normalized_transcript_sha256"]
    assert summary.details["effective_date"] == {
        "value": "2026-07-03",
        "confidence": "high",
        "source": "filename",
    }
    assert response_path.parent.is_dir()
    assert read_records(paths.ledger) == []


def test_development_response_contract_preserves_escaped_override_reason() -> None:
    request = {
        "quality": "balanced",
        "meeting_id": "meeting",
        "ingest_run_id": "run",
        "source_sha256": "source",
        "normalized_transcript_sha256": "transcript",
        "runtime_provenance_sha256": "sha256:" + "1" * 64,
        "runtime_provenance": {
            "runtime_mode": "development",
            "development_override_reason": "developer's handoff",
        },
    }

    contract = response_contract_for_request(request)

    assert contract["preflight_command"] == (
        "meeting-ingest validate-response RESPONSE --source SOURCE "
        "--development-override 'developer'\"'\"'s handoff' --json"
    )


def test_session_provider_response_completes_full_ingest_and_cleans_cache(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    request_summary = provider_request(
        source,
        start=paths.inbox,
        clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)),
    )
    request_path = paths.meetings_root / request_summary.details["request_path"]
    response_path = paths.meetings_root / request_summary.details["expected_response_path"]
    _write_session_response(request_path, response_path, title="Session Team Sync")

    summary = ingest(
        source,
        start=paths.inbox,
        provider="session",
        provider_response=response_path,
        clock=FrozenClock(datetime(2026, 7, 3, 12, 5, tzinfo=UTC)),
    )
    artifact = paths.meetings_root / summary.artifacts[0]["path"]
    markdown = artifact.read_text(encoding="utf-8")
    records = read_records(paths.ledger)

    assert summary.status == "success"
    assert summary.meeting_id == request_summary.meeting_id
    assert summary.ingest_run_id == request_summary.ingest_run_id
    assert summary.details["provider"] == "session"
    assert summary.details["provider_host"] == "codex"
    assert "provider: session" in markdown
    assert "provider_host: codex" in markdown
    assert "model_id: codex-session" in markdown
    assert records[-1]["artifacts"]["summary-plus-verbatim"]["provider"] == "session"
    assert records[-1]["artifacts"]["summary-plus-verbatim"]["provider_host"] == "codex"
    assert [record["event"] for record in records] == ["primary_artifacts_ready", "ingest_completed"]
    assert not request_path.exists()
    assert not response_path.exists()
    assert not source.exists()
    assert (paths.inbox_done / source.name).exists()


def test_session_provider_rejects_runtime_update_and_retries_under_original_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    request_summary = provider_request(source, start=paths.inbox)
    request_path = paths.meetings_root / request_summary.details["request_path"]
    response_path = paths.meetings_root / request_summary.details["expected_response_path"]
    _write_session_response(request_path, response_path)

    original = approved_runtime_inspection(tmp_path)
    updated = replace(
        original,
        build=replace(original.build, build_id="meeting-ingest-test-updated"),
        runtime_provenance=replace(original.runtime_provenance, build_id="meeting-ingest-test-updated"),
    )
    monkeypatch.setattr("meeting_ingest.readiness._RUNTIME_INSPECTOR", lambda _: updated)

    with pytest.raises(MeetingIngestError) as exc:
        ingest(source, start=paths.inbox, provider="session", provider_response=response_path)

    assert exc.value.code == "runtime_handoff_mismatch"
    assert exc.value.exit_code == EXIT_RUNTIME_READINESS
    assert request_path.exists()
    assert response_path.exists()
    assert source.exists()
    assert read_records(paths.ledger) == []

    monkeypatch.setattr("meeting_ingest.readiness._RUNTIME_INSPECTOR", lambda _: original)
    summary = ingest(source, start=paths.inbox, provider="session", provider_response=response_path)

    assert summary.status == "success"
    assert not request_path.exists()
    assert not response_path.exists()


def test_session_provider_can_abandon_mismatch_and_remint_under_updated_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    original_summary = provider_request(
        source,
        start=paths.inbox,
        clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)),
    )
    original_request = paths.meetings_root / original_summary.details["request_path"]
    original_response = paths.meetings_root / original_summary.details["expected_response_path"]
    _write_session_response(original_request, original_response)

    original = approved_runtime_inspection(tmp_path)
    updated = replace(
        original,
        build=replace(original.build, build_id="meeting-ingest-test-updated"),
        runtime_provenance=replace(original.runtime_provenance, build_id="meeting-ingest-test-updated"),
    )
    monkeypatch.setattr("meeting_ingest.readiness._RUNTIME_INSPECTOR", lambda _: updated)
    with pytest.raises(MeetingIngestError) as exc:
        ingest(source, start=paths.inbox, provider="session", provider_response=original_response)
    assert exc.value.code == "runtime_handoff_mismatch"

    original_request.unlink()
    original_response.unlink()
    fresh_summary = provider_request(
        source,
        start=paths.inbox,
        clock=FrozenClock(datetime(2026, 7, 3, 12, 5, tzinfo=UTC)),
    )
    fresh_request = paths.meetings_root / fresh_summary.details["request_path"]
    fresh_response = paths.meetings_root / fresh_summary.details["expected_response_path"]
    _write_session_response(fresh_request, fresh_response)

    summary = ingest(source, start=paths.inbox, provider="session", provider_response=fresh_response)

    assert summary.status == "success"
    assert summary.runtime_provenance["build_id"] == "meeting-ingest-test-updated"
    assert fresh_summary.ingest_run_id != original_summary.ingest_run_id


@pytest.mark.parametrize(
    "mutation",
    [
        "provenance_payload",
        "provenance_fingerprint",
        "response_echo",
        "legacy_handoff",
    ],
)
def test_session_provider_rejects_invalid_runtime_binding(
    tmp_path: Path, mutation: str
) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    request_summary = provider_request(source, start=paths.inbox)
    request_path = paths.meetings_root / request_summary.details["request_path"]
    response_path = paths.meetings_root / request_summary.details["expected_response_path"]
    _write_session_response(request_path, response_path)
    request_payload = json.loads(request_path.read_text(encoding="utf-8"))
    response_payload = json.loads(response_path.read_text(encoding="utf-8"))

    if mutation == "provenance_payload":
        request_payload["runtime_provenance"]["build_id"] = "tampered"
    elif mutation == "provenance_fingerprint":
        request_payload["runtime_provenance_sha256"] = "sha256:" + "0" * 64
        response_payload["runtime_provenance_sha256"] = "sha256:" + "0" * 64
    elif mutation == "response_echo":
        response_payload["runtime_provenance_sha256"] = "sha256:" + "0" * 64
    else:
        request_payload["schema_version"] = "1.0"
        response_payload["schema_version"] = "1.0"
        request_payload.pop("runtime_provenance_schema")
        request_payload.pop("runtime_provenance_sha256")
        request_payload.pop("runtime_provenance")
        response_payload.pop("runtime_provenance_sha256")

    request_path.write_text(json.dumps(request_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    response_path.write_text(json.dumps(response_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(MeetingIngestError) as exc:
        ingest(source, start=paths.inbox, provider="session", provider_response=response_path)

    assert exc.value.code == "runtime_handoff_mismatch"
    assert exc.value.exit_code == EXIT_RUNTIME_READINESS
    assert request_path.exists()
    assert response_path.exists()
    assert source.exists()
    assert read_records(paths.ledger) == []


def test_session_provider_rejects_development_tree_or_override_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    base = approved_runtime_inspection(tmp_path)
    editable_finding = ReadinessFinding(
        code="runtime_editable_blocked",
        category="runtime",
        severity="blocker",
        message="Editable runtime.",
        path=str(tmp_path),
        remediation="Use an override.",
    )
    original = replace(
        base,
        install=replace(base.install, mode="editable"),
        runtime_mode="development",
        findings=(editable_finding,),
        runtime_provenance=replace(
            base.runtime_provenance,
            source_commit="c" * 40,
            source_tree_sha256="sha256:" + "1" * 64,
            install_mode="editable",
            runtime_mode="development",
        ),
    )
    monkeypatch.setattr("meeting_ingest.readiness._RUNTIME_INSPECTOR", lambda _: original)
    override = DevelopmentOverride("session handoff test")
    request_summary = provider_request(source, start=paths.inbox, development_override=override)
    request_path = paths.meetings_root / request_summary.details["request_path"]
    response_path = paths.meetings_root / request_summary.details["expected_response_path"]
    _write_session_response(request_path, response_path)

    changed_tree = replace(
        original,
        runtime_provenance=replace(original.runtime_provenance, source_tree_sha256="sha256:" + "2" * 64),
    )
    monkeypatch.setattr("meeting_ingest.readiness._RUNTIME_INSPECTOR", lambda _: changed_tree)
    with pytest.raises(MeetingIngestError) as tree_exc:
        ingest(
            source,
            start=paths.inbox,
            provider="session",
            provider_response=response_path,
            development_override=override,
        )
    assert tree_exc.value.code == "runtime_handoff_mismatch"

    monkeypatch.setattr("meeting_ingest.readiness._RUNTIME_INSPECTOR", lambda _: original)
    with pytest.raises(MeetingIngestError) as reason_exc:
        ingest(
            source,
            start=paths.inbox,
            provider="session",
            provider_response=response_path,
            development_override=DevelopmentOverride("different reason"),
        )
    assert reason_exc.value.code == "runtime_handoff_mismatch"
    assert request_path.exists()
    assert response_path.exists()
    assert read_records(paths.ledger) == []


def test_session_provider_response_identity_mismatch_records_failure_without_side_effects(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    request_summary = provider_request(source, start=paths.inbox)
    request_path = paths.meetings_root / request_summary.details["request_path"]
    response_path = paths.meetings_root / request_summary.details["expected_response_path"]
    _write_session_response(request_path, response_path, source_sha256="wrong")

    with pytest.raises(MeetingIngestError) as exc:
        ingest(source, start=paths.inbox, provider="session", provider_response=response_path)
    records = read_records(paths.ledger)

    assert exc.value.phase == "provider_validation"
    assert exc.value.exit_code == EXIT_PROVIDER_VALIDATION
    assert [record["event"] for record in records] == ["ingest_failed"]
    assert records[-1]["meeting_id"] == request_summary.meeting_id
    assert records[-1]["ingest_run_id"] == request_summary.ingest_run_id
    assert source.exists()
    assert request_path.exists()
    assert response_path.exists()
    assert list(paths.meetings_root.glob("*.md")) == []
    assert list(paths.processed.iterdir()) == []


def test_session_provider_malformed_payload_records_validation_failure(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    request_summary = provider_request(source, start=paths.inbox)
    request_path = paths.meetings_root / request_summary.details["request_path"]
    response_path = paths.meetings_root / request_summary.details["expected_response_path"]
    _write_session_response(
        request_path,
        response_path,
        response_overrides={
            "topics": [{"id": 1, "topic": "Design", "summary": "Discussed design.", "evidence": "Ken: Hello"}]
        },
    )

    with pytest.raises(MeetingIngestError) as exc:
        ingest(source, start=paths.inbox, provider="session", provider_response=response_path)
    records = read_records(paths.ledger)

    assert exc.value.phase == "provider_validation"
    assert exc.value.exit_code == EXIT_PROVIDER_VALIDATION
    assert [record["event"] for record in records] == ["ingest_failed"]
    assert records[-1]["meeting_id"] == request_summary.meeting_id
    assert source.exists()
    assert list(paths.meetings_root.glob("*.md")) == []
    assert list(paths.processed.iterdir()) == []


def test_session_provider_missing_response_records_provider_failure_with_request_identity(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    request_summary = provider_request(source, start=paths.inbox)
    response_path = paths.meetings_root / request_summary.details["expected_response_path"]

    with pytest.raises(MeetingIngestError) as exc:
        ingest(source, start=paths.inbox, provider="session", provider_response=response_path)
    records = read_records(paths.ledger)

    assert exc.value.phase == "provider"
    assert exc.value.exit_code == EXIT_PROVIDER_FAILURE
    assert [record["event"] for record in records] == ["ingest_failed"]
    assert records[-1]["meeting_id"] == request_summary.meeting_id
    assert records[-1]["ingest_run_id"] == request_summary.ingest_run_id
    assert source.exists()


def test_session_provider_response_directory_records_provider_failure(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    provider_request(source, start=paths.inbox)

    with pytest.raises(MeetingIngestError) as exc:
        ingest(source, start=paths.inbox, provider="session", provider_response=paths.cache)
    records = read_records(paths.ledger)

    assert exc.value.phase == "provider"
    assert exc.value.exit_code == EXIT_PROVIDER_FAILURE
    assert [record["event"] for record in records] == ["ingest_failed"]
    assert source.exists()


def test_session_provider_missing_persisted_request_records_validation_failure(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    request_summary = provider_request(source, start=paths.inbox)
    request_path = paths.meetings_root / request_summary.details["request_path"]
    response_path = paths.meetings_root / request_summary.details["expected_response_path"]
    _write_session_response(request_path, response_path)
    request_path.unlink()

    with pytest.raises(MeetingIngestError) as exc:
        ingest(source, start=paths.inbox, provider="session", provider_response=response_path)
    records = read_records(paths.ledger)

    assert exc.value.phase == "provider_validation"
    assert exc.value.exit_code == EXIT_PROVIDER_VALIDATION
    assert [record["event"] for record in records] == ["ingest_failed"]
    assert source.exists()


def test_session_provider_rejects_path_traversal_ingest_run_id(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    request_summary = provider_request(source, start=paths.inbox)
    request_path = paths.meetings_root / request_summary.details["request_path"]
    response_path = paths.meetings_root / request_summary.details["expected_response_path"]
    _write_session_response(request_path, response_path, envelope_overrides={"ingest_run_id": "../../../outside"})

    with pytest.raises(MeetingIngestError) as exc:
        ingest(source, start=paths.inbox, provider="session", provider_response=response_path)

    assert exc.value.phase == "provider_validation"
    assert exc.value.exit_code == EXIT_PROVIDER_VALIDATION
    assert read_records(paths.ledger)[-1]["event"] == "ingest_failed"


def test_session_provider_rejects_path_traversal_ingest_run_id_even_when_target_exists(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    request_summary = provider_request(source, start=paths.inbox)
    request_path = paths.meetings_root / request_summary.details["request_path"]
    response_path = paths.meetings_root / request_summary.details["expected_response_path"]
    escaped_run_id = "../../outside/escaped"
    escaped_request = paths.cache / "provider-requests" / f"{escaped_run_id}.request.json"
    escaped_request.parent.mkdir(parents=True)
    escaped_request_payload = json.loads(request_path.read_text(encoding="utf-8"))
    escaped_request_payload["ingest_run_id"] = escaped_run_id
    escaped_request.write_text(json.dumps(escaped_request_payload), encoding="utf-8")
    _write_session_response(request_path, response_path, envelope_overrides={"ingest_run_id": escaped_run_id})

    with pytest.raises(MeetingIngestError) as exc:
        ingest(source, start=paths.inbox, provider="session", provider_response=response_path)

    assert exc.value.phase == "provider_validation"
    assert exc.value.exit_code == EXIT_PROVIDER_VALIDATION
    assert escaped_request.exists()
    assert read_records(paths.ledger)[-1]["event"] == "ingest_failed"


def test_session_provider_rejects_tampered_request_transcript_hash(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    request_summary = provider_request(source, start=paths.inbox)
    request_path = paths.meetings_root / request_summary.details["request_path"]
    response_path = paths.meetings_root / request_summary.details["expected_response_path"]
    _write_session_response(request_path, response_path)
    request_payload = json.loads(request_path.read_text(encoding="utf-8"))
    request_payload["normalized_transcript"] = "Tampered"
    request_path.write_text(json.dumps(request_payload), encoding="utf-8")

    with pytest.raises(MeetingIngestError) as exc:
        ingest(source, start=paths.inbox, provider="session", provider_response=response_path)

    assert exc.value.phase == "provider_validation"
    assert exc.value.exit_code == EXIT_PROVIDER_VALIDATION
    assert read_records(paths.ledger)[-1]["event"] == "ingest_failed"


def test_session_provider_rejects_unsupported_request_output_mode(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    request_summary = provider_request(source, start=paths.inbox)
    request_path = paths.meetings_root / request_summary.details["request_path"]
    response_path = paths.meetings_root / request_summary.details["expected_response_path"]
    _write_session_response(request_path, response_path)
    request_payload = json.loads(request_path.read_text(encoding="utf-8"))
    request_payload["output_mode"] = "summary"
    request_path.write_text(json.dumps(request_payload), encoding="utf-8")

    with pytest.raises(MeetingIngestError) as exc:
        ingest(source, start=paths.inbox, provider="session", provider_response=response_path)

    assert exc.value.phase == "provider_validation"
    assert exc.value.exit_code == EXIT_PROVIDER_VALIDATION


def test_session_provider_rejects_model_alias_mismatch(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    request_summary = provider_request(source, start=paths.inbox)
    request_path = paths.meetings_root / request_summary.details["request_path"]
    response_path = paths.meetings_root / request_summary.details["expected_response_path"]
    _write_session_response(request_path, response_path, provider_overrides={"model_alias": "deep"})

    with pytest.raises(MeetingIngestError) as exc:
        ingest(source, start=paths.inbox, provider="session", provider_response=response_path)

    assert exc.value.phase == "provider_validation"
    assert exc.value.exit_code == EXIT_PROVIDER_VALIDATION


def test_session_provider_request_file_as_response_records_validation_failure(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    request_summary = provider_request(source, start=paths.inbox)
    request_path = paths.meetings_root / request_summary.details["request_path"]

    with pytest.raises(MeetingIngestError) as exc:
        ingest(source, start=paths.inbox, provider="session", provider_response=request_path)

    assert exc.value.phase == "provider_validation"
    assert exc.value.exit_code == EXIT_PROVIDER_VALIDATION
    assert read_records(paths.ledger)[-1]["event"] == "ingest_failed"


def test_session_provider_model_id_falls_back_to_host_session(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    request_summary = provider_request(source, start=paths.inbox)
    request_path = paths.meetings_root / request_summary.details["request_path"]
    response_path = paths.meetings_root / request_summary.details["expected_response_path"]
    _write_session_response(request_path, response_path, provider_overrides={"model_id": None})

    summary = ingest(source, start=paths.inbox, provider="session", provider_response=response_path)
    artifact = paths.meetings_root / summary.artifacts[0]["path"]

    assert "model_id: codex-session" in artifact.read_text(encoding="utf-8")


def test_session_provider_phase2_warns_on_cli_quality_mismatch(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    request_summary = provider_request(source, start=paths.inbox, quality="balanced")
    request_path = paths.meetings_root / request_summary.details["request_path"]
    response_path = paths.meetings_root / request_summary.details["expected_response_path"]
    _write_session_response(request_path, response_path)

    summary = ingest(source, start=paths.inbox, provider="session", quality="fast", provider_response=response_path)
    artifact = paths.meetings_root / summary.artifacts[0]["path"]

    assert summary.details["quality"] == "balanced"
    assert summary.warnings == [
        "phase 2 ignored CLI quality 'fast'; using persisted provider request quality 'balanced'"
    ]
    assert "model_alias: balanced" in artifact.read_text(encoding="utf-8")


def test_session_provider_malformed_arbitrary_response_path_preserves_provider_failure(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    provider_request(source, start=paths.inbox)
    response_path = tmp_path / "my response.response.json"
    response_path.write_text("{not-json\n", encoding="utf-8")

    with pytest.raises(MeetingIngestError) as exc:
        ingest(source, start=paths.inbox, provider="session", provider_response=response_path)
    records = read_records(paths.ledger)

    assert exc.value.phase == "provider"
    assert exc.value.exit_code == EXIT_PROVIDER_FAILURE
    assert [record["event"] for record in records] == ["ingest_failed"]
    assert records[-1]["meeting_id"] is None
    assert records[-1]["ingest_run_id"] is None
    assert source.exists()


def test_provider_request_duplicate_source_returns_no_op_without_request_file(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    first = ingest(source, start=paths.inbox)
    redrop = paths.inbox / "2026-07-03-team-sync.txt"
    redrop.write_text("Ken: Hello\n", encoding="utf-8")

    summary = provider_request(redrop, start=paths.inbox)

    assert summary.status == "no_op"
    assert summary.meeting_id == first.meeting_id
    assert not list((paths.cache / "provider-requests").glob("*.json"))


def test_ingest_inbox_session_provider_creates_batch_provider_requests(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")

    summary = ingest_inbox(
        tmp_path,
        provider="session",
        clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)),
    )
    result = summary.details["results"][0]
    result_details = result["details"]

    assert summary.status == "success"
    assert summary.details["provider"] == "session"
    assert summary.details["phase"] == "provider_request"
    assert summary.details["processed"] == 1
    assert summary.details["pending_provider_responses"] == 1
    assert summary.details["succeeded"] == 1
    assert summary.details["no_ops"] == 0
    assert result["source"] == "_inbox/2026-07-03-team-sync.txt"
    assert result["status"] == "pending_provider_response"
    assert result["meeting_id"] == "mtg-20260703-28e2f332"
    assert result["ingest_run_id"].startswith("ingest-20260703-20260703T120000Z-")
    assert result_details["command"] == "provider-request"
    assert result_details["provider"] == "session"
    assert result_details["provider_request"]["status"] == "ready"
    assert result_details["provider_response"]["status"] == "pending"
    assert (paths.meetings_root / result_details["request_path"]).exists()
    assert not (paths.meetings_root / result_details["expected_response_path"]).exists()
    assert read_records(paths.ledger) == []
    assert source.exists()

    repeated = ingest_inbox(
        tmp_path,
        provider="session",
        clock=FrozenClock(datetime(2026, 7, 3, 12, 1, tzinfo=UTC)),
    )
    assert repeated.exit_code == 0
    assert repeated.details["pending_provider_responses"] == 1


def test_ingest_inbox_session_provider_reports_mixed_batch_outcomes(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    already = paths.inbox / "2026-07-03-already.txt"
    already.write_text("Ken: Already handled\n", encoding="utf-8")
    first = ingest(
        already,
        start=paths.inbox,
        clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)),
    )
    already.write_text("Ken: Already handled\n", encoding="utf-8")
    fresh = paths.inbox / "2026-07-03-fresh.txt"
    fresh.write_text("Ken: Fresh handoff\n", encoding="utf-8")
    unsupported = paths.inbox / "2026-07-03-unsupported.pdf"
    unsupported.write_text("not supported", encoding="utf-8")

    summary = ingest_inbox(
        tmp_path,
        provider="session",
        clock=FrozenClock(datetime(2026, 7, 3, 12, 5, tzinfo=UTC)),
    )
    results = {result["source"]: result for result in summary.details["results"]}
    records = read_records(paths.ledger)

    assert summary.status == "partial_success"
    assert summary.exit_code == EXIT_GENERAL_FAILURE
    assert summary.details["processed"] == 3
    assert summary.details["pending_provider_responses"] == 1
    assert summary.details["succeeded"] == 2
    assert summary.details["no_ops"] == 1
    assert summary.details["failed"] == 1
    assert results["_inbox/2026-07-03-already.txt"]["status"] == "no_op"
    assert results["_inbox/2026-07-03-already.txt"]["meeting_id"] == first.meeting_id
    assert results["_inbox/2026-07-03-fresh.txt"]["status"] == "pending_provider_response"
    assert results["_inbox/2026-07-03-fresh.txt"]["details"]["provider_request"]["status"] == "ready"
    assert results["_inbox/2026-07-03-unsupported.pdf"]["status"] == "failed"
    assert results["_inbox/2026-07-03-unsupported.pdf"]["exit_code"] == 3
    assert summary.errors == [
        {
            "source": "_inbox/2026-07-03-unsupported.pdf",
            "phase": "source_read",
            "code": "unsupported_source_format",
            "message": f"Unsupported source format: {unsupported.resolve()}",
            "recoverable": False,
            "details": {"path": str(unsupported.resolve())},
        }
    ]
    assert [record["event"] for record in records] == [
        "primary_artifacts_ready",
        "ingest_completed",
        "reconcile_repaired",
        "source_quarantined",
    ]
    assert records[-1]["quarantine"]["status"] == "quarantined"
    assert not already.exists()
    assert fresh.exists()
    assert not unsupported.exists()


def test_session_provider_stale_response_returns_no_op_without_consuming_response(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    first = ingest(source, start=paths.inbox, clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)))
    redrop = paths.inbox / "2026-07-03-team-sync.txt"
    redrop.write_text("Ken: Hello\n", encoding="utf-8")
    request_path = paths.cache / "provider-requests" / "stale.request.json"
    response_path = paths.cache / "provider-responses" / "stale.response.json"
    request_path.parent.mkdir(parents=True)
    response_path.parent.mkdir(parents=True)
    response_path.write_text("{not-json\n", encoding="utf-8")

    summary = ingest(redrop, start=paths.inbox, provider="session", provider_response=response_path)

    assert summary.status == "no_op"
    assert summary.meeting_id == first.meeting_id
    assert response_path.exists()
    assert not redrop.exists()


def test_cli_session_provider_response_returns_exit_6_for_validation_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    request_summary = provider_request(source, start=paths.inbox)
    request_path = paths.meetings_root / request_summary.details["request_path"]
    response_path = paths.meetings_root / request_summary.details["expected_response_path"]
    _write_session_response(request_path, response_path, title="")
    monkeypatch.chdir(tmp_path)

    exit_code = main(["ingest", str(source), "--provider", "session", "--provider-response", str(response_path), "--json"])
    captured = capsys.readouterr()
    summary = json.loads(captured.out)

    assert exit_code == EXIT_PROVIDER_VALIDATION
    assert summary["status"] == "failed"
    assert summary["errors"][0]["phase"] == "provider_validation"
    assert summary["errors"][0]["code"] == "invalid_provider_output"


def test_cli_validate_response_preflight_succeeds_without_side_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    request_summary = provider_request(source, start=paths.inbox)
    request_path = paths.meetings_root / request_summary.details["request_path"]
    response_path = paths.meetings_root / request_summary.details["expected_response_path"]
    _write_session_response(request_path, response_path)
    monkeypatch.chdir(tmp_path)

    exit_code = main(
        ["validate-response", str(response_path), "--source", str(source), "--root", str(tmp_path), "--json"]
    )
    summary = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert summary["status"] == "success"
    assert summary["command"] == "validate-response"
    assert summary["provider_response"]["status"] == "valid"
    assert summary["side_effects"] == "none"
    assert request_path.exists()
    assert response_path.exists()
    assert source.exists()
    assert read_records(paths.ledger) == []


def test_cli_validate_response_rejects_runtime_mismatch_with_current_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    request_summary = provider_request(source, start=paths.inbox)
    request_path = paths.meetings_root / request_summary.details["request_path"]
    response_path = paths.meetings_root / request_summary.details["expected_response_path"]
    _write_session_response(request_path, response_path)
    current = approved_runtime_inspection(tmp_path)
    changed = replace(
        current,
        build=replace(current.build, build_id="meeting-ingest-test-updated"),
        runtime_provenance=replace(current.runtime_provenance, build_id="meeting-ingest-test-updated"),
    )
    monkeypatch.setattr("meeting_ingest.readiness._RUNTIME_INSPECTOR", lambda _: changed)

    exit_code = main(
        ["validate-response", str(response_path), "--source", str(source), "--root", str(tmp_path), "--json"]
    )
    summary = json.loads(capsys.readouterr().out)

    assert exit_code == EXIT_RUNTIME_READINESS
    assert summary["errors"][0]["code"] == "runtime_handoff_mismatch"
    assert summary["runtime_provenance"]["build_id"] == "meeting-ingest-test-updated"
    assert request_path.exists()
    assert response_path.exists()
    assert source.exists()
    assert read_records(paths.ledger) == []


def test_cli_validate_response_accepts_matching_development_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    development = _development_runtime_inspection(tmp_path)
    monkeypatch.setattr("meeting_ingest.readiness._RUNTIME_INSPECTOR", lambda _: development)
    reason = "validate development handoff"
    request_summary = provider_request(
        source,
        start=paths.inbox,
        development_override=DevelopmentOverride(reason),
    )
    request_path = paths.meetings_root / request_summary.details["request_path"]
    response_path = paths.meetings_root / request_summary.details["expected_response_path"]
    _write_session_response(request_path, response_path)

    exit_code = main(
        [
            "validate-response",
            str(response_path),
            "--source",
            str(source),
            "--root",
            str(tmp_path),
            "--development-override",
            reason,
            "--json",
        ]
    )
    summary = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert summary["status"] == "success"
    assert summary["provider_response"]["status"] == "valid"
    assert summary["runtime_readiness"]["verdict"] == "development_override"
    assert summary["runtime_provenance"]["development_override_reason"] == reason
    assert request_path.exists()
    assert response_path.exists()
    assert source.exists()
    assert read_records(paths.ledger) == []


def test_cli_validate_response_blocks_valid_payload_when_project_readiness_is_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    request_summary = provider_request(source, start=paths.inbox)
    request_path = paths.meetings_root / request_summary.details["request_path"]
    response_path = paths.meetings_root / request_summary.details["expected_response_path"]
    _write_session_response(request_path, response_path)
    config_text = paths.config_path.read_text(encoding="utf-8")
    paths.config_path.write_text(
        config_text.replace("allow_session_provider = true", "allow_session_provider = false"),
        encoding="utf-8",
    )

    exit_code = main(
        ["validate-response", str(response_path), "--source", str(source), "--root", str(tmp_path), "--json"]
    )
    summary = json.loads(capsys.readouterr().out)

    assert exit_code == EXIT_RUNTIME_READINESS
    assert summary["status"] == "blocked"
    assert summary["provider_response"]["status"] == "valid"
    assert summary["runtime_readiness"]["verdict"] == "blocked"
    assert any(finding["code"] == "readiness_privacy_blocked" for finding in summary["runtime_readiness"]["findings"])
    assert request_path.exists()
    assert response_path.exists()
    assert source.exists()
    assert read_records(paths.ledger) == []


def test_cli_validate_response_reports_all_payload_errors_without_ledger_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    request_summary = provider_request(source, start=paths.inbox)
    request_path = paths.meetings_root / request_summary.details["request_path"]
    response_path = paths.meetings_root / request_summary.details["expected_response_path"]
    _write_session_response(
        request_path,
        response_path,
        response_overrides={
            "topics": [{"id": "T1"}],
            "dependencies_risks": [{"id": "R1", "type": "risk"}],
        },
    )
    monkeypatch.chdir(tmp_path)

    exit_code = main(
        ["validate-response", str(response_path), "--source", str(source), "--root", str(tmp_path), "--json"]
    )
    summary = json.loads(capsys.readouterr().out)

    assert exit_code == EXIT_PROVIDER_VALIDATION
    issues = summary["errors"][0]["details"]["issues"]
    assert "response.topics[0].topic is required and must be a string." in issues
    assert "response.dependencies_risks[0].owner_related_party is required and must be a string." in issues
    assert read_records(paths.ledger) == []


def test_cli_validate_response_reports_structured_source_read_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    request_summary = provider_request(source, start=paths.inbox)
    request_path = paths.meetings_root / request_summary.details["request_path"]
    response_path = paths.meetings_root / request_summary.details["expected_response_path"]
    _write_session_response(request_path, response_path)
    missing_source = paths.inbox / "missing.txt"
    monkeypatch.chdir(tmp_path)

    exit_code = main(
        [
            "validate-response",
            str(response_path),
            "--source",
            str(missing_source),
            "--root",
            str(tmp_path),
            "--json",
        ]
    )
    summary = json.loads(capsys.readouterr().out)

    assert exit_code == 4
    assert summary["status"] == "failed"
    assert summary["errors"][0]["phase"] == "source_read"
    assert summary["errors"][0]["code"] == "source_extraction_failed"
    assert summary["errors"][0]["details"]["path"] == str(missing_source)
    assert read_records(paths.ledger) == []


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
            "source_sha256": "0bee0730a4f92127e529b51401c3d53fee2ee323dc5b0cdc767c8a7c541d0be1",
            "meeting_id": None,
            "reason": "source_not_in_ledger",
        }
    ]
    assert retry_source.exists()


def test_reconcile_skipped_failed_record_reports_known_meeting_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")

    class FailingProvider:
        name = "mock"
        model_id = "none"

        def extract(self, request: object) -> ProviderResponse:
            raise RuntimeError("boom")

    monkeypatch.setattr(pipeline_module, "get_provider", lambda provider: FailingProvider())

    with pytest.raises(MeetingIngestError):
        ingest(source, start=paths.inbox, clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)))

    summary = reconcile(tmp_path)

    assert summary.details["repaired"] == []
    assert summary.details["skipped"] == [
        {
            "path": "_inbox/2026-07-03-team-sync.txt",
            "source_sha256": "28e2f3324abc0594006d4788e3913a97960727e0e1ebdd2e3e4d831b1f50c8e3",
            "meeting_id": "mtg-20260703-28e2f332",
            "reason": "source_not_in_ledger",
        }
    ]


def _allow_session_provider(config_path: Path) -> None:
    config_text = config_path.read_text(encoding="utf-8")
    config_path.write_text(config_text.replace("allow_session_provider = false", "allow_session_provider = true"), encoding="utf-8")


def _append_legacy_record(ledger_path: Path, source_sha256: str) -> None:
    with ledger_path.open("a", encoding="utf-8") as ledger:
        ledger.write(
            json.dumps(
                {
                    "source_sha256": source_sha256,
                    "meeting_id": "2026-05-04-generic-d01638d8",
                    "ingest_run_id": "20260518T030615Z",
                }
            )
            + "\n"
        )


def _file_snapshot(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def _development_runtime_inspection(root: Path):
    base = approved_runtime_inspection(root)
    finding = ReadinessFinding(
        code="runtime_editable_blocked",
        category="runtime",
        severity="blocker",
        message="Editable runtime.",
        path=str(root),
        remediation="Use an override.",
    )
    return replace(
        base,
        install=replace(base.install, mode="editable"),
        runtime_mode="development",
        findings=(finding,),
        runtime_provenance=replace(
            base.runtime_provenance,
            source_commit="c" * 40,
            source_tree_sha256="sha256:" + "1" * 64,
            install_mode="editable",
            runtime_mode="development",
        ),
    )


def _write_session_response(
    request_path: Path,
    response_path: Path,
    *,
    title: str = "Session Team Sync",
    source_sha256: str | None = None,
    envelope_overrides: dict[str, object] | None = None,
    provider_overrides: dict[str, object] | None = None,
    response_overrides: dict[str, object] | None = None,
) -> None:
    request_payload = json.loads(request_path.read_text(encoding="utf-8"))
    provider_payload = {
        "name": "session",
        "host": "codex",
        "model_alias": request_payload["quality"],
        "model_id": "codex-session",
        "generated_at": "2026-07-03T12:01:00Z",
    }
    if provider_overrides:
        provider_payload.update(provider_overrides)
    response_payload = {
        "title": title,
        "tl_dr": "Session summary.",
        "meeting_type": "team-sync",
        "attendees": [],
        "topics": [],
        "decisions": [],
        "action_items": [],
        "stakeholder_asks": [],
        "dependencies_risks": [],
        "communication_signals": [],
        "open_questions": [],
        "cross_references": [],
    }
    if response_overrides:
        response_payload.update(response_overrides)
    envelope = {
        "schema_version": "1.1",
        "handoff_type": "provider_response",
        "provider_contract": "meeting-ingest-provider-response-v1",
        "meeting_id": request_payload["meeting_id"],
        "ingest_run_id": request_payload["ingest_run_id"],
        "source_sha256": source_sha256 or request_payload["source_sha256"],
        "normalized_transcript_sha256": request_payload["normalized_transcript_sha256"],
        "runtime_provenance_sha256": request_payload["runtime_provenance_sha256"],
        "provider": provider_payload,
        "response": response_payload,
    }
    if envelope_overrides:
        envelope.update(envelope_overrides)
    response_path.write_text(
        json.dumps(envelope, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
