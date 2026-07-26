from meeting_ingest.transcript import TranscriptGrounding, index_normalized_transcript


def test_index_preserves_order_deduplicates_and_keeps_qualified_labels_distinct() -> None:
    transcript = """
**Graham, Ken (Contractor)** (00:39): First.
**Opeyemi, Baba** (00:51): Second.
**McCrary, Chandra (Contractor)** (01:02): Third.
**Opeyemi, Baba (Contractor)** (01:08): Fourth.
**Graham, Ken (Contractor)** (00:39): Repeated.
"""

    assert index_normalized_transcript(transcript) == TranscriptGrounding(
        speaker_labels=(
            "Graham, Ken (Contractor)",
            "Opeyemi, Baba",
            "McCrary, Chandra (Contractor)",
            "Opeyemi, Baba (Contractor)",
        ),
        timestamps=("00:39", "00:51", "01:02", "01:08"),
    )


def test_index_supports_markdown_without_timestamps_and_plain_speaker_lines() -> None:
    transcript = """
**Ken   Graham**: Markdown.
Kushali G: Plain text.
Olaleye,   Mark (Client): Qualified plain text.
Ken Graham (Contractor): Multiword qualified plain text.
"""

    assert index_normalized_transcript(transcript) == TranscriptGrounding(
        speaker_labels=(
            "Ken Graham",
            "Kushali G",
            "Olaleye, Mark (Client)",
            "Ken Graham (Contractor)",
        ),
        timestamps=(),
    )


def test_index_rejects_non_speaker_colon_forms() -> None:
    transcript = """
https://example.com/path
00:39: clock-prefixed prose
# Heading: not a speaker
Follow up required: this is generic prose.
status: lowercase prose
Note: common prose prefix
**Summary**: Project status
**https**://example.com
**Note** (10:30): timestamped generic prose
"""

    assert index_normalized_transcript(transcript) == TranscriptGrounding(
        speaker_labels=(),
        timestamps=(),
    )


def test_index_supports_unicode_plain_speaker_labels() -> None:
    transcript = """
José Álvarez: Hola
O’Brien: hello
"""

    assert index_normalized_transcript(transcript) == TranscriptGrounding(
        speaker_labels=("José Álvarez", "O’Brien"),
        timestamps=(),
    )


def test_index_preserves_unicode_markdown_speaker_labels() -> None:
    assert index_normalized_transcript("**José Álvarez** (00:39): Hola") == TranscriptGrounding(
        speaker_labels=("José Álvarez",),
        timestamps=("00:39",),
    )


def test_index_preserves_capitalization_punctuation_and_parenthetical_qualifiers() -> None:
    transcript = """
**O'Neil-Smith, Jo (External Contractor)** (1:02:15): Hello.
**O'Neil-Smith, Jo** (1:03:00): Again.
"""

    assert index_normalized_transcript(transcript) == TranscriptGrounding(
        speaker_labels=("O'Neil-Smith, Jo (External Contractor)", "O'Neil-Smith, Jo"),
        timestamps=("1:02:15", "1:03:00"),
    )
