"""Project status and hygiene checks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from meeting_ingest.ledger import read_records, read_records_with_issues
from meeting_ingest.locking import inspect_lock, lock_path
from meeting_ingest.paths import ProjectPaths
from meeting_ingest.provider_handoff import REQUEST_DIR, RESPONSE_DIR


STALE_PROVIDER_CACHE_AGE = timedelta(days=7)


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
    records, ledger_issues = read_records_with_issues(paths.ledger)
    for issue in ledger_issues:
        issues.append(
            DoctorIssue(
                code=issue.code,
                message=issue.message,
                path=f"{paths.ledger.name}:line:{issue.line_number}",
            )
        )

    lock_info = inspect_lock(lock_path(paths.cache))
    if lock_info is not None and lock_info.stale:
        issues.append(
            DoctorIssue(
                code="stale_lock",
                message="Project lock appears stale.",
                path=str(lock_info.path.relative_to(paths.meetings_root)),
            )
        )

    issues.extend(_stale_provider_cache_issues(paths))

    for source in _inbox_files(paths):
        issues.append(
            DoctorIssue(
                code="inbox_residue",
                message="Source file remains in inbox.",
                path=str(source.relative_to(paths.meetings_root)),
            )
        )

    for record in records:
        artifacts = record.get("artifacts", {})
        if isinstance(artifacts, dict):
            for artifact in artifacts.values():
                if isinstance(artifact, dict) and artifact.get("path"):
                    _append_missing_path_issue(paths, issues, "missing_artifact", str(artifact["path"]))
        signals = record.get("signals", {})
        if isinstance(signals, dict) and signals.get("path"):
            _append_missing_path_issue(paths, issues, "missing_signal_file", str(signals["path"]))
        source = record.get("source", {})
        if isinstance(source, dict) and source.get("processed_path"):
            _append_missing_path_issue(paths, issues, "missing_processed_source", str(source["processed_path"]))
        reconcile = record.get("reconcile", {})
        if isinstance(reconcile, dict) and reconcile.get("processed_path") and not (
            isinstance(source, dict) and source.get("processed_path")
        ):
            _append_missing_path_issue(paths, issues, "missing_processed_source", str(reconcile["processed_path"]))
    return issues


def _stale_provider_cache_issues(paths: ProjectPaths) -> list[DoctorIssue]:
    issues: list[DoctorIssue] = []
    now = datetime.now(UTC)
    for directory_name, code in (
        (REQUEST_DIR, "stale_provider_request"),
        (RESPONSE_DIR, "stale_provider_response"),
    ):
        directory = paths.cache / directory_name
        if not directory.exists():
            continue
        for path in directory.glob("*.json"):
            modified_at = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
            if now - modified_at <= STALE_PROVIDER_CACHE_AGE:
                continue
            issues.append(
                DoctorIssue(
                    code=code,
                    message="Provider handoff cache file is stale.",
                    path=str(path.relative_to(paths.meetings_root)),
                )
            )
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
