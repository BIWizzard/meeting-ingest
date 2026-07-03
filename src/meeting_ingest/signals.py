"""Signal JSONL writing."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json

from meeting_ingest.errors import EXIT_ARTIFACT_WRITE, MeetingIngestError
from meeting_ingest.schema import SignalRecord, validate_signal_record


@dataclass(frozen=True)
class SignalWriteResult:
    path: Path
    count: int


def write_signal_jsonl(path: Path, signals: list[SignalRecord]) -> SignalWriteResult:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as target:
            for signal in signals:
                validate_signal_record(signal)
                target.write(json.dumps(asdict(signal), sort_keys=True))
                target.write("\n")
    except OSError as exc:
        raise MeetingIngestError(
            phase="signal_write",
            code="signal_write_failed",
            message=f"Could not write signal JSONL: {path}",
            exit_code=EXIT_ARTIFACT_WRITE,
            recoverable=True,
            details={"path": str(path)},
        ) from exc
    return SignalWriteResult(path=path, count=len(signals))
