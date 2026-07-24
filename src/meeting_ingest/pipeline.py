"""Reusable pipeline entry points."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
import json
import re

from meeting_ingest.archive import archive_and_reconcile, quarantine_source, repair_duplicate_source
from meeting_ingest.clock import Clock, SystemClock, format_iso_timestamp
from meeting_ingest.config import MeetingIngestConfig
from meeting_ingest.doctor import find_issues, project_status, session_handoff_status
from meeting_ingest.errors import (
    ConfigError,
    EXIT_ARTIFACT_WRITE,
    EXIT_GENERAL_FAILURE,
    EXIT_RUNTIME_READINESS,
    EXIT_USAGE_OR_CONFIG,
    MeetingIngestError,
    ProviderError,
    RuntimeHandoffMismatchError,
    SourceExtractionError,
    UnsupportedSourceFormatError,
)
from meeting_ingest.extract import extract_source
from meeting_ingest.hashing import sha256_file
from meeting_ingest.ids import mint_ingest_run_id, mint_meeting_id, mint_source_id
from meeting_ingest.ledger import (
    LedgerSnapshot,
    append_snapshot,
    has_legacy_record_for_source,
    latest_record_for_source,
    read_records,
)
from meeting_ingest.locking import ProjectLock, lock_path
from meeting_ingest.paths import ProjectPaths, init_project, load_project
from meeting_ingest.provider import ProviderRequest
from meeting_ingest.provider_contract import PROVIDER_CONTRACT, response_contract_for_request
from meeting_ingest.provider_handoff import (
    SessionProviderEnvelope,
    cleanup_session_provider_files,
    normalized_transcript_sha256,
    read_session_provider_envelope,
    request_for_missing_response,
    runtime_provenance_sha256,
    verify_session_handoff_runtime,
    write_provider_request,
)
from meeting_ingest.providers import get_provider
from meeting_ingest.render import RenderContext, render_summary_plus_verbatim
from meeting_ingest.run_summary import RunSummary
from meeting_ingest.readiness import DevelopmentOverride, assess_readiness, require_write_readiness, with_runtime_provenance
from meeting_ingest.schema import (
    SUPPORTED_OUTPUT_MODES,
    ProviderResponse,
    ProviderSignal,
    ProviderValidationError,
    EvidenceLocator,
    SignalEvidence,
    SignalRecord,
    SignalSource,
    SignalTime,
    SignalTiming,
    validate_provider_response,
)
from meeting_ingest.signals import (
    SignalIdentityResult,
    SignalWriteResult,
    assign_deterministic_signal_ids,
    read_signal_jsonl,
    write_signal_jsonl,
)


class _PreparedNoOp(Exception):
    def __init__(self, summary: RunSummary) -> None:
        super().__init__("prepared ingest is a no-op")
        self.summary = summary


@dataclass(frozen=True)
class _PreparedEffectiveDate:
    value: str
    confidence: str
    source: str


@dataclass(frozen=True)
class _PreparedExtraction:
    normalized_text: str
    source_format: str
    effective_date: _PreparedEffectiveDate
    duration: str | None = None


@dataclass(frozen=True)
class _PreparedIngest:
    source: Path
    source_sha256: str
    extraction: object
    meeting_id: str
    ingest_run_id: str


@dataclass(frozen=True)
class _ArtifactPath:
    path: Path
    collision: bool


@dataclass(frozen=True)
class _TitleMetadata:
    value: str
    slug: str
    confidence: str
    rename_suggestion: str | None


def initialize(
    project_root: Path, *, development_override: DevelopmentOverride | None = None
) -> RunSummary:
    readiness = require_write_readiness(project_root, operation="init", development_override=development_override)
    paths = init_project(project_root)
    return with_runtime_provenance(RunSummary(
        status="success",
        exit_code=0,
        details={
            "command": "init",
            "config_path": str(paths.config_path),
            "meetings_root": str(paths.meetings_root),
        },
    ), readiness)


def ingest(
    source: Path,
    *,
    start: Path | None = None,
    mode: str | None = None,
    provider: str | None = None,
    quality: str | None = None,
    provider_response: Path | None = None,
    meeting_date: str | None = None,
    clock: Clock | None = None,
    development_override: DevelopmentOverride | None = None,
) -> RunSummary:
    config, paths = load_project(start or source)
    if provider_response is not None and meeting_date is not None:
        raise ConfigError(
            "--meeting-date is not valid with --provider-response; the persisted request already fixes the date.",
            code="invalid_meeting_date_phase",
        )
    selected_mode = mode or config.default_mode
    selected_provider = provider or ("session" if provider_response else config.default_provider)
    selected_quality = quality or config.default_quality
    readiness = require_write_readiness(
        paths.project_root,
        operation="ingest",
        development_override=development_override,
        require_session_provider=selected_provider == "session",
        require_remote_provider=selected_provider == "anthropic",
        allow_pending_handoffs=provider_response is not None,
    )
    _validate_ingest_options(config, selected_mode, selected_provider)
    if provider_response is not None and selected_provider != "session":
        raise ConfigError(
            "--provider-response is only valid with provider 'session'.",
            code="invalid_provider_response_provider",
        )
    if selected_provider == "session" and provider_response is None:
        raise ConfigError(
            "Session ingest requires --provider-response; use provider-request for phase 1.",
            code="missing_provider_response",
        )

    if provider_response is not None:
        verify_session_handoff_runtime(
            _resolve_provider_response_path(provider_response, paths),
            paths=paths,
            current_runtime_provenance=asdict(readiness.runtime_provenance),
        )

    with ProjectLock(lock_path(paths.cache), clock=clock):
        if provider_response is not None:
            summary = _complete_session_ingest_locked(
                source,
                provider_response=provider_response,
                paths=paths,
                selected_mode=selected_mode,
                selected_quality=selected_quality,
                current_runtime_provenance=asdict(readiness.runtime_provenance),
                clock=clock,
            )
        else:
            summary = _ingest_locked(
                source,
                paths=paths,
                selected_mode=selected_mode,
                selected_provider=selected_provider,
                selected_quality=selected_quality,
                meeting_date=meeting_date,
                clock=clock,
            )
    return with_runtime_provenance(summary, readiness)


def validate_response(
    provider_response: Path,
    *,
    source: Path,
    start: Path | None = None,
    development_override: DevelopmentOverride | None = None,
) -> RunSummary:
    """Validate a session response without producing ingest side effects."""
    _, paths = load_project(start or source)
    readiness = assess_readiness(
        paths.project_root,
        operation="validate-response",
        development_override=development_override,
        require_session_provider=True,
        allow_pending_handoffs=True,
    )
    resolved_source = source.resolve()
    response_path = _resolve_provider_response_path(provider_response, paths)
    try:
        current_source_sha256 = sha256_file(resolved_source)
    except OSError as exc:
        raise SourceExtractionError(
            str(resolved_source),
            f"Source file could not be read: {resolved_source}: {exc}",
        ) from exc
    try:
        envelope = read_session_provider_envelope(
            response_path,
            paths=paths,
            current_source_sha256=current_source_sha256,
            current_runtime_provenance=asdict(readiness.runtime_provenance),
        )
    except RuntimeHandoffMismatchError as exc:
        exc.details.setdefault("runtime_provenance", asdict(readiness.runtime_provenance))
        raise
    validate_provider_response(envelope.response)
    runtime_blocked = readiness.verdict == "blocked"
    return with_runtime_provenance(RunSummary(
        status="blocked" if runtime_blocked else "success",
        exit_code=readiness.exit_code if runtime_blocked else 0,
        source_sha256=str(envelope.request["source_sha256"]),
        meeting_id=str(envelope.request["meeting_id"]),
        ingest_run_id=str(envelope.request["ingest_run_id"]),
        details={
            "command": "validate-response",
            "provider": "session",
            "source": {"path": _relative_to_meetings(paths, resolved_source)},
            "provider_response": {
                "status": "valid",
                "path": _relative_to_meetings(paths, response_path),
            },
            "runtime_readiness": {
                "verdict": readiness.verdict,
                "findings": [finding.to_dict() for finding in readiness.findings],
            },
            "side_effects": "none",
        },
    ), readiness)


def repair_date(
    selector: str,
    *,
    date: str,
    start: Path | None = None,
    clock: Clock | None = None,
    development_override: DevelopmentOverride | None = None,
) -> RunSummary:
    new_date = _validate_meeting_date(date)
    _, paths = load_project(start or Path.cwd())
    readiness = require_write_readiness(paths.project_root, operation="repair-date", development_override=development_override)
    with ProjectLock(lock_path(paths.cache), clock=clock):
        summary = _repair_date_locked(selector, new_date=new_date, paths=paths, clock=clock)
    return with_runtime_provenance(summary, readiness)


def _repair_date_locked(selector: str, *, new_date: str, paths: ProjectPaths, clock: Clock | None) -> RunSummary:
    target: dict[str, Any] | None = None
    for record in read_records(paths.ledger):
        if selector in (record.get("meeting_id"), record.get("source_sha256")) and _record_has_primary_artifacts(record):
            target = record
    if target is None:
        raise MeetingIngestError(
            phase="repair",
            code="repair_target_not_found",
            message=f"No ready ingest found for selector: {selector}",
            exit_code=EXIT_USAGE_OR_CONFIG,
            recoverable=True,
            details={"selector": selector},
        )

    meeting_id = str(target["meeting_id"])
    artifacts = {mode: dict(entry) for mode, entry in target.get("artifacts", {}).items() if isinstance(entry, dict)}
    for mode, entry in artifacts.items():
        artifact_path = paths.meetings_root / str(entry.get("path", ""))
        if not entry.get("path") or not artifact_path.exists():
            raise MeetingIngestError(
                phase="repair",
                code="repair_artifact_missing",
                message=f"Artifact for mode {mode!r} is missing: {entry.get('path')}",
                exit_code=EXIT_ARTIFACT_WRITE,
                recoverable=False,
                details={"mode": mode, "path": entry.get("path")},
            )

    signals_state = dict(target.get("signals", {})) if isinstance(target.get("signals"), dict) else {}
    if signals_state.get("path"):
        signal_path = paths.meetings_root / str(signals_state["path"])
        if not signal_path.exists():
            raise MeetingIngestError(
                phase="repair",
                code="repair_artifact_missing",
                message=f"Signal file is missing: {signals_state['path']}",
                exit_code=EXIT_ARTIFACT_WRITE,
                recoverable=False,
                details={"path": signals_state["path"]},
            )

    first_entry = next(iter(artifacts.values()))
    previous = _front_matter_date_fields(paths.meetings_root / str(first_entry["path"]))
    paths_already_repaired = all(
        Path(str(entry["path"])).name.startswith(f"{new_date}-") for entry in artifacts.values()
    )
    if previous.get("date") == new_date and paths_already_repaired:
        return RunSummary(
            status="no_op",
            exit_code=0,
            source_sha256=str(target["source_sha256"]),
            meeting_id=meeting_id,
            details={"command": "repair-date", "date": new_date, "reason": "date_already_current"},
        )

    warnings: list[str] = []
    changed_modes: list[str] = []
    for mode, entry in artifacts.items():
        old_path = paths.meetings_root / str(entry["path"])
        slug = str(entry.get("slug") or re.sub(r"^\d{4}-\d{2}-\d{2}-", "", old_path.stem))
        destination = _repaired_artifact_path(paths, new_date, slug, current=old_path)
        content = _rewrite_front_matter_date(
            old_path.read_text(encoding="utf-8"), date=new_date, confidence="manual", source="repair"
        )
        destination.path.write_text(content, encoding="utf-8")
        if destination.path != old_path:
            old_path.unlink()
        if destination.collision:
            warnings.append(f"artifact filename collision; wrote {destination.path.relative_to(paths.meetings_root)}")
        entry["path"] = str(destination.path.relative_to(paths.meetings_root))
        changed_modes.append(mode)

    if signals_state.get("path"):
        repaired_artifact_path = str(next(iter(artifacts.values()))["path"])
        repaired_signal_path = paths.meetings_root / str(signals_state["path"])
        repaired_signals = _rewrite_signal_effective_at(
            repaired_signal_path,
            new_date=new_date,
            artifact_path=repaired_artifact_path,
        )
        signals_state["fingerprint"] = repaired_signals.fingerprint

    append_snapshot(
        paths.ledger,
        LedgerSnapshot(
            event="date_repaired",
            source_sha256=str(target["source_sha256"]),
            meeting_id=meeting_id,
            ingest_run_id=None,
            source=dict(target.get("source", {})),
            artifacts=artifacts,
            signals=signals_state,
            reconcile=dict(target.get("reconcile", {})),
            derived=dict(target.get("derived", {"playbook_update_status": "not_applicable"})),
            repair={
                "previous_date": previous.get("date"),
                "previous_date_confidence": previous.get("date_confidence"),
                "previous_date_source": previous.get("date_source"),
                "date": new_date,
                "changed_modes": changed_modes,
            },
        ),
        clock=clock,
    )
    return RunSummary(
        status="success",
        exit_code=0,
        source_sha256=str(target["source_sha256"]),
        meeting_id=meeting_id,
        artifacts=[
            {"kind": "markdown", "mode": mode, "status": "ready", "path": str(entry["path"])}
            for mode, entry in artifacts.items()
        ],
        warnings=warnings,
        details={
            "command": "repair-date",
            "repair": {
                "previous_date": previous.get("date"),
                "previous_date_confidence": previous.get("date_confidence"),
                "previous_date_source": previous.get("date_source"),
                "date": new_date,
                "changed_modes": changed_modes,
            },
        },
    )


def provider_request(
    source: Path,
    *,
    start: Path | None = None,
    mode: str | None = None,
    provider: str | None = None,
    quality: str | None = None,
    meeting_date: str | None = None,
    clock: Clock | None = None,
    development_override: DevelopmentOverride | None = None,
) -> RunSummary:
    config, paths = load_project(start or source)
    selected_mode = mode or config.default_mode
    selected_provider = provider or "session"
    selected_quality = quality or config.default_quality
    if selected_provider != "session":
        raise ConfigError("provider-request only supports provider 'session'.", code="invalid_provider_request_provider")

    readiness = require_write_readiness(
        paths.project_root,
        operation="provider-request",
        development_override=development_override,
        require_session_provider=True,
    )
    _validate_ingest_options(config, selected_mode, selected_provider)

    with ProjectLock(lock_path(paths.cache), clock=clock):
        summary = _provider_request_locked(
            source,
            paths=paths,
            selected_mode=selected_mode,
            selected_quality=selected_quality,
            meeting_date=meeting_date,
            runtime_provenance=asdict(readiness.runtime_provenance),
            clock=clock,
        )
    return with_runtime_provenance(summary, readiness)


def complete_session_ingest(
    source: Path,
    *,
    provider_response: Path,
    start: Path | None = None,
    clock: Clock | None = None,
    development_override: DevelopmentOverride | None = None,
) -> RunSummary:
    return ingest(
        source,
        start=start,
        provider="session",
        provider_response=provider_response,
        clock=clock,
        development_override=development_override,
    )


def ingest_inbox(
    start: Path,
    *,
    mode: str | None = None,
    provider: str | None = None,
    quality: str | None = None,
    clock: Clock | None = None,
    development_override: DevelopmentOverride | None = None,
) -> RunSummary:
    config, paths = load_project(start)
    selected_mode = mode or config.default_mode
    selected_provider = provider or config.default_provider
    selected_quality = quality or config.default_quality
    readiness = require_write_readiness(
        paths.project_root,
        operation="ingest-inbox",
        development_override=development_override,
        require_session_provider=selected_provider == "session",
        require_remote_provider=selected_provider == "anthropic",
        allow_pending_handoffs=selected_provider == "session",
    )
    _validate_ingest_options(config, selected_mode, selected_provider)
    if selected_provider == "session":
        return with_runtime_provenance(_session_ingest_inbox_requests(
            paths,
            selected_mode=selected_mode,
            selected_quality=selected_quality,
            runtime_provenance=asdict(readiness.runtime_provenance),
            clock=clock,
        ), readiness)

    sources = _direct_inbox_sources(paths)
    results: list[dict[str, object]] = []
    batch_errors: list[dict[str, object]] = []
    for source in sources:
        relative_source = str(source.relative_to(paths.meetings_root))
        try:
            summary = ingest(
                source,
                start=paths.meetings_root,
                mode=selected_mode,
                provider=selected_provider,
                quality=selected_quality,
                clock=clock,
                development_override=development_override,
            )
        except MeetingIngestError as exc:
            error_block = exc.to_error_block()
            batch_errors.append({"source": relative_source, **error_block})
            results.append(
                {
                    "source": relative_source,
                    "status": "failed",
                    "exit_code": exc.exit_code,
                    "errors": [error_block],
                    "artifacts": [],
                }
            )
            continue

        results.append(_batch_result_from_summary(relative_source, summary))

    succeeded = sum(1 for result in results if result["status"] in {"success", "no_op"})
    failed = sum(1 for result in results if result["status"] == "failed")
    if not results:
        status = "no_op"
        exit_code = 0
    elif failed:
        status = "partial_success" if succeeded else "failed"
        exit_code = EXIT_GENERAL_FAILURE
    else:
        status = "success"
        exit_code = 0

    return with_runtime_provenance(RunSummary(
        status=status,
        exit_code=exit_code,
        errors=batch_errors,
        details={
            "command": "ingest-inbox",
            "meetings_root": str(paths.meetings_root),
            "processed": len(results),
            "succeeded": succeeded,
            "failed": failed,
            "results": results,
        },
    ), readiness)


def _session_ingest_inbox_requests(
    paths: ProjectPaths,
    *,
    selected_mode: str,
    selected_quality: str,
    runtime_provenance: dict[str, Any],
    clock: Clock | None,
) -> RunSummary:
    sources = _direct_inbox_sources(paths)
    results: list[dict[str, object]] = []
    batch_errors: list[dict[str, object]] = []
    for source in sources:
        relative_source = str(source.relative_to(paths.meetings_root))
        try:
            with ProjectLock(lock_path(paths.cache), clock=clock):
                summary = _provider_request_locked(
                    source,
                    paths=paths,
                    selected_mode=selected_mode,
                    selected_quality=selected_quality,
                    meeting_date=None,
                    runtime_provenance=runtime_provenance,
                    clock=clock,
                )
        except MeetingIngestError as exc:
            error_block = exc.to_error_block()
            batch_errors.append({"source": relative_source, **error_block})
            results.append(
                {
                    "source": relative_source,
                    "status": "failed",
                    "exit_code": exc.exit_code,
                    "errors": [error_block],
                    "artifacts": [],
                }
            )
            continue

        result = _batch_result_from_summary(relative_source, summary)
        if summary.status == "success":
            result["status"] = "pending_provider_response"
        results.append(result)

    pending = sum(1 for result in results if result["status"] == "pending_provider_response")
    no_op = sum(1 for result in results if result["status"] == "no_op")
    failed = sum(1 for result in results if result["status"] == "failed")
    succeeded = pending + no_op
    if not results:
        status = "no_op"
        exit_code = 0
    elif failed:
        status = "partial_success" if succeeded else "failed"
        exit_code = EXIT_GENERAL_FAILURE
    else:
        status = "success"
        exit_code = 0

    return RunSummary(
        status=status,
        exit_code=exit_code,
        errors=batch_errors,
        details={
            "command": "ingest-inbox",
            "provider": "session",
            "phase": "provider_request",
            "meetings_root": str(paths.meetings_root),
            "processed": len(results),
            "pending_provider_responses": pending,
            "succeeded": succeeded,
            "no_ops": no_op,
            "failed": failed,
            "results": results,
        },
    )


def _batch_result_from_summary(relative_source: str, summary: RunSummary) -> dict[str, object]:
    summary_data = summary.to_dict()
    return {
        "source": relative_source,
        "status": summary.status,
        "exit_code": summary.exit_code,
        "source_sha256": summary.source_sha256,
        "meeting_id": summary.meeting_id,
        "ingest_run_id": summary.ingest_run_id,
        "artifacts": summary.artifacts,
        "warnings": summary.warnings,
        "errors": summary.errors,
        "details": {
            key: value
            for key, value in summary_data.items()
            if key
            not in {
                "schema_version",
                "status",
                "exit_code",
                "source_sha256",
                "meeting_id",
                "ingest_run_id",
                "artifacts",
                "warnings",
                "errors",
            }
        },
    }


def _ingest_locked(
    source: Path,
    *,
    paths: ProjectPaths,
    selected_mode: str,
    selected_provider: str,
    selected_quality: str,
    meeting_date: str | None,
    clock: Clock | None,
) -> RunSummary:
    try:
        prepared = _prepare_ingest(source, paths=paths, clock=clock, meeting_date=meeting_date)
    except _PreparedNoOp as no_op:
        return no_op.summary

    provider_impl = get_provider(selected_provider)
    try:
        provider_response = provider_impl.extract(
            ProviderRequest(
                transcript=prepared.extraction.normalized_text,
                source_name=prepared.source.name,
                meeting_id=prepared.meeting_id,
                effective_date=prepared.extraction.effective_date.value,
                quality=selected_quality,
            )
        )
        validate_provider_response(provider_response)
    except ProviderValidationError as exc:
        _record_source_failure(
            paths,
            source=prepared.source,
            source_sha256=prepared.source_sha256,
            error=exc,
            clock=clock,
            meeting_id=prepared.meeting_id,
            ingest_run_id=prepared.ingest_run_id,
        )
        raise
    except MeetingIngestError as exc:
        _record_source_failure(
            paths,
            source=prepared.source,
            source_sha256=prepared.source_sha256,
            error=exc,
            clock=clock,
            meeting_id=prepared.meeting_id,
            ingest_run_id=prepared.ingest_run_id,
        )
        raise
    except Exception as exc:
        provider_error = ProviderError(selected_provider, str(exc))
        _record_source_failure(
            paths,
            source=prepared.source,
            source_sha256=prepared.source_sha256,
            error=provider_error,
            clock=clock,
            meeting_id=prepared.meeting_id,
            ingest_run_id=prepared.ingest_run_id,
        )
        raise provider_error from exc
    return _finish_ingest(
        prepared,
        paths=paths,
        selected_mode=selected_mode,
        selected_provider=selected_provider,
        selected_quality=selected_quality,
        provider_response=provider_response,
        model_id=provider_impl.model_id,
        provider_host=None,
        clock=clock,
    )


def _provider_request_locked(
    source: Path,
    *,
    paths: ProjectPaths,
    selected_mode: str,
    selected_quality: str,
    meeting_date: str | None,
    runtime_provenance: dict[str, Any],
    clock: Clock | None,
) -> RunSummary:
    try:
        prepared = _prepare_ingest(source, paths=paths, clock=clock, meeting_date=meeting_date)
    except _PreparedNoOp as no_op:
        return no_op.summary
    request_payload = {
        "schema_version": "1.1",
        "handoff_type": "provider_request",
        "provider_contract": PROVIDER_CONTRACT,
        "source_name": prepared.source.name,
        "source_sha256": prepared.source_sha256,
        "normalized_transcript_sha256": normalized_transcript_sha256(prepared.extraction.normalized_text),
        "meeting_id": prepared.meeting_id,
        "ingest_run_id": prepared.ingest_run_id,
        "effective_date": prepared.extraction.effective_date.value,
        "quality": selected_quality,
        "output_mode": selected_mode,
        "runtime_provenance_schema": "1.0",
        "runtime_provenance_sha256": runtime_provenance_sha256(runtime_provenance),
        "runtime_provenance": runtime_provenance,
        "normalized_transcript": prepared.extraction.normalized_text,
        "source_format": prepared.extraction.source_format,
        "date_confidence": prepared.extraction.effective_date.confidence,
        "date_source": prepared.extraction.effective_date.source,
        "duration": prepared.extraction.duration,
    }
    request_payload["response_contract"] = response_contract_for_request(request_payload)
    transcript_sha256 = request_payload["normalized_transcript_sha256"]
    request_path, response_path = write_provider_request(paths, request_payload)
    return RunSummary(
        status="success",
        exit_code=0,
        source_sha256=prepared.source_sha256,
        meeting_id=prepared.meeting_id,
        ingest_run_id=prepared.ingest_run_id,
        warnings=_date_warnings(prepared.extraction),
        details={
            "command": "provider-request",
            "provider": "session",
            "quality": selected_quality,
            "output_mode": selected_mode,
            "source": {
                "path": _relative_to_meetings(paths, prepared.source),
                "source_type": prepared.extraction.source_format,
            },
            "request_path": _relative_to_meetings(paths, request_path),
            "expected_response_path": _relative_to_meetings(paths, response_path),
            "provider_request": {
                "status": "ready",
                "path": _relative_to_meetings(paths, request_path),
                "contract": PROVIDER_CONTRACT,
            },
            "provider_response": {
                "status": "pending",
                "path": _relative_to_meetings(paths, response_path),
            },
            "normalized_transcript_sha256": transcript_sha256,
            "effective_date": {
                "value": prepared.extraction.effective_date.value,
                "confidence": prepared.extraction.effective_date.confidence,
                "source": prepared.extraction.effective_date.source,
            },
        },
    )


def _complete_session_ingest_locked(
    source: Path,
    *,
    provider_response: Path,
    paths: ProjectPaths,
    selected_mode: str,
    selected_quality: str,
    current_runtime_provenance: dict[str, Any],
    clock: Clock | None,
) -> RunSummary:
    source = source.resolve()
    source_sha256 = sha256_file(source)
    existing_record = latest_record_for_source(paths.ledger, source_sha256)
    if _record_has_primary_artifacts(existing_record):
        return _no_op_summary(source, paths, source_sha256, existing_record, clock=clock)
    _raise_if_legacy_source_unresolved(source, paths, source_sha256, existing_record)

    response_path = _resolve_provider_response_path(provider_response, paths)
    try:
        envelope = read_session_provider_envelope(
            response_path,
            paths=paths,
            current_source_sha256=source_sha256,
            current_runtime_provenance=current_runtime_provenance,
        )
        validate_provider_response(envelope.response)
    # Runtime mismatches must bypass the generic exception wrapper and failure-ledger
    # write below so the original handoff remains recoverable under its bound runtime.
    except RuntimeHandoffMismatchError:
        raise
    except ProviderError as exc:
        _record_session_failure_from_response_path(paths, source=source, source_sha256=source_sha256, response_path=response_path, error=exc, clock=clock)
        raise
    except ProviderValidationError as exc:
        _record_session_failure_from_response_path(paths, source=source, source_sha256=source_sha256, response_path=response_path, error=exc, clock=clock)
        raise
    except Exception as exc:
        provider_error = ProviderError("session", str(exc))
        _record_session_failure_from_response_path(
            paths,
            source=source,
            source_sha256=source_sha256,
            response_path=response_path,
            error=provider_error,
            clock=clock,
        )
        raise provider_error from exc

    prepared = _prepared_ingest_from_session_request(source, source_sha256=source_sha256, envelope=envelope)
    request_mode = str(envelope.request["output_mode"])
    request_quality = envelope.metadata.model_alias
    summary = _finish_ingest(
        prepared,
        paths=paths,
        selected_mode=request_mode,
        selected_provider="session",
        selected_quality=request_quality,
        provider_response=envelope.response,
        model_id=envelope.metadata.model_id,
        provider_host=envelope.metadata.provider_host,
        clock=clock,
    )
    summary.warnings.extend(_session_phase2_option_warnings(selected_mode, selected_quality, request_mode, request_quality))
    cleanup_session_provider_files(envelope)
    return summary


def _finish_ingest(
    prepared: _PreparedIngest,
    *,
    paths: ProjectPaths,
    selected_mode: str,
    selected_provider: str,
    selected_quality: str,
    provider_response: ProviderResponse,
    model_id: str,
    provider_host: str | None,
    clock: Clock | None,
) -> RunSummary:
    source = prepared.source
    source_sha256 = prepared.source_sha256
    extraction = prepared.extraction
    meeting_id = prepared.meeting_id
    ingest_run_id = prepared.ingest_run_id
    artifact_slug = _slug(provider_response.title)
    title_metadata = _title_metadata(
        provider_response.title,
        artifact_slug=artifact_slug,
        source_name=source.name,
        effective_date=extraction.effective_date.value,
    )
    artifact_destination = _next_artifact_path(paths, extraction.effective_date.value, provider_response.title)
    artifact_path = artifact_destination.path
    signal_path = paths.signals / f"{meeting_id}.jsonl"
    recorded_at = format_iso_timestamp((clock or SystemClock()).now_utc())
    signal_identity = _signal_records_from_provider(
        provider_response.communication_signals,
        source=source,
        source_sha256=source_sha256,
        artifact_path=str(artifact_path.relative_to(paths.meetings_root)),
        meeting_id=meeting_id,
        ingest_run_id=ingest_run_id,
        effective_at=extraction.effective_date.value,
        date_confidence=extraction.effective_date.confidence,
        date_source=extraction.effective_date.source,
        recorded_at=recorded_at,
    )
    signal_records = signal_identity.signals
    signal_result = write_signal_jsonl(signal_path, signal_records)
    render_response = _provider_response_with_signals(provider_response, signal_records)
    markdown = render_summary_plus_verbatim(
        render_response,
        extraction.normalized_text,
        RenderContext(
            meeting_id=meeting_id,
            ingest_run_id=ingest_run_id,
            source_name=source.name,
            source_sha256=source_sha256,
            slug=artifact_slug,
            effective_date=extraction.effective_date.value,
            date_confidence=extraction.effective_date.confidence,
            date_source=extraction.effective_date.source,
            duration=extraction.duration,
            output_mode=selected_mode,
            provider=selected_provider,
            model_alias=selected_quality,
            model_id=model_id,
            provider_host=provider_host,
        ),
        clock=clock,
    )
    _write_artifact(artifact_path, markdown)

    relative_artifact_path = artifact_path.relative_to(paths.meetings_root)
    relative_signal_path = signal_result.path.relative_to(paths.meetings_root)
    artifact_state = {
        selected_mode: {
            "kind": "markdown",
            "status": "ready",
            "path": str(relative_artifact_path),
            "provider": selected_provider,
            "model_alias": selected_quality,
            "model_id": model_id,
            "schema_version": "1.0",
            "title": provider_response.title,
            "slug": artifact_slug,
            "title_confidence": title_metadata.confidence,
            "filename_confidence": title_metadata.confidence,
        }
    }
    if provider_host:
        artifact_state[selected_mode]["provider_host"] = provider_host
    signal_state = {
        "status": "ready",
        "path": str(relative_signal_path),
        "count": signal_result.count,
        "schema_version": "1.1",
        "fingerprint": signal_result.fingerprint,
    }
    source_state = _source_state(paths, source, extraction.source_format)
    _append_ingest_snapshot(
        paths,
        event="primary_artifacts_ready",
        source_sha256=source_sha256,
        meeting_id=meeting_id,
        ingest_run_id=ingest_run_id,
        source=source_state,
        artifacts=artifact_state,
        signals=signal_state,
        reconcile={"status": "pending"},
        clock=clock,
    )
    archive_result = archive_and_reconcile(source, source_sha256, paths)
    processed_path = archive_result.processed_path.relative_to(paths.meetings_root)
    completed_reconcile = {**archive_result.reconcile, "processed_path": str(processed_path)}
    completed_source_state = {**source_state, "processed_path": str(processed_path)}
    append_snapshot(
        paths.ledger,
        LedgerSnapshot(
            event="ingest_completed",
            source_sha256=source_sha256,
            meeting_id=meeting_id,
            ingest_run_id=ingest_run_id,
            source=completed_source_state,
            artifacts=artifact_state,
            signals=signal_state,
            reconcile=completed_reconcile,
        ),
        clock=clock,
    )
    warnings: list[str] = []
    if artifact_destination.collision:
        warnings.append(f"artifact filename collision; wrote {relative_artifact_path}")
    warnings.extend(_date_warnings(extraction))
    warnings.extend(signal_identity.warnings)
    return RunSummary(
        status="success",
        exit_code=0,
        source_sha256=source_sha256,
        meeting_id=meeting_id,
        ingest_run_id=ingest_run_id,
        artifacts=[
            {
                "kind": "markdown",
                "mode": selected_mode,
                "status": "ready",
                "path": str(relative_artifact_path),
            },
            {
                "kind": "signals",
                "status": "ready",
                "path": str(relative_signal_path),
                "count": signal_result.count,
            },
        ],
        warnings=warnings,
        details={
            "command": "ingest",
            "output_mode": selected_mode,
            "provider": selected_provider,
            "quality": selected_quality,
            **({"provider_host": provider_host} if provider_host else {}),
            "effective_date": {
                "value": extraction.effective_date.value,
                "confidence": extraction.effective_date.confidence,
                "source": extraction.effective_date.source,
            },
            "title": {
                "value": title_metadata.value,
                "slug": title_metadata.slug,
                "confidence": title_metadata.confidence,
                "rename_suggestion": title_metadata.rename_suggestion,
            },
            "archive": {"processed_path": str(processed_path)},
            "reconcile": completed_reconcile,
        },
    )


def _prepare_ingest(
    source: Path,
    *,
    paths: ProjectPaths,
    clock: Clock | None,
    meeting_date: str | None = None,
) -> _PreparedIngest:
    if meeting_date is not None:
        meeting_date = _validate_meeting_date(meeting_date)
    source = source.resolve()
    source_sha256 = sha256_file(source)
    existing_record = latest_record_for_source(paths.ledger, source_sha256)
    if _record_has_primary_artifacts(existing_record):
        raise _PreparedNoOp(_no_op_summary(source, paths, source_sha256, existing_record, clock=clock))
    _raise_if_legacy_source_unresolved(source, paths, source_sha256, existing_record)

    try:
        extraction = extract_source(source, meeting_date=meeting_date)
    except (UnsupportedSourceFormatError, SourceExtractionError) as exc:
        _record_source_failure(paths, source=source, source_sha256=source_sha256, error=exc, clock=clock)
        raise
    meeting_id = mint_meeting_id(extraction.effective_date.value, source_sha256)
    ingest_run_id = mint_ingest_run_id(extraction.effective_date.value, clock=clock)
    return _PreparedIngest(
        source=source,
        source_sha256=source_sha256,
        extraction=extraction,
        meeting_id=meeting_id,
        ingest_run_id=ingest_run_id,
    )


def _prepared_ingest_from_session_request(
    source: Path,
    *,
    source_sha256: str,
    envelope: SessionProviderEnvelope,
) -> _PreparedIngest:
    request = envelope.request
    extraction = _PreparedExtraction(
        normalized_text=str(request["normalized_transcript"]),
        source_format=str(request.get("source_format") or source.suffix.lower().lstrip(".") or "unknown"),
        effective_date=_PreparedEffectiveDate(
            value=str(request["effective_date"]),
            confidence=str(request.get("date_confidence") or "unknown"),
            source=str(request.get("date_source") or "provider_request"),
        ),
        duration=request.get("duration") if isinstance(request.get("duration"), str) else None,
    )
    return _PreparedIngest(
        source=source,
        source_sha256=source_sha256,
        extraction=extraction,
        meeting_id=str(request["meeting_id"]),
        ingest_run_id=str(request["ingest_run_id"]),
    )


def _resolve_provider_response_path(path: Path, paths: ProjectPaths) -> Path:
    if path.is_absolute():
        return path
    cwd_candidate = (Path.cwd() / path).resolve()
    if cwd_candidate.exists():
        return cwd_candidate
    meetings_candidate = (paths.meetings_root / path).resolve()
    if meetings_candidate.exists():
        return meetings_candidate
    return cwd_candidate


def _session_phase2_option_warnings(
    selected_mode: str,
    selected_quality: str,
    request_mode: str,
    request_quality: str,
) -> list[str]:
    warnings: list[str] = []
    if selected_mode != request_mode:
        warnings.append(
            f"phase 2 ignored CLI mode {selected_mode!r}; using persisted provider request mode {request_mode!r}"
        )
    if selected_quality != request_quality:
        warnings.append(
            f"phase 2 ignored CLI quality {selected_quality!r}; using persisted provider request quality {request_quality!r}"
        )
    return warnings


def _record_session_failure_from_response_path(
    paths: ProjectPaths,
    *,
    source: Path,
    source_sha256: str,
    response_path: Path,
    error: MeetingIngestError,
    clock: Clock | None,
) -> None:
    request_data = request_for_missing_response(response_path, paths)
    meeting_id = None
    ingest_run_id = None
    if request_data is not None:
        request, _ = request_data
        meeting_id = str(request.get("meeting_id")) if request.get("meeting_id") else None
        ingest_run_id = str(request.get("ingest_run_id")) if request.get("ingest_run_id") else None
    _record_source_failure(
        paths,
        source=source,
        source_sha256=source_sha256,
        error=error,
        clock=clock,
        meeting_id=meeting_id,
        ingest_run_id=ingest_run_id,
    )


def doctor(start: Path) -> RunSummary:
    _, paths = load_project(start)
    issues = find_issues(paths)
    return RunSummary(
        status="success" if not issues else "issues_found",
        exit_code=0 if not issues else 1,
        details={
            "command": "doctor",
            "project": project_status(paths),
            "issues": [issue.to_dict() for issue in issues],
        },
    )


def status(start: Path) -> RunSummary:
    _, paths = load_project(start)
    return RunSummary(
        status="success",
        exit_code=0,
        details={
            "command": "status",
            "project": project_status(paths),
            "session_handoffs": session_handoff_status(paths),
        },
    )


def reconcile(
    start: Path, *, development_override: DevelopmentOverride | None = None
) -> RunSummary:
    _, paths = load_project(start)
    readiness = require_write_readiness(paths.project_root, operation="reconcile", development_override=development_override)
    repaired: list[dict[str, object]] = []
    skipped: list[dict[str, object]] = []
    with ProjectLock(lock_path(paths.cache)):
        inbox_sources: list[tuple[Path, str, dict[str, object] | None]] = []
        for source in _inbox_sources(paths):
            source_sha256 = sha256_file(source)
            existing_record = latest_record_for_source(paths.ledger, source_sha256)
            inbox_sources.append((source, source_sha256, existing_record))

        for source, source_sha256, existing_record in inbox_sources:
            if not _record_has_primary_artifacts(existing_record):
                _raise_if_legacy_source_unresolved(source, paths, source_sha256, existing_record)

        for source, source_sha256, existing_record in inbox_sources:
            if not _record_has_primary_artifacts(existing_record):
                skipped.append(
                    {
                        "path": str(source.relative_to(paths.meetings_root)),
                        "source_sha256": source_sha256,
                        "meeting_id": existing_record.get("meeting_id") if existing_record else None,
                        "reason": "source_not_in_ledger",
                    }
                )
                continue
            repair_result = _repair_duplicate_source(
                source,
                paths=paths,
                source_sha256=source_sha256,
                record=existing_record,
                clock=None,
            )
            repaired.append(
                {
                    "path": repair_result["reconcile"].get("path", ""),
                    "source_sha256": source_sha256,
                    "meeting_id": existing_record.get("meeting_id"),
                    "status": repair_result["reconcile"]["status"],
                    "reason": repair_result["reconcile"]["reason"],
                    "processed_path": repair_result["processed_path"],
                    "changed": repair_result["changed"],
                }
            )
    return with_runtime_provenance(RunSummary(
        status="success",
        exit_code=0,
        details={
            "command": "reconcile",
            "repaired": repaired,
            "skipped": skipped,
        },
    ), readiness)


def _validate_ingest_options(config: MeetingIngestConfig, mode: str, provider: str) -> None:
    if mode not in SUPPORTED_OUTPUT_MODES:
        raise ConfigError(f"Unsupported output mode: {mode}", code="unsupported_output_mode")
    if provider == "mock":
        return
    if provider == "session":
        if not config.privacy.allow_session_provider:
            raise ConfigError("Session provider use is disabled by config.", code="session_provider_disabled")
        return
    if provider == "anthropic":
        if not config.privacy.allow_remote_provider:
            raise ConfigError("Remote provider use is disabled by config.", code="remote_provider_disabled")
        return
    raise ConfigError(f"Provider is not implemented yet: {provider}", code="provider_not_implemented")


_MEETING_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _validate_meeting_date(value: str) -> str:
    if _MEETING_DATE.match(value):
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            pass
        else:
            return value
    raise ConfigError(
        f"--meeting-date must be a real calendar date in YYYY-MM-DD form, got: {value}",
        code="invalid_meeting_date",
    )


def _date_warnings(extraction: object) -> list[str]:
    warnings: list[str] = []
    effective = extraction.effective_date
    if effective.source == "file_mtime":
        warnings.append(
            f"effective date {effective.value} was inferred from file modification time and may be a "
            "download date rather than the meeting occurrence; re-run with --meeting-date YYYY-MM-DD "
            "or fix later with repair-date"
        )
    selection = getattr(extraction, "date_selection", None)
    if selection is not None and selection.conflict:
        listing = ", ".join(
            f"{candidate.source}={candidate.value}"
            for candidate in selection.candidates
            if candidate.source != "file_mtime"
        )
        warnings.append(
            f"conflicting meeting date evidence ({listing}); selected {effective.source}={effective.value}"
        )
    return warnings


def _front_matter_date_fields(path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return fields
    for line in lines[1:]:
        if line.strip() == "---":
            break
        for key in ("date", "date_confidence", "date_source"):
            prefix = f"{key}: "
            if line.startswith(prefix):
                fields[key] = line[len(prefix):].strip()
    return fields


def _rewrite_front_matter_date(content: str, *, date: str, confidence: str, source: str) -> str:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return content
    replacements = {"date": date, "date_confidence": confidence, "date_source": source}
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            break
        for key, value in replacements.items():
            if lines[index].startswith(f"{key}: "):
                lines[index] = f"{key}: {value}"
    return "\n".join(lines) + ("\n" if content.endswith("\n") else "")


def _repaired_artifact_path(paths: ProjectPaths, new_date: str, slug: str, *, current: Path) -> _ArtifactPath:
    base = f"{new_date}-{slug}"
    candidate = paths.meetings_root / f"{base}.md"
    collision = False
    counter = 2
    while candidate.exists() and candidate != current:
        collision = True
        candidate = paths.meetings_root / f"{base}-{counter}.md"
        counter += 1
    return _ArtifactPath(path=candidate, collision=collision)


def _rewrite_signal_effective_at(path: Path, *, new_date: str, artifact_path: str) -> SignalWriteResult:
    updated: list[SignalRecord] = []
    for record in read_signal_jsonl(path):
        timing = record.timing
        if timing is not None:
            timing = replace(
                timing,
                occurred=replace(
                    timing.occurred,
                    value=new_date,
                    end_value=None,
                    precision="date",
                    timezone=None,
                    source="repair",
                    confidence="manual",
                ),
            )
        source = replace(record.source, artifact_path=artifact_path) if record.source is not None else None
        updated.append(replace(record, effective_at=new_date, timing=timing, source=source))
    return write_signal_jsonl(path, updated)


def _next_artifact_path(paths: ProjectPaths, effective_date: str, title: str) -> _ArtifactPath:
    slug = _slug(title) or "untitled-meeting"
    base = f"{effective_date}-{slug}"
    candidate = paths.meetings_root / f"{base}.md"
    collision = False
    counter = 2
    while candidate.exists():
        collision = True
        candidate = paths.meetings_root / f"{base}-{counter}.md"
        counter += 1
    return _ArtifactPath(path=candidate, collision=collision)


def _slug(value: str, *, max_length: int = 80) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug[:max_length].strip("-")


def _title_metadata(title: str, *, artifact_slug: str, source_name: str, effective_date: str) -> _TitleMetadata:
    if not _is_low_signal_slug(artifact_slug):
        return _TitleMetadata(value=title, slug=artifact_slug, confidence="medium", rename_suggestion=None)
    source_slug = _source_slug_candidate(source_name)
    rename_suggestion = f"{effective_date}-{source_slug}.md" if source_slug else None
    return _TitleMetadata(value=title, slug=artifact_slug, confidence="low", rename_suggestion=rename_suggestion)


def _source_slug_candidate(source_name: str) -> str | None:
    stem = Path(source_name).stem
    stem = re.sub(r"^20\d{2}[-_ ]?\d{2}[-_ ]?\d{2}[-_ ]*", "", stem)
    slug = _slug(stem)
    return None if _is_low_signal_slug(slug) else slug


def _is_low_signal_slug(slug: str) -> bool:
    if slug in {"", "generic", "untitled", "untitled-meeting", "meeting", "call"}:
        return True
    return bool(re.fullmatch(r"generic(?:-[0-9a-f]{6,})?", slug))


def _inbox_sources(paths: ProjectPaths) -> list[Path]:
    if not paths.inbox.exists():
        return []
    sources: list[Path] = []
    for path in paths.inbox.rglob("*"):
        if not path.is_file():
            continue
        if paths.inbox_done in path.parents:
            continue
        sources.append(path)
    return sources


def _direct_inbox_sources(paths: ProjectPaths) -> list[Path]:
    if not paths.inbox.exists():
        return []
    return sorted(path for path in paths.inbox.iterdir() if path.is_file())


def _write_artifact(path: Path, markdown: str) -> None:
    try:
        path.write_text(markdown, encoding="utf-8")
    except OSError as exc:
        raise MeetingIngestError(
            phase="artifact_write",
            code="artifact_write_failed",
            message=f"Could not write artifact: {path}",
            exit_code=EXIT_ARTIFACT_WRITE,
            recoverable=True,
            details={"path": str(path)},
        ) from exc


def _no_op_summary(
    source: Path,
    paths: ProjectPaths,
    source_sha256: str,
    record: dict[str, object],
    *,
    clock: Clock | None,
) -> RunSummary:
    repair_result = _repair_duplicate_source(source, paths=paths, source_sha256=source_sha256, record=record, clock=clock)
    reconcile = repair_result["reconcile"]
    artifacts = record.get("artifacts", {})
    existing_artifacts = {}
    existing_artifact_details = {}
    if isinstance(artifacts, dict):
        existing_artifacts = {
            mode: artifact.get("path")
            for mode, artifact in artifacts.items()
            if isinstance(artifact, dict) and artifact.get("path")
        }
        existing_artifact_details = {
            mode: artifact
            for mode, artifact in artifacts.items()
            if isinstance(artifact, dict) and artifact.get("path")
        }
    source_state = _dict_value(record.get("source"))
    return RunSummary(
        status="no_op",
        exit_code=0,
        source_sha256=source_sha256,
        meeting_id=str(record.get("meeting_id")) if record.get("meeting_id") else None,
        ingest_run_id=None,
        artifacts=[],
        warnings=[f"source already ingested; reconcile {reconcile['status']}"],
        details={
            "reason": "source_already_ingested",
            "source": {
                "path": _relative_to_meetings(paths, source),
                "source_type": source.suffix.lower().lstrip(".") or "unknown",
                "known_original_path": source_state.get("original_path"),
            },
            "existing_artifacts": existing_artifacts,
            "existing_artifact_details": existing_artifact_details,
            "archive": {"processed_path": repair_result["processed_path"]},
            "reconcile": reconcile,
            "repair": {
                "changed": repair_result["changed"],
                "ledger_event": "reconcile_repaired" if repair_result["changed"] else None,
            },
        },
    )


def _repair_duplicate_source(
    source: Path,
    *,
    paths: ProjectPaths,
    source_sha256: str,
    record: dict[str, object],
    clock: Clock | None,
) -> dict[str, object]:
    repair = repair_duplicate_source(source, source_sha256, paths)
    processed_path = str(repair.processed_path.relative_to(paths.meetings_root))
    reconcile = {**repair.reconcile, "processed_path": processed_path}
    source_state = _dict_value(record.get("source"))
    if not source_state:
        source_state = _source_state(paths, source, source.suffix.lower().lstrip(".") or "unknown")
    source_state = {**source_state, "processed_path": processed_path}
    if repair.changed:
        append_snapshot(
            paths.ledger,
            LedgerSnapshot(
                event="reconcile_repaired",
                source_sha256=source_sha256,
                meeting_id=str(record.get("meeting_id")),
                ingest_run_id=str(record.get("ingest_run_id") or "repair"),
                source=source_state,
                artifacts=_dict_value(record.get("artifacts")),
                signals=_dict_value(record.get("signals")),
                reconcile=reconcile,
            ),
            clock=clock,
        )
    return {"processed_path": processed_path, "reconcile": reconcile, "changed": repair.changed}


def _dict_value(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _record_has_primary_artifacts(record: dict[str, object] | None) -> bool:
    if record is None:
        return False
    if record.get("event") not in {"primary_artifacts_ready", "ingest_completed", "reconcile_repaired", "date_repaired"}:
        return False
    artifacts = record.get("artifacts")
    return isinstance(artifacts, dict) and bool(artifacts)


def _raise_if_legacy_source_unresolved(
    source: Path,
    paths: ProjectPaths,
    source_sha256: str,
    existing_record: dict[str, object] | None,
) -> None:
    if existing_record is not None or not has_legacy_record_for_source(paths.ledger, source_sha256):
        return
    raise MeetingIngestError(
        phase="ledger",
        code="legacy_source_unresolved",
        message=(
            f"The content of source file {source} matches a deprecated legacy ledger record and cannot be "
            "re-ingested until that history is explicitly adopted or the re-ingest is explicitly authorized."
        ),
        exit_code=EXIT_RUNTIME_READINESS,
        recoverable=False,
        details={"source_path": str(source), "source_sha256": source_sha256},
    )


def _signal_records_from_provider(
    signals: list[ProviderSignal | SignalRecord],
    *,
    source: Path,
    source_sha256: str,
    artifact_path: str,
    meeting_id: str,
    ingest_run_id: str,
    effective_at: str,
    date_confidence: str,
    date_source: str,
    recorded_at: str,
) -> SignalIdentityResult:
    records: list[SignalRecord] = []
    source_id = mint_source_id(source_sha256)
    acquired_at = format_iso_timestamp(datetime.fromtimestamp(source.stat().st_mtime, tz=UTC))
    for signal in signals:
        if isinstance(signal, SignalRecord):
            raise ProviderValidationError(
                "Provider returned enriched SignalRecord; providers must return ProviderSignal candidates.",
            )
        if isinstance(signal, ProviderSignal):
            locator = EvidenceLocator(
                scheme="timestamp" if signal.evidence.timestamp else "none",
                value=signal.evidence.timestamp,
            )
            evidence = SignalEvidence(
                kind=signal.evidence.kind,
                text=signal.evidence.text,
                speaker=signal.evidence.speaker,
                timestamp=signal.evidence.timestamp,
                locator=locator,
            )
            records.append(
                SignalRecord(
                    signal_id="pending",
                    meeting_id=meeting_id,
                    ingest_run_id=ingest_run_id,
                    effective_at=effective_at,
                    recorded_at=recorded_at,
                    signal_type=signal.signal_type,
                    stakeholder_id=signal.stakeholder_id,
                    stakeholder_name=signal.stakeholder_name,
                    stakeholder_name_raw=signal.evidence.speaker or signal.stakeholder_name,
                    summary=signal.summary,
                    evidence=evidence,
                    inference_level=signal.inference_level,
                    confidence=signal.confidence,
                    source=SignalSource(
                        source_id=source_id,
                        source_kind="meeting_transcript",
                        source_sha256=source_sha256,
                        meeting_id=meeting_id,
                        artifact_path=artifact_path,
                        channel=None,
                        evidence_locator_scheme=locator.scheme,
                    ),
                    timing=SignalTiming(
                        occurred=SignalTime(
                            value=effective_at,
                            end_value=None,
                            precision="date",
                            timezone=None,
                            source=date_source,
                            confidence=date_confidence,
                        ),
                        acquired=SignalTime(
                            value=acquired_at,
                            end_value=None,
                            precision="datetime",
                            timezone="UTC",
                            source="filesystem_mtime",
                            confidence="low",
                        ),
                        recorded=SignalTime(
                            value=recorded_at,
                            end_value=None,
                            precision="datetime",
                            timezone="UTC",
                            source="system_clock",
                            confidence="high",
                        ),
                    ),
                    topics=signal.topics,
                    project_refs=signal.project_refs,
                    recurrence=signal.recurrence,
                    status=signal.status,
                    schema_version="1.1",
                )
            )
            continue
        raise ProviderValidationError(f"Unsupported provider signal shape: {type(signal).__name__}")
    return assign_deterministic_signal_ids(records)


def _provider_response_with_signals(response: ProviderResponse, signals: list[SignalRecord]) -> ProviderResponse:
    return ProviderResponse(
        title=response.title,
        tl_dr=response.tl_dr,
        meeting_type=response.meeting_type,
        attendees=response.attendees,
        topics=response.topics,
        decisions=response.decisions,
        action_items=response.action_items,
        stakeholder_asks=response.stakeholder_asks,
        dependencies_risks=response.dependencies_risks,
        communication_signals=signals,
        open_questions=response.open_questions,
        cross_references=response.cross_references,
    )


def _append_ingest_snapshot(
    paths: ProjectPaths,
    *,
    event: str,
    source_sha256: str,
    meeting_id: str,
    ingest_run_id: str,
    source: dict[str, str | None],
    artifacts: dict[str, dict[str, str]],
    signals: dict[str, str | int],
    reconcile: dict[str, str],
    clock: Clock | None,
) -> None:
    append_snapshot(
        paths.ledger,
        LedgerSnapshot(
            event=event,
            source_sha256=source_sha256,
            meeting_id=meeting_id,
            ingest_run_id=ingest_run_id,
            source=source,
            artifacts=artifacts,
            signals=signals,
            reconcile=reconcile,
        ),
        clock=clock,
    )


def _record_source_failure(
    paths: ProjectPaths,
    *,
    source: Path,
    source_sha256: str,
    error: MeetingIngestError,
    clock: Clock | None,
    meeting_id: str | None = None,
    ingest_run_id: str | None = None,
) -> None:
    source_state = _source_state(paths, source, source.suffix.lower().lstrip(".") or "unknown")
    quarantine_block = None
    event = "ingest_failed"
    if isinstance(error, (UnsupportedSourceFormatError, SourceExtractionError)) and _is_in_inbox(paths, source):
        quarantine = quarantine_source(source, source_sha256, paths, reason=error.code)
        quarantine_block = {
            "status": "quarantined",
            "path": str(quarantine.path.relative_to(paths.meetings_root)),
            "reason": quarantine.reason,
        }
        event = "source_quarantined"
    append_snapshot(
        paths.ledger,
        LedgerSnapshot(
            event=event,
            source_sha256=source_sha256,
            meeting_id=meeting_id,
            ingest_run_id=ingest_run_id,
            source=source_state,
            artifacts={},
            signals={"status": "skipped", "path": None, "count": 0},
            reconcile={"status": "skipped", "reason": "primary_artifacts_not_ready"},
            error=error.to_error_block(),
            quarantine=quarantine_block,
        ),
        clock=clock,
    )


def _source_state(paths: ProjectPaths, source: Path, source_type: str) -> dict[str, str | None]:
    return {
        "original_path": _relative_to_meetings(paths, source),
        "processed_path": None,
        "source_type": source_type,
    }


def _relative_to_meetings(paths: ProjectPaths, path: Path) -> str:
    try:
        return str(path.relative_to(paths.meetings_root))
    except ValueError:
        return str(path)


def _is_in_inbox(paths: ProjectPaths, path: Path) -> bool:
    try:
        path.relative_to(paths.inbox)
    except ValueError:
        return False
    return paths.inbox_done not in path.parents
