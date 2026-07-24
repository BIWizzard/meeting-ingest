"""Human-reviewed stakeholder registry and deterministic identity resolution."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import re
import tomllib
import unicodedata

from meeting_ingest.identity import normalize_display_name, slugify_person_id
from meeting_ingest.errors import EXIT_ARTIFACT_WRITE, MeetingIngestError
from meeting_ingest.schema import SignalRecord


REGISTRY_SCHEMA_VERSION = "1.0"
_PERSON_ID = re.compile(r"^person-[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class Stakeholder:
    person_id: str
    display_name: str
    aliases: tuple[str, ...]
    status: str


@dataclass(frozen=True)
class RegistryIssue:
    code: str
    message: str
    alias: str | None = None


@dataclass(frozen=True)
class IdentityResolution:
    status: str
    raw_name: str
    normalized_name: str
    person_id: str | None
    display_name: str | None
    reason: str


@dataclass(frozen=True)
class IdentityCandidate:
    raw_name: str
    normalized_name: str
    signal_count: int
    source_count: int
    suggested_person_id: str | None
    reason: str


@dataclass(frozen=True)
class StakeholderRegistry:
    people: tuple[Stakeholder, ...]
    issues: tuple[RegistryIssue, ...] = ()

    def resolve(self, raw_name: str) -> IdentityResolution:
        normalized = normalize_registry_name(raw_name)
        alias_matches = self._alias_matches(normalized)
        display_matches = [
            person for person in self.people if normalize_registry_name(person.display_name) == normalized
        ]
        matches = {person.person_id: person for person in (*alias_matches, *display_matches)}
        if len(matches) == 1:
            person = next(iter(matches.values()))
            return IdentityResolution(
                status="reviewed",
                raw_name=raw_name,
                normalized_name=display_normalized_name(raw_name),
                person_id=person.person_id,
                display_name=person.display_name,
                reason="reviewed_alias" if alias_matches else "reviewed_display_name",
            )
        if len(matches) > 1:
            return _unresolved(raw_name, "ambiguous_reviewed_alias", status="ambiguous")
        return _unresolved(raw_name, "unresolved_identity")

    def _alias_matches(self, normalized: str) -> list[Stakeholder]:
        return [
            person
            for person in self.people
            if normalized in {normalize_registry_name(alias) for alias in person.aliases}
        ]


def read_stakeholder_registry(path: Path) -> StakeholderRegistry:
    if not path.exists():
        return StakeholderRegistry(people=())
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        return StakeholderRegistry(
            people=(),
            issues=(RegistryIssue("identity_registry_invalid", f"Stakeholder registry is invalid: {exc}"),),
        )

    if payload.get("schema_version") != REGISTRY_SCHEMA_VERSION:
        return StakeholderRegistry(
            people=(),
            issues=(
                RegistryIssue(
                    "identity_registry_invalid",
                    f"Unsupported stakeholder registry schema_version {payload.get('schema_version')!r}.",
                ),
            ),
        )
    issues: list[RegistryIssue] = []
    raw_people = payload.get("people", [])
    if not isinstance(raw_people, list):
        return StakeholderRegistry(
            people=(),
            issues=(*issues, RegistryIssue("identity_registry_invalid", "Registry people must be an array.")),
        )

    people: list[Stakeholder] = []
    seen_ids: set[str] = set()
    for index, raw_person in enumerate(raw_people):
        if not isinstance(raw_person, dict):
            issues.append(RegistryIssue("identity_registry_invalid", f"people[{index}] must be a table."))
            continue
        person_id = raw_person.get("person_id")
        display_name = raw_person.get("display_name")
        aliases = raw_person.get("aliases")
        status = raw_person.get("status")
        if not isinstance(person_id, str) or not _PERSON_ID.fullmatch(person_id):
            issues.append(RegistryIssue("identity_registry_invalid", f"people[{index}].person_id is invalid."))
            continue
        if person_id in seen_ids:
            issues.append(RegistryIssue("identity_registry_invalid", f"Duplicate person_id {person_id!r}."))
            continue
        seen_ids.add(person_id)
        if not isinstance(display_name, str) or not display_name.strip():
            issues.append(RegistryIssue("identity_registry_invalid", f"people[{index}].display_name is required."))
            continue
        if not isinstance(aliases, list) or any(not isinstance(alias, str) or not alias.strip() for alias in aliases):
            issues.append(RegistryIssue("identity_registry_invalid", f"people[{index}].aliases must be strings."))
            continue
        if status != "reviewed":
            issues.append(RegistryIssue("identity_registry_invalid", f"people[{index}].status must be 'reviewed'."))
            continue
        people.append(Stakeholder(person_id, display_name, tuple(aliases), status))

    aliases_by_person: dict[str, set[str]] = {}
    for person in people:
        for alias in (*person.aliases, person.display_name):
            aliases_by_person.setdefault(normalize_registry_name(alias), set()).add(person.person_id)
    for alias, person_ids in sorted(aliases_by_person.items()):
        if len(person_ids) > 1:
            issues.append(
                RegistryIssue(
                    "identity_alias_ambiguous",
                    f"Reviewed alias {alias!r} belongs to multiple people: {', '.join(sorted(person_ids))}.",
                    alias=alias,
                )
            )
    return StakeholderRegistry(people=tuple(people), issues=tuple(issues))


def collect_identity_candidates(
    signals: list[SignalRecord], registry: StakeholderRegistry
) -> list[IdentityCandidate]:
    grouped: dict[tuple[str, str], dict[str, object]] = {}
    for signal in signals:
        raw_name = signal.stakeholder_name_raw if signal.schema_version == "1.1" else signal.stakeholder_name
        if not raw_name:
            continue
        resolution = registry.resolve(raw_name)
        if resolution.status == "reviewed":
            continue
        key = (normalize_registry_name(raw_name), resolution.reason)
        item = grouped.setdefault(
            key,
            {"raw_names": set(), "signal_count": 0, "source_ids": set()},
        )
        item["raw_names"].add(raw_name)  # type: ignore[union-attr]
        item["signal_count"] = int(item["signal_count"]) + 1
        source_id = signal.source.source_id if signal.source is not None else signal.meeting_id
        if source_id:
            item["source_ids"].add(source_id)  # type: ignore[union-attr]

    candidates: list[IdentityCandidate] = []
    for (_, reason), item in sorted(grouped.items()):
        raw_names = sorted(item["raw_names"])  # type: ignore[arg-type]
        display_name = normalize_display_name(raw_names[0])
        suggested = slugify_person_id(display_name) if display_name is not None else None
        candidate_reason = "generic_or_ambiguous_label" if display_name is None else reason
        candidates.append(
            IdentityCandidate(
                raw_name=raw_names[0],
                normalized_name=display_normalized_name(raw_names[0]),
                signal_count=int(item["signal_count"]),
                source_count=len(item["source_ids"]),  # type: ignore[arg-type]
                suggested_person_id=suggested,
                reason=candidate_reason,
            )
        )
    return candidates


def write_identity_candidates(
    path: Path,
    candidates: list[IdentityCandidate],
    *,
    generated_at: str,
    provenance: dict[str, object] | None = None,
    derivation_run_id: str | None = None,
) -> None:
    payload = {
        "schema_version": "2.0" if provenance is not None else "1.0",
        "generated_at": generated_at,
        **({"derivation_run_id": derivation_run_id} if derivation_run_id is not None else {}),
        "candidates": [asdict(candidate) for candidate in candidates],
        **(provenance or {}),
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise MeetingIngestError(
            phase="identity_candidates_write",
            code="identity_candidates_write_failed",
            message=f"Could not write identity candidates: {path}",
            exit_code=EXIT_ARTIFACT_WRITE,
            recoverable=True,
            details={"path": str(path)},
        ) from exc


def normalize_registry_name(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).strip().split()).casefold()


def display_normalized_name(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).strip().split())


def _unresolved(raw_name: str, reason: str, *, status: str = "unresolved") -> IdentityResolution:
    return IdentityResolution(
        status=status,
        raw_name=raw_name,
        normalized_name=display_normalized_name(raw_name),
        person_id=None,
        display_name=None,
        reason=reason,
    )
