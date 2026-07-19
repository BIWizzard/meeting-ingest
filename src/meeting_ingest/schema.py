"""Schema constants and dataclasses shared by providers and renderers."""

from __future__ import annotations

from dataclasses import dataclass, field

from meeting_ingest.errors import MeetingIngestError


SCHEMA_VERSION = "1.0"
SUPPORTED_OUTPUT_MODES = ("summary-plus-verbatim",)
SUPPORTED_PROVIDERS = ("mock", "anthropic", "session")
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
    def __init__(self, message: str, *, issues: list[str] | None = None) -> None:
        validation_issues = issues or [message]
        super().__init__(
            phase="provider_validation",
            code="invalid_provider_output",
            message=message,
            exit_code=6,
            recoverable=True,
            details={"issues": validation_issues},
        )

    @classmethod
    def from_issues(cls, issues: list[str]) -> ProviderValidationError:
        if not issues:
            raise ValueError("Provider validation issues must not be empty.")
        if len(issues) == 1:
            return cls(issues[0], issues=issues)
        message = f"Provider response has {len(issues)} validation errors:\n" + "\n".join(
            f"- {issue}" for issue in issues
        )
        return cls(message, issues=issues)


def validate_provider_response(response: ProviderResponse) -> None:
    issues = _response_base_issues(response)
    for index, signal in enumerate(response.communication_signals):
        if not isinstance(signal, ProviderSignal):
            issues.append(f"communication_signals[{index}] must be a ProviderSignal record.")
            continue
        issues.extend(_provider_signal_issues(signal, prefix=f"communication_signals[{index}]."))
    if issues:
        raise ProviderValidationError.from_issues(issues)


def validate_render_response(response: ProviderResponse) -> None:
    issues = _response_base_issues(response)
    signal_ids: list[str] = []
    for index, signal in enumerate(response.communication_signals):
        if not isinstance(signal, SignalRecord):
            issues.append(f"communication_signals[{index}] must be a SignalRecord record.")
            continue
        issues.extend(_signal_record_issues(signal, prefix=f"communication_signals[{index}]."))
        signal_ids.append(signal.signal_id)
    issues.extend(_id_issues("communication_signals", signal_ids))
    if issues:
        raise ProviderValidationError.from_issues(issues)


def _response_base_issues(response: ProviderResponse) -> list[str]:
    issues: list[str] = []
    if not response.title.strip():
        issues.append("response.title is required.")
    if not response.tl_dr.strip():
        issues.append("response.tl_dr is required.")
    issues.extend(_id_issues("response.topics", [topic.id for topic in response.topics]))
    issues.extend(_id_issues("response.decisions", [decision.id for decision in response.decisions]))
    issues.extend(_id_issues("response.action_items", [item.id for item in response.action_items]))
    issues.extend(_id_issues("response.stakeholder_asks", [ask.id for ask in response.stakeholder_asks]))
    issues.extend(_id_issues("response.dependencies_risks", [item.id for item in response.dependencies_risks]))
    issues.extend(_id_issues("response.open_questions", [question.id for question in response.open_questions]))
    return issues


def validate_provider_signal(signal: ProviderSignal) -> None:
    issues = _provider_signal_issues(signal)
    if issues:
        raise ProviderValidationError.from_issues(issues)


def _provider_signal_issues(signal: ProviderSignal, *, prefix: str = "") -> list[str]:
    issues: list[str] = []
    if signal.signal_type not in SIGNAL_TYPES:
        issues.append(f"{prefix}signal_type {signal.signal_type!r} is unsupported.")
    if not signal.stakeholder_name.strip():
        issues.append(f"{prefix}stakeholder_name is required.")
    if not signal.summary.strip():
        issues.append(f"{prefix}summary is required.")
    if signal.evidence.kind not in EVIDENCE_KINDS:
        issues.append(f"{prefix}evidence.kind {signal.evidence.kind!r} is unsupported.")
    if not signal.evidence.text.strip():
        issues.append(f"{prefix}evidence.text is required.")
    if signal.inference_level not in INFERENCE_LEVELS:
        issues.append(f"{prefix}inference_level {signal.inference_level!r} is unsupported.")
    if signal.confidence not in CONFIDENCE_VALUES:
        issues.append(f"{prefix}confidence {signal.confidence!r} is unsupported.")
    if signal.recurrence not in RECURRENCE_VALUES:
        issues.append(f"{prefix}recurrence {signal.recurrence!r} is unsupported.")
    return issues


def validate_signal_record(signal: SignalRecord) -> None:
    issues = _signal_record_issues(signal)
    if issues:
        raise ProviderValidationError.from_issues(issues)


def _signal_record_issues(signal: SignalRecord, *, prefix: str = "") -> list[str]:
    issues: list[str] = []
    if signal.schema_version != SCHEMA_VERSION:
        issues.append(f"{prefix}schema_version {signal.schema_version!r} is unsupported.")
    for field_name in ("signal_id", "meeting_id", "ingest_run_id", "effective_at", "recorded_at"):
        if not getattr(signal, field_name).strip():
            issues.append(f"{prefix}{field_name} is required.")
    if signal.signal_type not in SIGNAL_TYPES:
        issues.append(f"{prefix}signal_type {signal.signal_type!r} is unsupported.")
    if not signal.stakeholder_name.strip():
        issues.append(f"{prefix}stakeholder_name is required.")
    if not signal.summary.strip():
        issues.append(f"{prefix}summary is required.")
    if signal.evidence.kind not in EVIDENCE_KINDS:
        issues.append(f"{prefix}evidence.kind {signal.evidence.kind!r} is unsupported.")
    if not signal.evidence.text.strip():
        issues.append(f"{prefix}evidence.text is required.")
    if signal.inference_level not in INFERENCE_LEVELS:
        issues.append(f"{prefix}inference_level {signal.inference_level!r} is unsupported.")
    if signal.confidence not in CONFIDENCE_VALUES:
        issues.append(f"{prefix}confidence {signal.confidence!r} is unsupported.")
    if signal.recurrence not in RECURRENCE_VALUES:
        issues.append(f"{prefix}recurrence {signal.recurrence!r} is unsupported.")
    return issues


def _validate_ids(section: str, ids: list[str]) -> None:
    issues = _id_issues(section, ids)
    if issues:
        raise ProviderValidationError.from_issues(issues)


def _id_issues(section: str, ids: list[str]) -> list[str]:
    issues: list[str] = []
    seen: set[str] = set()
    for item_id in ids:
        if not item_id.strip():
            issues.append(f"{section} contains an empty ID.")
        if item_id in seen:
            issues.append(f"{section} contains duplicate ID {item_id!r}.")
        seen.add(item_id)
    return issues


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ProviderValidationError(message)
