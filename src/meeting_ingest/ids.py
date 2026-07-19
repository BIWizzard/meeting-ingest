"""Immutable ID minting."""

from __future__ import annotations

from datetime import date
import hashlib
import json
import re
import unicodedata
from typing import Any

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


def mint_source_id(source_sha256: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{64}", source_sha256):
        raise ValueError("source_sha256 must be 64 lowercase hexadecimal characters")
    return f"src-{source_sha256[:12]}"


def normalize_identity_actor(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).strip().split()).casefold()


def normalize_identity_evidence(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).strip().split())


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def observation_identity_hash(
    *,
    signal_type: str,
    actor_name: str,
    locator: dict[str, str | None],
    evidence_text: str,
) -> str:
    normalized_locator = _normalized_locator(locator)
    identity: dict[str, object] = {
        "signal_type": signal_type,
        "actor": normalize_identity_actor(actor_name),
    }
    if normalized_locator["scheme"] == "none":
        identity["evidence_text"] = normalize_identity_evidence(evidence_text)
    else:
        identity["evidence_locator"] = normalized_locator
    return hashlib.sha256(canonical_json(identity).encode("utf-8")).hexdigest()


def _normalized_locator(locator: dict[str, str | None]) -> dict[str, str | None]:
    scheme = normalize_identity_actor(str(locator.get("scheme") or "none"))
    raw_value = locator.get("value")
    value = normalize_identity_evidence(raw_value) if isinstance(raw_value, str) else None
    return {"scheme": scheme, "value": value}
