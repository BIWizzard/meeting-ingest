"""Machine-readable command summaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


RESERVED_KEYS = {
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


@dataclass
class RunSummary:
    schema_version: str = "1.0"
    status: str = "success"
    exit_code: int = 0
    source_sha256: str | None = None
    meeting_id: str | None = None
    ingest_run_id: str | None = None
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "schema_version": self.schema_version,
            "status": self.status,
            "exit_code": self.exit_code,
            "source_sha256": self.source_sha256,
            "meeting_id": self.meeting_id,
            "ingest_run_id": self.ingest_run_id,
            "artifacts": self.artifacts,
            "warnings": self.warnings,
            "errors": self.errors,
        }
        collisions = RESERVED_KEYS.intersection(self.details)
        if collisions:
            raise ValueError(f"RunSummary details cannot override reserved keys: {', '.join(sorted(collisions))}")
        data.update(self.details)
        return data
