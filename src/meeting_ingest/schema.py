"""Schema constants and dataclasses shared by providers and renderers."""

from __future__ import annotations

from dataclasses import dataclass, field

from meeting_ingest.errors import MeetingIngestError


SCHEMA_VERSION = "1.0"
SUPPORTED_OUTPUT_MODES = ("summary-plus-verbatim",)
SUPPORTED_PROVIDERS = ("mock", "anthropic")
SUPPORTED_QUALITIES = ("fast", "balanced", "deep")


@dataclass(frozen=True)
class Attendee:
    person_id: str | None
    display_name: str | None
    raw_labels: list[str]
    role_context: str = "Unknown"
    confidence: str = "medium"


@dataclass(frozen=True)
class Topic:
    id: str
    topic: str
    summary: str
    evidence: str


@dataclass(frozen=True)
class Decision:
    id: str
    decision: str
    owner_decider: str
    evidence: str
    status: str = "active"


@dataclass(frozen=True)
class ActionItem:
    id: str
    owner: str
    action: str
    due_timing: str
    evidence: str
    status: str = "open"


@dataclass(frozen=True)
class StakeholderAsk:
    id: str
    stakeholder: str
    ask: str
    directed_to: str
    evidence: str
    status: str = "open"


@dataclass(frozen=True)
class DependencyRisk:
    id: str
    type: str
    description: str
    owner_related_party: str
    impact: str
    status: str = "active"


@dataclass(frozen=True)
class SignalSummary:
    signal_id: str
    type: str
    stakeholder: str
    summary: str
    confidence: str


@dataclass(frozen=True)
class OpenQuestion:
    id: str
    question: str
    owner_next_step: str
    evidence: str
    status: str = "open"


@dataclass(frozen=True)
class ProviderResponse:
    title: str
    tl_dr: str
    meeting_type: str = "unknown"
    attendees: list[Attendee] = field(default_factory=list)
    topics: list[Topic] = field(default_factory=list)
    decisions: list[Decision] = field(default_factory=list)
    action_items: list[ActionItem] = field(default_factory=list)
    stakeholder_asks: list[StakeholderAsk] = field(default_factory=list)
    dependencies_risks: list[DependencyRisk] = field(default_factory=list)
    communication_signals: list[SignalSummary] = field(default_factory=list)
    open_questions: list[OpenQuestion] = field(default_factory=list)
    cross_references: list[str] = field(default_factory=list)


class ProviderValidationError(MeetingIngestError):
    def __init__(self, message: str) -> None:
        super().__init__(
            phase="provider_validation",
            code="invalid_provider_output",
            message=message,
            exit_code=6,
            recoverable=True,
        )


def validate_provider_response(response: ProviderResponse) -> None:
    if not response.title.strip():
        raise ProviderValidationError("Provider response title is required.")
    if not response.tl_dr.strip():
        raise ProviderValidationError("Provider response TL;DR is required.")
    _validate_ids("topics", [topic.id for topic in response.topics])
    _validate_ids("decisions", [decision.id for decision in response.decisions])
    _validate_ids("action_items", [item.id for item in response.action_items])
    _validate_ids("stakeholder_asks", [ask.id for ask in response.stakeholder_asks])
    _validate_ids("dependencies_risks", [item.id for item in response.dependencies_risks])
    _validate_ids("open_questions", [question.id for question in response.open_questions])


def _validate_ids(section: str, ids: list[str]) -> None:
    seen: set[str] = set()
    for item_id in ids:
        if not item_id.strip():
            raise ProviderValidationError(f"{section} contains an empty ID.")
        if item_id in seen:
            raise ProviderValidationError(f"{section} contains duplicate ID {item_id!r}.")
        seen.add(item_id)
