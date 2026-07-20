from datetime import UTC, datetime
import json
from pathlib import Path

import pytest

from meeting_ingest.clock import FrozenClock
from meeting_ingest.paths import init_project
from meeting_ingest.playbook import update
from meeting_ingest.playbook_review import mutate_review, read_review_state


FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 7, 19, 17, 0, tzinfo=UTC)


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


def _current_profile(paths, person_id: str = "person-kushali-g") -> dict[str, object]:
    index = json.loads((paths.derived / "playbook-index.json").read_text(encoding="utf-8"))
    profile_path = index["profiles"][person_id]["profile_path"]
    return json.loads((paths.meetings_root / profile_path).read_text(encoding="utf-8"))


def test_review_mutation_appends_valid_event_and_duplicate_is_no_op(tmp_path: Path) -> None:
    paths = _configured_project(tmp_path)
    target = {"source_id": "src-a1b2c3d4e5f6", "signal_id": "sig-a1b2c3d4e5f6-91aa2c80b731"}

    first = mutate_review(
        tmp_path,
        action="suppress_signal",
        target=target,
        reason="Bad extraction",
        actor="reviewer",
        clock=FrozenClock(NOW),
        suffix_factory=lambda: "a1b2ffff",
    )
    second = mutate_review(
        tmp_path,
        action="suppress_signal",
        target=target,
        reason="Bad extraction",
        actor="reviewer",
        clock=FrozenClock(NOW),
    )

    state = read_review_state(paths.playbook_state / "overrides.jsonl")
    assert first.details["review_event_id"] == "review-20260719T170000Z-a1b2"
    assert second.status == "no_op"
    assert state.suppressed_signals == {(target["source_id"], target["signal_id"])}
    assert state.suppressed_signal_matches[(target["source_id"], target["signal_id"])] == {
        "signal_type": "explicit_ask",
        "raw_actor": "g, kushali",
        "locator_scheme": "timestamp",
        "locator_value": "09:18",
    }
    assert len(state.valid_events) == 1


def test_malformed_review_events_are_ignored_and_reported(tmp_path: Path) -> None:
    path = tmp_path / "overrides.jsonl"
    path.write_text('{"action":"reject_entry"}\nnot json\n', encoding="utf-8")

    state = read_review_state(path)

    assert state.valid_events == []
    assert [issue.code for issue in state.issues] == ["review_event_malformed", "review_event_malformed"]


def test_unsuppress_removes_signal_match_snapshot_from_folded_state(tmp_path: Path) -> None:
    paths = _configured_project(tmp_path)
    target = {"source_id": "src-a1b2c3d4e5f6", "signal_id": "sig-a1b2c3d4e5f6-91aa2c80b731"}
    mutate_review(
        tmp_path,
        action="suppress_signal",
        target=target,
        reason="Bad extraction",
        clock=FrozenClock(NOW),
        suffix_factory=lambda: "1111aaaa",
    )
    mutate_review(
        tmp_path,
        action="unsuppress_signal",
        target=target,
        note="Extraction was valid",
        clock=FrozenClock(NOW),
        suffix_factory=lambda: "2222bbbb",
    )

    state = read_review_state(paths.playbook_state / "overrides.jsonl")

    assert state.suppressed_signals == set()
    assert state.suppressed_signal_matches == {}


def test_group_directed_signal_uses_audience_for_suppression_match_without_person_profile(
    tmp_path: Path,
) -> None:
    paths = _configured_project(tmp_path)
    signal_path = paths.signals / "signal.jsonl"
    signal = json.loads(signal_path.read_text(encoding="utf-8"))
    signal["stakeholder_id"] = None
    signal["stakeholder_name"] = "Revenue Team"
    signal["stakeholder_name_raw"] = None
    signal["audience_id"] = "group-revenue-team"
    signal["audience_name"] = "Revenue Team"
    signal_path.write_text(json.dumps(signal) + "\n", encoding="utf-8")

    summary = update(tmp_path, clock=FrozenClock(NOW), suffix_factory=lambda: "1111aaaa")
    mutate_review(
        tmp_path,
        action="suppress_signal",
        target={"source_id": signal["source"]["source_id"], "signal_id": signal["signal_id"]},
        reason="Bad extraction",
        clock=FrozenClock(NOW),
        suffix_factory=lambda: "2222bbbb",
    )
    state = read_review_state(paths.playbook_state / "overrides.jsonl")

    assert summary.details["profiles_written"] == 0
    assert next(iter(state.suppressed_signal_matches.values()))["raw_actor"] == "revenue team"


def test_review_mutation_validates_required_reason_note_and_resolution_state(tmp_path: Path) -> None:
    _configured_project(tmp_path)

    with pytest.raises(ValueError, match="require a reason"):
        mutate_review(
            tmp_path,
            action="reject_entry",
            target={"entry_id": "entry-person-test-ask-123456789abc"},
        )
    with pytest.raises(ValueError, match="supported resolution_state"):
        mutate_review(
            tmp_path,
            action="resolve_tracked_item",
            target={"entry_id": "entry-person-test-ask-123456789abc", "resolution_state": "open"},
            note="Reviewed",
        )


def test_rebuild_applies_reject_and_resolution_overlays_and_records_recent_changes(tmp_path: Path) -> None:
    paths = _configured_project(tmp_path)
    update(tmp_path, clock=FrozenClock(NOW), suffix_factory=lambda: "1111aaaa")
    first_profile = _current_profile(paths)
    entry_id = first_profile["tracked_asks"][0]["entry_id"]

    mutate_review(
        tmp_path,
        action="reject_entry",
        target={"entry_id": entry_id},
        reason="Not relevant",
        clock=FrozenClock(NOW),
        suffix_factory=lambda: "2222aaaa",
    )
    mutate_review(
        tmp_path,
        action="resolve_tracked_item",
        target={"entry_id": entry_id, "resolution_state": "resolved"},
        note="Confirmed delivered",
        clock=FrozenClock(NOW),
        suffix_factory=lambda: "3333aaaa",
    )
    update(tmp_path, clock=FrozenClock(NOW), suffix_factory=lambda: "4444aaaa")

    profile = _current_profile(paths)
    entry = profile["tracked_asks"][0]
    assert entry["review_state"] == "rejected"
    assert entry["resolution_state"] == "resolved"
    assert entry["resolution_source"] == "review-20260719T170000Z-3333"
    assert profile["recent_changes"] == [
        {
            "entry_id": entry_id,
            "change_kinds": ["review_state_changed"],
            "review_state": {"prior": "unreviewed", "current": "rejected"},
        }
    ]


def test_suppressed_signal_is_excluded_without_changing_input_eligibility(tmp_path: Path) -> None:
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

    summary = update(tmp_path, clock=FrozenClock(NOW), suffix_factory=lambda: "bbbb2222")
    index = json.loads((paths.derived / "playbook-index.json").read_text(encoding="utf-8"))

    assert summary.details["profiles_written"] == 0
    assert index["profiles"] == {}


def test_exact_tag_grouping_promotes_recurrence_across_distinct_sources(tmp_path: Path) -> None:
    paths = _configured_project(tmp_path)
    first = json.loads((paths.signals / "signal.jsonl").read_text(encoding="utf-8"))
    first["signal_type"] = "stakeholder_priority"
    first["summary"] = "Source clarity matters."
    (paths.signals / "signal.jsonl").write_text(json.dumps(first) + "\n", encoding="utf-8")
    second = json.loads(json.dumps(first))
    second["signal_id"] = "sig-bbbbbbbbbbbb-222222222222"
    second["source"]["source_id"] = "src-bbbbbbbbbbbb"
    second["source"]["source_sha256"] = "b" * 64
    second["source"]["meeting_id"] = "mtg-20260710-bbbbbbbb"
    second["meeting_id"] = "mtg-20260710-bbbbbbbb"
    second["effective_at"] = "2026-07-10"
    second["timing"]["occurred"]["value"] = "2026-07-10"
    (paths.signals / "second.jsonl").write_text(json.dumps(second) + "\n", encoding="utf-8")

    update(tmp_path, clock=FrozenClock(NOW), suffix_factory=lambda: "cccc3333")

    entry = _current_profile(paths)["priorities"][0]
    assert entry["recurrence"] == "recurring"
    assert entry["distinct_source_count"] == 2
    assert len(entry["supporting_observations"]) == 2
    assert entry["first_observed_at"] == "2026-07-03"
    assert entry["last_observed_at"] == "2026-07-10"


def test_aggregated_group_uses_lowest_confidence_for_unresolved_routing(tmp_path: Path) -> None:
    paths = _configured_project(tmp_path)
    first = json.loads((paths.signals / "signal.jsonl").read_text(encoding="utf-8"))
    first["signal_type"] = "stakeholder_priority"
    first["summary"] = "Source clarity matters."
    (paths.signals / "signal.jsonl").write_text(json.dumps(first) + "\n", encoding="utf-8")
    second = json.loads(json.dumps(first))
    second["confidence"] = "low"
    second["signal_id"] = "sig-cccccccccccc-333333333333"
    second["source"]["source_id"] = "src-cccccccccccc"
    second["source"]["source_sha256"] = "c" * 64
    (paths.signals / "second.jsonl").write_text(json.dumps(second) + "\n", encoding="utf-8")

    update(tmp_path, clock=FrozenClock(NOW), suffix_factory=lambda: "dddd4444")

    profile = _current_profile(paths)
    assert profile["priorities"] == []
    assert profile["unresolved_observations"][0]["confidence"] == "low"
