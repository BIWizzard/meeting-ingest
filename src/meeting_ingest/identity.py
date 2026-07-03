"""V1 person identity normalization.

V1 intentionally does not maintain a roster. It preserves raw labels and creates
deterministic local IDs only when a display name has enough signal.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata


_UNKNOWN_LABELS = {"", "unknown", "speaker", "participant", "attendee", "unidentified"}
_GENERIC_LABEL = re.compile(r"^(speaker|participant|attendee)\s*\d+$", re.IGNORECASE)


@dataclass(frozen=True)
class PersonReference:
    person_id: str | None
    display_name: str | None
    raw_label: str
    confidence: str


def normalize_display_name(raw_label: str) -> str | None:
    normalized = " ".join(raw_label.strip().split())
    if not normalized:
        return None
    if normalized.lower() in _UNKNOWN_LABELS or _GENERIC_LABEL.match(normalized):
        return None
    return normalized


def slugify_person_id(display_name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", display_name).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    if not slug:
        return "person-unresolved"
    return f"person-{slug}"


def normalize_person(raw_label: str, *, confidence: str = "medium") -> PersonReference:
    display_name = normalize_display_name(raw_label)
    if display_name is None:
        return PersonReference(
            person_id=None,
            display_name=None,
            raw_label=raw_label,
            confidence="low",
        )
    return PersonReference(
        person_id=slugify_person_id(display_name),
        display_name=display_name,
        raw_label=raw_label,
        confidence=confidence,
    )
