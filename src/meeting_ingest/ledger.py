"""Append-only source ledger."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json

from meeting_ingest.clock import Clock, SystemClock, format_iso_timestamp
from meeting_ingest.errors import EXIT_LEDGER_WRITE, MeetingIngestError


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
    schema_version: str = "1.0"

    def to_dict(self, *, clock: Clock | None = None) -> dict[str, Any]:
        active_clock = clock or SystemClock()
        return {
            "schema_version": self.schema_version,
            "event": self.event,
            "recorded_at": format_iso_timestamp(active_clock.now_utc()),
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


def append_snapshot(ledger_path: Path, snapshot: LedgerSnapshot, *, clock: Clock | None = None) -> None:
    try:
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with ledger_path.open("a", encoding="utf-8") as ledger:
            ledger.write(json.dumps(snapshot.to_dict(clock=clock), sort_keys=True))
            ledger.write("\n")
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


def _is_valid_record(record: object) -> bool:
    if not isinstance(record, dict):
        return False
    if not all(record.get(key) for key in ("schema_version", "event", "source_sha256")):
        return False
    if record.get("event") not in {"ingest_failed", "source_quarantined"} and not record.get("meeting_id"):
        return False
    return True
