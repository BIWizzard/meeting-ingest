"""Project status and hygiene checks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from meeting_ingest.ledger import read_records, read_records_with_issues
from meeting_ingest.locking import inspect_lock, lock_path
from meeting_ingest.paths import ProjectPaths
from meeting_ingest.provider_handoff import REQUEST_DIR, RESPONSE_DIR
from meeting_ingest.session_handoffs import pending_session_handoffs, session_handoff_counts


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
    handoffs = pending_session_handoffs(paths)
    return {
        "meetings_root": str(paths.meetings_root),
        "ledger_records": len(records),
        "known_sources": len(current_sources),
        "inbox_files": len(_inbox_files(paths)),
        "session_handoffs": session_handoff_counts(handoffs),
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
    issues.extend(_session_handoff_issues(paths))

    for source in _inbox_files(paths):
        issues.append(
            DoctorIssue(
                code="inbox_residue",
                message="Source file remains in inbox.",
                path=str(source.relative_to(paths.meetings_root)),
            )
        )

    for record in _current_records(records):
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
        if _has_primary_artifacts(record) and isinstance(reconcile, dict) and reconcile.get("status") == "pending":
            issues.append(
                DoctorIssue(
                    code="incomplete_reconcile",
                    message="Primary artifacts are ready but archive/reconcile did not complete.",
                    path=_source_issue_path(source),
                )
            )
        if isinstance(reconcile, dict) and reconcile.get("processed_path") and not (
            isinstance(source, dict) and source.get("processed_path")
        ):
            _append_missing_path_issue(paths, issues, "missing_processed_source", str(reconcile["processed_path"]))
    return issues


def session_handoff_status(paths: ProjectPaths) -> dict[str, object]:
    handoffs = pending_session_handoffs(paths)
    return {
        "counts": session_handoff_counts(handoffs),
        "results": handoffs,
    }


def _session_handoff_issues(paths: ProjectPaths) -> list[DoctorIssue]:
    issues: list[DoctorIssue] = []
    for handoff in pending_session_handoffs(paths):
        status = handoff.get("status")
        details = handoff.get("details")
        request_path = None
        if isinstance(details, dict) and details.get("request_path"):
            request_path = str(details["request_path"])
        if status == "pending_provider_response":
            issues.append(
                DoctorIssue(
                    code="session_handoff_pending",
                    message="Session provider handoff is waiting for provider response or phase-2 completion.",
                    path=request_path,
                )
            )
        elif status == "stale_handoff":
            issues.append(
                DoctorIssue(
                    code="session_handoff_stale",
                    message="Session provider handoff is stale or outside the inbox wrapper scope.",
                    path=request_path,
                )
            )
        elif status == "failed":
            issues.append(
                DoctorIssue(
                    code="session_handoff_invalid",
                    message="Session provider handoff request could not be parsed or planned.",
                    path=request_path,
                )
            )
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


def _has_primary_artifacts(record: dict[str, object]) -> bool:
    if record.get("event") not in {"primary_artifacts_ready", "ingest_completed", "reconcile_repaired"}:
        return False
    artifacts = record.get("artifacts")
    return isinstance(artifacts, dict) and bool(artifacts)


def _current_records(records: list[dict[str, object]]) -> list[dict[str, object]]:
    current: dict[str, dict[str, object]] = {}
    for record in records:
        source_sha256 = record.get("source_sha256")
        if source_sha256:
            current[str(source_sha256)] = record
    return list(current.values())


def _source_issue_path(source: object) -> str | None:
    if not isinstance(source, dict):
        return None
    original_path = source.get("original_path")
    return str(original_path) if original_path else None


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
