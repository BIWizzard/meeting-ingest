"""Fail-closed runtime and project readiness classification."""

from __future__ import annotations

from collections import Counter
from contextvars import ContextVar
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Callable, Iterable, TYPE_CHECKING

from meeting_ingest.config import MeetingIngestConfig, load_config
from meeting_ingest.errors import EXIT_RUNTIME_READINESS, MeetingIngestError
from meeting_ingest.locking import inspect_lock, lock_path
from meeting_ingest.paths import DEFAULT_CONFIG_RELATIVE, ProjectPaths, discover_config, infer_project_root_from_config
from meeting_ingest.run_summary import RunSummary
from meeting_ingest.runtime import ReadinessFinding, ReadinessResult, RuntimeInspection, inspect_runtime
from meeting_ingest.schema import SUPPORTED_PROVIDERS

if TYPE_CHECKING:
    from meeting_ingest.doctor import DoctorIssue


@dataclass(frozen=True)
class DevelopmentOverride:
    """Invocation-scoped authorization for development runtime selection."""

    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("Development override reason must be non-empty.")
        object.__setattr__(self, "reason", self.reason.strip())


RuntimeInspector = Callable[[Path], RuntimeInspection]
_RUNTIME_INSPECTOR: RuntimeInspector = inspect_runtime
_CURRENT_RUNTIME_PROVENANCE: ContextVar[dict[str, object] | None] = ContextVar(
    "meeting_ingest_runtime_provenance", default=None
)

_OVERRIDABLE_SELECTION_CODES = {
    "runtime_editable_blocked",
    "runtime_executable_mismatch",
    "runtime_pin_invalid",
    "runtime_pin_mismatch",
    "runtime_pin_missing",
    "runtime_receipt_invalid",
    "runtime_receipt_mismatch",
}
_EDITABLE_DEVELOPMENT_CODES = {
    "runtime_git_dirty",
    "workflow_contract_mismatch",
    "workflow_hash_mismatch",
}
_NEVER_OVERRIDABLE_RUNTIME_CODES = {
    "runtime_git_uninspectable",
    "runtime_install_unknown",
    "runtime_package_integrity_failed",
}
_HISTORY_ISSUE_CODES = {
    "derivation_generation_uncommitted": "optional_playbook_output_missing",
    "derivation_index_mismatch": "optional_playbook_output_missing",
    "historical_identity_gap": "historical_identity_gap",
    "identity_alias_ambiguous": "historical_identity_gap",
    "inbox_residue": "corpus_adoption_pending",
    "low_confidence_meeting_date": "historical_date_low_confidence",
    "playbook_profile_missing": "optional_playbook_output_missing",
    "playbook_stale": "optional_playbook_output_missing",
    "playbook_state_missing": "optional_playbook_output_missing",
    "review_event_orphaned": "historical_identity_gap",
    "session_handoff_stale": "corpus_adoption_pending",
    "stale_provider_request": "corpus_adoption_pending",
    "stale_provider_response": "corpus_adoption_pending",
}
_PROJECT_BLOCKER_CODES = {
    "derivation_ledger_malformed",
    "incomplete_reconcile",
    "identity_registry_invalid",
    "invalid_ledger_record",
    "malformed_ledger_json",
    "missing_artifact",
    "missing_processed_source",
    "missing_signal_file",
    "playbook_profile_invalid",
    "review_event_malformed",
    "session_handoff_invalid",
    "signal_identity_invalid",
    "signal_invalid",
    "signal_read_failed",
    "signal_suppression_reemerged",
}


class RuntimeReadinessError(MeetingIngestError):
    def __init__(self, result: ReadinessResult) -> None:
        blocker = next((finding for finding in result.findings if finding.severity == "blocker"), None)
        message = blocker.message if blocker else "Runtime readiness is blocked."
        super().__init__(
            phase="readiness",
            code=blocker.code if blocker else "runtime_readiness_blocked",
            message=message,
            exit_code=EXIT_RUNTIME_READINESS,
            recoverable=True,
            details={
                "verdict": result.verdict,
                "findings": [finding.to_dict() for finding in result.findings],
                "runtime_provenance": asdict(result.runtime_provenance),
            },
        )
        self.result = result


def assess_readiness(
    root: Path,
    *,
    development_override: DevelopmentOverride | None = None,
    operation: str = "readiness",
    require_session_provider: bool = False,
    require_remote_provider: bool = False,
    allow_pending_handoffs: bool = False,
    runtime_inspector: RuntimeInspector | None = None,
) -> ReadinessResult:
    """Inspect and classify next-write safety without mutating project state."""
    resolved_root = root.expanduser().resolve(strict=False)
    inspection = (runtime_inspector or _RUNTIME_INSPECTOR)(resolved_root)
    findings = list(inspection.findings)
    if inspection.install.mode == "editable" and inspection.install.git_dirty is True:
        findings.append(
            ReadinessFinding(
                code="runtime_git_dirty",
                category="runtime",
                severity="blocker",
                message="Editable runtime source has uncommitted or untracked changes.",
                path=inspection.install.editable_root,
                remediation="Commit or remove source changes before a write-capable development invocation.",
            )
        )
    findings.extend(
        _project_findings(
            resolved_root,
            operation=operation,
            require_session_provider=require_session_provider,
            require_remote_provider=require_remote_provider,
            allow_pending_handoffs=allow_pending_handoffs,
        )
    )
    findings = _classify_runtime_findings(findings)

    provenance = inspection.runtime_provenance
    waived_codes: set[str] = set()
    if development_override is not None:
        waived_codes = {
            finding.code
            for finding in findings
            if finding.category == "runtime"
            and (
                finding.code in _OVERRIDABLE_SELECTION_CODES
                or (
                    inspection.install.mode == "editable"
                    and finding.code in _EDITABLE_DEVELOPMENT_CODES
                )
            )
        }
        provenance = replace(
            provenance,
            runtime_mode="development",
            development_override_reason=development_override.reason,
        )

    blockers = [
        finding
        for finding in findings
        if finding.severity == "blocker" and finding.code not in waived_codes
    ]
    warnings = [finding for finding in findings if finding.severity == "warning"]
    if blockers:
        verdict = "blocked"
        exit_code = EXIT_RUNTIME_READINESS
    elif development_override is not None:
        verdict = "development_override"
        exit_code = 0
    elif warnings:
        verdict = "ready_with_history_warnings"
        exit_code = 0
    else:
        verdict = "ready"
        exit_code = 0
    return ReadinessResult(
        verdict=verdict,
        exit_code=exit_code,
        runtime_provenance=provenance,
        findings=tuple(sorted(findings, key=_finding_sort_key)),
    )


def require_write_readiness(root: Path, **kwargs: object) -> ReadinessResult:
    """Apply the shared write guard and raise before callers acquire locks or write."""
    result = assess_readiness(root, **kwargs)
    _CURRENT_RUNTIME_PROVENANCE.set(asdict(result.runtime_provenance))
    if result.verdict == "blocked":
        raise RuntimeReadinessError(result)
    return result


def clear_runtime_provenance() -> None:
    _CURRENT_RUNTIME_PROVENANCE.set(None)


def current_runtime_provenance() -> dict[str, object] | None:
    value = _CURRENT_RUNTIME_PROVENANCE.get()
    return dict(value) if value is not None else None


def with_runtime_provenance(summary: RunSummary, result: ReadinessResult) -> RunSummary:
    """Bind the guard's canonical provenance to a mutating operation summary."""
    summary.runtime_provenance = asdict(result.runtime_provenance)
    return summary


def readiness_summary(root: Path, **kwargs: object) -> RunSummary:
    inspector = kwargs.get("runtime_inspector") or _RUNTIME_INSPECTOR
    inspection = inspector(root.expanduser().resolve(strict=False))  # type: ignore[operator]
    result = assess_readiness(root, **{**kwargs, "runtime_inspector": lambda _: inspection})
    category_counts = Counter(finding.category for finding in result.findings)
    severity_counts = Counter(finding.severity for finding in result.findings)
    approved_build = inspection.pin.get("comparisons", [])
    return RunSummary(
        status="success" if result.exit_code == 0 else "blocked",
        exit_code=result.exit_code,
        runtime_provenance=asdict(result.runtime_provenance),
        details={
            "command": "readiness",
            "verdict": result.verdict,
            "running_build": inspection.build.build_id,
            "approved_build": _comparison_expected(approved_build, "approved_build_id"),
            "match": bool(inspection.pin.get("match", False)),
            "update_available": bool(inspection.channel.get("update_available", False)),
            "finding_counts": {
                "by_category": dict(sorted(category_counts.items())),
                "by_severity": dict(sorted(severity_counts.items())),
            },
            "findings": [finding.to_dict() for finding in result.findings],
        },
    )


def _project_findings(
    root: Path,
    *,
    operation: str,
    require_session_provider: bool,
    require_remote_provider: bool,
    allow_pending_handoffs: bool,
) -> list[ReadinessFinding]:
    findings: list[ReadinessFinding] = []
    config_path: Path
    expected = root / DEFAULT_CONFIG_RELATIVE
    if operation == "init":
        if not expected.exists():
            return findings
        config_path = expected
    else:
        try:
            config_path = discover_config(root)
        except MeetingIngestError as exc:
            return [_project_finding("readiness_config_invalid", str(exc), "Repair or initialize the project config.", path=str(expected))]
    if config_path.is_symlink() or not config_path.is_file():
        return [
            _project_finding(
                "readiness_path_unsafe",
                "Project config must be a regular file and may not be a symbolic link.",
                "Replace the config symlink with a reviewed regular file inside the project.",
                path=str(config_path),
            )
        ]
    try:
        config = load_config(config_path)
    except MeetingIngestError as exc:
        return [_project_finding("readiness_config_invalid", str(exc), "Repair the project config before writing.", path=str(config_path))]

    if operation == "readiness":
        if config.default_provider not in SUPPORTED_PROVIDERS:
            findings.append(
                _project_finding(
                    "readiness_config_invalid",
                    f"Configured default provider is unsupported: {config.default_provider}",
                    "Select a supported default provider before writing.",
                    path=str(config_path),
                )
            )
        require_session_provider = require_session_provider or config.default_provider == "session"
        require_remote_provider = require_remote_provider or config.default_provider == "anthropic"

    project_root = infer_project_root_from_config(config_path)
    paths = ProjectPaths.from_config(project_root, config_path, config)
    findings.extend(_path_findings(config, paths))
    if require_session_provider and not config.privacy.allow_session_provider:
        findings.append(
            _project_finding(
                "readiness_privacy_blocked",
                "Session provider use is disabled by project privacy config.",
                "Set [privacy].allow_session_provider = true only after approving session-provider use.",
                path=str(config_path),
            )
        )
    if require_remote_provider and not config.privacy.allow_remote_provider:
        findings.append(
            _project_finding(
                "readiness_privacy_blocked",
                "Remote provider use is disabled by project privacy config.",
                "Set [privacy].allow_remote_provider = true only after approving remote-provider use.",
                path=str(config_path),
            )
        )
    lock = inspect_lock(lock_path(paths.cache))
    if lock is not None:
        findings.append(
            _project_finding(
                "lock_conflict",
                "Another meeting-ingest operation owns the project lock." if not lock.stale else "The project lock is stale but still blocks writes.",
                "Let the active operation finish or explicitly repair the stale lock.",
                path=str(lock.path),
            )
        )
    if any(finding.code == "readiness_path_unsafe" for finding in findings):
        return findings
    try:
        # Keep this import lazy: doctor -> playbook_status -> playbook -> readiness.
        from meeting_ingest.doctor import find_issues

        issues = find_issues(paths)
    except (MeetingIngestError, OSError, ValueError) as exc:
        findings.append(
            _project_finding(
                "readiness_current_integrity_unknown",
                f"Current project integrity could not be inspected: {exc}",
                "Repair the reported project data before writing.",
                path=str(paths.meetings_root),
            )
        )
        return findings
    findings.extend(
        _doctor_findings(
            issues,
            operation=operation,
            allow_pending_handoffs=allow_pending_handoffs,
        )
    )
    return findings


def _path_findings(config: MeetingIngestConfig, paths: ProjectPaths) -> list[ReadinessFinding]:
    configured = [config.paths.root, config.paths.inbox, config.paths.processed, config.paths.signals,
                  config.paths.quarantine, config.paths.derived, config.paths.cache, config.paths.ledger]
    unsafe = [value for value in configured if not isinstance(value, str) or not value or Path(value).is_absolute() or ".." in Path(value).parts]
    resolved_project = paths.project_root.resolve(strict=False)
    resolved_meetings = paths.meetings_root.resolve(strict=False)
    if not unsafe:
        try:
            resolved_meetings.relative_to(resolved_project)
            for path in (paths.inbox, paths.processed, paths.signals, paths.quarantine, paths.derived, paths.cache, paths.ledger):
                path.resolve(strict=False).relative_to(resolved_meetings)
        except ValueError:
            unsafe.append("resolved path escapes configured roots")
    if not unsafe:
        return []
    return [
        _project_finding(
            "readiness_path_unsafe",
            "Project path configuration is unsafe or escapes the project/meetings root.",
            "Use non-empty relative paths without '..' components, all contained by the project root.",
            path=str(paths.config_path),
        )
    ]


def _doctor_findings(
    issues: Iterable["DoctorIssue"],
    *,
    operation: str,
    allow_pending_handoffs: bool,
) -> list[ReadinessFinding]:
    findings: list[ReadinessFinding] = []
    for issue in issues:
        if issue.code == "stale_lock":
            continue
        if issue.code == "session_handoff_pending" and allow_pending_handoffs:
            continue
        if issue.code == "incomplete_reconcile" and operation in {"ingest", "reconcile"}:
            continue
        if issue.code == "playbook_profile_invalid" and operation in {
            "playbook-update",
            "playbook-repair-index",
            "playbook-cleanup",
        }:
            continue
        if issue.code in _HISTORY_ISSUE_CODES:
            findings.append(
                ReadinessFinding(
                    code=_HISTORY_ISSUE_CODES[issue.code],
                    category="history",
                    severity="warning",
                    message=issue.message,
                    path=issue.path,
                    remediation="Review or adopt this historical state separately; it does not block the next safe write.",
                )
            )
        elif issue.code == "session_handoff_pending" or issue.code in _PROJECT_BLOCKER_CODES:
            findings.append(
                _project_finding(
                    issue.code,
                    issue.message,
                    "Resolve this current project integrity issue before writing.",
                    path=issue.path,
                )
            )
        else:
            findings.append(
                _project_finding(
                    "readiness_issue_unclassified",
                    f"Unclassified health issue {issue.code!r}: {issue.message}",
                    "Classify this issue code explicitly before allowing project writes.",
                    path=issue.path,
                )
            )
    return findings


def _classify_runtime_findings(findings: Iterable[ReadinessFinding]) -> list[ReadinessFinding]:
    classified: list[ReadinessFinding] = []
    for finding in findings:
        if finding.category == "advisory" and finding.severity == "advisory":
            classified.append(finding)
        elif finding.category == "runtime" and finding.code in (
            _OVERRIDABLE_SELECTION_CODES
            | _EDITABLE_DEVELOPMENT_CODES
            | _NEVER_OVERRIDABLE_RUNTIME_CODES
        ):
            classified.append(replace(finding, category="runtime", severity="blocker"))
        elif finding.category in {"project", "history"}:
            classified.append(finding)
        else:
            classified.append(
                _project_finding(
                    "readiness_issue_unclassified",
                    f"Unclassified runtime finding {finding.code!r}: {finding.message}",
                    "Classify this runtime finding before allowing writes.",
                    path=finding.path,
                )
            )
    return classified


def _project_finding(code: str, message: str, remediation: str, *, path: str | None = None) -> ReadinessFinding:
    return ReadinessFinding(code=code, category="project", severity="blocker", message=message, path=path, remediation=remediation)


def _finding_sort_key(finding: ReadinessFinding) -> tuple[int, str, str, str]:
    return ({"blocker": 0, "warning": 1, "advisory": 2}[finding.severity], finding.category, finding.code, finding.path or "")


def _comparison_expected(comparisons: object, field: str) -> object:
    if not isinstance(comparisons, list):
        return None
    for comparison in comparisons:
        if isinstance(comparison, dict) and comparison.get("field") == field:
            return comparison.get("expected")
    return None
