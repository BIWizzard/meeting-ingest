from datetime import UTC, datetime
import json
from pathlib import Path

import pytest

from meeting_ingest.clock import FrozenClock
from meeting_ingest.doctor import find_issues, project_status
from meeting_ingest.errors import MeetingIngestError
from meeting_ingest.paths import init_project
from meeting_ingest.playbook import brief, repair_index, show, update
from meeting_ingest.playbook_review import mutate_review
from meeting_ingest.playbook_status import _nearest_successor


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


def test_repair_index_replaces_corrupted_index_json(tmp_path: Path) -> None:
    paths = _configured_project(tmp_path)
    update(tmp_path, clock=FrozenClock(NOW), suffix_factory=lambda: "abcd1111")
    expected = json.loads((paths.derived / "playbook-index.json").read_text(encoding="utf-8"))
    (paths.derived / "playbook-index.json").write_text("{broken", encoding="utf-8")

    repair_index(tmp_path, clock=FrozenClock(NOW))

    assert json.loads((paths.derived / "playbook-index.json").read_text(encoding="utf-8")) == expected


def test_repair_index_rejects_ledger_profile_path_outside_meetings_root(tmp_path: Path) -> None:
    paths = _configured_project(tmp_path)
    update(tmp_path, clock=FrozenClock(NOW), suffix_factory=lambda: "abcd1111")
    ledger_path = paths.playbook_state / "derivation-ledger.jsonl"
    record = json.loads(ledger_path.read_text(encoding="utf-8"))
    record["profiles"][0]["profile_path"] = "../outside/profile.json"
    ledger_path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    (paths.derived / "playbook-index.json").unlink()

    with pytest.raises(MeetingIngestError, match="escapes the meetings root"):
        repair_index(tmp_path, clock=FrozenClock(NOW))

    assert not (paths.derived / "playbook-index.json").exists()


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


def test_doctor_reports_suppressed_signal_reemerging_under_new_id(tmp_path: Path) -> None:
    paths = _configured_project(tmp_path)
    target = {"source_id": "src-a1b2c3d4e5f6", "signal_id": "sig-a1b2c3d4e5f6-91aa2c80b731"}
    mutate_review(
        tmp_path,
        action="suppress_signal",
        target=target,
        reason="Bad extraction",
        clock=FrozenClock(NOW),
        suffix_factory=lambda: "aaaa1111",
    )
    signal_path = paths.signals / "signal.jsonl"
    regenerated = json.loads(signal_path.read_text(encoding="utf-8"))
    regenerated["signal_id"] = "sig-a1b2c3d4e5f6-222222222222"
    signal_path.write_text(json.dumps(regenerated) + "\n", encoding="utf-8")

    issues = find_issues(paths)
    reemerged = [issue for issue in issues if issue.code == "signal_suppression_reemerged"]

    assert len(reemerged) == 1
    assert target["signal_id"] in reemerged[0].message
    assert regenerated["signal_id"] in reemerged[0].message


@pytest.mark.parametrize("difference", ("locator", "actor", "signal_type", "source"))
def test_doctor_does_not_report_suppression_reemergence_when_identity_differs(
    tmp_path: Path, difference: str
) -> None:
    paths = _configured_project(tmp_path)
    target = {"source_id": "src-a1b2c3d4e5f6", "signal_id": "sig-a1b2c3d4e5f6-91aa2c80b731"}
    mutate_review(
        tmp_path,
        action="suppress_signal",
        target=target,
        reason="Bad extraction",
        clock=FrozenClock(NOW),
        suffix_factory=lambda: "aaaa1111",
    )
    signal_path = paths.signals / "signal.jsonl"
    regenerated = json.loads(signal_path.read_text(encoding="utf-8"))
    regenerated["signal_id"] = "sig-a1b2c3d4e5f6-333333333333"
    if difference == "locator":
        regenerated["evidence"]["locator"]["value"] = "10:42"
        regenerated["evidence"]["timestamp"] = "10:42"
    elif difference == "actor":
        regenerated["stakeholder_name_raw"] = "Different Person"
    elif difference == "signal_type":
        regenerated["signal_type"] = "risk_or_concern"
    else:
        regenerated["source"]["source_sha256"] = "b" * 64
        regenerated["source"]["source_id"] = "src-bbbbbbbbbbbb"
        regenerated["signal_id"] = "sig-bbbbbbbbbbbb-333333333333"
    signal_path.write_text(json.dumps(regenerated) + "\n", encoding="utf-8")

    assert "signal_suppression_reemerged" not in {issue.code for issue in find_issues(paths)}


def test_doctor_recovers_suppression_match_from_historical_profile(tmp_path: Path) -> None:
    paths = _configured_project(tmp_path)
    update(tmp_path, clock=FrozenClock(NOW), suffix_factory=lambda: "1111aaaa")
    target = {"source_id": "src-a1b2c3d4e5f6", "signal_id": "sig-a1b2c3d4e5f6-91aa2c80b731"}
    mutate_review(
        tmp_path,
        action="suppress_signal",
        target=target,
        reason="Bad extraction",
        clock=FrozenClock(NOW),
        suffix_factory=lambda: "2222bbbb",
    )
    review_path = paths.playbook_state / "overrides.jsonl"
    legacy_event = json.loads(review_path.read_text(encoding="utf-8"))
    legacy_event.pop("suppression_match")
    review_path.write_text(json.dumps(legacy_event) + "\n", encoding="utf-8")
    signal_path = paths.signals / "signal.jsonl"
    regenerated = json.loads(signal_path.read_text(encoding="utf-8"))
    regenerated["signal_id"] = "sig-a1b2c3d4e5f6-444444444444"
    signal_path.write_text(json.dumps(regenerated) + "\n", encoding="utf-8")

    assert "signal_suppression_reemerged" in {issue.code for issue in find_issues(paths)}


def test_doctor_hints_nearest_successor_for_orphaned_entry_review(tmp_path: Path) -> None:
    paths = _configured_project(tmp_path)
    first_path = paths.signals / "signal.jsonl"
    first = json.loads(first_path.read_text(encoding="utf-8"))
    first["signal_type"] = "stakeholder_priority"
    first["summary"] = "Source clarity matters."
    first_path.write_text(json.dumps(first) + "\n", encoding="utf-8")
    second = json.loads(json.dumps(first))
    second["signal_id"] = "sig-bbbbbbbbbbbb-222222222222"
    second["source"]["source_id"] = "src-bbbbbbbbbbbb"
    second["source"]["source_sha256"] = "b" * 64
    second["source"]["meeting_id"] = "mtg-20260710-bbbbbbbb"
    second["meeting_id"] = "mtg-20260710-bbbbbbbb"
    second["effective_at"] = "2026-07-10"
    second["timing"]["occurred"]["value"] = "2026-07-10"
    (paths.signals / "second.jsonl").write_text(json.dumps(second) + "\n", encoding="utf-8")
    update(tmp_path, clock=FrozenClock(NOW), suffix_factory=lambda: "1111aaaa")
    first_index = json.loads((paths.derived / "playbook-index.json").read_text(encoding="utf-8"))
    first_profile_path = first_index["profiles"]["person-kushali-g"]["profile_path"]
    first_profile = json.loads((paths.meetings_root / first_profile_path).read_text(encoding="utf-8"))
    old_entry_id = first_profile["priorities"][0]["entry_id"]
    mutate_review(
        tmp_path,
        action="reject_entry",
        target={"entry_id": old_entry_id},
        reason="Not relevant",
        clock=FrozenClock(NOW),
        suffix_factory=lambda: "2222bbbb",
    )
    mutate_review(
        tmp_path,
        action="suppress_signal",
        target={"source_id": first["source"]["source_id"], "signal_id": first["signal_id"]},
        reason="Bad extraction",
        clock=FrozenClock(NOW),
        suffix_factory=lambda: "3333cccc",
    )
    update(tmp_path, clock=FrozenClock(NOW), suffix_factory=lambda: "4444dddd")
    current_index = json.loads((paths.derived / "playbook-index.json").read_text(encoding="utf-8"))
    current_profile_path = current_index["profiles"]["person-kushali-g"]["profile_path"]
    current_profile = json.loads((paths.meetings_root / current_profile_path).read_text(encoding="utf-8"))
    successor_id = current_profile["priorities"][0]["entry_id"]

    issues = find_issues(paths)
    orphaned = [issue for issue in issues if issue.code == "review_event_orphaned" and old_entry_id in issue.message]

    assert len(orphaned) == 1
    assert f"Nearest current successor: {successor_id}." in orphaned[0].message


def test_nearest_successor_rejects_incompatible_candidates() -> None:
    shared = {"source_id": "src-aaaaaaaaaaaa", "signal_id": "sig-aaaaaaaaaaaa-111111111111"}
    old_entry = _successor_entry("priority", "teams", [shared])
    historical = {"entry-old": ("person-one", old_entry)}
    current = {
        "entry-other-person": ("person-two", _successor_entry("priority", "teams", [shared])),
        "entry-other-kind": ("person-one", _successor_entry("concern", "teams", [shared])),
        "entry-other-channel": ("person-one", _successor_entry("priority", "email", [shared])),
        "entry-no-overlap": (
            "person-one",
            _successor_entry(
                "priority",
                "teams",
                [{"source_id": "src-bbbbbbbbbbbb", "signal_id": "sig-bbbbbbbbbbbb-222222222222"}],
            ),
        ),
    }

    assert _nearest_successor("entry-old", historical, current) is None


def test_nearest_successor_uses_entry_id_as_final_deterministic_tie_break() -> None:
    shared = {"source_id": "src-aaaaaaaaaaaa", "signal_id": "sig-aaaaaaaaaaaa-111111111111"}
    old_entry = _successor_entry("priority", "teams", [shared])
    candidate = _successor_entry("priority", "teams", [shared])

    successor = _nearest_successor(
        "entry-old",
        {"entry-old": ("person-one", old_entry)},
        {
            "entry-z-successor": ("person-one", candidate),
            "entry-a-successor": ("person-one", candidate),
        },
    )

    assert successor == "entry-a-successor"


def _successor_entry(
    entry_kind: str, channel: str, references: list[dict[str, str]]
) -> dict[str, object]:
    return {
        "entry_kind": entry_kind,
        "scope": {"channel": channel, "project_refs": ["project-a"], "topics": ["topic-a"]},
        "supporting_observations": references,
    }
