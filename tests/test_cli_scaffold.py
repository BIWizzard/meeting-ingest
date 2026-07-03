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


def test_ingest_stub_returns_documented_failure(capsys) -> None:
    exit_code = main(["ingest", "missing.txt", "--json"])

    captured = capsys.readouterr()
    summary = json.loads(captured.out)

    assert exit_code == 1
    assert summary["status"] == "failed"
    assert summary["reason"] == "not_implemented"
    assert summary["errors"][0]["phase"] == "pipeline"
