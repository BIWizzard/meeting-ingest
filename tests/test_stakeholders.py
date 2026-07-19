from dataclasses import replace
from pathlib import Path

from meeting_ingest.signals import read_signal_jsonl
import json

from meeting_ingest.stakeholders import (
    collect_identity_candidates,
    read_stakeholder_registry,
    write_identity_candidates,
)


FIXTURES = Path(__file__).parent / "fixtures"


def test_reviewed_alias_resolves_retroactively_without_signal_rewrite() -> None:
    signal = read_signal_jsonl(FIXTURES / "signals" / "schema-1.1-meeting.jsonl")[0]
    registry = read_stakeholder_registry(FIXTURES / "stakeholders" / "reviewed.toml")

    resolution = registry.resolve(signal.stakeholder_name_raw or "")

    assert signal.stakeholder_id == "person-kushali-g"
    assert resolution.person_id == "person-kushali-g"
    assert resolution.status == "reviewed"
    assert resolution.reason == "reviewed_alias"


def test_stored_signal_identity_is_ignored_in_favor_of_registry() -> None:
    signal = read_signal_jsonl(FIXTURES / "signals" / "schema-1.1-meeting.jsonl")[0]
    signal = replace(signal, stakeholder_id="person-wrong")
    registry = read_stakeholder_registry(FIXTURES / "stakeholders" / "reviewed.toml")

    resolution = registry.resolve(signal.stakeholder_name_raw or "")

    assert resolution.person_id == "person-kushali-g"


def test_ambiguous_reviewed_alias_resolves_to_neither_person() -> None:
    registry = read_stakeholder_registry(FIXTURES / "stakeholders" / "ambiguous.toml")

    resolution = registry.resolve("  ALEX ")

    assert resolution.status == "ambiguous"
    assert resolution.person_id is None
    assert [issue.code for issue in registry.issues] == ["identity_alias_ambiguous"]


def test_unresolved_identity_candidates_count_signals_and_sources() -> None:
    signal = read_signal_jsonl(FIXTURES / "signals" / "schema-1.1-meeting.jsonl")[0]
    unresolved = replace(signal, stakeholder_name_raw="New Person", stakeholder_id="person-provider-guess")
    second = replace(unresolved, signal_id=f"{signal.signal_id}-2", stakeholder_name_raw="new person")
    registry = read_stakeholder_registry(FIXTURES / "stakeholders" / "reviewed.toml")

    candidates = collect_identity_candidates([unresolved, second], registry)

    assert len(candidates) == 1
    assert candidates[0].raw_name == "New Person"
    assert candidates[0].signal_count == 2
    assert candidates[0].source_count == 1
    assert candidates[0].suggested_person_id == "person-new-person"


def test_alias_and_other_person_display_name_collision_is_ambiguous(tmp_path: Path) -> None:
    path = tmp_path / "stakeholders.toml"
    path.write_text(
        """schema_version = "1.0"

[[people]]
person_id = "person-alex-one"
display_name = "Alex One"
aliases = ["Shared Name"]
status = "reviewed"

[[people]]
person_id = "person-shared-name"
display_name = "Shared Name"
aliases = []
status = "reviewed"
""",
        encoding="utf-8",
    )

    registry = read_stakeholder_registry(path)
    resolution = registry.resolve("Shared Name")

    assert resolution.status == "ambiguous"
    assert resolution.person_id is None


def test_unsupported_registry_schema_exposes_no_usable_people(tmp_path: Path) -> None:
    source = (FIXTURES / "stakeholders" / "reviewed.toml").read_text(encoding="utf-8")
    path = tmp_path / "stakeholders.toml"
    path.write_text(source.replace('schema_version = "1.0"', 'schema_version = "2.0"'), encoding="utf-8")

    registry = read_stakeholder_registry(path)

    assert registry.people == ()
    assert [issue.code for issue in registry.issues] == ["identity_registry_invalid"]


def test_identity_candidates_write_only_to_explicit_generation_path(tmp_path: Path) -> None:
    signal = read_signal_jsonl(FIXTURES / "signals" / "schema-1.1-meeting.jsonl")[0]
    signal = replace(signal, stakeholder_name_raw="New Person")
    candidates = collect_identity_candidates([signal], read_stakeholder_registry(tmp_path / "missing.toml"))
    path = tmp_path / "_derived" / "generations" / "derive-1" / "identity-candidates.json"

    write_identity_candidates(path, candidates, generated_at="2026-07-19T15:00:00Z")

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload == {
        "schema_version": "1.0",
        "generated_at": "2026-07-19T15:00:00Z",
        "candidates": [
            {
                "raw_name": "New Person",
                "normalized_name": "New Person",
                "signal_count": 1,
                "source_count": 1,
                "suggested_person_id": "person-new-person",
                "reason": "unresolved_identity",
            }
        ],
    }


def test_undecodable_registry_is_invalid_instead_of_crashing(tmp_path: Path) -> None:
    path = tmp_path / "stakeholders.toml"
    path.write_bytes(b"\xff\xfe\x00")

    registry = read_stakeholder_registry(path)

    assert registry.people == ()
    assert [issue.code for issue in registry.issues] == ["identity_registry_invalid"]


def test_generic_presenter_candidate_does_not_suggest_reviewed_identity(tmp_path: Path) -> None:
    signal = read_signal_jsonl(FIXTURES / "signals" / "schema-1.1-meeting.jsonl")[0]
    signal = replace(signal, stakeholder_name_raw="Presenter", stakeholder_id=None)

    candidates = collect_identity_candidates([signal], read_stakeholder_registry(tmp_path / "missing.toml"))

    assert candidates[0].suggested_person_id is None
    assert candidates[0].reason == "generic_or_ambiguous_label"
