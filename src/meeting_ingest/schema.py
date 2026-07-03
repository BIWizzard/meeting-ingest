"""Schema constants and dataclasses shared by providers and renderers."""

from __future__ import annotations

from dataclasses import dataclass, field

from meeting_ingest.errors import MeetingIngestError


SCHEMA_VERSION = "1.0"
SUPPORTED_OUTPUT_MODES = ("summary-plus-verbatim",)
SUPPORTED_PROVIDERS = ("mock", "anthropic")
SUPPORTED_QUALITIES = ("fast", "balanced", "deep")
SIGNAL_TYPES = ("explicit_ask", "stakeholder_priority", "decision_rationale", "commitment", "risk_or_concern")
EVIDENCE_KINDS = ("quote", "paraphrase", "timestamp_only")
INFERENCE_LEVELS = ("explicit", "strong_inference", "weak_inference")
CONFIDENCE_VALUES = ("high", "medium", "low")
RECURRENCE_VALUES = ("one_off", "recurring", "unknown")


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
class SignalEvidence:
    kind: str
    text: str
    speaker: str | None = None
    timestamp: str | None = None


@dataclass(frozen=True)
class SignalRecord:
    signal_id: str
    meeting_id: str
    ingest_run_id: str
    effective_at: str
    recorded_at: str
    signal_type: str
    stakeholder_id: str | None
    stakeholder_name: str
    summary: str
    evidence: SignalEvidence
    inference_level: str
    confidence: str
    topics: list[str] = field(default_factory=list)
    project_refs: list[str] = field(default_factory=list)
    recurrence: str = "unknown"
    status: str = "active"
    schema_version: str = SCHEMA_VERSION

    def to_summary(self) -> SignalSummary:
        return SignalSummary(
            signal_id=self.signal_id,
            type=self.signal_type,
            stakeholder=self.stakeholder_name,
            summary=self.summary,
            confidence=self.confidence,
        )


@dataclass(frozen=True)
class ProviderSignal:
    signal_type: str
    stakeholder_id: str | None
    stakeholder_name: str
    summary: str
    evidence: SignalEvidence
    inference_level: str
    confidence: str
    topics: list[str] = field(default_factory=list)
    project_refs: list[str] = field(default_factory=list)
    recurrence: str = "unknown"
    status: str = "active"


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
    communication_signals: list[ProviderSignal | SignalRecord] = field(default_factory=list)
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
    _validate_ids("communication_signals", [signal.signal_id for signal in response.communication_signals])
    _validate_ids("open_questions", [question.id for question in response.open_questions])


def validate_signal_record(signal: SignalRecord) -> None:
    _require(signal.schema_version == SCHEMA_VERSION, f"Unsupported signal schema_version {signal.schema_version!r}.")
    _require(bool(signal.signal_id.strip()), "signal_id is required.")
    _require(bool(signal.meeting_id.strip()), "meeting_id is required.")
    _require(bool(signal.ingest_run_id.strip()), "ingest_run_id is required.")
    _require(bool(signal.effective_at.strip()), "effective_at is required.")
    _require(bool(signal.recorded_at.strip()), "recorded_at is required.")
    _require(signal.signal_type in SIGNAL_TYPES, f"Unsupported signal_type {signal.signal_type!r}.")
    _require(bool(signal.stakeholder_name.strip()), "stakeholder_name is required.")
    _require(bool(signal.summary.strip()), "summary is required.")
    _require(signal.evidence.kind in EVIDENCE_KINDS, f"Unsupported evidence.kind {signal.evidence.kind!r}.")
    _require(bool(signal.evidence.text.strip()), "evidence.text is required.")
    _require(signal.inference_level in INFERENCE_LEVELS, f"Unsupported inference_level {signal.inference_level!r}.")
    _require(signal.confidence in CONFIDENCE_VALUES, f"Unsupported confidence {signal.confidence!r}.")
    _require(signal.recurrence in RECURRENCE_VALUES, f"Unsupported recurrence {signal.recurrence!r}.")


def _validate_ids(section: str, ids: list[str]) -> None:
    seen: set[str] = set()
    for item_id in ids:
        if not item_id.strip():
            raise ProviderValidationError(f"{section} contains an empty ID.")
        if item_id in seen:
            raise ProviderValidationError(f"{section} contains duplicate ID {item_id!r}.")
        seen.add(item_id)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ProviderValidationError(message)
