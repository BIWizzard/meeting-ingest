import json
from pathlib import Path

import meeting_ingest.cli as cli_module
from meeting_ingest.cli import build_parser, emit, main
from meeting_ingest.run_summary import RunSummary


def test_cli_parses_meeting_date_for_ingest_and_provider_request() -> None:
    parser = build_parser()
    ingest_args = parser.parse_args(["ingest", "meeting.vtt", "--meeting-date", "2026-07-10"])
    assert ingest_args.meeting_date == "2026-07-10"
    request_args = parser.parse_args(["provider-request", "meeting.vtt", "--meeting-date", "2026-07-13"])
    assert request_args.meeting_date == "2026-07-13"


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
