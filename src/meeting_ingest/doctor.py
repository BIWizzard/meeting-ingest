"""Project status and hygiene checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from meeting_ingest.ledger import read_records
from meeting_ingest.paths import ProjectPaths


@dataclass(frozen=True)
class DoctorIssue:
    code: str
    message: str
    path: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {"code": self.code, "message": self.message, "path": self.path}


def project_status(paths: ProjectPaths) -> dict[str, object]:
    records = read_records(paths.ledger)
    current_sources = {record.get("source_sha256") for record in records if record.get("source_sha256")}
    return {
        "meetings_root": str(paths.meetings_root),
        "ledger_records": len(records),
        "known_sources": len(current_sources),
        "inbox_files": len(_inbox_files(paths)),
    }


def find_issues(paths: ProjectPaths) -> list[DoctorIssue]:
    issues: list[DoctorIssue] = []
    for source in _inbox_files(paths):
        issues.append(
            DoctorIssue(
                code="inbox_residue",
                message="Source file remains in inbox.",
                path=str(source.relative_to(paths.meetings_root)),
            )
        )

    for record in read_records(paths.ledger):
        artifacts = record.get("artifacts", {})
        if isinstance(artifacts, dict):
            for artifact in artifacts.values():
                if isinstance(artifact, dict) and artifact.get("path"):
                    _append_missing_path_issue(paths, issues, "missing_artifact", str(artifact["path"]))
        signals = record.get("signals", {})
        if isinstance(signals, dict) and signals.get("path"):
            _append_missing_path_issue(paths, issues, "missing_signal_file", str(signals["path"]))
    return issues


def _append_missing_path_issue(paths: ProjectPaths, issues: list[DoctorIssue], code: str, relative_path: str) -> None:
    if not (paths.meetings_root / relative_path).exists():
        issues.append(
            DoctorIssue(
                code=code,
                message="Ledger references a missing path.",
                path=relative_path,
            )
        )


def _inbox_files(paths: ProjectPaths) -> list[Path]:
    if not paths.inbox.exists():
        return []
    files: list[Path] = []
    for path in paths.inbox.rglob("*"):
        if not path.is_file():
            continue
        if path == paths.inbox_done or paths.inbox_done in path.parents:
            continue
        files.append(path)
    return files
