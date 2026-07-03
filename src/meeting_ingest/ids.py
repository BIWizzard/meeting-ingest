"""Immutable ID minting."""

from __future__ import annotations

from datetime import date
import re

from meeting_ingest.clock import Clock, mint_ingest_run_id as _mint_ingest_run_id
from meeting_ingest.hashing import short_hash


_DATE_WITH_DASHES = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_COMPACT_DATE = re.compile(r"^\d{8}$")


def compact_effective_date(effective_date: str | date) -> str:
    if isinstance(effective_date, date):
        return effective_date.strftime("%Y%m%d")
    if _DATE_WITH_DASHES.match(effective_date):
        return effective_date.replace("-", "")
    if _COMPACT_DATE.match(effective_date):
        return effective_date
    raise ValueError("effective_date must be YYYY-MM-DD or YYYYMMDD")


def mint_meeting_id(effective_date: str | date, source_sha256: str) -> str:
    date_part = compact_effective_date(effective_date)
    return f"mtg-{date_part}-{short_hash(source_sha256)}"


def mint_ingest_run_id(effective_date: str | date, *, clock: Clock | None = None) -> str:
    return _mint_ingest_run_id(compact_effective_date(effective_date), clock=clock)
