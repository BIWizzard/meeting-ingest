"""Append-only source ledger."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json

from meeting_ingest.clock import Clock, SystemClock, format_timestamp


@dataclass(frozen=True)
class LedgerSnapshot:
    event: str
    source_sha256: str
    meeting_id: str
    ingest_run_id: str
    source_path: str
    artifacts: dict[str, dict[str, Any]]
    signals: dict[str, Any]
    reconcile: dict[str, Any]
    derived: dict[str, Any] = field(default_factory=lambda: {"playbook_update_status": "not_applicable"})
    schema_version: str = "1.0"

    def to_dict(self, *, clock: Clock | None = None) -> dict[str, Any]:
        active_clock = clock or SystemClock()
        return {
            "schema_version": self.schema_version,
            "event": self.event,
            "recorded_at": format_timestamp(active_clock.now_utc()),
            "source_sha256": self.source_sha256,
            "meeting_id": self.meeting_id,
            "ingest_run_id": self.ingest_run_id,
            "source_path": self.source_path,
            "artifacts": self.artifacts,
            "signals": self.signals,
            "derived": self.derived,
            "reconcile": self.reconcile,
        }


def append_snapshot(ledger_path: Path, snapshot: LedgerSnapshot, *, clock: Clock | None = None) -> None:
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8") as ledger:
        ledger.write(json.dumps(snapshot.to_dict(clock=clock), sort_keys=True))
        ledger.write("\n")


def read_records(ledger_path: Path) -> list[dict[str, Any]]:
    if not ledger_path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records
