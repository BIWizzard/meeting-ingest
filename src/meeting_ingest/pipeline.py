"""Reusable pipeline entry points."""

from __future__ import annotations

from pathlib import Path
import re

from meeting_ingest.archive import archive_and_reconcile, repair_duplicate_source
from meeting_ingest.clock import Clock, SystemClock, format_iso_timestamp
from meeting_ingest.config import MeetingIngestConfig
from meeting_ingest.doctor import find_issues, project_status
from meeting_ingest.errors import ConfigError, EXIT_ARTIFACT_WRITE, MeetingIngestError, PipelineNotImplementedError
from meeting_ingest.extract import extract_source
from meeting_ingest.hashing import sha256_file
from meeting_ingest.ids import mint_ingest_run_id, mint_meeting_id
from meeting_ingest.ledger import LedgerSnapshot, append_snapshot, latest_record_for_source
from meeting_ingest.locking import ProjectLock, lock_path
from meeting_ingest.paths import ProjectPaths, init_project, load_project
from meeting_ingest.provider import ProviderRequest
from meeting_ingest.providers.mock import MockProvider
from meeting_ingest.render import RenderContext, render_summary_plus_verbatim
from meeting_ingest.run_summary import RunSummary
from meeting_ingest.schema import SUPPORTED_OUTPUT_MODES, SignalRecord
from meeting_ingest.signals import write_signal_jsonl


def initialize(project_root: Path) -> RunSummary:
    paths = init_project(project_root)
    return RunSummary(
        status="success",
        exit_code=0,
        details={
            "command": "init",
            "config_path": str(paths.config_path),
            "meetings_root": str(paths.meetings_root),
        },
    )


def ingest(
    source: Path,
    *,
    start: Path | None = None,
    mode: str | None = None,
    provider: str | None = None,
    quality: str | None = None,
    clock: Clock | None = None,
) -> RunSummary:
    config, paths = load_project(start or source)
    selected_mode = mode or config.default_mode
    selected_provider = provider or config.default_provider
    selected_quality = quality or config.default_quality
    _validate_ingest_options(config, selected_mode, selected_provider)

    with ProjectLock(lock_path(paths.cache), clock=clock):
        return _ingest_locked(
            source,
            paths=paths,
            selected_mode=selected_mode,
            selected_provider=selected_provider,
            selected_quality=selected_quality,
            clock=clock,
        )


def _ingest_locked(
    source: Path,
    *,
    paths: ProjectPaths,
    selected_mode: str,
    selected_provider: str,
    selected_quality: str,
    clock: Clock | None,
) -> RunSummary:
    source = source.resolve()
    source_sha256 = sha256_file(source)
    existing_record = latest_record_for_source(paths.ledger, source_sha256)
    if existing_record is not None:
        return _no_op_summary(source, paths, source_sha256, existing_record)

    extraction = extract_source(source)
    meeting_id = mint_meeting_id(extraction.effective_date.value, source_sha256)
    ingest_run_id = mint_ingest_run_id(extraction.effective_date.value, clock=clock)

    provider_response = MockProvider().extract(
        ProviderRequest(
            transcript=extraction.normalized_text,
            source_name=source.name,
            meeting_id=meeting_id,
            effective_date=extraction.effective_date.value,
            quality=selected_quality,
        )
    )
    artifact_path = _next_artifact_path(paths, extraction.effective_date.value, provider_response.title)
    artifact_slug = _slug(provider_response.title)
    markdown = render_summary_plus_verbatim(
        provider_response,
        extraction.normalized_text,
        RenderContext(
            meeting_id=meeting_id,
            ingest_run_id=ingest_run_id,
            source_name=source.name,
            source_sha256=source_sha256,
            slug=artifact_slug,
            effective_date=extraction.effective_date.value,
            output_mode=selected_mode,
            provider=selected_provider,
            model_alias=selected_quality,
            model_id="none" if selected_provider == "mock" else selected_provider,
        ),
        clock=clock,
    )
    _write_artifact(artifact_path, markdown)
    signal_path = paths.signals / f"{meeting_id}.jsonl"
    signal_records = _signal_records_from_provider(
        provider_response.communication_signals,
        meeting_id=meeting_id,
        ingest_run_id=ingest_run_id,
        effective_at=extraction.effective_date.value,
        recorded_at=format_iso_timestamp((clock or SystemClock()).now_utc()),
    )
    signal_result = write_signal_jsonl(signal_path, signal_records)
    provider_response = provider_response.__class__(
        **{
            **provider_response.__dict__,
            "communication_signals": [signal.to_summary() for signal in signal_records],
        }
    )

    relative_artifact_path = artifact_path.relative_to(paths.meetings_root)
    relative_signal_path = signal_result.path.relative_to(paths.meetings_root)
    artifact_state = {
        selected_mode: {
            "kind": "markdown",
            "status": "ready",
            "path": str(relative_artifact_path),
            "provider": selected_provider,
            "model_alias": selected_quality,
            "model_id": selected_provider,
            "schema_version": "1.0",
        }
    }
    signal_state = {
        "status": "ready",
        "path": str(relative_signal_path),
        "count": signal_result.count,
        "schema_version": "1.0",
    }
    source_path = str(source)
    _append_ingest_snapshot(
        paths,
        event="primary_artifacts_ready",
        source_sha256=source_sha256,
        meeting_id=meeting_id,
        ingest_run_id=ingest_run_id,
        source_path=source_path,
        artifacts=artifact_state,
        signals=signal_state,
        reconcile={"status": "pending"},
        clock=clock,
    )
    archive_result = archive_and_reconcile(source, source_sha256, paths)
    processed_path = archive_result.processed_path.relative_to(paths.meetings_root)
    completed_reconcile = {**archive_result.reconcile, "processed_path": str(processed_path)}
    append_snapshot(
        paths.ledger,
        LedgerSnapshot(
            event="ingest_completed",
            source_sha256=source_sha256,
            meeting_id=meeting_id,
            ingest_run_id=ingest_run_id,
            source_path=source_path,
            artifacts=artifact_state,
            signals=signal_state,
            reconcile=completed_reconcile,
        ),
        clock=clock,
    )
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
        details={
            "command": "ingest",
            "output_mode": selected_mode,
            "provider": selected_provider,
            "quality": selected_quality,
            "title": {
                "value": provider_response.title,
                "slug": artifact_slug,
                "confidence": "medium",
                "rename_suggestion": None,
            },
            "archive": {"processed_path": str(processed_path)},
            "reconcile": completed_reconcile,
        },
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
        },
    )


def reconcile(start: Path) -> RunSummary:
    _, paths = load_project(start)
    repaired: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    with ProjectLock(lock_path(paths.cache)):
        for source in _inbox_sources(paths):
            source_sha256 = sha256_file(source)
            existing_record = latest_record_for_source(paths.ledger, source_sha256)
            if existing_record is None:
                skipped.append(
                    {
                        "path": str(source.relative_to(paths.meetings_root)),
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
                    "status": repair_result["reconcile"]["status"],
                    "reason": repair_result["reconcile"]["reason"],
                    "processed_path": repair_result["processed_path"],
                }
            )
    return RunSummary(
        status="success",
        exit_code=0,
        details={
            "command": "reconcile",
            "repaired": repaired,
            "skipped": skipped,
        },
    )


def _validate_ingest_options(config: MeetingIngestConfig, mode: str, provider: str) -> None:
    if mode not in SUPPORTED_OUTPUT_MODES:
        raise ConfigError(f"Unsupported output mode: {mode}", code="unsupported_output_mode")
    if provider != "mock":
        if provider == "anthropic" and not config.privacy.allow_remote_provider:
            raise ConfigError("Remote provider use is disabled by config.", code="remote_provider_disabled")
        raise ConfigError(f"Provider is not implemented yet: {provider}", code="provider_not_implemented")


def _next_artifact_path(paths: ProjectPaths, effective_date: str, title: str) -> Path:
    slug = _slug(title) or "untitled-meeting"
    base = f"{effective_date}-{slug}"
    candidate = paths.meetings_root / f"{base}.md"
    counter = 2
    while candidate.exists():
        candidate = paths.meetings_root / f"{base}-{counter}.md"
        counter += 1
    return candidate


def _slug(value: str, *, max_length: int = 80) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug[:max_length].strip("-")


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


def _no_op_summary(source: Path, paths: ProjectPaths, source_sha256: str, record: dict[str, object]) -> RunSummary:
    repair_result = _repair_duplicate_source(source, paths=paths, source_sha256=source_sha256, record=record, clock=None)
    reconcile = repair_result["reconcile"]
    artifacts = record.get("artifacts", {})
    existing_artifacts = {}
    if isinstance(artifacts, dict):
        existing_artifacts = {
            mode: artifact.get("path")
            for mode, artifact in artifacts.items()
            if isinstance(artifact, dict) and artifact.get("path")
        }
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
            "existing_artifacts": existing_artifacts,
            "archive": {"processed_path": repair_result["processed_path"]},
            "reconcile": reconcile,
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
    append_snapshot(
        paths.ledger,
        LedgerSnapshot(
            event="reconcile_repaired",
            source_sha256=source_sha256,
            meeting_id=str(record.get("meeting_id")),
            ingest_run_id=str(record.get("ingest_run_id") or "repair"),
            source_path=str(source),
            artifacts=_dict_value(record.get("artifacts")),
            signals=_dict_value(record.get("signals")),
            reconcile=reconcile,
        ),
        clock=clock,
    )
    return {"processed_path": processed_path, "reconcile": reconcile}


def _dict_value(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _signal_records_from_provider(
    signals: object,
    *,
    meeting_id: str,
    ingest_run_id: str,
    effective_at: str,
    recorded_at: str,
) -> list[SignalRecord]:
    records: list[SignalRecord] = []
    for signal in signals:
        if isinstance(signal, SignalRecord):
            records.append(signal)
    return records


def _append_ingest_snapshot(
    paths: ProjectPaths,
    *,
    event: str,
    source_sha256: str,
    meeting_id: str,
    ingest_run_id: str,
    source_path: str,
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
            source_path=source_path,
            artifacts=artifacts,
            signals=signals,
            reconcile=reconcile,
        ),
        clock=clock,
    )
