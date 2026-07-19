"""Host/session provider request and response envelope helpers."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

from meeting_ingest.errors import ProviderError
from meeting_ingest.paths import ProjectPaths
from meeting_ingest.provider_contract import PROVIDER_CONTRACT
from meeting_ingest.provider_json import provider_response_from_payload
from meeting_ingest.schema import SUPPORTED_OUTPUT_MODES, SUPPORTED_QUALITIES, ProviderResponse, ProviderValidationError


REQUEST_DIR = "provider-requests"
RESPONSE_DIR = "provider-responses"
INGEST_RUN_ID_PATTERN = re.compile(r"[A-Za-z0-9._-]+")


@dataclass(frozen=True)
class SessionProviderMetadata:
    model_alias: str
    model_id: str
    provider_host: str | None = None


@dataclass(frozen=True)
class SessionProviderEnvelope:
    response: ProviderResponse
    metadata: SessionProviderMetadata
    request: dict[str, Any]
    request_path: Path
    response_path: Path


def normalized_transcript_sha256(transcript: str) -> str:
    return sha256(transcript.encode("utf-8")).hexdigest()


def provider_request_path(paths: ProjectPaths, ingest_run_id: str) -> Path:
    return paths.cache / REQUEST_DIR / f"{ingest_run_id}.request.json"


def provider_response_path(paths: ProjectPaths, ingest_run_id: str) -> Path:
    return paths.cache / RESPONSE_DIR / f"{ingest_run_id}.response.json"


def write_provider_request(paths: ProjectPaths, request_payload: dict[str, Any]) -> tuple[Path, Path]:
    ingest_run_id = str(request_payload["ingest_run_id"])
    request_path = _safe_provider_request_path(paths, ingest_run_id)
    response_path = provider_response_path(paths, ingest_run_id)
    request_path.parent.mkdir(parents=True, exist_ok=True)
    response_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.write_text(json.dumps(request_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return request_path, response_path


def read_session_provider_envelope(
    response_path: Path,
    *,
    paths: ProjectPaths,
    current_source_sha256: str,
) -> SessionProviderEnvelope:
    payload = _read_json(response_path)
    _require(payload.get("schema_version") == "1.0", "Unsupported provider response schema_version.")
    _require(payload.get("handoff_type") == "provider_response", "Provider response envelope has wrong handoff_type.")
    _require(payload.get("provider_contract") == PROVIDER_CONTRACT, "Unsupported provider response contract.")

    ingest_run_id = _required_string(payload, "ingest_run_id")
    request_path = _safe_provider_request_path(paths, ingest_run_id)
    request_payload = _read_request_json(request_path)
    _validate_request(request_payload)
    _verify_identity(payload, request_payload, current_source_sha256)

    provider = payload.get("provider")
    _require(isinstance(provider, dict), "Provider response envelope provider must be an object.")
    _require(provider.get("name") == "session", "Session response provider.name must be 'session'.")
    _require(provider.get("model_alias") == request_payload.get("quality"), "Session response model_alias must match request quality.")

    response_payload = payload.get("response")
    _require(isinstance(response_payload, dict), "Provider response envelope response must be an object.")
    response = provider_response_from_payload(response_payload)
    return SessionProviderEnvelope(
        response=response,
        metadata=SessionProviderMetadata(
            model_alias=str(provider.get("model_alias")),
            model_id=_model_id(provider),
            provider_host=_optional_string(provider.get("host")),
        ),
        request=request_payload,
        request_path=request_path,
        response_path=response_path,
    )


def request_for_missing_response(response_path: Path, paths: ProjectPaths) -> tuple[dict[str, Any], Path] | None:
    ingest_run_id = _ingest_run_id_from_response_path(response_path)
    if ingest_run_id is None:
        return None
    try:
        request_path = _safe_provider_request_path(paths, ingest_run_id)
        request_payload = _read_request_json(request_path)
    except ProviderValidationError:
        return None
    return request_payload, request_path


def cleanup_session_provider_files(envelope: SessionProviderEnvelope) -> None:
    for path in (envelope.request_path, envelope.response_path):
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ProviderError("session", f"Provider response file not found: {path}") from exc
    except OSError as exc:
        raise ProviderError("session", f"Provider response file could not be read: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ProviderError("session", f"Provider response file is not valid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ProviderValidationError("Provider response JSON root must be an object.")
    return payload


def _read_request_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ProviderValidationError(f"Persisted provider request file not found: {path}") from exc
    except OSError as exc:
        raise ProviderValidationError(f"Persisted provider request file could not be read: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ProviderValidationError(f"Persisted provider request file is not valid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ProviderValidationError("Persisted provider request JSON root must be an object.")
    return payload


def _validate_request(payload: dict[str, Any]) -> None:
    _require(payload.get("schema_version") == "1.0", "Unsupported provider request schema_version.")
    _require(payload.get("handoff_type") == "provider_request", "Provider request has wrong handoff_type.")
    _require(payload.get("provider_contract") == PROVIDER_CONTRACT, "Unsupported provider request contract.")
    for field in (
        "source_name",
        "source_sha256",
        "normalized_transcript_sha256",
        "meeting_id",
        "ingest_run_id",
        "effective_date",
        "quality",
        "output_mode",
        "normalized_transcript",
    ):
        _required_string(payload, field)
    _require(payload["output_mode"] in SUPPORTED_OUTPUT_MODES, "Persisted provider request output_mode is unsupported.")
    _require(payload["quality"] in SUPPORTED_QUALITIES, "Persisted provider request quality is unsupported.")


def _verify_identity(response: dict[str, Any], request: dict[str, Any], current_source_sha256: str) -> None:
    for field in ("meeting_id", "ingest_run_id", "source_sha256", "normalized_transcript_sha256"):
        if response.get(field) != request.get(field):
            raise ProviderValidationError(f"Provider response {field} does not match persisted request.")
    if request.get("source_sha256") != current_source_sha256:
        raise ProviderValidationError("Current source hash does not match persisted provider request.")
    transcript = str(request.get("normalized_transcript"))
    if request.get("normalized_transcript_sha256") != normalized_transcript_sha256(transcript):
        raise ProviderValidationError("Persisted provider request transcript hash is invalid.")


def _ingest_run_id_from_response_path(path: Path) -> str | None:
    name = path.name
    suffix = ".response.json"
    if not name.endswith(suffix):
        return None
    ingest_run_id = name[: -len(suffix)]
    return ingest_run_id or None


def _safe_provider_request_path(paths: ProjectPaths, ingest_run_id: str) -> Path:
    _require(bool(INGEST_RUN_ID_PATTERN.fullmatch(ingest_run_id)), "Provider response ingest_run_id is invalid.")
    request_path = provider_request_path(paths, ingest_run_id).resolve()
    request_dir = (paths.cache / REQUEST_DIR).resolve()
    try:
        request_path.relative_to(request_dir)
    except ValueError as exc:
        raise ProviderValidationError("Provider response ingest_run_id escapes provider request cache.") from exc
    return request_path


def _required_string(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value:
        raise ProviderValidationError(f"Provider envelope field {field!r} is required.")
    return value


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ProviderValidationError(message)


def _model_id(provider: dict[str, Any]) -> str:
    model_id = _optional_string(provider.get("model_id"))
    if model_id:
        return model_id
    host = _optional_string(provider.get("host"))
    if host:
        return f"{host}-session"
    return "session"


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
