import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from meeting_ingest.clock import FrozenClock
from meeting_ingest.cli import main
from meeting_ingest.errors import ConfigError
from meeting_ingest.ledger import read_records
from meeting_ingest.paths import init_project
from meeting_ingest.pipeline import ingest


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
    assert "# Kushali Sync" in markdown
    assert "## Verbatim Transcript" in markdown
    assert markdown.endswith("<!-- transcript:end -->")
    assert [record["event"] for record in ledger_records] == ["primary_artifacts_ready", "ingest_completed"]
    assert ledger_records[-1]["artifacts"]["summary-plus-verbatim"]["path"] == "2026-07-03-kushali-sync.md"
    assert ledger_records[-1]["signals"]["path"] == "_signals/mtg-20260703-bf3b2898.jsonl"
    assert ledger_records[-1]["reconcile"]["status"] == "skipped"


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


def test_ingest_rejects_remote_provider_when_privacy_gate_disabled(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")

    with pytest.raises(ConfigError) as exc:
        ingest(source, start=paths.inbox, provider="anthropic")

    assert exc.value.code == "remote_provider_disabled"
