"""Append-only source ledger."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any
import hashlib
import json
import re

from meeting_ingest.clock import Clock, SystemClock, format_iso_timestamp
from meeting_ingest.errors import EXIT_LEDGER_WRITE, MeetingIngestError
from meeting_ingest.provider_handoff import (
    RUNTIME_PROVENANCE_SCHEMA,
    runtime_provenance_sha256,
    valid_runtime_provenance_binding,
)
from meeting_ingest.readiness import current_runtime_provenance
from meeting_ingest.ids import canonical_json


_LEGACY_RECORD_KEYS = frozenset({"source_sha256", "meeting_id", "ingest_run_id"})
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_LEGACY_RUN_ID_RE = re.compile(r"(?:\d{8}T\d{6}Z|ingest-\d{8}-[a-z0-9-]+)")


@dataclass(frozen=True)
class LedgerSnapshot:
    event: str
    source_sha256: str
    meeting_id: str | None
    ingest_run_id: str | None
    source: dict[str, Any]
    artifacts: dict[str, dict[str, Any]]
    signals: dict[str, Any]
    reconcile: dict[str, Any]
    derived: dict[str, Any] = field(default_factory=lambda: {"playbook_update_status": "not_applicable"})
    error: dict[str, Any] | None = None
    quarantine: dict[str, Any] | None = None
    repair: dict[str, Any] | None = None
    schema_version: str = "2.0"
    ledger_record_id: str | None = None
    source_record_sequence: int | None = None

    def to_dict(self, *, clock: Clock | None = None) -> dict[str, Any]:
        active_clock = clock or SystemClock()
        provenance = current_runtime_provenance()
        if self.schema_version == "2.0" and provenance is None:
            raise MeetingIngestError(
                phase="ledger",
                code="ledger_provenance_missing",
                message="Runtime provenance is unavailable for a ledger 2.0 snapshot.",
                exit_code=EXIT_LEDGER_WRITE,
                recoverable=False,
            )
        return {
            "schema_version": self.schema_version,
            **(
                {
                    "ledger_record_id": self.ledger_record_id,
                    "source_record_sequence": self.source_record_sequence,
                }
                if self.schema_version == "2.0"
                else {}
            ),
            "event": self.event,
            "recorded_at": format_iso_timestamp(active_clock.now_utc()),
            **(
                {
                    "runtime_provenance_schema": RUNTIME_PROVENANCE_SCHEMA,
                    "runtime_provenance_sha256": runtime_provenance_sha256(provenance),
                    "runtime_provenance": provenance,
                }
                if provenance is not None and self.schema_version == "2.0"
                else {}
            ),
            "source_sha256": self.source_sha256,
            "meeting_id": self.meeting_id,
            "ingest_run_id": self.ingest_run_id,
            "source": self.source,
            "artifacts": self.artifacts,
            "signals": self.signals,
            "derived": self.derived,
            "error": self.error,
            "quarantine": self.quarantine,
            "reconcile": self.reconcile,
            **({"repair": self.repair} if self.repair is not None else {}),
        }


@dataclass(frozen=True)
class LedgerReadIssue:
    line_number: int
    code: str
    message: str


def mint_ledger_identity(
    ledger_path: Path,
    *,
    source_sha256: str,
    event: str,
    ingest_run_id: str | None,
) -> tuple[str, int]:
    """Mint the next source-local ledger identity while the project lock is held."""
    highest = max(
        (
            int(record["source_record_sequence"])
            for record in read_records(ledger_path)
            if record.get("source_sha256") == source_sha256
            and isinstance(record.get("source_record_sequence"), int)
            and int(record["source_record_sequence"]) > 0
        ),
        default=0,
    )
    sequence = highest + 1
    identity = {
        "source_sha256": source_sha256,
        "source_record_sequence": sequence,
        "event": event,
        "ingest_run_id": ingest_run_id,
    }
    digest = hashlib.sha256(canonical_json(identity).encode("utf-8")).hexdigest()
    return f"lr-{digest[:32]}", sequence


def append_snapshot(ledger_path: Path, snapshot: LedgerSnapshot, *, clock: Clock | None = None) -> None:
    try:
        if snapshot.schema_version == "2.0" and (
            snapshot.ledger_record_id is None or snapshot.source_record_sequence is None
        ):
            ledger_record_id, source_record_sequence = mint_ledger_identity(
                ledger_path,
                source_sha256=snapshot.source_sha256,
                event=snapshot.event,
                ingest_run_id=snapshot.ingest_run_id,
            )
            snapshot = replace(
                snapshot,
                ledger_record_id=ledger_record_id,
                source_record_sequence=source_record_sequence,
            )
        if snapshot.schema_version == "2.0":
            existing = [
                record
                for record in read_records(ledger_path)
                if record.get("source_sha256") == snapshot.source_sha256
            ]
            if any(
                record.get("ledger_record_id") == snapshot.ledger_record_id
                or record.get("source_record_sequence") == snapshot.source_record_sequence
                for record in existing
            ):
                raise MeetingIngestError(
                    phase="ledger",
                    code="ledger_identity_conflict",
                    message="Ledger record ID or source sequence has already been appended.",
                    exit_code=EXIT_LEDGER_WRITE,
                    recoverable=False,
                    details={
                        "ledger_record_id": snapshot.ledger_record_id,
                        "source_record_sequence": snapshot.source_record_sequence,
                    },
                )
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with ledger_path.open("a", encoding="utf-8") as ledger:
            ledger.write(json.dumps(snapshot.to_dict(clock=clock)))
            ledger.write("\n")
    except MeetingIngestError:
        raise
    except OSError as exc:
        raise MeetingIngestError(
            phase="ledger",
            code="ledger_write_failed",
            message=f"Could not append ledger snapshot: {ledger_path}",
            exit_code=EXIT_LEDGER_WRITE,
            recoverable=True,
            details={"ledger_path": str(ledger_path)},
        ) from exc


def read_records(ledger_path: Path) -> list[dict[str, Any]]:
    records, _ = read_records_with_issues(ledger_path)
    return records


def read_records_with_issues(ledger_path: Path) -> tuple[list[dict[str, Any]], list[LedgerReadIssue]]:
    if not ledger_path.exists():
        return [], []
    records: list[dict[str, Any]] = []
    issues: list[LedgerReadIssue] = []
    for line_number, line in enumerate(ledger_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            issues.append(
                LedgerReadIssue(
                    line_number=line_number,
                    code="malformed_ledger_json",
                    message=f"Ledger line is not valid JSON: {exc.msg}",
                )
            )
            continue
        if _is_legacy_record(record):
            issues.append(
                LedgerReadIssue(
                    line_number=line_number,
                    code="legacy_ledger_record",
                    message="Ledger line uses the deprecated three-field record format.",
                )
            )
            continue
        if _has_invalid_runtime_provenance(record):
            issues.append(
                LedgerReadIssue(
                    line_number=line_number,
                    code="ledger_provenance_invalid",
                    message="Ledger 2.0 runtime-provenance binding is invalid.",
                )
            )
            continue
        if not _is_valid_record(record):
            issues.append(
                LedgerReadIssue(
                    line_number=line_number,
                    code="invalid_ledger_record",
                    message="Ledger line is missing required current-state fields.",
                )
            )
            continue
        records.append(record)
    return records, issues


def latest_record_for_source(ledger_path: Path, source_sha256: str) -> dict[str, Any] | None:
    latest: dict[str, Any] | None = None
    for record in read_records(ledger_path):
        if record.get("source_sha256") == source_sha256:
            latest = record
    return latest


def has_legacy_record_for_source(ledger_path: Path, source_sha256: str) -> bool:
    if not ledger_path.exists():
        return False
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if _is_legacy_record(record) and record["source_sha256"] == source_sha256:
            return True
    return False


def _is_valid_record(record: object) -> bool:
    if not isinstance(record, dict):
        return False
    if record.get("schema_version") not in {"1.0", "2.0"}:
        return False
    if not all(record.get(key) for key in ("event", "source_sha256")):
        return False
    if record.get("event") not in {"ingest_failed", "source_quarantined"} and not record.get("meeting_id"):
        return False
    if record["schema_version"] == "2.0" and not valid_runtime_provenance_binding(
        record.get("runtime_provenance_schema"),
        record.get("runtime_provenance_sha256"),
        record.get("runtime_provenance"),
    ):
        return False
    if record["schema_version"] == "2.0":
        sequence = record.get("source_record_sequence")
        ledger_record_id = record.get("ledger_record_id")
        if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence <= 0:
            return False
        if not isinstance(ledger_record_id, str):
            return False
        identity = {
            "source_sha256": record["source_sha256"],
            "source_record_sequence": sequence,
            "event": record["event"],
            "ingest_run_id": record.get("ingest_run_id"),
        }
        expected = "lr-" + hashlib.sha256(canonical_json(identity).encode("utf-8")).hexdigest()[:32]
        if ledger_record_id != expected:
            return False
    return True


def _has_invalid_runtime_provenance(record: object) -> bool:
    return (
        isinstance(record, dict)
        and record.get("schema_version") == "2.0"
        and not valid_runtime_provenance_binding(
            record.get("runtime_provenance_schema"),
            record.get("runtime_provenance_sha256"),
            record.get("runtime_provenance"),
        )
    )


def _is_legacy_record(record: object) -> bool:
    if not isinstance(record, dict) or frozenset(record) != _LEGACY_RECORD_KEYS:
        return False
    source_sha256 = record.get("source_sha256")
    meeting_id = record.get("meeting_id")
    ingest_run_id = record.get("ingest_run_id")
    return (
        isinstance(source_sha256, str)
        and _SHA256_RE.fullmatch(source_sha256) is not None
        and isinstance(meeting_id, str)
        and bool(meeting_id.strip())
        and isinstance(ingest_run_id, str)
        and _LEGACY_RUN_ID_RE.fullmatch(ingest_run_id) is not None
    )
