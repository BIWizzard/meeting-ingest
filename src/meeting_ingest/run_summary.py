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
    "runtime_provenance_schema",
    "runtime_provenance_sha256",
    "runtime_provenance",
}


@dataclass
class RunSummary:
    schema_version: str = "1.1"
    status: str = "success"
    exit_code: int = 0
    source_sha256: str | None = None
    meeting_id: str | None = None
    ingest_run_id: str | None = None
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    runtime_provenance: dict[str, Any] | None = None
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
        if self.runtime_provenance is not None:
            from meeting_ingest.provider_handoff import RUNTIME_PROVENANCE_SCHEMA, runtime_provenance_sha256

            data["runtime_provenance_schema"] = RUNTIME_PROVENANCE_SCHEMA
            data["runtime_provenance_sha256"] = runtime_provenance_sha256(self.runtime_provenance)
            data["runtime_provenance"] = self.runtime_provenance
        collisions = RESERVED_KEYS.intersection(self.details)
        if collisions:
            raise ValueError(f"RunSummary details cannot override reserved keys: {', '.join(sorted(collisions))}")
        data.update(self.details)
        return data
