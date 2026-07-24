from datetime import UTC, datetime
from pathlib import Path

import pytest

from meeting_ingest.clock import FrozenClock
from meeting_ingest.provider import ProviderRequest
from meeting_ingest.provider_json import provider_response_from_payload
from meeting_ingest.providers.mock import MockProvider
from meeting_ingest.render import RenderContext, render_summary_plus_verbatim
from meeting_ingest.schema import (
    ProviderResponse,
    ProviderSignal,
    ProviderValidationError,
    SignalEvidence,
    SignalRecord,
    Topic,
    validate_provider_response,
)


APPROVED_PROVENANCE = {
    "semantic_version": "0.1.0",
    "build_id": "meeting-ingest-test-approved",
    "source_commit": "a" * 40,
    "source_tree_sha256": "sha256:" + "b" * 64,
    "install_mode": "approved_frozen",
    "runtime_mode": "approved",
    "workflow_contract_version": "claude-code-session-v1",
    "development_override_reason": None,
}


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


def test_provider_response_parser_aggregates_independent_payload_errors() -> None:
    with pytest.raises(ProviderValidationError) as caught:
        provider_response_from_payload(
            {
                "title": 42,
                "topics": [{"id": "T1"}],
                "dependencies_risks": [{"id": "R1", "type": "risk"}],
                "communication_signals": [{"signal_type": "explicit_ask", "evidence": {}}],
            }
        )

    issues = caught.value.details["issues"]
    assert "response.title must be a string." in issues
    assert "response.tl_dr is required and must be a string." in issues
    assert "response.meeting_type is required and must be a string." in issues
    assert "response.attendees is required and must be an array." in issues
    assert "response.topics[0].topic is required and must be a string." in issues
    assert "response.dependencies_risks[0].owner_related_party is required and must be a string." in issues
    assert "response.communication_signals[0].stakeholder_name is required and must be a string." in issues
    assert "response.communication_signals[0].evidence.kind is required and must be a string." in issues


def test_provider_response_parser_accepts_documented_nullable_identity_fields() -> None:
    response = provider_response_from_payload(
        {
            "title": "Team Sync",
            "tl_dr": "Summary",
            "meeting_type": "team-sync",
            "attendees": [{"person_id": None, "display_name": None, "raw_labels": []}],
            "topics": [],
            "decisions": [],
            "action_items": [],
            "stakeholder_asks": [],
            "dependencies_risks": [],
            "communication_signals": [],
            "open_questions": [],
            "cross_references": [],
        }
    )

    assert response.attendees[0].person_id is None
    assert response.attendees[0].display_name is None


def test_provider_response_semantic_validation_aggregates_independent_errors() -> None:
    response = ProviderResponse(
        title="",
        tl_dr="",
        topics=[Topic(id="T1", topic="First", summary="Summary", evidence="Evidence"), Topic(id="T1", topic="Second", summary="Summary", evidence="Evidence")],
        communication_signals=[
            ProviderSignal(
                signal_type="unsupported",
                stakeholder_id=None,
                stakeholder_name="",
                summary="",
                evidence=SignalEvidence(kind="unsupported", text=""),
                inference_level="unsupported",
                confidence="unsupported",
                recurrence="unsupported",
            )
        ],
    )

    with pytest.raises(ProviderValidationError) as caught:
        validate_provider_response(response)

    issues = caught.value.details["issues"]
    assert "response.title is required." in issues
    assert "response.tl_dr is required." in issues
    assert "response.topics contains duplicate ID 'T1'." in issues
    assert "communication_signals[0].stakeholder_name is required." in issues
    assert len(issues) == 11


def test_validate_provider_response_accepts_lightweight_provider_signals() -> None:
    response = ProviderResponse(
        title="Signals",
        tl_dr="Summary",
        communication_signals=[
            ProviderSignal(
                signal_type="explicit_ask",
                stakeholder_id="person-kushali",
                stakeholder_name="Kushali",
                summary="Asked for source clarity.",
                evidence=SignalEvidence(kind="paraphrase", text="Asked for source clarity."),
                inference_level="explicit",
                confidence="high",
            )
        ],
    )

    validate_provider_response(response)


def test_render_summary_plus_verbatim_emits_required_sections_and_final_transcript() -> None:
    response = ProviderResponse(title="Kushali Sync", tl_dr="Discussed project status.")
    context = RenderContext(
        meeting_id="mtg-20260703-f953bbd2",
        ingest_run_id="ingest-20260703-20260703T120000Z-abcd1234",
        source_name="2026-07-03-kushali-sync.txt",
        source_sha256="f953bbd204bb867e48a6ff774cffa3dcffd02c6580e8f1d00c37dbbaa743d6c8",
        slug="kushali-sync",
        effective_date="2026-07-03",
        runtime_provenance=APPROVED_PROVENANCE,
        runtime_provenance_ledger_record_id="lr-" + "c" * 32,
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
    assert 'schema_version: "1.1"' in markdown
    assert "artifact_type: meeting" in markdown
    assert "slug: kushali-sync" in markdown
    assert "source_file: \"2026-07-03-kushali-sync.txt\"" in markdown
    assert "source_sha256: f953bbd204bb867e48a6ff774cffa3dcffd02c6580e8f1d00c37dbbaa743d6c8" in markdown
    assert "provider: mock" in markdown
    assert "model_id: none" in markdown
    assert 'runtime_provenance_schema: "1.0"' in markdown
    assert markdown.index("runtime_provenance_schema:") < markdown.index("runtime_provenance_sha256:")
    assert "| Runtime | approved (meeting-ingest-test-approved) |" in markdown
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
        runtime_provenance=APPROVED_PROVENANCE,
        runtime_provenance_ledger_record_id="lr-" + "c" * 32,
    )
    expected = Path("tests/fixtures/expected_markdown/summary_plus_verbatim_basic.md").read_text(encoding="utf-8").rstrip("\n")

    markdown = render_summary_plus_verbatim(
        response,
        "Ken: Hello\nKushali: Hi\n",
        context,
        clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)),
    )

    assert markdown == expected


def test_render_summary_plus_verbatim_marks_development_artifact_and_escapes_reason() -> None:
    reason = 'exercise *local* [workflow] with "quotes" and a newline\ncontinued'
    context = RenderContext(
        meeting_id="mtg-20260703-f953bbd2",
        ingest_run_id="ingest-20260703-20260703T120000Z-abcd1234",
        source_name="source.txt",
        source_sha256="f953bbd204bb867e48a6ff774cffa3dcffd02c6580e8f1d00c37dbbaa743d6c8",
        slug="development",
        effective_date="2026-07-03",
        runtime_provenance={
            **APPROVED_PROVENANCE,
            "runtime_mode": "development",
            "development_override_reason": reason,
        },
        runtime_provenance_ledger_record_id="lr-" + "c" * 32,
    )

    markdown = render_summary_plus_verbatim(
        ProviderResponse(title="Development", tl_dr="Summary"),
        "Ken: Hello\n",
        context,
        clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)),
    )

    assert 'development_override_reason: "exercise *local* [workflow] with \\"quotes\\" and a newline\\ncontinued"' in markdown
    assert (
        "**Development artifact:** generated by a development runtime — "
        'exercise \\*local\\* \\[workflow\\] with "quotes" and a newline continued.'
    ) in markdown
    assert markdown.index("**Development artifact:**") < markdown.index("**TL;DR:**")


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
        runtime_provenance=APPROVED_PROVENANCE,
        runtime_provenance_ledger_record_id="lr-" + "c" * 32,
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
        runtime_provenance=APPROVED_PROVENANCE,
        runtime_provenance_ledger_record_id="lr-" + "c" * 32,
    )

    markdown = render_summary_plus_verbatim(
        response,
        "Ken: Hello\n",
        context,
        clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)),
    )

    assert "| `sig-20260703-001` | explicit_ask | Kushali | Asked for source clarity. | high |" in markdown


def test_render_summary_plus_verbatim_rejects_unenriched_provider_signals() -> None:
    response = ProviderResponse(
        title="Signals",
        tl_dr="Summary",
        communication_signals=[
            ProviderSignal(
                signal_type="explicit_ask",
                stakeholder_id="person-kushali",
                stakeholder_name="Kushali",
                summary="Asked for source clarity.",
                evidence=SignalEvidence(kind="paraphrase", text="Asked for source clarity."),
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
        runtime_provenance=APPROVED_PROVENANCE,
        runtime_provenance_ledger_record_id="lr-" + "c" * 32,
    )

    with pytest.raises(ProviderValidationError, match="SignalRecord"):
        render_summary_plus_verbatim(
            response,
            "Ken: Hello\n",
            context,
            clock=FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC)),
        )
