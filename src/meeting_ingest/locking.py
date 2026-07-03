"""Coarse project lockfile handling."""

from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
from types import TracebackType
from typing import Any

from meeting_ingest.clock import Clock, SystemClock, format_timestamp
from meeting_ingest.errors import LockConflictError


LOCK_FILENAME = "meeting-ingest.lock"
STALE_LOCK_SECONDS = 24 * 60 * 60


@dataclass(frozen=True)
class LockInfo:
    path: Path
    pid: int | None
    created_at: str | None
    age_seconds: float | None
    stale: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "pid": self.pid,
            "created_at": self.created_at,
            "age_seconds": self.age_seconds,
            "stale": self.stale,
        }


class ProjectLock(AbstractContextManager["ProjectLock"]):
    def __init__(self, lock_path: Path, *, clock: Clock | None = None) -> None:
        self.lock_path = lock_path
        self.clock = clock or SystemClock()
        self._acquired = False

    def __enter__(self) -> "ProjectLock":
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "pid": os.getpid(),
            "created_at": format_timestamp(self.clock.now_utc()),
        }
        try:
            fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise LockConflictError(str(self.lock_path)) from exc
        with os.fdopen(fd, "w", encoding="utf-8") as lock_file:
            json.dump(payload, lock_file, sort_keys=True)
            lock_file.write("\n")
        self._acquired = True
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        if self._acquired:
            try:
                self.lock_path.unlink()
            except FileNotFoundError:
                pass
            self._acquired = False
        return False


def lock_path(cache_path: Path) -> Path:
    return cache_path / LOCK_FILENAME


def inspect_lock(lock_file: Path, *, clock: Clock | None = None, stale_after_seconds: int = STALE_LOCK_SECONDS) -> LockInfo | None:
    if not lock_file.exists():
        return None
    active_clock = clock or SystemClock()
    pid: int | None = None
    created_at: str | None = None
    try:
        payload = json.loads(lock_file.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            pid_value = payload.get("pid")
            pid = pid_value if isinstance(pid_value, int) else None
            created_value = payload.get("created_at")
            created_at = created_value if isinstance(created_value, str) else None
    except (OSError, json.JSONDecodeError):
        pass

    created = _parse_timestamp(created_at)
    if created is None:
        age_seconds = None
        stale = True
    else:
        age_seconds = max(0.0, (active_clock.now_utc() - created).total_seconds())
        stale = age_seconds > stale_after_seconds
    return LockInfo(path=lock_file, pid=pid, created_at=created_at, age_seconds=age_seconds, stale=stale)


def _parse_timestamp(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
    except ValueError:
        return None
