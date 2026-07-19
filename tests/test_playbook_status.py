from datetime import UTC, datetime
import json
from pathlib import Path

import pytest

from meeting_ingest.clock import FrozenClock
from meeting_ingest.doctor import find_issues, project_status
from meeting_ingest.errors import MeetingIngestError
from meeting_ingest.paths import init_project
from meeting_ingest.playbook import brief, repair_index, show, update


FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 7, 19, 18, 0, tzinfo=UTC)


def _configured_project(tmp_path: Path):
    paths = init_project(tmp_path)
    (paths.playbook_state / "stakeholders.toml").write_text(
        (FIXTURES / "stakeholders" / "reviewed.toml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (paths.signals / "signal.jsonl").write_text(
        (FIXTURES / "signals" / "schema-1.1-meeting.jsonl").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return paths


def test_status_moves_from_current_to_stale_when_eligible_input_changes(tmp_path: Path) -> None:
    paths = _configured_project(tmp_path)
    update(tmp_path, clock=FrozenClock(NOW), suffix_factory=lambda: "1111aaaa")

    current = project_status(paths)["playbook"]
    assert current["status"] == "current"
    assert current["latest_attempt_status"] == "success"

    second = json.loads((paths.signals / "signal.jsonl").read_text(encoding="utf-8"))
    second["signal_id"] = "sig-bbbbbbbbbbbb-222222222222"
    second["source"]["source_id"] = "src-bbbbbbbbbbbb"
    second["source"]["source_sha256"] = "b" * 64
    (paths.signals / "second.jsonl").write_text(json.dumps(second) + "\n", encoding="utf-8")

    stale = project_status(paths)["playbook"]
    assert stale["status"] == "stale"
    assert stale["input_fingerprint"] != stale["current_input_fingerprint"]
    assert "playbook_stale" in {issue.code for issue in find_issues(paths)}


def test_failed_attempt_is_recorded_without_replacing_current_index(tmp_path: Path, monkeypatch) -> None:
    paths = _configured_project(tmp_path)
    update(tmp_path, clock=FrozenClock(NOW), suffix_factory=lambda: "1111aaaa")
    original_index = (paths.derived / "playbook-index.json").read_text(encoding="utf-8")

    def fail_generation(*args, **kwargs):
        raise MeetingIngestError(
            phase="playbook_generation",
            code="test_generation_failed",
            message="generation failed",
            exit_code=7,
            recoverable=True,
        )

    monkeypatch.setattr("meeting_ingest.playbook._write_json_atomic", fail_generation)
    with pytest.raises(MeetingIngestError, match="generation failed"):
        update(tmp_path, clock=FrozenClock(NOW), suffix_factory=lambda: "2222bbbb")

    records = [
        json.loads(line)
        for line in (paths.playbook_state / "derivation-ledger.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    status = project_status(paths)["playbook"]
    assert records[-1]["event"] == "briefing_derivation_failed"
    assert records[-1]["generation_path"] is None
    assert (paths.derived / "playbook-index.json").read_text(encoding="utf-8") == original_index
    assert status["status"] == "current"
    assert status["latest_attempt_status"] == "failed"


def test_failed_first_attempt_reports_failed_status(tmp_path: Path) -> None:
    paths = _configured_project(tmp_path)
    (paths.playbook_state / "stakeholders.toml").write_text('schema_version = "2.0"\n', encoding="utf-8")

    with pytest.raises(MeetingIngestError, match="registry is invalid"):
        update(tmp_path, clock=FrozenClock(NOW), suffix_factory=lambda: "deadbeef")

    assert project_status(paths)["playbook"]["status"] == "failed"


def test_repair_index_restores_latest_committed_generation(tmp_path: Path) -> None:
    paths = _configured_project(tmp_path)
    update(tmp_path, clock=FrozenClock(NOW), suffix_factory=lambda: "abcd1111")
    expected = json.loads((paths.derived / "playbook-index.json").read_text(encoding="utf-8"))
    (paths.derived / "playbook-index.json").unlink()

    assert "derivation_index_mismatch" in {issue.code for issue in find_issues(paths)}

    summary = repair_index(tmp_path, clock=FrozenClock(NOW))
    repaired = json.loads((paths.derived / "playbook-index.json").read_text(encoding="utf-8"))

    assert summary.details["derivation_run_id"] == expected["derivation_run_id"]
    assert repaired == expected


def test_show_and_brief_resolve_reviewed_alias_and_return_requested_format(tmp_path: Path) -> None:
    _configured_project(tmp_path)
    update(tmp_path, clock=FrozenClock(NOW), suffix_factory=lambda: "abcd2222")

    shown = show(tmp_path, "Kushali", output_format="json")
    concise = brief(tmp_path, "person-kushali-g", output_format="markdown")

    assert shown.details["content"]["profile_kind"] == "stakeholder_briefing"
    assert concise.details["content"].startswith("# Stakeholder Brief: Kushali G")
    assert "## Evidence Index" not in concise.details["content"]


def test_doctor_reports_malformed_derivation_and_review_ledgers(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    (paths.playbook_state / "derivation-ledger.jsonl").write_text("not json\n", encoding="utf-8")
    (paths.playbook_state / "overrides.jsonl").write_text("{}\n", encoding="utf-8")

    codes = {issue.code for issue in find_issues(paths)}

    assert "derivation_ledger_malformed" in codes
    assert "review_event_malformed" in codes


def test_show_rejects_indexed_paths_outside_meetings_root(tmp_path: Path) -> None:
    paths = _configured_project(tmp_path)
    update(tmp_path, clock=FrozenClock(NOW), suffix_factory=lambda: "abcd3333")
    index_path = paths.derived / "playbook-index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["profiles"]["person-kushali-g"]["profile_path"] = "/etc/passwd"
    index_path.write_text(json.dumps(index), encoding="utf-8")

    with pytest.raises(MeetingIngestError, match="escapes the meetings root"):
        show(tmp_path, "person-kushali-g", output_format="json")


def test_update_ignores_invalid_previous_profile_path_and_rebuilds_safely(tmp_path: Path) -> None:
    paths = _configured_project(tmp_path)
    update(tmp_path, clock=FrozenClock(NOW), suffix_factory=lambda: "abcd4444")
    index_path = paths.derived / "playbook-index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["profiles"]["person-kushali-g"]["profile_path"] = "/etc/passwd"
    index_path.write_text(json.dumps(index), encoding="utf-8")

    summary = update(tmp_path, clock=FrozenClock(NOW), suffix_factory=lambda: "efgh5555")

    assert summary.details["profiles_written"] == 1
    assert project_status(paths)["playbook"]["status"] == "current"
