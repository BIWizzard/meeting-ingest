from datetime import UTC, datetime
from pathlib import Path

import pytest

from meeting_ingest.clock import FrozenClock
from meeting_ingest.errors import LockConflictError
from meeting_ingest.locking import ProjectLock, inspect_lock, lock_path
from meeting_ingest.paths import init_project
from meeting_ingest.pipeline import doctor, ingest
from meeting_ingest.readiness import RuntimeReadinessError


def test_project_lock_creates_and_removes_lockfile(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    path = lock_path(paths.cache)

    with ProjectLock(path, clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC))):
        assert path.exists()
        info = inspect_lock(path, clock=FrozenClock(datetime(2026, 7, 3, 12, 1, tzinfo=UTC)))
        assert info is not None
        assert info.created_at == "20260703T120000Z"
        assert info.stale is False

    assert not path.exists()


def test_project_lock_conflict_raises_typed_error(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    path = lock_path(paths.cache)

    with ProjectLock(path):
        with pytest.raises(LockConflictError):
            with ProjectLock(path):
                pass


def test_ingest_fails_with_lock_conflict(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")

    with ProjectLock(lock_path(paths.cache)):
        with pytest.raises(RuntimeReadinessError) as exc:
            ingest(source, start=paths.inbox)

    assert exc.value.code == "lock_conflict"
    assert exc.value.exit_code == 12
    assert source.exists()


def test_doctor_reports_stale_lock(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    path = lock_path(paths.cache)
    path.write_text('{"pid": 123, "created_at": "not-a-timestamp"}\n', encoding="utf-8")

    summary = doctor(tmp_path)

    assert {
        "code": "stale_lock",
        "message": "Project lock appears stale.",
        "path": "_cache/meeting-ingest.lock",
    } in summary.details["issues"]
