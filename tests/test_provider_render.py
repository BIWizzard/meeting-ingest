from datetime import UTC, datetime
from pathlib import Path

import pytest

from meeting_ingest.clock import FrozenClock
from meeting_ingest.provider import ProviderRequest
from meeting_ingest.providers.mock import MockProvider
from meeting_ingest.render import RenderContext, render_summary_plus_verbatim
from meeting_ingest.schema import (
    ProviderResponse,
    ProviderValidationError,
    SignalEvidence,
    SignalRecord,
    Topic,
    validate_provider_response,
)


def test_mock_provider_returns_valid_deterministic_response() -> None:
    provider = MockProvider()
    request = ProviderRequest(
        transcript="Ken: Hello\nKushali: Hi\n",
        source_name="2026-07-03-kushali-sync.txt",
        meeting_id="mtg-20260703-f953bbd2",
        effective_date="2026-07-03",
    )

    response = provider.extract(request)

    validate_provider_response(response)
    assert response.title == "Kushali Sync"
    assert [attendee.person_id for attendee in response.attendees] == ["person-ken", "person-kushali"]


def test_validate_provider_response_rejects_missing_title() -> None:
    with pytest.raises(ProviderValidationError):
        validate_provider_response(ProviderResponse(title="", tl_dr="Summary"))


def test_render_summary_plus_verbatim_emits_required_sections_and_final_transcript() -> None:
    response = ProviderResponse(title="Kushali Sync", tl_dr="Discussed project status.")
    context = RenderContext(
        meeting_id="mtg-20260703-f953bbd2",
        ingest_run_id="ingest-20260703-20260703T120000Z-abcd1234",
        source_name="2026-07-03-kushali-sync.txt",
        source_sha256="f953bbd204bb867e48a6ff774cffa3dcffd02c6580e8f1d00c37dbbaa743d6c8",
        slug="kushali-sync",
        effective_date="2026-07-03",
    )

    markdown = render_summary_plus_verbatim(
        response,
        "Ken: Hello\nKushali: Hi\n",
        context,
        clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)),
    )

    required_headings = [
        "# Kushali Sync",
        "## Meeting Overview",
        "## Attendees And Identity",
        "## Key Topics",
        "## Decisions",
        "## Commitments And Action Items",
        "## Stakeholder Asks",
        "## Dependencies And Risks",
        "## Communication Signals",
        "## Open Questions",
        "## Cross-References",
        "## Verbatim Transcript",
    ]
    for heading in required_headings:
        assert heading in markdown
    assert 'schema_version: "1.0"' in markdown
    assert "artifact_type: meeting" in markdown
    assert "slug: kushali-sync" in markdown
    assert "source_file: \"2026-07-03-kushali-sync.txt\"" in markdown
    assert "source_sha256: f953bbd204bb867e48a6ff774cffa3dcffd02c6580e8f1d00c37dbbaa743d6c8" in markdown
    assert "provider: mock" in markdown
    assert "model_id: none" in markdown
    assert "generated_at: 2026-07-03T12:00:00Z" in markdown
    assert "<!-- transcript:begin policy=cleaned-verbatim -->" in markdown
    assert markdown.endswith("<!-- transcript:end -->")
    assert markdown.rfind("## Verbatim Transcript") > markdown.rfind("## Cross-References")


def test_render_summary_plus_verbatim_matches_golden_fixture() -> None:
    response = ProviderResponse(title="Kushali Sync", tl_dr="Discussed project status.")
    context = RenderContext(
        meeting_id="mtg-20260703-f953bbd2",
        ingest_run_id="ingest-20260703-20260703T120000Z-abcd1234",
        source_name="2026-07-03-kushali-sync.txt",
        source_sha256="f953bbd204bb867e48a6ff774cffa3dcffd02c6580e8f1d00c37dbbaa743d6c8",
        slug="kushali-sync",
        effective_date="2026-07-03",
    )
    expected = Path("tests/fixtures/expected_markdown/summary_plus_verbatim_basic.md").read_text(encoding="utf-8").rstrip("\n")

    markdown = render_summary_plus_verbatim(
        response,
        "Ken: Hello\nKushali: Hi\n",
        context,
        clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)),
    )

    assert markdown == expected


def test_render_summary_plus_verbatim_escapes_table_cells() -> None:
    response = ProviderResponse(
        title="Escaping",
        tl_dr="Summary",
        topics=[Topic(id="T1", topic="A | B", summary="Line one\nline two", evidence="source | quote")],
    )
    context = RenderContext(
        meeting_id="mtg-20260703-f953bbd2",
        ingest_run_id="ingest-20260703-20260703T120000Z-abcd1234",
        source_name="source.txt",
        source_sha256="f953bbd204bb867e48a6ff774cffa3dcffd02c6580e8f1d00c37dbbaa743d6c8",
        slug="escaping",
        effective_date="2026-07-03",
    )

    markdown = render_summary_plus_verbatim(
        response,
        "Ken: Hello\n",
        context,
        clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)),
    )

    assert "| T1 | A \\| B | Line one line two | source \\| quote |" in markdown


def test_render_summary_plus_verbatim_derives_signal_table_from_record() -> None:
    response = ProviderResponse(
        title="Signals",
        tl_dr="Summary",
        communication_signals=[
            SignalRecord(
                signal_id="sig-20260703-001",
                meeting_id="mtg-20260703-f953bbd2",
                ingest_run_id="ingest-20260703-20260703T120000Z-abcd1234",
                effective_at="2026-07-03",
                recorded_at="2026-07-03T12:00:00Z",
                signal_type="explicit_ask",
                stakeholder_id="person-kushali",
                stakeholder_name="Kushali",
                summary="Asked for source clarity.",
                evidence=SignalEvidence(kind="paraphrase", text="Kushali asked for source clarity."),
                inference_level="explicit",
                confidence="high",
            )
        ],
    )
    context = RenderContext(
        meeting_id="mtg-20260703-f953bbd2",
        ingest_run_id="ingest-20260703-20260703T120000Z-abcd1234",
        source_name="source.txt",
        source_sha256="f953bbd204bb867e48a6ff774cffa3dcffd02c6580e8f1d00c37dbbaa743d6c8",
        slug="signals",
        effective_date="2026-07-03",
    )

    markdown = render_summary_plus_verbatim(
        response,
        "Ken: Hello\n",
        context,
        clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)),
    )

    assert "| `sig-20260703-001` | explicit_ask | Kushali | Asked for source clarity. | high |" in markdown
