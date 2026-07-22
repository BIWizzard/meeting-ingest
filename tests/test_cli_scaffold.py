import json
from pathlib import Path

import meeting_ingest.cli as cli_module
from meeting_ingest.cli import build_parser, emit, main
from meeting_ingest.run_summary import RunSummary
from conftest import approved_runtime_inspection
from meeting_ingest.runtime import ReadinessFinding


def test_cli_parses_meeting_date_for_ingest_and_provider_request() -> None:
    parser = build_parser()
    ingest_args = parser.parse_args(["ingest", "meeting.vtt", "--meeting-date", "2026-07-10"])
    assert ingest_args.meeting_date == "2026-07-10"
    request_args = parser.parse_args(["provider-request", "meeting.vtt", "--meeting-date", "2026-07-13"])
    assert request_args.meeting_date == "2026-07-13"


def test_cli_parses_development_override_before_or_after_command() -> None:
    parser = build_parser()
    before = parser.parse_args(["--development-override", "local test", "init"])
    after = parser.parse_args(["init", "--development-override", "local test"])

    assert before.development_override == "local test"
    assert after.development_override == "local test"


def test_cli_parses_playbook_update() -> None:
    args = build_parser().parse_args(["playbook", "update", "--root", "/tmp/project", "--json"])

    assert args.command == "playbook"
    assert args.playbook_command == "update"
    assert args.root == "/tmp/project"
    assert args.json is True


def test_cli_parses_runtime_inspect() -> None:
    args = build_parser().parse_args(["runtime", "inspect", "--root", "/tmp/consumer", "--json"])

    assert args.command == "runtime"
    assert args.runtime_command == "inspect"
    assert args.root == "/tmp/consumer"
    assert args.json is True


def test_cli_parses_runtime_pin_and_update_check() -> None:
    pin = build_parser().parse_args(
        [
            "runtime",
            "pin",
            "--receipt",
            "/tmp/release/receipt.json",
            "--root",
            "/tmp/consumer",
            "--json",
        ]
    )
    update = build_parser().parse_args(
        ["runtime", "update-check", "--root", "/tmp/consumer", "--json"]
    )

    assert pin.runtime_command == "pin"
    assert pin.receipt == "/tmp/release/receipt.json"
    assert pin.root == "/tmp/consumer"
    assert update.runtime_command == "update-check"
    assert update.root == "/tmp/consumer"


def test_emit_prints_runtime_inspection_summary(capsys) -> None:
    summary = RunSummary(
        details={
            "command": "runtime_inspect",
            "runtime_mode": "development",
            "build": {"build_id": "development"},
            "install": {"mode": "editable"},
            "executable": {"invoked": "/tmp/bin/meeting-ingest"},
            "distribution": {"record_integrity": "valid"},
            "findings": [
                {
                    "code": "runtime_editable_blocked",
                    "message": "The running distribution is editable.",
                }
            ],
        }
    )

    emit(summary, as_json=False)

    assert capsys.readouterr().out == (
        "Runtime: development\n"
        "Build: development\n"
        "Install: editable\n"
        "Executable: /tmp/bin/meeting-ingest\n"
        "Package integrity: valid\n"
        "Findings:\n"
        "- runtime_editable_blocked: The running distribution is editable.\n"
    )


def test_emit_blocked_readiness_leads_with_verdict_and_remediation(capsys) -> None:
    summary = RunSummary(
        status="blocked",
        exit_code=12,
        runtime_provenance={"development_override_reason": None},
        details={
            "command": "readiness",
            "verdict": "blocked",
            "findings": [
                {
                    "severity": "blocker",
                    "remediation": "Install and pin the approved runtime.",
                }
            ],
            "finding_counts": {"by_severity": {"blocker": 1}},
        },
    )

    emit(summary, as_json=False)

    assert capsys.readouterr().out == (
        "Readiness: Blocked\n"
        "Next action: Install and pin the approved runtime.\n"
        "Findings: blocker=1\n"
    )


def test_runtime_inspect_json_outputs_machine_readable_evidence(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        cli_module,
        "inspect_runtime_summary",
        lambda root: RunSummary(
            runtime_provenance={"build_id": "development", "runtime_mode": "development"},
            details={
                "command": "runtime_inspect",
                "runtime_mode": "development",
                "build": {"build_id": "development"},
                "install": {"mode": "editable"},
                "executable": {"invoked": "/tmp/bin/meeting-ingest"},
                "distribution": {"record_integrity": "valid"},
                "findings": [],
            },
        ),
    )

    exit_code = main(["runtime", "inspect", "--root", "/tmp/consumer", "--json"])
    result = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert result["command"] == "runtime_inspect"
    assert result["runtime_mode"] == "development"
    assert result["runtime_provenance"]["build_id"] == "development"


def test_runtime_pin_expected_failure_uses_stable_runtime_code(tmp_path: Path, capsys) -> None:
    exit_code = main(
        [
            "runtime",
            "pin",
            "--receipt",
            str(tmp_path / "missing-receipt.json"),
            "--root",
            str(tmp_path / "consumer"),
            "--json",
        ]
    )
    result = json.loads(capsys.readouterr().out)

    assert exit_code == 12
    assert result["reason"] == "runtime_receipt_invalid"
    assert result["errors"][0]["code"] == "runtime_receipt_invalid"


def test_mutating_cli_failure_after_guard_preserves_runtime_provenance(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    assert main(["init", "--root", str(tmp_path), "--json"]) == 0
    capsys.readouterr()
    source = tmp_path / "_local/project-context/meetings/_inbox/unsupported.pdf"
    source.write_text("unsupported", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    exit_code = main(["ingest", str(source), "--json"])
    result = json.loads(capsys.readouterr().out)

    assert exit_code == 3
    assert result["errors"][0]["code"] == "unsupported_source_format"
    assert result["runtime_provenance"]["runtime_mode"] == "approved"


def test_readiness_cli_returns_stable_blocked_exit_code(tmp_path: Path, monkeypatch, capsys) -> None:
    from dataclasses import replace

    from meeting_ingest.paths import init_project

    init_project(tmp_path)
    inspection = approved_runtime_inspection(tmp_path)
    finding = ReadinessFinding(
        code="runtime_package_integrity_failed",
        category="runtime",
        severity="blocker",
        message="Package integrity failed.",
        path="/runtime/RECORD",
        remediation="Reinstall the package.",
    )
    inspection = replace(inspection, findings=(finding,), runtime_mode="unverified")
    monkeypatch.setattr("meeting_ingest.readiness._RUNTIME_INSPECTOR", lambda _: inspection)

    exit_code = main(["readiness", "--root", str(tmp_path), "--json"])
    result = json.loads(capsys.readouterr().out)

    assert exit_code == 12
    assert result["verdict"] == "blocked"
    assert result["findings"][0]["code"] == "runtime_package_integrity_failed"


def test_emit_update_check_warns_when_status_is_unavailable(capsys) -> None:
    summary = RunSummary(
        warnings=["Runtime pin unavailable or invalid: missing"],
        details={
            "command": "runtime_update_check",
            "update_available": False,
            "installed_build_id": "development",
            "channel": {"latest_build_id": None},
        },
    )

    emit(summary, as_json=False)

    assert capsys.readouterr().out == (
        "Update status unavailable\n"
        "Installed: development\n"
        "Channel: unavailable\n"
        "Warning: Runtime pin unavailable or invalid: missing\n"
    )


def test_cli_parses_playbook_review_and_read_commands() -> None:
    reject = build_parser().parse_args(
        ["playbook", "reject", "entry-person-kushali-g-ask-123456789abc", "--reason", "Bad", "--json"]
    )
    show = build_parser().parse_args(["playbook", "show", "Kushali", "--format", "json"])

    assert reject.playbook_command == "reject"
    assert reject.reason == "Bad"
    assert show.playbook_command == "show"
    assert show.selector == "Kushali"
    assert show.format == "json"


def test_emit_prints_playbook_read_payload_without_summary_wrapper(capsys) -> None:
    summary = RunSummary(details={"command": "playbook_show", "format": "markdown", "content": "# Brief\n"})

    emit(summary, as_json=False)

    assert capsys.readouterr().out == "# Brief\n\n"


def test_init_json_outputs_run_summary(tmp_path: Path, capsys) -> None:
    exit_code = main(["init", "--root", str(tmp_path), "--json"])

    captured = capsys.readouterr()
    summary = json.loads(captured.out)

    assert exit_code == 0
    assert summary["schema_version"] == "1.0"
    assert summary["status"] == "success"
    assert summary["command"] == "init"
    assert Path(summary["meetings_root"]).is_dir()


def test_ingest_without_project_returns_config_failure(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)

    exit_code = main(["ingest", "missing.txt", "--json"])

    captured = capsys.readouterr()
    summary = json.loads(captured.out)

    assert exit_code == 2
    assert summary["status"] == "failed"
    assert summary["reason"] == "config_not_found"
    assert summary["errors"][0]["phase"] == "config"


def test_ingest_inbox_json_outputs_batch_summary(tmp_path: Path, monkeypatch, capsys) -> None:
    exit_code = main(["init", "--root", str(tmp_path), "--json"])
    assert exit_code == 0
    capsys.readouterr()
    inbox = tmp_path / "_local/project-context/meetings/_inbox"
    source = inbox / "2026-07-03-kushali-sync.txt"
    source.write_text("Ken: Hello\nKushali: Hi\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    exit_code = main(["ingest-inbox", "--json"])

    captured = capsys.readouterr()
    summary = json.loads(captured.out)

    assert exit_code == 0
    assert summary["command"] == "ingest-inbox"
    assert summary["status"] == "success"
    assert summary["processed"] == 1
    assert summary["results"][0]["status"] == "success"
    assert summary["results"][0]["artifacts"][0]["path"] == "2026-07-03-kushali-sync.md"


def test_doctor_json_outputs_project_and_issues(tmp_path: Path, monkeypatch, capsys) -> None:
    exit_code = main(["init", "--root", str(tmp_path), "--json"])
    assert exit_code == 0
    capsys.readouterr()
    inbox = tmp_path / "_local/project-context/meetings/_inbox"
    source = inbox / "unprocessed.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    exit_code = main(["doctor", "--json"])

    captured = capsys.readouterr()
    summary = json.loads(captured.out)

    assert exit_code == 1
    assert summary["command"] == "doctor"
    assert summary["status"] == "issues_found"
    assert summary["artifacts"] == []
    assert summary["project"]["known_sources"] == 0
    assert summary["project"]["inbox_files"] == 1
    assert summary["issues"] == [
        {
            "code": "inbox_residue",
            "message": "Source file remains in inbox.",
            "path": "_inbox/unprocessed.txt",
        }
    ]
