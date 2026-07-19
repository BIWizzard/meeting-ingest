"""Project status and hygiene checks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
import re

from meeting_ingest.errors import MeetingIngestError
from meeting_ingest.ledger import read_records, read_records_with_issues
from meeting_ingest.locking import inspect_lock, lock_path
from meeting_ingest.paths import ProjectPaths
from meeting_ingest.playbook_status import live_playbook_status, playbook_issues
from meeting_ingest.provider_handoff import REQUEST_DIR, RESPONSE_DIR
from meeting_ingest.signals import read_signal_jsonl
from meeting_ingest.session_handoffs import pending_session_handoffs, session_handoff_counts
from meeting_ingest.stakeholders import collect_identity_candidates, read_stakeholder_registry


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
    signal_issues = _signal_contract_issues(paths, records)
    return {
        "meetings_root": str(paths.meetings_root),
        "ledger_records": len(records),
        "known_sources": len(current_sources),
        "inbox_files": len(_inbox_files(paths)),
        "session_handoffs": session_handoff_counts(handoffs),
        "identity_registry": _identity_registry_status(paths),
        "signal_contract": {
            "status": "invalid" if signal_issues else "valid",
            "issues": [issue.to_dict() for issue in signal_issues],
        },
        "playbook": live_playbook_status(paths),
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
    issues.extend(_identity_registry_issues(paths))
    issues.extend(_signal_contract_issues(paths, records))
    issues.extend(DoctorIssue(**issue) for issue in playbook_issues(paths))

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
    issues.extend(_low_confidence_date_issues(paths, records))
    return issues


def _identity_registry_status(paths: ProjectPaths) -> dict[str, object]:
    registry_path = paths.playbook_state / "stakeholders.toml"
    registry = read_stakeholder_registry(registry_path)
    signals = []
    if paths.signals.exists():
        for signal_path in sorted(paths.signals.glob("*.jsonl")):
            try:
                signals.extend(read_signal_jsonl(signal_path))
            except MeetingIngestError:
                continue
    candidates = collect_identity_candidates(signals, registry)
    return {
        "status": "missing" if not registry_path.exists() else ("invalid" if registry.issues else "valid"),
        "people": len(registry.people),
        "issues": len(registry.issues),
        "identity_candidates": len(candidates),
    }


def _identity_registry_issues(paths: ProjectPaths) -> list[DoctorIssue]:
    registry_path = paths.playbook_state / "stakeholders.toml"
    if not registry_path.exists():
        return []
    registry = read_stakeholder_registry(registry_path)
    relative_path = str(registry_path.relative_to(paths.meetings_root))
    return [
        DoctorIssue(code=issue.code, message=issue.message, path=relative_path)
        for issue in registry.issues
    ]


def _signal_contract_issues(
    paths: ProjectPaths, ledger_records: list[dict[str, object]] | None = None
) -> list[DoctorIssue]:
    issues: list[DoctorIssue] = []
    source_hash_by_meeting = {
        str(record["meeting_id"]): str(record["source_sha256"])
        for record in (ledger_records or [])
        if record.get("meeting_id")
        and isinstance(record.get("source_sha256"), str)
        and re.fullmatch(r"[0-9a-f]{64}", str(record["source_sha256"]))
    }
    if not paths.signals.exists():
        return issues
    for path in sorted(paths.signals.glob("*.jsonl")):
        try:
            records = read_signal_jsonl(path)
        except MeetingIngestError as exc:
            issues.append(
                DoctorIssue(
                    code=exc.code,
                    message=str(exc),
                    path=str(path.relative_to(paths.meetings_root)),
                )
            )
            continue
        unmapped_meeting_ids = sorted(
            {
                str(record.meeting_id)
                for record in records
                if record.schema_version == "1.0"
                and record.meeting_id
                and record.meeting_id not in source_hash_by_meeting
            }
        )
        if unmapped_meeting_ids:
            issues.append(
                DoctorIssue(
                    code="signal_identity_invalid",
                    message=(
                        "Schema 1.0 signal meeting identity cannot be mapped to a valid source-ledger hash: "
                        + ", ".join(unmapped_meeting_ids)
                    ),
                    path=str(path.relative_to(paths.meetings_root)),
                )
            )
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
    if record.get("event") not in {"primary_artifacts_ready", "ingest_completed", "reconcile_repaired", "date_repaired"}:
        return False
    artifacts = record.get("artifacts")
    return isinstance(artifacts, dict) and bool(artifacts)


def _low_confidence_date_issues(paths: ProjectPaths, records: list[dict[str, object]]) -> list[DoctorIssue]:
    issues: list[DoctorIssue] = []
    for record in _current_records(records):
        if not _has_primary_artifacts(record):
            continue
        artifacts = record.get("artifacts", {})
        if not isinstance(artifacts, dict):
            continue
        for artifact in artifacts.values():
            if not isinstance(artifact, dict) or not artifact.get("path"):
                continue
            artifact_path = paths.meetings_root / str(artifact["path"])
            if not artifact_path.exists():
                continue
            if _front_matter_value(artifact_path, "date_source") == "file_mtime":
                issues.append(
                    DoctorIssue(
                        code="low_confidence_meeting_date",
                        message="Artifact meeting date came from file modification time and may be a download date; verify and fix with repair-date.",
                        path=str(artifact["path"]),
                    )
                )
    return issues


def _front_matter_value(path: Path, key: str) -> str | None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    if not lines or lines[0].strip() != "---":
        return None
    prefix = f"{key}: "
    for line in lines[1:]:
        if line.strip() == "---":
            return None
        if line.startswith(prefix):
            return line[len(prefix):].strip()
    return None


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
