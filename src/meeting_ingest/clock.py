"""Injectable clock and run ID helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable, Protocol
from uuid import uuid4


class Clock(Protocol):
    def now_utc(self) -> datetime:
        """Return the current UTC timestamp."""


class SystemClock:
    def now_utc(self) -> datetime:
        return datetime.now(UTC)


@dataclass(frozen=True)
class FrozenClock:
    value: datetime

    def now_utc(self) -> datetime:
        if self.value.tzinfo is None:
            return self.value.replace(tzinfo=UTC)
        return self.value.astimezone(UTC)


def format_timestamp(value: datetime) -> str:
    utc_value = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
    return utc_value.strftime("%Y%m%dT%H%M%SZ")


def format_iso_timestamp(value: datetime) -> str:
    utc_value = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
    return utc_value.strftime("%Y-%m-%dT%H:%M:%SZ")


def default_suffix() -> str:
    return uuid4().hex[:8]


def mint_ingest_run_id(
    effective_date: str,
    *,
    clock: Clock | None = None,
    suffix_factory: Callable[[], str] = default_suffix,
) -> str:
    active_clock = clock or SystemClock()
    timestamp = format_timestamp(active_clock.now_utc())
    return f"ingest-{effective_date}-{timestamp}-{suffix_factory()}"
