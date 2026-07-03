from meeting_ingest.identity import normalize_person, slugify_person_id


def test_slugify_person_id_is_deterministic() -> None:
    assert slugify_person_id("Kushali G") == "person-kushali-g"
    assert slugify_person_id(" José  Núñez ") == "person-jose-nunez"


def test_normalize_person_preserves_raw_label() -> None:
    person = normalize_person("  Kushali G  ", confidence="high")

    assert person.person_id == "person-kushali-g"
    assert person.display_name == "Kushali G"
    assert person.raw_label == "  Kushali G  "
    assert person.confidence == "high"


def test_normalize_person_does_not_invent_unknown_identity() -> None:
    person = normalize_person("Unknown")

    assert person.person_id is None
    assert person.display_name is None
    assert person.raw_label == "Unknown"
    assert person.confidence == "low"


def test_normalize_person_does_not_invent_generic_speaker_identity() -> None:
    person = normalize_person("Speaker 1")

    assert person.person_id is None
    assert person.display_name is None
    assert person.raw_label == "Speaker 1"
    assert person.confidence == "low"
