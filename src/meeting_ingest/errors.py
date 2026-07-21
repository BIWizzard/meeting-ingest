"""Shared error taxonomy for CLI, pipeline, and tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


EXIT_SUCCESS = 0
EXIT_GENERAL_FAILURE = 1
EXIT_USAGE_OR_CONFIG = 2
EXIT_UNSUPPORTED_SOURCE = 3
EXIT_EXTRACTION_FAILURE = 4
EXIT_PROVIDER_FAILURE = 5
EXIT_PROVIDER_VALIDATION = 6
EXIT_ARTIFACT_WRITE = 7
EXIT_LEDGER_WRITE = 8
EXIT_ARCHIVE_RECONCILE = 9
EXIT_LOCK_CONFLICT = 10
EXIT_BLOCKING_DERIVED_FAILURE = 11
EXIT_RUNTIME_READINESS = 12


@dataclass
class MeetingIngestError(Exception):
    """Base typed error that can be rendered into run-summary JSON."""

    phase: str
    code: str
    message: str
    exit_code: int = EXIT_GENERAL_FAILURE
    recoverable: bool = False
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        Exception.__init__(self, self.message)

    def to_error_block(self) -> dict[str, Any]:
        block: dict[str, Any] = {
            "phase": self.phase,
            "code": self.code,
            "message": self.message,
            "recoverable": self.recoverable,
        }
        if self.details:
            block["details"] = self.details
        return block


class ConfigError(MeetingIngestError):
    def __init__(self, message: str, *, code: str = "invalid_config", recoverable: bool = True) -> None:
        super().__init__(
            phase="config",
            code=code,
            message=message,
            exit_code=EXIT_USAGE_OR_CONFIG,
            recoverable=recoverable,
        )


class UnsupportedSourceFormatError(MeetingIngestError):
    def __init__(self, path: str) -> None:
        super().__init__(
            phase="source_read",
            code="unsupported_source_format",
            message=f"Unsupported source format: {path}",
            exit_code=EXIT_UNSUPPORTED_SOURCE,
            recoverable=False,
            details={"path": path},
        )


class SourceExtractionError(MeetingIngestError):
    def __init__(self, path: str, message: str) -> None:
        super().__init__(
            phase="source_read",
            code="source_extraction_failed",
            message=message,
            exit_code=EXIT_EXTRACTION_FAILURE,
            recoverable=True,
            details={"path": path},
        )


class ProviderError(MeetingIngestError):
    def __init__(self, provider: str, message: str) -> None:
        super().__init__(
            phase="provider",
            code="provider_failed",
            message=f"Provider {provider!r} failed: {message}",
            exit_code=EXIT_PROVIDER_FAILURE,
            recoverable=True,
            details={"provider": provider},
        )


class LockConflictError(MeetingIngestError):
    def __init__(self, lock_path: str) -> None:
        super().__init__(
            phase="lock",
            code="lock_conflict",
            message=f"Another meeting-ingest process holds the project lock: {lock_path}",
            exit_code=EXIT_LOCK_CONFLICT,
            recoverable=True,
            details={"lock_path": lock_path},
        )


class PipelineNotImplementedError(MeetingIngestError):
    def __init__(self, command: str) -> None:
        super().__init__(
            phase="pipeline",
            code="not_implemented",
            message=f"`{command}` is not implemented yet.",
            exit_code=EXIT_GENERAL_FAILURE,
            recoverable=False,
            details={"command": command},
        )
