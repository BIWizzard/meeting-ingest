import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from meeting_ingest.clock import FrozenClock
from meeting_ingest.cli import main
from meeting_ingest.errors import MeetingIngestError
from meeting_ingest.ledger import read_records
from meeting_ingest.paths import init_project
from meeting_ingest.pipeline import provider_request
from meeting_ingest.session_inbox import process_session_inbox


def test_session_inbox_without_extractor_reports_pending_response(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")

    summary = process_session_inbox(
        tmp_path,
        clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)),
    )
    result = summary.details["results"][0]

    assert summary.status == "success"
    assert summary.details["command"] == "session-inbox"
    assert summary.details["completed"] == 0
    assert summary.details["pending_provider_responses"] == 1
    assert result["status"] == "pending_provider_response"
    assert (paths.meetings_root / result["details"]["request_path"]).exists()
    assert not (paths.meetings_root / result["details"]["expected_response_path"]).exists()
    assert read_records(paths.ledger) == []
    assert source.exists()


def test_session_inbox_with_extractor_completes_phase2_ingest(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\nKushali: Hi\n", encoding="utf-8")

    summary = process_session_inbox(
        tmp_path,
        extractor=_write_session_response,
        clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)),
    )
    result = summary.details["results"][0]
    records = read_records(paths.ledger)

    assert summary.status == "success"
    assert summary.details["completed"] == 1
    assert summary.details["pending_provider_responses"] == 0
    assert result["status"] == "success"
    assert result["details"]["provider"] == "session"
    assert result["details"]["provider_host"] == "codex"
    assert result["artifacts"][0]["kind"] == "markdown"
    assert result["artifacts"][1]["kind"] == "signals"
    assert not source.exists()
    assert (paths.inbox_done / source.name).exists()
    assert (paths.meetings_root / result["details"]["archive"]["processed_path"]).exists()
    assert result["details"]["reconcile"]["status"] == "completed"
    assert [record["event"] for record in records] == ["primary_artifacts_ready", "ingest_completed"]


def test_cli_session_inbox_json_reports_pending_response(tmp_path: Path, monkeypatch, capsys) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    exit_code = main(["session-inbox", "--json"])
    captured = capsys.readouterr()
    summary = json.loads(captured.out)

    assert exit_code == 0
    assert summary["command"] == "session-inbox"
    assert summary["pending_provider_responses"] == 1
    assert summary["results"][0]["status"] == "pending_provider_response"


def test_session_inbox_completes_existing_response_before_phase1(tmp_path: Path) -> None:
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
    request_payload = json.loads(request_path.read_text(encoding="utf-8"))
    _write_session_response(request_payload, request_path, response_path)

    summary = process_session_inbox(
        tmp_path,
        clock=FrozenClock(datetime(2026, 7, 3, 12, 5, tzinfo=UTC)),
    )
    result = summary.details["results"][0]

    assert summary.status == "success"
    assert summary.details["completed"] == 1
    assert summary.details["phase1"]["status"] == "no_op"
    assert result["status"] == "success"
    assert result["meeting_id"] == request_summary.meeting_id
    assert not request_path.exists()
    assert not response_path.exists()
    assert not source.exists()


def test_session_inbox_reports_existing_missing_response_without_minting_new_request(tmp_path: Path) -> None:
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

    summary = process_session_inbox(
        tmp_path,
        clock=FrozenClock(datetime(2026, 7, 3, 12, 5, tzinfo=UTC)),
    )
    result = summary.details["results"][0]
    request_paths = sorted((paths.cache / "provider-requests").glob("*.request.json"))

    assert summary.status == "success"
    assert summary.details["completed"] == 0
    assert summary.details["pending_provider_responses"] == 1
    assert summary.details["phase1"]["status"] == "skipped_existing_pending"
    assert result["status"] == "pending_provider_response"
    assert result["ingest_run_id"] == request_summary.ingest_run_id
    assert request_paths == [request_path]
    assert source.exists()


def test_session_inbox_keeps_legacy_handoff_visible_but_not_actionable(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    request_summary = provider_request(source, start=paths.inbox)
    request_path = paths.meetings_root / request_summary.details["request_path"]
    request_payload = json.loads(request_path.read_text(encoding="utf-8"))
    request_payload["schema_version"] = "1.0"
    request_payload.pop("runtime_provenance_schema")
    request_payload.pop("runtime_provenance_sha256")
    request_payload.pop("runtime_provenance")
    request_path.write_text(json.dumps(request_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    summary = process_session_inbox(tmp_path)
    result = summary.details["results"][0]

    assert summary.status == "blocked"
    assert summary.exit_code == 12
    assert summary.details["stale_handoffs"] == 0
    assert summary.details["blocked_handoffs"] == 1
    assert summary.details["stale_handoffs"] == 0
    assert summary.details["phase1"]["status"] == "skipped_existing_pending"
    assert result["status"] == "stale_handoff"
    assert result["details"]["reason"] == "legacy_runtime_binding"
    assert "mint a fresh provider request" in result["warnings"][0]
    assert sorted((paths.cache / "provider-requests").glob("*.request.json")) == [request_path]
    assert source.exists()


def test_session_inbox_does_not_extract_invalid_runtime_binding(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    request_summary = provider_request(source, start=paths.inbox)
    request_path = paths.meetings_root / request_summary.details["request_path"]
    request_payload = json.loads(request_path.read_text(encoding="utf-8"))
    request_payload["runtime_provenance"]["build_id"] = "tampered"
    request_path.write_text(json.dumps(request_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    called = False

    def extractor(_request_payload: dict[str, object], _request_path: Path, _response_path: Path) -> None:
        nonlocal called
        called = True

    summary = process_session_inbox(tmp_path, extractor=extractor)
    result = summary.details["results"][0]

    assert summary.status == "blocked"
    assert summary.exit_code == 12
    assert summary.details["blocked_handoffs"] == 1
    assert result["status"] == "stale_handoff"
    assert result["details"]["reason"] == "invalid_runtime_binding"
    assert called is False
    assert request_path.exists()
    assert source.exists()


def test_session_inbox_reports_existing_handoff_with_missing_source_as_stale(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    request_summary = provider_request(source, start=paths.inbox)
    request_path = paths.meetings_root / request_summary.details["request_path"]
    response_path = paths.meetings_root / request_summary.details["expected_response_path"]
    request_payload = json.loads(request_path.read_text(encoding="utf-8"))
    _write_session_response(request_payload, request_path, response_path)
    source.unlink()

    summary = process_session_inbox(tmp_path)
    result = summary.details["results"][0]

    assert summary.status == "success"
    assert summary.details["failed"] == 0
    assert summary.details["stale_handoffs"] == 1
    assert result["status"] == "stale_handoff"
    assert result["errors"] == []
    assert result["details"]["reason"] == "source_missing"
    assert "stale or outside the inbox wrapper scope" in result["warnings"][0]
    assert request_path.exists()
    assert response_path.exists()


def test_session_inbox_reports_out_of_inbox_request_as_stale(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = tmp_path / "2026-07-03-external-sync.txt"
    source.write_text("Ken: External source\n", encoding="utf-8")
    request_summary = provider_request(source, start=tmp_path)
    request_path = paths.meetings_root / request_summary.details["request_path"]

    summary = process_session_inbox(tmp_path)
    result = summary.details["results"][0]

    assert summary.status == "success"
    assert summary.details["stale_handoffs"] == 1
    assert result["status"] == "stale_handoff"
    assert result["details"]["reason"] == "source_missing"
    assert result["details"]["request_path"] == request_summary.details["request_path"]
    assert request_path.exists()


def test_session_inbox_requires_privacy_gate_before_scanning_or_extracting(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    provider_request(source, start=paths.inbox)
    _disable_session_provider(paths.config_path)

    called = False

    def extractor(_request_payload: dict[str, object], _request_path: Path, _response_path: Path) -> None:
        nonlocal called
        called = True

    with pytest.raises(MeetingIngestError) as exc:
        process_session_inbox(tmp_path, extractor=extractor)

    assert exc.value.code == "readiness_privacy_blocked"
    assert exc.value.exit_code == 12
    assert called is False


def test_session_inbox_reports_extractor_failure(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")

    def failing_extractor(_request_payload: dict[str, object], _request_path: Path, _response_path: Path) -> None:
        raise RuntimeError("model unavailable")

    summary = process_session_inbox(tmp_path, extractor=failing_extractor)
    result = summary.details["results"][0]

    assert summary.status == "failed"
    assert summary.details["failed"] == 1
    assert result["status"] == "failed"
    assert result["errors"][0]["phase"] == "provider"
    assert "model unavailable" in result["errors"][0]["message"]
    assert source.exists()


def _allow_session_provider(config_path: Path) -> None:
    config_text = config_path.read_text(encoding="utf-8")
    config_path.write_text(
        config_text.replace("allow_session_provider = false", "allow_session_provider = true"),
        encoding="utf-8",
    )


def _disable_session_provider(config_path: Path) -> None:
    config_text = config_path.read_text(encoding="utf-8")
    config_path.write_text(
        config_text.replace("allow_session_provider = true", "allow_session_provider = false"),
        encoding="utf-8",
    )


def _write_session_response(request_payload: dict[str, object], _request_path: Path, response_path: Path) -> None:
    provider_payload = {
        "name": "session",
        "host": "codex",
        "model_alias": request_payload["quality"],
        "model_id": "codex-session",
        "generated_at": "2026-07-03T12:01:00Z",
    }
    response_payload = {
        "title": "Session Team Sync",
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
    envelope = {
        "schema_version": "1.1",
        "handoff_type": "provider_response",
        "provider_contract": "meeting-ingest-provider-response-v1",
        "meeting_id": request_payload["meeting_id"],
        "ingest_run_id": request_payload["ingest_run_id"],
        "source_sha256": request_payload["source_sha256"],
        "normalized_transcript_sha256": request_payload["normalized_transcript_sha256"],
        "runtime_provenance_sha256": request_payload["runtime_provenance_sha256"],
        "provider": provider_payload,
        "response": response_payload,
    }
    response_path.write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8")
