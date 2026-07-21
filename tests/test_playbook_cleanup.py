from datetime import UTC, datetime
import json
from pathlib import Path
import shutil

import pytest

from meeting_ingest.cli import build_parser, run
from meeting_ingest.clock import FrozenClock
from meeting_ingest.errors import MeetingIngestError
from meeting_ingest.paths import init_project
from meeting_ingest.playbook import cleanup_uncommitted, update


FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 7, 19, 19, 0, tzinfo=UTC)


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


def test_cleanup_uncommitted_supports_dry_run_then_removes_only_uncommitted_generation(
    tmp_path: Path,
) -> None:
    paths = _configured_project(tmp_path)
    older_committed = update(tmp_path, clock=FrozenClock(NOW), suffix_factory=lambda: "1111aaaa")
    current_committed = update(tmp_path, clock=FrozenClock(NOW), suffix_factory=lambda: "3333aaaa")
    orphan = paths.derived / "generations" / "derive-20260719-20260719T190000Z-2222"
    orphan.mkdir(parents=True)
    (orphan / "partial.json").write_text("{}", encoding="utf-8")

    preview = cleanup_uncommitted(tmp_path, dry_run=True, clock=FrozenClock(NOW))

    assert preview.status == "success"
    assert preview.details["changed"] is False
    assert preview.details["candidates"] == [
        "_derived/generations/derive-20260719-20260719T190000Z-2222"
    ]
    assert orphan.exists()

    result = cleanup_uncommitted(tmp_path, clock=FrozenClock(NOW))

    assert result.status == "success"
    assert result.details["removed"] == preview.details["candidates"]
    assert not orphan.exists()
    assert (paths.derived / "generations" / older_committed.details["derivation_run_id"]).is_dir()
    assert (paths.derived / "generations" / current_committed.details["derivation_run_id"]).is_dir()


def test_cleanup_uncommitted_refuses_malformed_derivation_ledger(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    candidate = paths.derived / "generations" / "derive-20260719-20260719T190000Z-3333"
    candidate.mkdir(parents=True)
    (paths.playbook_state / "derivation-ledger.jsonl").write_text("not-json\n", encoding="utf-8")

    with pytest.raises(MeetingIngestError) as exc:
        cleanup_uncommitted(tmp_path, clock=FrozenClock(NOW))

    assert exc.value.code == "cleanup_ledger_invalid"
    assert candidate.exists()


def test_cleanup_uncommitted_skips_index_reference_symlink_and_unknown_name(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    generations = paths.derived / "generations"
    indexed = generations / "derive-20260719-20260719T190000Z-4444"
    indexed.mkdir(parents=True)
    unknown = generations / "manual-backup"
    unknown.mkdir()
    outside = tmp_path / "outside-generation"
    outside.mkdir()
    symlink = generations / "derive-20260719-20260719T190000Z-5555"
    symlink.symlink_to(outside, target_is_directory=True)
    (paths.derived / "playbook-index.json").write_text(
        json.dumps({"generation_path": indexed.relative_to(paths.meetings_root).as_posix()}),
        encoding="utf-8",
    )

    result = cleanup_uncommitted(tmp_path, clock=FrozenClock(NOW))

    assert result.status == "no_op"
    assert result.details["skipped"] == [
        {
            "path": "_derived/generations/derive-20260719-20260719T190000Z-4444",
            "reason": "referenced_by_index",
        },
        {
            "path": "_derived/generations/derive-20260719-20260719T190000Z-5555",
            "reason": "symlink",
        },
        {"path": "_derived/generations/manual-backup", "reason": "unrecognized_name"},
    ]
    assert indexed.exists()
    assert symlink.is_symlink()
    assert outside.exists()
    assert unknown.exists()


def test_cleanup_uncommitted_cli_routes_dry_run(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    candidate = paths.derived / "generations" / "derive-20260719-20260719T190000Z-6666"
    candidate.mkdir(parents=True)
    args = build_parser().parse_args(
        ["playbook", "cleanup-uncommitted", "--root", str(tmp_path), "--dry-run", "--json"]
    )

    summary = run(args)

    assert summary.details["command"] == "playbook_cleanup_uncommitted"
    assert summary.details["dry_run"] is True
    assert candidate.exists()


def test_cleanup_uncommitted_refuses_symlinked_generations_root(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    paths.derived.rmdir()
    outside = tmp_path / "outside-derived"
    (outside / "generations" / "derive-20260719-20260719T190000Z-7777").mkdir(parents=True)
    paths.derived.symlink_to(outside, target_is_directory=True)

    with pytest.raises(MeetingIngestError) as exc:
        cleanup_uncommitted(tmp_path, clock=FrozenClock(NOW))

    assert exc.value.code == "cleanup_generations_path_invalid"
    assert (outside / "generations" / "derive-20260719-20260719T190000Z-7777").exists()


def test_cleanup_uncommitted_refuses_corrupted_existing_index(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    candidate = paths.derived / "generations" / "derive-20260719-20260719T190000Z-8888"
    candidate.mkdir(parents=True)
    (paths.derived / "playbook-index.json").write_text("{broken", encoding="utf-8")

    with pytest.raises(MeetingIngestError) as exc:
        cleanup_uncommitted(tmp_path, clock=FrozenClock(NOW))

    assert exc.value.code == "cleanup_index_invalid"
    assert candidate.exists()


def test_cleanup_uncommitted_reports_prior_removals_when_later_delete_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = init_project(tmp_path)
    generations = paths.derived / "generations"
    first = generations / "derive-20260719-20260719T190000Z-8888"
    second = generations / "derive-20260719-20260719T190000Z-9999"
    first.mkdir(parents=True)
    second.mkdir()
    real_rmtree = shutil.rmtree

    def fail_second(path: Path) -> None:
        if path == second:
            raise OSError("simulated delete failure")
        real_rmtree(path)

    monkeypatch.setattr("meeting_ingest.playbook.shutil.rmtree", fail_second)

    with pytest.raises(MeetingIngestError) as exc:
        cleanup_uncommitted(tmp_path, clock=FrozenClock(NOW))

    assert exc.value.code == "generation_cleanup_failed"
    assert exc.value.details == {
        "path": "_derived/generations/derive-20260719-20260719T190000Z-9999",
        "removed": ["_derived/generations/derive-20260719-20260719T190000Z-8888"],
    }
    assert not first.exists()
    assert second.exists()
