"""Deterministic markdown rendering."""

from __future__ import annotations

from dataclasses import dataclass

from meeting_ingest.clock import Clock, SystemClock, format_timestamp
from meeting_ingest.schema import ProviderResponse, SignalRecord, validate_provider_response


@dataclass(frozen=True)
class RenderContext:
    meeting_id: str
    ingest_run_id: str
    source_name: str
    source_sha256: str
    slug: str
    effective_date: str
    output_mode: str = "summary-plus-verbatim"
    transcript_policy: str = "cleaned-verbatim"
    provider: str = "mock"
    model_alias: str = "balanced"
    model_id: str = "none"
    tool_version: str = "0.1.0"


def render_summary_plus_verbatim(
    response: ProviderResponse,
    transcript: str,
    context: RenderContext,
    *,
    clock: Clock | None = None,
) -> str:
    validate_provider_response(response)
    active_clock = clock or SystemClock()
    generated_at = format_timestamp(active_clock.now_utc())
    lines: list[str] = []
    lines.extend(_front_matter(response, context, generated_at))
    lines.append(f"# {response.title}")
    lines.append("")
    lines.extend(_overview(response, context))
    lines.extend(_attendees(response))
    lines.extend(_topics(response))
    lines.extend(_decisions(response))
    lines.extend(_actions(response))
    lines.extend(_asks(response))
    lines.extend(_dependencies(response))
    lines.extend(_signals(response))
    lines.extend(_questions(response))
    lines.extend(_cross_references(response))
    lines.extend(_transcript(transcript, context.transcript_policy))
    return "\n".join(lines)


def _front_matter(response: ProviderResponse, context: RenderContext, generated_at: str) -> list[str]:
    return [
        "---",
        'schema_version: "1.0"',
        "artifact_type: meeting",
        f"meeting_id: {context.meeting_id}",
        f"ingest_run_id: {context.ingest_run_id}",
        f"output_mode: {context.output_mode}",
        f"title: {_quote(response.title)}",
        f"slug: {context.slug}",
        f"date: {context.effective_date}",
        f"meeting_type: {response.meeting_type}",
        f"source_file: {_quote(context.source_name)}",
        f"source_sha256: {context.source_sha256}",
        f"transcript_policy: {context.transcript_policy}",
        f"provider: {context.provider}",
        f"model_alias: {context.model_alias}",
        f"model_id: {context.model_id}",
        f"generated_by: meeting-ingest {context.tool_version}",
        f"generated_at: {generated_at}",
        "---",
        "",
    ]


def _overview(response: ProviderResponse, context: RenderContext) -> list[str]:
    return [
        "## Meeting Overview",
        "",
        f"**TL;DR:** {response.tl_dr}",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Meeting ID | `{context.meeting_id}` |",
        f"| Date | {context.effective_date} |",
        f"| Type | {response.meeting_type} |",
        f"| Source | `{context.source_name}` |",
        f"| Output Mode | `{context.output_mode}` |",
        "",
    ]


def _attendees(response: ProviderResponse) -> list[str]:
    lines = ["## Attendees And Identity", ""]
    if not response.attendees:
        return [*lines, "None identified.", ""]
    lines.extend(
        [
            "| Person ID | Display Name | Raw Speaker Labels | Role / Context | Confidence |",
            "|---|---|---|---|---|",
        ]
    )
    for attendee in response.attendees:
        person_id = f"`{attendee.person_id}`" if attendee.person_id else "`null`"
        display_name = attendee.display_name or "Unresolved"
        raw_labels = ", ".join(attendee.raw_labels) if attendee.raw_labels else "Unknown"
        lines.append(
            f"| {person_id} | {_cell(display_name)} | {_cell(raw_labels)} | {_cell(attendee.role_context)} | {_cell(attendee.confidence)} |"
        )
    lines.append("")
    return lines


def _topics(response: ProviderResponse) -> list[str]:
    lines = ["## Key Topics", ""]
    if not response.topics:
        return [*lines, "None identified.", ""]
    lines.extend(["| ID | Topic | Summary | Evidence |", "|---|---|---|---|"])
    for topic in response.topics:
        lines.append(f"| {_cell(topic.id)} | {_cell(topic.topic)} | {_cell(topic.summary)} | {_cell(topic.evidence)} |")
    lines.append("")
    return lines


def _decisions(response: ProviderResponse) -> list[str]:
    lines = ["## Decisions", ""]
    if not response.decisions:
        return [*lines, "None identified.", ""]
    lines.extend(["| ID | Decision | Owner / Decider | Evidence | Status |", "|---|---|---|---|---|"])
    for decision in response.decisions:
        lines.append(
            f"| {_cell(decision.id)} | {_cell(decision.decision)} | {_cell(decision.owner_decider)} | {_cell(decision.evidence)} | {_cell(decision.status)} |"
        )
    lines.append("")
    return lines


def _actions(response: ProviderResponse) -> list[str]:
    lines = ["## Commitments And Action Items", ""]
    if not response.action_items:
        return [*lines, "None identified.", ""]
    lines.extend(
        [
            "| ID | Owner | Commitment / Action | Due / Timing | Evidence | Status |",
            "|---|---|---|---|---|---|",
        ]
    )
    for item in response.action_items:
        lines.append(
            f"| {_cell(item.id)} | {_cell(item.owner)} | {_cell(item.action)} | {_cell(item.due_timing)} | {_cell(item.evidence)} | {_cell(item.status)} |"
        )
    lines.append("")
    return lines


def _asks(response: ProviderResponse) -> list[str]:
    lines = ["## Stakeholder Asks", ""]
    if not response.stakeholder_asks:
        return [*lines, "None identified.", ""]
    lines.extend(["| ID | Stakeholder | Ask | Directed To | Evidence | Status |", "|---|---|---|---|---|---|"])
    for ask in response.stakeholder_asks:
        lines.append(
            f"| {_cell(ask.id)} | {_cell(ask.stakeholder)} | {_cell(ask.ask)} | {_cell(ask.directed_to)} | {_cell(ask.evidence)} | {_cell(ask.status)} |"
        )
    lines.append("")
    return lines


def _dependencies(response: ProviderResponse) -> list[str]:
    lines = ["## Dependencies And Risks", ""]
    if not response.dependencies_risks:
        return [*lines, "None identified.", ""]
    lines.extend(["| ID | Type | Description | Owner / Related Party | Impact | Status |", "|---|---|---|---|---|---|"])
    for item in response.dependencies_risks:
        lines.append(
            f"| {_cell(item.id)} | {_cell(item.type)} | {_cell(item.description)} | {_cell(item.owner_related_party)} | {_cell(item.impact)} | {_cell(item.status)} |"
        )
    lines.append("")
    return lines


def _signals(response: ProviderResponse) -> list[str]:
    lines = ["## Communication Signals", ""]
    if not response.communication_signals:
        return [*lines, "None identified.", ""]
    lines.extend(["| Signal ID | Type | Stakeholder | Summary | Confidence |", "|---|---|---|---|---|"])
    for signal in response.communication_signals:
        summary = signal.to_summary() if isinstance(signal, SignalRecord) else signal
        lines.append(
            f"| `{_cell(summary.signal_id)}` | {_cell(summary.type)} | {_cell(summary.stakeholder)} | {_cell(summary.summary)} | {_cell(summary.confidence)} |"
        )
    lines.append("")
    return lines


def _questions(response: ProviderResponse) -> list[str]:
    lines = ["## Open Questions", ""]
    if not response.open_questions:
        return [*lines, "None identified.", ""]
    lines.extend(["| ID | Question | Owner / Next Step | Evidence | Status |", "|---|---|---|---|---|"])
    for question in response.open_questions:
        lines.append(
            f"| {_cell(question.id)} | {_cell(question.question)} | {_cell(question.owner_next_step)} | {_cell(question.evidence)} | {_cell(question.status)} |"
        )
    lines.append("")
    return lines


def _cross_references(response: ProviderResponse) -> list[str]:
    lines = ["## Cross-References", ""]
    if not response.cross_references:
        return [*lines, "None identified.", ""]
    lines.extend(f"- {reference}" for reference in response.cross_references)
    lines.append("")
    return lines


def _transcript(transcript: str, policy: str) -> list[str]:
    return [
        "## Verbatim Transcript",
        "",
        f"<!-- transcript:begin policy={policy} -->",
        "",
        transcript.strip(),
        "",
        "<!-- transcript:end -->",
    ]


def _quote(value: str) -> str:
    escaped = value.replace('"', '\\"')
    return f'"{escaped}"'


def _cell(value: str) -> str:
    return " ".join(value.split()).replace("|", "\\|")
