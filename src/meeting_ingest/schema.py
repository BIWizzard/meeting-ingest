"""Schema constants and dataclasses shared by providers and renderers."""

from __future__ import annotations

from dataclasses import dataclass, field
import re

from meeting_ingest.errors import MeetingIngestError


SCHEMA_VERSION = "1.1"
SUPPORTED_SIGNAL_SCHEMA_VERSIONS = ("1.0", SCHEMA_VERSION)
SUPPORTED_OUTPUT_MODES = ("summary-plus-verbatim",)
SUPPORTED_PROVIDERS = ("mock", "anthropic", "session")
SUPPORTED_QUALITIES = ("fast", "balanced", "deep")
SIGNAL_TYPES = ("explicit_ask", "stakeholder_priority", "decision_rationale", "commitment", "risk_or_concern")
GENERALIZED_SIGNAL_TYPES = (
    *SIGNAL_TYPES,
    "communication_preference",
    "communication_behavior",
    "interaction_response",
)
EVIDENCE_KINDS = ("quote", "paraphrase", "timestamp_only")
EVIDENCE_LOCATOR_SCHEMES = (
    "timestamp",
    "message_id",
    "line_range",
    "document_anchor",
    "image_region",
    "url_element",
    "none",
)
SOURCE_KINDS = (
    "meeting_transcript",
    "email",
    "chat_thread",
    "text_thread",
    "document",
    "screenshot",
    "social_post",
    "social_profile",
)
TIMING_PRECISIONS = ("datetime", "date", "range", "unknown")
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
class EvidenceLocator:
    scheme: str
    value: str | None


@dataclass(frozen=True)
class SignalEvidence:
    kind: str
    text: str
    speaker: str | None = None
    timestamp: str | None = None
    locator: EvidenceLocator | None = None


@dataclass(frozen=True)
class SignalSource:
    source_id: str
    source_kind: str
    source_sha256: str
    meeting_id: str | None
    artifact_path: str
    channel: str | None
    evidence_locator_scheme: str


@dataclass(frozen=True)
class SignalTime:
    value: str | None
    end_value: str | None
    precision: str
    timezone: str | None
    source: str
    confidence: str


@dataclass(frozen=True)
class SignalTiming:
    occurred: SignalTime
    acquired: SignalTime | None
    recorded: SignalTime


@dataclass(frozen=True)
class SignalRecord:
    signal_id: str
    meeting_id: str | None
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
    source: SignalSource | None = None
    timing: SignalTiming | None = None
    stakeholder_name_raw: str | None = None
    audience_id: str | None = None
    audience_name: str | None = None
    topics: list[str] = field(default_factory=list)
    project_refs: list[str] = field(default_factory=list)
    recurrence: str = "unknown"
    status: str = "active"
    schema_version: str = "1.0"

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
    if signal.schema_version not in SUPPORTED_SIGNAL_SCHEMA_VERSIONS:
        issues.append(f"{prefix}schema_version {signal.schema_version!r} is unsupported.")
    for field_name in ("signal_id", "ingest_run_id", "effective_at", "recorded_at"):
        if not getattr(signal, field_name).strip():
            issues.append(f"{prefix}{field_name} is required.")
    if signal.schema_version == "1.0" and not (signal.meeting_id or "").strip():
        issues.append(f"{prefix}meeting_id is required.")
    allowed_signal_types = GENERALIZED_SIGNAL_TYPES if signal.schema_version == "1.1" else SIGNAL_TYPES
    if signal.signal_type not in allowed_signal_types:
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
    if signal.schema_version == "1.1":
        issues.extend(_generalized_signal_issues(signal, prefix=prefix))
    return issues


def _generalized_signal_issues(signal: SignalRecord, *, prefix: str) -> list[str]:
    issues: list[str] = []
    if signal.source is None:
        issues.append(f"{prefix}source is required for schema 1.1.")
    else:
        source = signal.source
        if source.source_kind not in SOURCE_KINDS:
            issues.append(f"{prefix}source.source_kind {source.source_kind!r} is unsupported.")
        if source.evidence_locator_scheme not in EVIDENCE_LOCATOR_SCHEMES:
            issues.append(
                f"{prefix}source.evidence_locator_scheme {source.evidence_locator_scheme!r} is unsupported."
            )
        if not source.source_id.strip():
            issues.append(f"{prefix}source.source_id is required.")
        if not re.fullmatch(r"[0-9a-f]{64}", source.source_sha256):
            issues.append(f"{prefix}source.source_sha256 must be 64 lowercase hexadecimal characters.")
        expected_source_id = f"src-{source.source_sha256[:12]}"
        if source.source_id != expected_source_id:
            issues.append(f"{prefix}source.source_id must be {expected_source_id!r}.")
        if not re.fullmatch(
            rf"sig-{re.escape(source.source_sha256[:12])}-[0-9a-f]{{12}}(?:-(?:[2-9]|[1-9][0-9]+))?",
            signal.signal_id,
        ):
            issues.append(f"{prefix}signal_id does not match schema 1.1 source identity.")
        if source.source_kind == "meeting_transcript":
            if not (signal.meeting_id or "").strip():
                issues.append(f"{prefix}meeting_id is required for meeting_transcript.")
            if source.meeting_id != signal.meeting_id:
                issues.append(f"{prefix}source.meeting_id must match meeting_id.")
            if not source.artifact_path.strip():
                issues.append(f"{prefix}source.artifact_path is required for meeting_transcript.")
            if source.evidence_locator_scheme not in {"timestamp", "none"}:
                issues.append(
                    f"{prefix}meeting_transcript evidence locator scheme must be 'timestamp' or 'none'."
                )
        elif source.meeting_id is not None or signal.meeting_id:
            issues.append(f"{prefix}meeting_id must be null for non-meeting sources.")
    if signal.timing is None:
        issues.append(f"{prefix}timing is required for schema 1.1.")
    else:
        issues.extend(_signal_time_issues(signal.timing.occurred, prefix=f"{prefix}timing.occurred."))
        if signal.timing.acquired is None:
            if signal.source is not None and signal.source.source_kind == "meeting_transcript":
                issues.append(f"{prefix}timing.acquired is required for meeting_transcript.")
        else:
            issues.extend(_signal_time_issues(signal.timing.acquired, prefix=f"{prefix}timing.acquired."))
        issues.extend(_signal_time_issues(signal.timing.recorded, prefix=f"{prefix}timing.recorded."))
        if signal.timing.occurred.value is not None and signal.timing.occurred.value != signal.effective_at:
            issues.append(f"{prefix}timing.occurred.value must match effective_at.")
        if signal.timing.recorded.value is not None and signal.timing.recorded.value != signal.recorded_at:
            issues.append(f"{prefix}timing.recorded.value must match recorded_at.")
    if not (signal.stakeholder_name_raw or "").strip() and not (signal.audience_name or "").strip():
        issues.append(f"{prefix}stakeholder_name_raw is required for person-directed schema 1.1 signals.")
    locator = signal.evidence.locator
    if locator is None:
        issues.append(f"{prefix}evidence.locator is required for schema 1.1.")
    elif locator.scheme not in EVIDENCE_LOCATOR_SCHEMES:
        issues.append(f"{prefix}evidence.locator.scheme {locator.scheme!r} is unsupported.")
    elif locator.scheme == "none" and locator.value is not None:
        issues.append(f"{prefix}evidence.locator.value must be null when scheme is 'none'.")
    elif locator.scheme != "none" and not (locator.value or "").strip():
        issues.append(f"{prefix}evidence.locator.value is required for scheme {locator.scheme!r}.")
    if signal.source is not None and locator is not None and signal.source.evidence_locator_scheme != locator.scheme:
        issues.append(f"{prefix}source.evidence_locator_scheme must match evidence.locator.scheme.")
    return issues


def _signal_time_issues(value: SignalTime, *, prefix: str) -> list[str]:
    issues: list[str] = []
    if value.precision not in TIMING_PRECISIONS:
        issues.append(f"{prefix}precision {value.precision!r} is unsupported.")
    if value.confidence not in (*CONFIDENCE_VALUES, "manual"):
        issues.append(f"{prefix}confidence {value.confidence!r} is unsupported.")
    if not value.source.strip():
        issues.append(f"{prefix}source is required.")
    if value.precision == "unknown":
        if value.value is not None:
            issues.append(f"{prefix}value must be null when precision is 'unknown'.")
    elif value.value is None or not value.value.strip():
        issues.append(f"{prefix}value is required unless precision is 'unknown'.")
    if value.precision == "range":
        if value.end_value is None or not value.end_value.strip():
            issues.append(f"{prefix}end_value is required when precision is 'range'.")
    elif value.end_value is not None:
        issues.append(f"{prefix}end_value must be null unless precision is 'range'.")
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
