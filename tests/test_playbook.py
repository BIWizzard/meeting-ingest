from datetime import UTC, datetime
import json
from pathlib import Path

import pytest

from meeting_ingest.clock import FrozenClock
from meeting_ingest.errors import MeetingIngestError
from meeting_ingest.paths import init_project
from meeting_ingest.playbook import discover_inputs, update


FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 7, 19, 16, 30, tzinfo=UTC)


def _configured_project(tmp_path: Path):
    paths = init_project(tmp_path)
    (paths.playbook_state / "stakeholders.toml").write_text(
        (FIXTURES / "stakeholders" / "reviewed.toml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (paths.signals / "mtg-20260703-a1b2c3d4.jsonl").write_text(
        (FIXTURES / "signals" / "schema-1.1-meeting.jsonl").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return paths


def test_playbook_update_commits_generation_ledger_then_index(tmp_path: Path) -> None:
    paths = _configured_project(tmp_path)

    summary = update(
        tmp_path,
        clock=FrozenClock(NOW),
        suffix_factory=lambda: "a1b2c3d4",
    )

    run_id = "derive-20260719-20260719T163000Z-a1b2"
    generation = paths.derived / "generations" / run_id
    index = json.loads((paths.derived / "playbook-index.json").read_text(encoding="utf-8"))
    ledger = [
        json.loads(line)
        for line in (paths.playbook_state / "derivation-ledger.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    profile = json.loads(
        (generation / "stakeholders" / "person-kushali-g" / "profile.json").read_text(encoding="utf-8")
    )

    assert summary.details["derivation_run_id"] == run_id
    assert summary.details["profiles_written"] == 1
    assert index["derivation_run_id"] == run_id
    assert index["generation_path"] == f"_derived/generations/{run_id}"
    assert index["input_fingerprint"] == ledger[0]["input_fingerprint"]
    assert ledger[0]["event"] == "briefing_derivation_completed"
    assert ledger[0]["profiles"][0]["person_id"] == "person-kushali-g"
    assert profile["coverage"] == {
        "source_count": 1,
        "source_kinds": {"meeting_transcript": 1},
        "first_observed_at": "2026-07-03",
        "last_observed_at": "2026-07-03",
    }
    assert profile["tracked_asks"][0]["entry_id"].startswith("entry-person-kushali-g-ask-")
    assert profile["tracked_asks"][0]["resolution_state"] == "unknown"
    assert (generation / "stakeholders" / "person-kushali-g" / "briefing.md").exists()
    assert (generation / "identity-candidates.json").exists()


def test_rebuild_keeps_fingerprint_and_entry_identity_stable_across_generations(tmp_path: Path) -> None:
    paths = _configured_project(tmp_path)

    first = update(tmp_path, clock=FrozenClock(NOW), suffix_factory=lambda: "1111aaaa")
    second = update(tmp_path, clock=FrozenClock(NOW), suffix_factory=lambda: "2222bbbb")

    def read_profile(run_id: str) -> dict[str, object]:
        path = paths.derived / "generations" / run_id / "stakeholders/person-kushali-g/profile.json"
        return json.loads(path.read_text(encoding="utf-8"))

    first_profile = read_profile(first.details["derivation_run_id"])
    second_profile = read_profile(second.details["derivation_run_id"])
    assert first.details["input_fingerprint"] == second.details["input_fingerprint"]
    assert first_profile["tracked_asks"][0]["entry_id"] == second_profile["tracked_asks"][0]["entry_id"]
    assert len(list((paths.derived / "generations").iterdir())) == 2


def test_schema_1_0_file_requires_source_ledger_mapping_for_eligibility(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    fixture = FIXTURES / "signals" / "schema-1.0-meeting.jsonl"
    signal_path = paths.signals / "legacy.jsonl"
    signal_path.write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")

    excluded = discover_inputs(paths)
    assert excluded.eligible_files == ()
    assert excluded.warnings == ("excluded _signals/legacy.jsonl: signal_identity_invalid",)

    signal = json.loads(fixture.read_text(encoding="utf-8"))
    source_hash = "a" * 64
    paths.ledger.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "event": "ingest_completed",
                "source_sha256": source_hash,
                "meeting_id": signal["meeting_id"],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    included = discover_inputs(paths)
    assert included.eligible_files[0]["path"] == "_signals/legacy.jsonl"
    assert included.observations[0].source_id == "src-aaaaaaaaaaaa"


def test_index_does_not_advance_when_derivation_ledger_commit_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _configured_project(tmp_path)

    def fail_commit(*args, **kwargs):
        raise MeetingIngestError(
            phase="playbook_ledger",
            code="test_commit_failed",
            message="commit failed",
            exit_code=9,
            recoverable=True,
        )

    monkeypatch.setattr("meeting_ingest.playbook._append_derivation_record", fail_commit)

    with pytest.raises(MeetingIngestError, match="commit failed"):
        update(tmp_path, clock=FrozenClock(NOW), suffix_factory=lambda: "deadbeef")

    assert not (paths.derived / "playbook-index.json").exists()
    assert (paths.derived / "generations" / "derive-20260719-20260719T163000Z-dead").is_dir()


def test_playbook_update_honors_configured_derived_directory(tmp_path: Path) -> None:
    paths = _configured_project(tmp_path)
    config = paths.config_path.read_text(encoding="utf-8")
    paths.config_path.write_text(config.replace('derived = "_derived"', 'derived = "generated"'), encoding="utf-8")

    summary = update(tmp_path, clock=FrozenClock(NOW), suffix_factory=lambda: "cafe1234")

    assert summary.artifacts[0]["path"] == "generated/playbook-index.json"
    assert (paths.meetings_root / "generated" / "playbook-index.json").exists()
