"""Signal JSONL writing."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json

from meeting_ingest.schema import SignalSummary


@dataclass(frozen=True)
class SignalWriteResult:
    path: Path
    count: int


def write_signal_jsonl(path: Path, signals: list[SignalSummary]) -> SignalWriteResult:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as target:
        for signal in signals:
            target.write(json.dumps(asdict(signal), sort_keys=True))
            target.write("\n")
    return SignalWriteResult(path=path, count=len(signals))
