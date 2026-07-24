"""Signal JSONL writing."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from dataclasses import replace
import hashlib
import json
from typing import Any

from meeting_ingest.errors import EXIT_ARTIFACT_WRITE, MeetingIngestError
from meeting_ingest.hashing import sha256_file
from meeting_ingest.ids import canonical_json, observation_identity_hash
from meeting_ingest.schema import (
    EvidenceLocator,
    SignalEvidence,
    SignalRecord,
    RuntimeProvenanceRef,
    SignalSource,
    SignalTime,
    SignalTiming,
    ProviderValidationError,
    validate_signal_record,
)


_DEPRECATED_EVENT_KEYS = frozenset(
    {
        "schema_version",
        "event",
        "event_id",
        "ingest_run_id",
        "effective_at",
        "recorded_at",
        "origin",
        "payload",
        "provenance",
    }
)


@dataclass(frozen=True)
class SignalWriteResult:
    path: Path
    count: int
    fingerprint: str


@dataclass(frozen=True)
class SignalIdentityResult:
    signals: list[SignalRecord]
    warnings: list[str]


def write_signal_jsonl(path: Path, signals: list[SignalRecord]) -> SignalWriteResult:
    for signal in signals:
        validate_signal_record(signal)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with temporary.open("w", encoding="utf-8") as target:
            for signal in signals:
                target.write(json.dumps(signal_record_to_dict(signal), sort_keys=True))
                target.write("\n")
        temporary.replace(path)
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise MeetingIngestError(
            phase="signal_write",
            code="signal_write_failed",
            message=f"Could not write signal JSONL: {path}",
            exit_code=EXIT_ARTIFACT_WRITE,
            recoverable=True,
            details={"path": str(path)},
        ) from exc
    return SignalWriteResult(path=path, count=len(signals), fingerprint=f"sha256:{sha256_file(path)}")


def signal_record_to_dict(signal: SignalRecord) -> dict[str, Any]:
    payload = asdict(signal)
    if signal.schema_version in {"1.0", "1.1"}:
        payload.pop("runtime_provenance_ref", None)
    if signal.schema_version == "1.0":
        for key in ("source", "timing", "stakeholder_name_raw", "audience_id", "audience_name"):
            payload.pop(key, None)
        evidence = payload.get("evidence")
        if isinstance(evidence, dict):
            evidence.pop("locator", None)
    return payload


def read_signal_jsonl(path: Path) -> list[SignalRecord]:
    records: list[SignalRecord] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise MeetingIngestError(
            phase="signal_read",
            code="signal_read_failed",
            message=f"Could not read signal JSONL: {path}",
            exit_code=EXIT_ARTIFACT_WRITE,
            recoverable=True,
            details={"path": str(path)},
        ) from exc
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError("record must be an object")
            record = signal_record_from_dict(payload)
        except (TypeError, ValueError, KeyError) as exc:
            raise MeetingIngestError(
                phase="signal_read",
                code="signal_invalid",
                message=f"Signal JSONL is invalid at line {line_number}: {exc}",
                exit_code=EXIT_ARTIFACT_WRITE,
                recoverable=True,
                details={"path": str(path), "line": line_number},
            ) from exc
        try:
            validate_signal_record(record)
        except ProviderValidationError as exc:
            issues = exc.details.get("issues", [])
            issue_strings = [str(issue) for issue in issues] if isinstance(issues, list) else []
            code = _signal_validation_code(issue_strings)
            raise MeetingIngestError(
                phase="signal_read",
                code=code,
                message=str(exc),
                exit_code=EXIT_ARTIFACT_WRITE,
                recoverable=True,
                details={"path": str(path), "line": line_number, "issues": issue_strings},
            ) from exc
        records.append(record)
    return records


def is_deprecated_signal_event_jsonl(path: Path) -> bool:
    """Recognize the pre-Meeting-Ingest event envelope without adopting it as a signal."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return False
    found = False
    for line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            return False
        if not _is_deprecated_signal_event(payload):
            return False
        found = True
    return found


def _is_deprecated_signal_event(payload: object) -> bool:
    if not isinstance(payload, dict) or frozenset(payload) != _DEPRECATED_EVENT_KEYS:
        return False
    return (
        payload.get("schema_version") == "1.0"
        and all(
            isinstance(payload.get(key), str) and bool(str(payload[key]).strip())
            for key in ("event", "event_id", "ingest_run_id", "effective_at", "recorded_at", "origin")
        )
        and all(isinstance(payload.get(key), dict) for key in ("payload", "provenance"))
    )


def signal_record_from_dict(payload: dict[str, Any]) -> SignalRecord:
    schema_version = _required_string(payload, "schema_version")
    evidence_payload = _mapping(payload["evidence"], "evidence")
    locator_payload = evidence_payload.get("locator")
    locator = None
    if locator_payload is not None:
        locator_data = _mapping(locator_payload, "evidence.locator")
        locator = EvidenceLocator(
            scheme=_required_string(locator_data, "scheme", field="evidence.locator.scheme"),
            value=_optional_string(locator_data.get("value")),
        )
    evidence = SignalEvidence(
        kind=_required_string(evidence_payload, "kind", field="evidence.kind"),
        text=_required_string(evidence_payload, "text", field="evidence.text"),
        speaker=_optional_string(evidence_payload.get("speaker")),
        timestamp=_optional_string(evidence_payload.get("timestamp")),
        locator=locator,
    )
    generalized = schema_version in {"1.1", "1.2"}
    source = _source_from_payload(payload.get("source")) if generalized else None
    timing = _timing_from_payload(payload.get("timing")) if generalized else None
    provenance_payload = payload.get("runtime_provenance_ref")
    runtime_provenance_ref = (
        _runtime_provenance_ref_from_payload(provenance_payload)
        if schema_version == "1.2" and provenance_payload is not None
        else None
    )
    return SignalRecord(
        signal_id=_required_string(payload, "signal_id"),
        meeting_id=_optional_string(payload.get("meeting_id")),
        ingest_run_id=_required_string(payload, "ingest_run_id"),
        effective_at=_required_string(payload, "effective_at"),
        recorded_at=_required_string(payload, "recorded_at"),
        signal_type=_required_string(payload, "signal_type"),
        stakeholder_id=_optional_string(payload.get("stakeholder_id")),
        stakeholder_name=_required_string(payload, "stakeholder_name"),
        summary=_required_string(payload, "summary"),
        evidence=evidence,
        inference_level=_required_string(payload, "inference_level"),
        confidence=_required_string(payload, "confidence"),
        source=source,
        timing=timing,
        runtime_provenance_ref=runtime_provenance_ref,
        stakeholder_name_raw=_optional_string(payload.get("stakeholder_name_raw")),
        audience_id=_optional_string(payload.get("audience_id")),
        audience_name=_optional_string(payload.get("audience_name")),
        topics=_string_list(payload.get("topics", []), "topics"),
        project_refs=_string_list(payload.get("project_refs", []), "project_refs"),
        recurrence=_string_default(payload, "recurrence", "unknown"),
        status=_string_default(payload, "status", "active"),
        schema_version=schema_version,
    )


def assign_deterministic_signal_ids(signals: list[SignalRecord]) -> SignalIdentityResult:
    grouped: dict[str, list[tuple[str, SignalRecord]]] = {}
    for signal in signals:
        if signal.source is None or signal.evidence.locator is None:
            raise ValueError("deterministic signal identity requires schema 1.1 source and locator")
        source_prefix = signal.source.source_id.removeprefix("src-")
        actor = signal.stakeholder_name_raw or signal.audience_name or ""
        observation_hash = observation_identity_hash(
            signal_type=signal.signal_type,
            actor_name=actor,
            locator=asdict(signal.evidence.locator),
            evidence_text=signal.evidence.text,
        )
        base_id = f"sig-{source_prefix}-{observation_hash[:12]}"
        content_hash = hashlib.sha256(_identity_content_json(signal).encode("utf-8")).hexdigest()
        grouped.setdefault(base_id, []).append((content_hash, signal))

    assigned: list[SignalRecord] = []
    warnings: list[str] = []
    for base_id in sorted(grouped):
        entries = grouped[base_id]
        unique: dict[str, tuple[str, SignalRecord]] = {}
        duplicate_count = 0
        for content_hash, signal in entries:
            canonical_record = canonical_json(asdict(signal))
            if content_hash in unique:
                duplicate_count += 1
                if canonical_record < unique[content_hash][0]:
                    unique[content_hash] = (canonical_record, signal)
                continue
            unique[content_hash] = (canonical_record, signal)
        if duplicate_count:
            warnings.append(f"collapsed {duplicate_count} exact duplicate signal(s) for {base_id}")
        for ordinal, content_hash in enumerate(sorted(unique), start=1):
            signal_id = base_id if ordinal == 1 else f"{base_id}-{ordinal}"
            assigned.append(replace(unique[content_hash][1], signal_id=signal_id))
        if len(unique) > 1:
            warnings.append(f"assigned deterministic collision suffixes for {base_id}")
    return SignalIdentityResult(signals=assigned, warnings=warnings)


def _identity_content_json(signal: SignalRecord) -> str:
    payload = asdict(signal)
    for key in ("signal_id", "ingest_run_id", "recorded_at"):
        payload.pop(key, None)
    timing = payload.get("timing")
    if isinstance(timing, dict):
        timing.pop("recorded", None)
    return canonical_json(payload)


def _source_from_payload(value: object) -> SignalSource:
    payload = _mapping(value, "source")
    return SignalSource(
        source_id=_required_string(payload, "source_id", field="source.source_id"),
        source_kind=_required_string(payload, "source_kind", field="source.source_kind"),
        source_sha256=_required_string(payload, "source_sha256", field="source.source_sha256"),
        meeting_id=_optional_string(payload.get("meeting_id")),
        artifact_path=_string_default(payload, "artifact_path", ""),
        channel=_optional_string(payload.get("channel")),
        evidence_locator_scheme=_required_string(
            payload, "evidence_locator_scheme", field="source.evidence_locator_scheme"
        ),
    )


def _timing_from_payload(value: object) -> SignalTiming:
    payload = _mapping(value, "timing")
    acquired = payload.get("acquired")
    return SignalTiming(
        occurred=_time_from_payload(payload["occurred"], "timing.occurred"),
        acquired=_time_from_payload(acquired, "timing.acquired") if acquired is not None else None,
        recorded=_time_from_payload(payload["recorded"], "timing.recorded"),
    )


def _runtime_provenance_ref_from_payload(value: object) -> RuntimeProvenanceRef:
    payload = _mapping(value, "runtime_provenance_ref")
    return RuntimeProvenanceRef(
        schema_version=_required_string(
            payload, "schema_version", field="runtime_provenance_ref.schema_version"
        ),
        producer_ledger_record_id=_required_string(
            payload,
            "producer_ledger_record_id",
            field="runtime_provenance_ref.producer_ledger_record_id",
        ),
        sha256=_required_string(payload, "sha256", field="runtime_provenance_ref.sha256"),
    )


def _time_from_payload(value: object, field: str) -> SignalTime:
    payload = _mapping(value, field)
    return SignalTime(
        value=_optional_string(payload.get("value")),
        end_value=_optional_string(payload.get("end_value")),
        precision=_required_string(payload, "precision", field=f"{field}.precision"),
        timezone=_optional_string(payload.get("timezone")),
        source=_required_string(payload, "source", field=f"{field}.source"),
        confidence=_required_string(payload, "confidence", field=f"{field}.confidence"),
    )


def _mapping(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{field} must be an object")
    return value


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("expected a string or null")
    return value


def _required_string(payload: dict[str, Any], key: str, *, field: str | None = None) -> str:
    value = payload[key]
    if not isinstance(value, str):
        raise TypeError(f"{field or key} must be a string")
    return value


def _string_default(payload: dict[str, Any], key: str, default: str) -> str:
    if key not in payload:
        return default
    return _required_string(payload, key)


def _string_list(value: object, field: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise TypeError(f"{field} must be an array of strings")
    return value


def _signal_validation_code(issues: list[str]) -> str:
    if any("evidence.locator" in issue for issue in issues):
        return "evidence_locator_invalid"
    identity_fields = ("signal_id", "source.source_id", "source.source_sha256")
    if any(any(field in issue for field in identity_fields) for issue in issues):
        return "signal_identity_invalid"
    return "signal_invalid"
