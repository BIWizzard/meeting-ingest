"""Session-provider handoff planner records."""

from __future__ import annotations

import json
from pathlib import Path

from meeting_ingest.errors import MeetingIngestError, ProviderError
from meeting_ingest.hashing import sha256_file
from meeting_ingest.paths import ProjectPaths
from meeting_ingest.provider_handoff import PROVIDER_CONTRACT, provider_response_path


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


def session_handoff_counts(handoffs: list[dict[str, object]]) -> dict[str, int]:
    return {
        "total": len(handoffs),
        "pending": sum(1 for handoff in handoffs if handoff.get("status") == "pending_provider_response"),
        "stale": sum(1 for handoff in handoffs if handoff.get("status") == "stale_handoff"),
        "failed": sum(1 for handoff in handoffs if handoff.get("status") == "failed"),
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
