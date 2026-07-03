import json
from pathlib import Path

from meeting_ingest.cli import main


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
