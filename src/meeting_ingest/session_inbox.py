"""Session-provider inbox orchestration for active agent hosts."""

from __future__ import annotations

from collections.abc import Callable
import json
from pathlib import Path
from typing import Any

from meeting_ingest.clock import Clock
from meeting_ingest.errors import EXIT_GENERAL_FAILURE, ConfigError, MeetingIngestError, ProviderError
from meeting_ingest.hashing import sha256_file
from meeting_ingest.paths import ProjectPaths, load_project
from meeting_ingest import pipeline
from meeting_ingest.provider_handoff import PROVIDER_CONTRACT, provider_response_path
from meeting_ingest.run_summary import RunSummary


SessionInboxExtractor = Callable[[dict[str, Any], Path, Path], None]


def process_session_inbox(
    start: Path,
    *,
    extractor: SessionInboxExtractor | None = None,
    mode: str | None = None,
    quality: str | None = None,
    clock: Clock | None = None,
) -> RunSummary:
    """Run session inbox phase 1 and complete phase 2 when responses are available.

    The optional extractor is owned by the active host/session wrapper. It receives
    the persisted request payload, request path, and expected response path, and is
    responsible only for writing provider-response JSON.
    """

    results: list[dict[str, object]] = []
    errors: list[dict[str, object]] = []
    completed = 0
    pending = 0
    no_ops = 0
    failed = 0
    phase1_data: dict[str, object] = {
        "status": "not_run",
        "exit_code": 0,
        "pending_provider_responses": 0,
        "failed": 0,
    }
    warnings: list[str] = []

    config, paths = load_project(start)
    if not config.privacy.allow_session_provider:
        raise ConfigError("Session provider use is disabled by config.", code="session_provider_disabled")

    existing_results = pending_session_handoffs(paths)
    existing_pending = False
    stale = 0

    for result in existing_results:
        if not isinstance(result, dict):
            continue
        if result.get("status") == "stale_handoff":
            stale += 1
            result_warnings = result.get("warnings")
            if isinstance(result_warnings, list):
                warnings.extend(warning for warning in result_warnings if isinstance(warning, str))
            results.append(result)
            continue
        if result.get("status") == "failed":
            failed += 1
            result_errors = result.get("errors")
            if isinstance(result_errors, list):
                errors.extend(error for error in result_errors if isinstance(error, dict))
            results.append(result)
            continue

        completion = _complete_pending_result(
            result,
            paths_meetings_root=paths.meetings_root,
            extractor=extractor,
            clock=clock,
        )
        results.append(completion)
        if completion.get("status") in {"success", "no_op"}:
            completed += 1
        elif completion.get("status") == "pending_provider_response":
            pending += 1
        elif completion.get("status") == "failed":
            failed += 1
            result_errors = completion.get("errors")
            if isinstance(result_errors, list):
                errors.extend(error for error in result_errors if isinstance(error, dict))
        existing_pending = existing_pending or completion.get("status") == "pending_provider_response"

    if not existing_pending:
        phase1 = pipeline.ingest_inbox(
            paths.meetings_root,
            mode=mode,
            provider="session",
            quality=quality,
            clock=clock,
        )
        phase1_data = phase1.to_dict()
        phase1_results = phase1_data.get("results", [])
        if not isinstance(phase1_results, list):
            phase1_results = []
        errors.extend(phase1.errors)
        warnings.extend(phase1.warnings)
        failed += sum(1 for result in phase1_results if isinstance(result, dict) and result.get("status") == "failed")

        for result in phase1_results:
            if not isinstance(result, dict):
                continue
            if result.get("status") == "no_op":
                no_ops += 1
                results.append(result)
                continue
            if result.get("status") == "failed":
                results.append(result)
                continue
            if result.get("status") != "pending_provider_response":
                results.append(result)
                continue

            completion = _complete_pending_result(
                result,
                paths_meetings_root=paths.meetings_root,
                extractor=extractor,
                clock=clock,
            )
            results.append(completion)
            if completion.get("status") in {"success", "no_op"}:
                completed += 1
            elif completion.get("status") == "pending_provider_response":
                pending += 1
            elif completion.get("status") == "failed":
                failed += 1
                result_errors = completion.get("errors")
                if isinstance(result_errors, list):
                    errors.extend(error for error in result_errors if isinstance(error, dict))
    else:
        phase1_data = {
            "status": "skipped_existing_pending",
            "exit_code": 0,
            "pending_provider_responses": 0,
            "failed": 0,
        }

    if not results:
        status = "no_op"
        exit_code = 0
    elif failed:
        status = "partial_success" if completed or no_ops or pending else "failed"
        exit_code = EXIT_GENERAL_FAILURE
    else:
        status = "success"
        exit_code = 0

    return RunSummary(
        status=status,
        exit_code=exit_code,
        warnings=warnings,
        errors=errors,
        details={
            "command": "session-inbox",
            "provider": "session",
            "meetings_root": str(paths.meetings_root),
            "processed": len(results),
            "completed": completed,
            "pending_provider_responses": pending,
            "stale_handoffs": stale,
            "no_ops": no_ops,
            "failed": failed,
            "phase1": {
                "status": phase1_data.get("status", "unknown"),
                "exit_code": phase1_data.get("exit_code", 0),
                "pending_provider_responses": phase1_data.get("pending_provider_responses", 0),
                "failed": phase1_data.get("failed", 0),
            },
            "results": results,
        },
    )


def pending_session_handoffs(paths: ProjectPaths) -> list[dict[str, object]]:
    request_dir = paths.cache / "provider-requests"
    if not request_dir.exists():
        return []

    results: list[dict[str, object]] = []
    for request_path in sorted(request_dir.glob("*.request.json")):
        try:
            request_payload = json.loads(request_path.read_text(encoding="utf-8"))
            if not isinstance(request_payload, dict):
                raise ProviderError("session", f"Provider request JSON root must be an object: {request_path}")
            result = _pending_handoff_result(paths, request_payload, request_path)
        except MeetingIngestError as exc:
            result = _failed_handoff_result(paths, request_path, exc)
        except Exception as exc:
            result = _failed_handoff_result(paths, request_path, ProviderError("session", str(exc)))
        results.append(result)
    return results


def _complete_pending_result(
    result: dict[str, object],
    *,
    paths_meetings_root: Path,
    extractor: SessionInboxExtractor | None,
    clock: Clock | None,
) -> dict[str, object]:
    details = result.get("details")
    source = result.get("source")
    if not isinstance(details, dict) or not isinstance(source, str):
        error = ProviderError("session", "Session inbox result is missing source or handoff details.")
        return _failed_result(result, error)

    request_path_text = details.get("request_path")
    response_path_text = details.get("expected_response_path")
    if not isinstance(request_path_text, str) or not isinstance(response_path_text, str):
        error = ProviderError("session", "Session inbox result is missing request or response path.")
        return _failed_result(result, error)

    request_path = paths_meetings_root / request_path_text
    response_path = paths_meetings_root / response_path_text
    source_path = paths_meetings_root / source

    if extractor is not None:
        try:
            request_payload = json.loads(request_path.read_text(encoding="utf-8"))
            if not isinstance(request_payload, dict):
                raise ProviderError("session", f"Provider request JSON root must be an object: {request_path}")
            extractor(request_payload, request_path, response_path)
        except MeetingIngestError as exc:
            return _failed_result(result, exc)
        except Exception as exc:
            return _failed_result(result, ProviderError("session", str(exc)))

    if not response_path.exists():
        return {
            **result,
            "status": "pending_provider_response",
            "details": {
                **details,
                "provider_response": {
                    "status": "pending",
                    "path": response_path_text,
                },
            },
        }

    try:
        summary = pipeline.complete_session_ingest(
            source_path,
            start=paths_meetings_root,
            provider_response=response_path,
            clock=clock,
        )
    except MeetingIngestError as exc:
        return _failed_result(result, exc)

    completed = _batch_result_from_summary(source, summary)
    completed["phase1"] = result
    return completed


def _failed_result(result: dict[str, object], error: MeetingIngestError) -> dict[str, object]:
    return {
        **result,
        "status": "failed",
        "exit_code": error.exit_code,
        "errors": [error.to_error_block()],
    }


def _pending_handoff_result(
    paths: ProjectPaths,
    request_payload: dict[str, object],
    request_path: Path,
) -> dict[str, object]:
    _require_request_field(request_payload, "ingest_run_id")
    _require_request_field(request_payload, "source_name")
    _require_request_field(request_payload, "source_sha256")
    _require_request_field(request_payload, "meeting_id")
    _require_request_field(request_payload, "quality")
    _require_request_field(request_payload, "output_mode")
    if request_payload.get("provider_contract") != PROVIDER_CONTRACT:
        raise ProviderError("session", f"Unsupported provider request contract: {request_path}")

    ingest_run_id = str(request_payload["ingest_run_id"])
    response_path = provider_response_path(paths, ingest_run_id)
    source_path = paths.inbox / str(request_payload["source_name"])
    relative_source = _relative_to_meetings(paths, source_path)
    relative_request = _relative_to_meetings(paths, request_path)
    relative_response = _relative_to_meetings(paths, response_path)
    if not source_path.exists():
        return _stale_handoff_result(
            source=relative_source,
            request_payload=request_payload,
            request_path=relative_request,
            response_path=relative_response,
            response_exists=response_path.exists(),
            reason="source_missing",
        )
    if sha256_file(source_path) != str(request_payload["source_sha256"]):
        return _stale_handoff_result(
            source=relative_source,
            request_payload=request_payload,
            request_path=relative_request,
            response_path=relative_response,
            response_exists=response_path.exists(),
            reason="source_hash_mismatch",
        )

    response_status = "ready" if response_path.exists() else "pending"
    return {
        "source": relative_source,
        "status": "pending_provider_response",
        "exit_code": 0,
        "source_sha256": str(request_payload["source_sha256"]),
        "meeting_id": str(request_payload["meeting_id"]),
        "ingest_run_id": ingest_run_id,
        "artifacts": [],
        "warnings": [],
        "errors": [],
        "details": {
            "command": "session-inbox",
            "provider": "session",
            "phase": "existing_provider_request",
            "quality": str(request_payload["quality"]),
            "output_mode": str(request_payload["output_mode"]),
            "request_path": relative_request,
            "expected_response_path": relative_response,
            "provider_request": {
                "status": "ready",
                "path": relative_request,
                "contract": PROVIDER_CONTRACT,
            },
            "provider_response": {
                "status": response_status,
                "path": relative_response,
            },
        },
    }


def _stale_handoff_result(
    *,
    source: str,
    request_payload: dict[str, object],
    request_path: str,
    response_path: str,
    response_exists: bool,
    reason: str,
) -> dict[str, object]:
    message = (
        "Session provider handoff is stale or outside the inbox wrapper scope; "
        "complete it manually with `meeting-ingest ingest ... --provider-response ...` "
        "or remove the stale request/response files after confirming they are no longer needed."
    )
    response_status = "ready" if response_exists else "unknown"
    return {
        "source": source,
        "status": "stale_handoff",
        "exit_code": 0,
        "source_sha256": str(request_payload["source_sha256"]),
        "meeting_id": str(request_payload["meeting_id"]),
        "ingest_run_id": str(request_payload["ingest_run_id"]),
        "artifacts": [],
        "warnings": [message],
        "errors": [],
        "details": {
            "command": "session-inbox",
            "provider": "session",
            "phase": "existing_provider_request",
            "reason": reason,
            "quality": str(request_payload["quality"]),
            "output_mode": str(request_payload["output_mode"]),
            "request_path": request_path,
            "expected_response_path": response_path,
            "provider_request": {
                "status": "stale",
                "path": request_path,
                "contract": PROVIDER_CONTRACT,
            },
            "provider_response": {
                "status": response_status,
                "path": response_path,
            },
        },
    }


def _failed_handoff_result(paths: ProjectPaths, request_path: Path, error: MeetingIngestError) -> dict[str, object]:
    return {
        "source": None,
        "status": "failed",
        "exit_code": error.exit_code,
        "source_sha256": None,
        "meeting_id": None,
        "ingest_run_id": None,
        "artifacts": [],
        "warnings": [],
        "errors": [error.to_error_block()],
        "details": {
            "command": "session-inbox",
            "phase": "existing_provider_request",
            "request_path": _relative_to_meetings(paths, request_path),
        },
    }


def _require_request_field(payload: dict[str, object], field: str) -> None:
    value = payload.get(field)
    if not isinstance(value, str) or not value:
        raise ProviderError("session", f"Provider request field {field!r} is required.")


def _relative_to_meetings(paths: ProjectPaths, path: Path) -> str:
    try:
        return str(path.relative_to(paths.meetings_root))
    except ValueError:
        return str(path)


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
