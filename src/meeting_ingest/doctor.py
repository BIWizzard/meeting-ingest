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
from meeting_ingest.signals import is_deprecated_signal_event_jsonl, read_signal_jsonl
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

    artifact_identity_index: dict[tuple[str, str], list[Path]] | None = None
    for record in _current_records(records):
        artifacts = record.get("artifacts", {})
        if isinstance(artifacts, dict):
            for artifact in artifacts.values():
                if isinstance(artifact, dict) and artifact.get("path"):
                    relative_path = str(artifact["path"])
                    if not (paths.meetings_root / relative_path).exists():
                        if artifact_identity_index is None:
                            artifact_identity_index = _artifact_identity_index(paths)
                        _append_artifact_path_issue(
                            paths,
                            issues,
                            record,
                            relative_path,
                            artifact_identity_index,
                        )
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
        if is_deprecated_signal_event_jsonl(path):
            issues.append(
                DoctorIssue(
                    code="legacy_signal_format",
                    message="Signal JSONL uses the deprecated event-envelope format.",
                    path=str(path.relative_to(paths.meetings_root)),
                )
            )
            continue
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
            reason = details.get("reason") if isinstance(details, dict) else None
            if reason == "legacy_runtime_binding":
                code = "session_handoff_runtime_blocked"
                message = (
                    "Session provider handoff uses legacy schema 1.0 without runtime provenance; "
                    "abandon it and mint a fresh request under the intended runtime."
                )
            elif reason == "invalid_runtime_binding":
                code = "session_handoff_runtime_blocked"
                message = (
                    "Session provider handoff has an invalid runtime-provenance binding; "
                    "restore the reviewed request or explicitly abandon and remint it."
                )
            else:
                code = "session_handoff_stale"
                message = "Session provider handoff is stale or outside the inbox wrapper scope."
            issues.append(
                DoctorIssue(
                    code=code,
                    message=message,
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


def _append_artifact_path_issue(
    paths: ProjectPaths,
    issues: list[DoctorIssue],
    record: dict[str, object],
    relative_path: str,
    identity_index: dict[tuple[str, str], list[Path]],
) -> None:
    identity = (str(record.get("meeting_id") or ""), str(record.get("source_sha256") or ""))
    relocated = identity_index.get(identity, [])
    if len(relocated) == 1:
        actual_path = str(relocated[0].relative_to(paths.meetings_root))
        issues.append(
            DoctorIssue(
                code="historical_artifact_path_drift",
                message=f"Ledger artifact path differs from the uniquely identity-matched file: {actual_path}",
                path=relative_path,
            )
        )
        return
    _append_missing_path_issue(paths, issues, "missing_artifact", relative_path)


def _artifact_identity_index(paths: ProjectPaths) -> dict[tuple[str, str], list[Path]]:
    index: dict[tuple[str, str], list[Path]] = {}
    for path in paths.meetings_root.glob("*.md"):
        fields = _front_matter_fields(path)
        identity = (fields.get("meeting_id", ""), fields.get("source_sha256", ""))
        if all(identity):
            index.setdefault(identity, []).append(path)
    return index


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
    return _front_matter_fields(path).get(key)


def _front_matter_fields(path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    try:
        with path.open(encoding="utf-8") as source:
            if source.readline().strip() != "---":
                return fields
            for line in source:
                if line.strip() == "---":
                    break
                if ": " in line:
                    key, value = line.split(": ", 1)
                    fields[key] = value.strip().strip('"')
    except (OSError, UnicodeError):
        return {}
    return fields


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
