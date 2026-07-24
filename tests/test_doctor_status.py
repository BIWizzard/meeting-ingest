from datetime import UTC, datetime
import json
import os
from pathlib import Path
import time

import pytest

from meeting_ingest import pipeline
from meeting_ingest.clock import FrozenClock
from meeting_ingest.ledger import (
    LedgerSnapshot,
    append_snapshot,
    read_records,
    read_records_with_issues,
)
from meeting_ingest.paths import init_project
from meeting_ingest.pipeline import doctor, ingest, provider_request, status
from meeting_ingest.playbook import update as update_playbook


def test_status_reports_project_counts(tmp_path: Path) -> None:
    paths = init_project(tmp_path)

    summary = status(tmp_path)

    assert summary.status == "success"
    assert summary.exit_code == 0
    project = summary.details["project"]
    playbook = project.pop("playbook")
    assert project == {
        "meetings_root": str(paths.meetings_root),
        "ledger_records": 0,
        "known_sources": 0,
        "inbox_files": 0,
        "session_handoffs": {
            "total": 0,
            "pending": 0,
            "stale": 0,
            "blocked": 0,
            "failed": 0,
        },
        "identity_registry": {"status": "missing", "people": 0, "issues": 0, "identity_candidates": 0},
        "signal_contract": {"status": "valid", "issues": []},
    }
    assert playbook["status"] == "missing"
    assert playbook["derivation_run_id"] is None
    assert playbook["profile_count"] == 0
    assert playbook["latest_attempt_status"] is None
    assert summary.details["session_handoffs"] == {
        "counts": {
            "total": 0,
            "pending": 0,
            "stale": 0,
            "blocked": 0,
            "failed": 0,
        },
        "results": [],
    }


def test_doctor_reports_clean_project_after_ingest(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")

    ingest(source, start=paths.inbox, clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)))
    summary = doctor(tmp_path)

    assert summary.status == "success"
    assert summary.exit_code == 0
    assert summary.details["issues"] == []
    assert summary.details["project"]["ledger_records"] == 2
    assert summary.details["project"]["known_sources"] == 1


def test_doctor_reports_invalid_ledger_runtime_provenance(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    ingest(source, start=paths.inbox)
    records = [
        json.loads(line) for line in paths.ledger.read_text(encoding="utf-8").splitlines()
    ]
    records[-1]["runtime_provenance_sha256"] = "sha256:" + "0" * 64
    paths.ledger.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )

    valid_records, read_issues = read_records_with_issues(paths.ledger)
    summary = doctor(tmp_path)

    assert len(valid_records) == 1
    assert [(issue.line_number, issue.code) for issue in read_issues] == [
        (2, "ledger_provenance_invalid")
    ]
    assert {
        "code": "ledger_provenance_invalid",
        "message": "Ledger 2.0 runtime-provenance binding is invalid.",
        "path": "_ledger.jsonl:line:2",
    } in summary.details["issues"]


def test_doctor_reports_no_runtime_provenance_link_findings_after_clean_ingest(
    tmp_path: Path,
) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Please capture this. [mock-signal]\n", encoding="utf-8")
    ingest(source, start=paths.inbox)

    codes = {issue["code"] for issue in doctor(tmp_path).details["issues"]}

    assert codes.isdisjoint(
        {
            "ledger_provenance_invalid",
            "current_signal_link_invalid",
            "artifact_provenance_mismatch",
            "playbook_provenance_invalid",
        }
    )


@pytest.mark.parametrize("mutation", ["bytes", "missing", "producer_fingerprint"])
def test_doctor_reports_invalid_current_signal_producer_link(
    tmp_path: Path,
    mutation: str,
) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Please capture this. [mock-signal]\n", encoding="utf-8")
    result = ingest(source, start=paths.inbox)
    signal_path = paths.meetings_root / result.artifacts[1]["path"]
    if mutation == "bytes":
        signal_path.write_text(
            signal_path.read_text(encoding="utf-8") + "\n",
            encoding="utf-8",
        )
    elif mutation == "missing":
        signal_path.unlink()
    else:
        records = [
            json.loads(line)
            for line in paths.ledger.read_text(encoding="utf-8").splitlines()
        ]
        producer = next(
            record
            for record in records
            if record["signals"]["produced_in_this_record"] is True
        )
        producer["signals"]["fingerprint"] = "sha256:" + "0" * 64
        paths.ledger.write_text(
            "".join(json.dumps(record) + "\n" for record in records),
            encoding="utf-8",
        )

    issues = doctor(tmp_path).details["issues"]
    matches = [
        issue for issue in issues if issue["code"] == "current_signal_link_invalid"
    ]

    assert len(matches) == 1
    assert matches[0]["path"] == result.artifacts[1]["path"]
    assert "Current signal producer link is invalid:" in matches[0]["message"]


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [("mismatch", True), ("missing_key", True), ("legacy", False)],
)
def test_doctor_checks_current_artifact_runtime_provenance(
    tmp_path: Path,
    mutation: str,
    expected: bool,
) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    result = ingest(source, start=paths.inbox)
    artifact_path = paths.meetings_root / result.artifacts[0]["path"]
    lines = artifact_path.read_text(encoding="utf-8").splitlines()
    if mutation == "legacy":
        lines = [
            'schema_version: "1.0"' if line.startswith("schema_version:") else line
            for line in lines
        ]
    elif mutation == "missing_key":
            lines = [line for line in lines if not line.startswith("  build_id:")]
    else:
        lines = [
            f'runtime_provenance_sha256: "sha256:{"0" * 64}"'
            if line.startswith("runtime_provenance_sha256:")
            else line
            for line in lines
        ]
    artifact_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    matches = [
        issue
        for issue in doctor(tmp_path).details["issues"]
        if issue["code"] == "artifact_provenance_mismatch"
    ]

    assert bool(matches) is expected
    if expected:
        assert matches[0]["path"] == result.artifacts[0]["path"]


@pytest.mark.parametrize("target", ["index", "derivation_ledger"])
def test_doctor_reports_invalid_playbook_runtime_provenance(
    tmp_path: Path,
    target: str,
) -> None:
    paths = _project_with_playbook(tmp_path)
    update_playbook(tmp_path)
    if target == "index":
        target_path = paths.derived / "playbook-index.json"
        payload = json.loads(target_path.read_text(encoding="utf-8"))
        payload["runtime_provenance_sha256"] = "sha256:" + "0" * 64
        target_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    else:
        target_path = paths.playbook_state / "derivation-ledger.jsonl"
        payload = json.loads(target_path.read_text(encoding="utf-8"))
        payload["runtime_provenance_sha256"] = "sha256:" + "0" * 64
        target_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    matches = [
        issue
        for issue in doctor(tmp_path).details["issues"]
        if issue["code"] == "playbook_provenance_invalid"
    ]

    assert len(matches) == 1
    assert matches[0]["path"].startswith(
        "_derived/playbook-index.json"
        if target == "index"
        else "_playbook-state/derivation-ledger.jsonl:line:"
    )


def test_doctor_leaves_schema_1_0_playbook_index_provenance_unchanged(
    tmp_path: Path,
) -> None:
    paths = _project_with_playbook(tmp_path)
    update_playbook(tmp_path)
    index_path = paths.derived / "playbook-index.json"
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    payload["schema_version"] = "1.0"
    payload.pop("runtime_provenance_schema")
    payload.pop("runtime_provenance_sha256")
    payload.pop("runtime_provenance")
    index_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    codes = {issue["code"] for issue in doctor(tmp_path).details["issues"]}

    assert "playbook_provenance_invalid" not in codes


def test_doctor_rejects_tampered_playbook_profile_provenance(tmp_path: Path) -> None:
    paths = _project_with_playbook(tmp_path)
    update_playbook(tmp_path)
    index = json.loads((paths.derived / "playbook-index.json").read_text(encoding="utf-8"))
    profile_path = paths.meetings_root / index["profiles"]["person-kushali-g"]["profile_path"]
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    profile["runtime_provenance_sha256"] = "sha256:" + "0" * 64
    profile_path.write_text(json.dumps(profile) + "\n", encoding="utf-8")

    matches = [
        issue
        for issue in doctor(tmp_path).details["issues"]
        if issue["code"] == "playbook_provenance_invalid"
    ]

    assert len(matches) == 1
    assert "profile person-kushali-g" in matches[0]["message"]


def test_doctor_rejects_ambiguous_signal_producer_snapshot(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Please capture this. [mock-signal]\n", encoding="utf-8")
    ingest(source, start=paths.inbox)
    records = [
        json.loads(line)
        for line in paths.ledger.read_text(encoding="utf-8").splitlines()
    ]
    producer = next(
        record for record in records if record["signals"]["produced_in_this_record"] is True
    )
    with paths.ledger.open("a", encoding="utf-8") as ledger:
        ledger.write(json.dumps(producer) + "\n")

    matches = [
        issue
        for issue in doctor(tmp_path).details["issues"]
        if issue["code"] == "current_signal_link_invalid"
    ]

    assert len(matches) == 1
    assert "resolved to 2 snapshots" in matches[0]["message"]


def test_doctor_reports_low_confidence_meeting_date_and_clears_after_repair(tmp_path: Path) -> None:
    pipeline.initialize(tmp_path)
    meetings_root = tmp_path / "_local/project-context/meetings"
    source = meetings_root / "_inbox" / "Daily Stand Up - Post-MVP (41).vtt"
    source.write_text(
        "WEBVTT\n\n"
        "7f3a2c9e-4b1d-4e8a-9c5f-1a2b3c4d5e6f/1-0\n"
        "00:00:03.120 --> 00:00:06.480\n"
        "<v Graham, Ken (Contractor)>Please capture this request. [mock-signal]</v>\n",
        encoding="utf-8",
    )
    os.utime(source, (1784160000, 1784160000))
    summary = pipeline.ingest(source, start=tmp_path, provider="mock")

    doctor_summary = pipeline.doctor(tmp_path)
    issue_codes = [issue["code"] for issue in doctor_summary.details["issues"]]
    assert "low_confidence_meeting_date" in issue_codes

    pipeline.repair_date(summary.meeting_id, date="2026-07-10", start=tmp_path)

    doctor_summary = pipeline.doctor(tmp_path)
    issue_codes = [issue["code"] for issue in doctor_summary.details["issues"]]
    assert "low_confidence_meeting_date" not in issue_codes


def test_doctor_reports_inbox_residue(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "unprocessed.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")

    summary = doctor(tmp_path)

    assert summary.status == "issues_found"
    assert summary.exit_code == 1
    assert summary.details["issues"] == [
        {
            "code": "inbox_residue",
            "message": "Source file remains in inbox.",
            "path": "_inbox/unprocessed.txt",
        }
    ]


def test_doctor_reports_missing_ledger_artifact(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    result = ingest(source, start=paths.inbox, clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)))
    artifact = paths.meetings_root / result.artifacts[0]["path"]
    artifact.unlink()

    summary = doctor(tmp_path)
    records = read_records(paths.ledger)

    assert len(records) == 2
    assert summary.status == "issues_found"
    assert {
        "code": "missing_artifact",
        "message": "Ledger references a missing path.",
        "path": result.artifacts[0]["path"],
    } in summary.details["issues"]


def test_doctor_reports_missing_processed_copy(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    result = ingest(source, start=paths.inbox, clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)))
    processed = paths.meetings_root / result.details["archive"]["processed_path"]
    processed.unlink()

    summary = doctor(tmp_path)

    assert {
        "code": "missing_processed_source",
        "message": "Ledger references a missing path.",
        "path": result.details["archive"]["processed_path"],
    } in summary.details["issues"]


def test_doctor_reports_incomplete_reconcile_state(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    artifact = paths.meetings_root / "2026-07-03-team-sync.md"
    artifact.write_text("# Team Sync\n", encoding="utf-8")
    signal = paths.signals / "mtg-20260703-abc12345.jsonl"
    signal.write_text("", encoding="utf-8")
    append_snapshot(
        paths.ledger,
        LedgerSnapshot(
            schema_version="1.0",
            event="primary_artifacts_ready",
            source_sha256="abc12345",
            meeting_id="mtg-20260703-abc12345",
            ingest_run_id="ingest-20260703-20260703T120000Z-abcd",
            source={"original_path": "_inbox/2026-07-03-team-sync.txt", "source_type": "txt"},
            artifacts={
                "summary-plus-verbatim": {
                    "kind": "markdown",
                    "status": "ready",
                    "path": "2026-07-03-team-sync.md",
                }
            },
            signals={"status": "ready", "path": "_signals/mtg-20260703-abc12345.jsonl", "count": 0},
            reconcile={"status": "pending"},
        ),
        clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)),
    )

    summary = doctor(tmp_path)

    assert {
        "code": "incomplete_reconcile",
        "message": "Primary artifacts are ready but archive/reconcile did not complete.",
        "path": "_inbox/2026-07-03-team-sync.txt",
    } in summary.details["issues"]


def test_doctor_reports_malformed_ledger_line(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    paths.ledger.write_text("{not-json\n", encoding="utf-8")

    summary = doctor(tmp_path)

    assert summary.status == "issues_found"
    assert summary.details["issues"] == [
        {
            "code": "malformed_ledger_json",
            "message": "Ledger line is not valid JSON: Expecting property name enclosed in double quotes",
            "path": "_ledger.jsonl:line:1",
        }
    ]


def test_doctor_reports_stale_provider_handoff_cache(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    request = paths.cache / "provider-requests" / "old.request.json"
    response = paths.cache / "provider-responses" / "old.response.json"
    request.parent.mkdir(parents=True)
    response.parent.mkdir(parents=True)
    request.write_text("{}", encoding="utf-8")
    response.write_text("{}", encoding="utf-8")
    old_time = time.time() - (8 * 24 * 60 * 60)
    os.utime(request, (old_time, old_time))
    os.utime(response, (old_time, old_time))

    summary = doctor(tmp_path)

    assert {
        "code": "stale_provider_request",
        "message": "Provider handoff cache file is stale.",
        "path": "_cache/provider-requests/old.request.json",
    } in summary.details["issues"]
    assert {
        "code": "stale_provider_response",
        "message": "Provider handoff cache file is stale.",
        "path": "_cache/provider-responses/old.response.json",
    } in summary.details["issues"]


def test_status_and_doctor_report_ambiguous_identity_registry(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    fixture = Path(__file__).parent / "fixtures" / "stakeholders" / "ambiguous.toml"
    (paths.playbook_state / "stakeholders.toml").write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")

    status_summary = status(tmp_path)
    doctor_summary = doctor(tmp_path)

    assert status_summary.details["project"]["identity_registry"] == {
        "status": "invalid",
        "people": 2,
        "issues": 1,
        "identity_candidates": 0,
    }
    assert {
        "code": "identity_alias_ambiguous",
        "message": "Reviewed alias 'alex' belongs to multiple people: person-alex-one, person-alex-two.",
        "path": "_playbook-state/stakeholders.toml",
    } in doctor_summary.details["issues"]


def test_doctor_reports_invalid_schema_1_1_signal_identity(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    fixture = Path(__file__).parent / "fixtures" / "signals" / "schema-1.1-meeting.jsonl"
    payload = fixture.read_text(encoding="utf-8").replace(
        "sig-a1b2c3d4e5f6-91aa2c80b731", "sig-wrong-identity"
    )
    (paths.signals / "invalid.jsonl").write_text(payload, encoding="utf-8")

    summary = doctor(tmp_path)

    assert any(issue["code"] == "signal_identity_invalid" for issue in summary.details["issues"])

    status_summary = status(tmp_path)
    assert status_summary.details["project"]["signal_contract"]["status"] == "invalid"
    assert status_summary.details["project"]["signal_contract"]["issues"][0]["code"] == "signal_identity_invalid"


def test_doctor_reports_unmapped_schema_1_0_meeting_identity(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    fixture = Path(__file__).parent / "fixtures" / "signals" / "schema-1.0-meeting.jsonl"
    (paths.signals / "legacy.jsonl").write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")

    summary = doctor(tmp_path)

    assert {
        "code": "signal_identity_invalid",
        "message": (
            "Schema 1.0 signal meeting identity cannot be mapped to a valid source-ledger hash: "
            "mtg-20260703-f953bbd2"
        ),
        "path": "_signals/legacy.jsonl",
    } in summary.details["issues"]


def test_status_reports_pending_session_handoff(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    request_summary = provider_request(source, start=paths.inbox)

    summary = status(tmp_path)
    handoff_status = summary.details["session_handoffs"]
    result = handoff_status["results"][0]

    assert handoff_status["counts"] == {
        "total": 1,
        "pending": 1,
        "stale": 0,
        "blocked": 0,
        "failed": 0,
    }
    assert summary.details["project"]["session_handoffs"] == handoff_status["counts"]
    assert result["status"] == "pending_provider_response"
    assert result["ingest_run_id"] == request_summary.ingest_run_id
    assert result["details"]["request_path"] == request_summary.details["request_path"]


def test_doctor_reports_pending_session_handoff(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    request_summary = provider_request(source, start=paths.inbox)

    summary = doctor(tmp_path)

    assert {
        "code": "session_handoff_pending",
        "message": "Session provider handoff is waiting for provider response or phase-2 completion.",
        "path": request_summary.details["request_path"],
    } in summary.details["issues"]


def test_doctor_reports_stale_session_handoff(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    request_summary = provider_request(source, start=paths.inbox)
    source.unlink()

    handoff_status = status(tmp_path).details["session_handoffs"]
    summary = doctor(tmp_path)

    assert handoff_status["counts"] == {"total": 1, "pending": 0, "stale": 1, "blocked": 0, "failed": 0}
    assert {
        "code": "session_handoff_stale",
        "message": "Session provider handoff is stale or outside the inbox wrapper scope.",
        "path": request_summary.details["request_path"],
    } in summary.details["issues"]


def test_doctor_reports_legacy_runtime_handoff_remediation(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    request_summary = provider_request(source, start=paths.inbox)
    request_path = paths.meetings_root / request_summary.details["request_path"]
    request = json.loads(request_path.read_text(encoding="utf-8"))
    request["schema_version"] = "1.0"
    request.pop("runtime_provenance_schema")
    request.pop("runtime_provenance_sha256")
    request.pop("runtime_provenance")
    request_path.write_text(json.dumps(request, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    handoff_status = status(tmp_path).details["session_handoffs"]
    summary = doctor(tmp_path)

    assert handoff_status["counts"] == {"total": 1, "pending": 0, "stale": 0, "blocked": 1, "failed": 0}
    assert {
        "code": "session_handoff_runtime_blocked",
        "message": (
            "Session provider handoff uses legacy schema 1.0 without runtime provenance; "
            "abandon it and mint a fresh request under the intended runtime."
        ),
        "path": request_summary.details["request_path"],
    } in summary.details["issues"]


def test_doctor_reports_invalid_runtime_handoff_remediation(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    _allow_session_provider(paths.config_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    request_summary = provider_request(source, start=paths.inbox)
    request_path = paths.meetings_root / request_summary.details["request_path"]
    request = json.loads(request_path.read_text(encoding="utf-8"))
    request["runtime_provenance"]["build_id"] = "tampered"
    request_path.write_text(json.dumps(request, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    handoff_status = status(tmp_path).details["session_handoffs"]
    summary = doctor(tmp_path)

    assert handoff_status["counts"] == {"total": 1, "pending": 0, "stale": 0, "blocked": 1, "failed": 0}
    assert {
        "code": "session_handoff_runtime_blocked",
        "message": (
            "Session provider handoff has an invalid runtime-provenance binding; "
            "restore the reviewed request or explicitly abandon and remint it."
        ),
        "path": request_summary.details["request_path"],
    } in summary.details["issues"]


def test_doctor_reports_invalid_session_handoff(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    request = paths.cache / "provider-requests" / "broken.request.json"
    request.parent.mkdir(parents=True)
    request.write_text("{not-json\n", encoding="utf-8")

    summary = doctor(tmp_path)

    assert {
        "code": "session_handoff_invalid",
        "message": "Session provider handoff request could not be parsed or planned.",
        "path": "_cache/provider-requests/broken.request.json",
    } in summary.details["issues"]


def _allow_session_provider(config_path: Path) -> None:
    config_text = config_path.read_text(encoding="utf-8")
    config_path.write_text(
        config_text.replace("allow_session_provider = false", "allow_session_provider = true"),
        encoding="utf-8",
    )


def _project_with_playbook(tmp_path: Path):
    paths = init_project(tmp_path)
    fixtures = Path(__file__).parent / "fixtures"
    (paths.playbook_state / "stakeholders.toml").write_text(
        (fixtures / "stakeholders" / "reviewed.toml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (paths.signals / "mtg-20260703-a1b2c3d4.jsonl").write_text(
        (fixtures / "signals" / "schema-1.1-meeting.jsonl").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    return paths
