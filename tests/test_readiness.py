from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from conftest import approved_runtime_inspection
from meeting_ingest.doctor import DoctorIssue
from meeting_ingest.errors import EXIT_RUNTIME_READINESS
from meeting_ingest.paths import init_project
from meeting_ingest.readiness import (
    DevelopmentOverride,
    RuntimeReadinessError,
    assess_readiness,
    readiness_summary,
    require_write_readiness,
)
from meeting_ingest.runtime import ReadinessFinding


def _runtime_with_finding(root: Path, finding: ReadinessFinding, *, mode: str = "unverified"):
    inspection = approved_runtime_inspection(root)
    install_mode = "editable" if finding.code == "runtime_editable_blocked" or mode == "editable" else mode
    runtime_mode = "development" if install_mode == "editable" else mode
    return replace(
        inspection,
        install=replace(inspection.install, mode=install_mode),
        runtime_mode=runtime_mode,
        findings=(finding,),
        runtime_provenance=replace(
            inspection.runtime_provenance,
            install_mode=install_mode,
            runtime_mode=runtime_mode,
        ),
    )


def _runtime_blocker(code: str) -> ReadinessFinding:
    return ReadinessFinding(
        code=code,
        category="runtime",
        severity="blocker",
        message=f"Blocked by {code}.",
        path="/runtime/evidence",
        remediation="Repair runtime evidence.",
    )


def test_ready_has_no_blockers_or_history_warnings(tmp_path: Path) -> None:
    init_project(tmp_path)

    result = assess_readiness(tmp_path, runtime_inspector=approved_runtime_inspection)

    assert result.verdict == "ready"
    assert result.exit_code == 0
    assert result.findings == ()


def test_mutating_summary_carries_guard_provenance(tmp_path: Path) -> None:
    from meeting_ingest.pipeline import initialize

    summary = initialize(tmp_path)

    assert summary.runtime_provenance is not None
    assert summary.runtime_provenance["runtime_mode"] == "approved"


def test_history_issue_is_renamed_and_does_not_block(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    init_project(tmp_path)
    monkeypatch.setattr(
        "meeting_ingest.doctor.find_issues",
        lambda _: [DoctorIssue("low_confidence_meeting_date", "Date needs review.", "meeting.md")],
    )

    result = assess_readiness(tmp_path, runtime_inspector=approved_runtime_inspection)

    assert result.verdict == "ready_with_history_warnings"
    assert result.findings[0].code == "historical_date_low_confidence"
    assert result.findings[0].category == "history"
    assert result.findings[0].severity == "warning"


def test_deprecated_three_field_ledger_record_is_a_history_warning(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    paths.ledger.write_text(
        json.dumps(
            {
                "source_sha256": "a" * 64,
                "meeting_id": "2026-05-04-generic-d01638d8",
                "ingest_run_id": "20260518T030615Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = assess_readiness(tmp_path, runtime_inspector=approved_runtime_inspection)

    assert result.verdict == "ready_with_history_warnings"
    assert [(finding.code, finding.category, finding.severity) for finding in result.findings] == [
        ("legacy_provenance_missing", "history", "warning")
    ]


def test_invalid_legacy_lookalike_remains_a_project_blocker(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    paths.ledger.write_text(
        json.dumps(
            {
                "source_sha256": "not-a-sha256",
                "meeting_id": "2026-05-04-generic-d01638d8",
                "ingest_run_id": "20260518T030615Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = assess_readiness(tmp_path, runtime_inspector=approved_runtime_inspection)

    assert result.verdict == "blocked"
    assert [(finding.code, finding.category, finding.severity) for finding in result.findings] == [
        ("invalid_ledger_record", "project", "blocker")
    ]


def test_invalid_ledger_runtime_provenance_blocks_readiness(tmp_path: Path) -> None:
    from meeting_ingest.pipeline import ingest

    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")
    ingest(source, start=paths.inbox)
    records = [
        json.loads(line) for line in paths.ledger.read_text(encoding="utf-8").splitlines()
    ]
    records[-1]["runtime_provenance_sha256"] = "sha256:" + "0" * 64
    paths.ledger.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )

    result = assess_readiness(tmp_path, runtime_inspector=approved_runtime_inspection)
    finding = next(
        finding
        for finding in result.findings
        if finding.code == "ledger_provenance_invalid"
    )

    assert result.verdict == "blocked"
    assert (finding.category, finding.severity) == ("project", "blocker")


def test_tampered_current_signal_file_blocks_readiness(tmp_path: Path) -> None:
    from meeting_ingest.pipeline import ingest

    paths = init_project(tmp_path)
    source = paths.inbox / "2026-07-03-team-sync.txt"
    source.write_text("Ken: Please capture this. [mock-signal]\n", encoding="utf-8")
    summary = ingest(source, start=paths.inbox)
    signal_path = paths.meetings_root / summary.artifacts[1]["path"]
    signal_path.write_text(
        signal_path.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )

    result = assess_readiness(tmp_path, runtime_inspector=approved_runtime_inspection)
    finding = next(
        finding
        for finding in result.findings
        if finding.code == "current_signal_link_invalid"
    )

    assert result.verdict == "blocked"
    assert (finding.category, finding.severity) == ("project", "blocker")


@pytest.mark.parametrize(
    "code",
    [
        "ledger_provenance_invalid",
        "current_signal_link_invalid",
        "artifact_provenance_mismatch",
        "playbook_provenance_invalid",
    ],
)
def test_runtime_provenance_integrity_issues_are_project_blockers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    code: str,
) -> None:
    init_project(tmp_path)
    monkeypatch.setattr(
        "meeting_ingest.doctor.find_issues",
        lambda _: [DoctorIssue(code, "Runtime provenance is inconsistent.", "evidence")],
    )

    result = assess_readiness(tmp_path, runtime_inspector=approved_runtime_inspection)

    assert result.verdict == "blocked"
    assert [(finding.code, finding.category, finding.severity) for finding in result.findings] == [
        (code, "project", "blocker")
    ]


def test_legacy_ledger_and_schema_1_1_signals_remain_history_only(
    tmp_path: Path,
) -> None:
    paths = init_project(tmp_path)
    paths.ledger.write_text(
        json.dumps(
            {
                "source_sha256": "a" * 64,
                "meeting_id": "2026-05-04-generic-d01638d8",
                "ingest_run_id": "20260518T030615Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    fixture = Path(__file__).parent / "fixtures" / "signals" / "schema-1.1-meeting.jsonl"
    (paths.signals / "legacy.jsonl").write_text(
        fixture.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    result = assess_readiness(tmp_path, runtime_inspector=approved_runtime_inspection)

    assert result.verdict == "ready_with_history_warnings"
    assert [(finding.code, finding.category, finding.severity) for finding in result.findings] == [
        ("legacy_provenance_missing", "history", "warning")
    ]


def test_deprecated_signal_event_file_is_a_history_warning(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    event = {
        "schema_version": "1.0",
        "event": "stakeholder_signal_recorded",
        "event_id": "event-1",
        "ingest_run_id": "ingest-20260518-batch1",
        "effective_at": "2026-05-04",
        "recorded_at": "2026-05-18T03:06:15Z",
        "origin": "meeting",
        "payload": {},
        "provenance": {},
    }
    (paths.signals / "legacy.jsonl").write_text(json.dumps(event) + "\n", encoding="utf-8")

    result = assess_readiness(tmp_path, runtime_inspector=approved_runtime_inspection)

    assert result.verdict == "ready_with_history_warnings"
    assert [(finding.code, finding.category, finding.severity) for finding in result.findings] == [
        ("legacy_signal_link_missing", "history", "warning")
    ]


def test_uniquely_identity_matched_relocated_artifact_is_a_history_warning(tmp_path: Path) -> None:
    from meeting_ingest.ledger import LedgerSnapshot, append_snapshot

    paths = init_project(tmp_path)
    source_sha256 = "a" * 64
    meeting_id = "mtg-20260713-af5978a9"
    relocated = paths.meetings_root / "2026-07-10-relocated.md"
    relocated.write_text(
        "\n".join(
            [
                "---",
                f"meeting_id: {meeting_id}",
                f"source_sha256: {source_sha256}",
                "---",
                "# Relocated",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    append_snapshot(
        paths.ledger,
        LedgerSnapshot(
            schema_version="1.0",
            event="ingest_completed",
            source_sha256=source_sha256,
            meeting_id=meeting_id,
            ingest_run_id="ingest-20260713-test",
            source={},
            artifacts={"summary-plus-verbatim": {"path": "2026-07-13-missing.md"}},
            signals={},
            reconcile={"status": "completed"},
        ),
    )

    result = assess_readiness(tmp_path, runtime_inspector=approved_runtime_inspection)

    assert result.verdict == "ready_with_history_warnings"
    assert [(finding.code, finding.category, finding.severity) for finding in result.findings] == [
        ("corpus_adoption_pending", "history", "warning")
    ]


def test_unresolved_missing_artifact_remains_a_project_blocker(tmp_path: Path) -> None:
    from meeting_ingest.ledger import LedgerSnapshot, append_snapshot

    paths = init_project(tmp_path)
    append_snapshot(
        paths.ledger,
        LedgerSnapshot(
            schema_version="1.0",
            event="ingest_completed",
            source_sha256="a" * 64,
            meeting_id="mtg-20260713-af5978a9",
            ingest_run_id="ingest-20260713-test",
            source={},
            artifacts={"summary-plus-verbatim": {"path": "missing.md"}},
            signals={},
            reconcile={"status": "completed"},
        ),
    )

    result = assess_readiness(tmp_path, runtime_inspector=approved_runtime_inspection)

    assert result.verdict == "blocked"
    assert [(finding.code, finding.category, finding.severity) for finding in result.findings] == [
        ("missing_artifact", "project", "blocker")
    ]


def test_ambiguous_identity_matched_artifacts_remain_a_project_blocker(tmp_path: Path) -> None:
    from meeting_ingest.ledger import LedgerSnapshot, append_snapshot

    paths = init_project(tmp_path)
    source_sha256 = "a" * 64
    meeting_id = "mtg-20260713-af5978a9"
    front_matter = f"---\nmeeting_id: {meeting_id}\nsource_sha256: {source_sha256}\n---\n"
    (paths.meetings_root / "candidate-one.md").write_text(front_matter, encoding="utf-8")
    (paths.meetings_root / "candidate-two.md").write_text(front_matter, encoding="utf-8")
    append_snapshot(
        paths.ledger,
        LedgerSnapshot(
            schema_version="1.0",
            event="ingest_completed",
            source_sha256=source_sha256,
            meeting_id=meeting_id,
            ingest_run_id="ingest-20260713-test",
            source={},
            artifacts={"summary-plus-verbatim": {"path": "missing.md"}},
            signals={},
            reconcile={"status": "completed"},
        ),
    )

    result = assess_readiness(tmp_path, runtime_inspector=approved_runtime_inspection)

    assert result.verdict == "blocked"
    assert [(finding.code, finding.category, finding.severity) for finding in result.findings] == [
        ("missing_artifact", "project", "blocker")
    ]


def test_development_override_marks_provenance_and_waives_only_selection(tmp_path: Path) -> None:
    init_project(tmp_path)
    inspection = _runtime_with_finding(tmp_path, _runtime_blocker("runtime_editable_blocked"))

    result = assess_readiness(
        tmp_path,
        development_override=DevelopmentOverride("exercise local provider workflow"),
        runtime_inspector=lambda _: inspection,
    )

    assert result.verdict == "development_override"
    assert result.exit_code == 0
    assert result.runtime_provenance.runtime_mode == "development"
    assert result.runtime_provenance.development_override_reason == "exercise local provider workflow"


@pytest.mark.parametrize(
    "code",
    [
        "runtime_git_uninspectable",
        "runtime_install_unknown",
        "runtime_package_integrity_failed",
    ],
)
def test_development_override_never_waives_integrity_blockers(tmp_path: Path, code: str) -> None:
    init_project(tmp_path)
    inspection = _runtime_with_finding(tmp_path, _runtime_blocker(code))

    result = assess_readiness(
        tmp_path,
        development_override=DevelopmentOverride("local diagnosis"),
        runtime_inspector=lambda _: inspection,
    )

    assert result.verdict == "blocked"
    assert result.exit_code == EXIT_RUNTIME_READINESS


@pytest.mark.parametrize("code", ["runtime_git_dirty", "workflow_hash_mismatch"])
def test_development_override_waives_identified_development_state(tmp_path: Path, code: str) -> None:
    init_project(tmp_path)
    inspection = _runtime_with_finding(tmp_path, _runtime_blocker(code), mode="editable")

    result = assess_readiness(
        tmp_path,
        development_override=DevelopmentOverride("worktree implementation test"),
        runtime_inspector=lambda _: inspection,
    )

    assert result.verdict == "development_override"


def test_workflow_mismatch_is_not_waived_for_an_unverified_install(tmp_path: Path) -> None:
    init_project(tmp_path)
    inspection = _runtime_with_finding(tmp_path, _runtime_blocker("workflow_hash_mismatch"))

    result = assess_readiness(
        tmp_path,
        development_override=DevelopmentOverride("unverified install"),
        runtime_inspector=lambda _: inspection,
    )

    assert result.verdict == "blocked"


def test_unknown_health_issue_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    init_project(tmp_path)
    monkeypatch.setattr(
        "meeting_ingest.doctor.find_issues",
        lambda _: [DoctorIssue("future_health_code", "New issue.", None)],
    )

    result = assess_readiness(tmp_path, runtime_inspector=approved_runtime_inspection)

    assert result.verdict == "blocked"
    assert result.findings[0].code == "readiness_issue_unclassified"


def test_uninspectable_current_integrity_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    init_project(tmp_path)

    def fail_inspection(_paths):
        raise OSError("unreadable ledger")

    monkeypatch.setattr("meeting_ingest.doctor.find_issues", fail_inspection)

    result = assess_readiness(tmp_path, runtime_inspector=approved_runtime_inspection)

    assert result.verdict == "blocked"
    assert {finding.code for finding in result.findings} == {
        "readiness_current_integrity_unknown"
    }


def test_privacy_and_unsafe_paths_are_project_blockers(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    privacy = assess_readiness(
        tmp_path,
        require_session_provider=True,
        runtime_inspector=approved_runtime_inspection,
    )
    assert "readiness_privacy_blocked" in {finding.code for finding in privacy.findings}

    text = paths.config_path.read_text(encoding="utf-8").replace(
        'root = "_local/project-context/meetings"', 'root = "../outside"'
    )
    paths.config_path.write_text(text, encoding="utf-8")
    unsafe = assess_readiness(tmp_path, runtime_inspector=approved_runtime_inspection)
    assert "readiness_path_unsafe" in {finding.code for finding in unsafe.findings}


@pytest.mark.parametrize("provider", ["session", "anthropic"])
def test_generic_readiness_applies_privacy_to_the_configured_default_provider(
    tmp_path: Path, provider: str
) -> None:
    paths = init_project(tmp_path)
    text = paths.config_path.read_text(encoding="utf-8").replace(
        'default_provider = "mock"', f'default_provider = "{provider}"'
    )
    paths.config_path.write_text(text, encoding="utf-8")

    result = assess_readiness(tmp_path, runtime_inspector=approved_runtime_inspection)

    assert result.verdict == "blocked"
    assert "readiness_privacy_blocked" in {finding.code for finding in result.findings}


def test_generic_readiness_blocks_an_unsupported_default_provider_as_config(
    tmp_path: Path,
) -> None:
    paths = init_project(tmp_path)
    text = paths.config_path.read_text(encoding="utf-8").replace(
        'default_provider = "mock"', 'default_provider = "sesion"'
    )
    paths.config_path.write_text(text, encoding="utf-8")

    result = assess_readiness(tmp_path, runtime_inspector=approved_runtime_inspection)

    assert result.verdict == "blocked"
    assert "readiness_config_invalid" in {finding.code for finding in result.findings}
    assert "readiness_privacy_blocked" not in {finding.code for finding in result.findings}


def test_ambiguous_identity_alias_is_a_history_warning(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    (paths.playbook_state / "stakeholders.toml").write_text(
        '''schema_version = "1.0"

[[people]]
person_id = "person-one"
display_name = "Person One"
aliases = ["Shared"]
status = "reviewed"

[[people]]
person_id = "person-two"
display_name = "Person Two"
aliases = ["Shared"]
status = "reviewed"
''',
        encoding="utf-8",
    )

    result = assess_readiness(tmp_path, runtime_inspector=approved_runtime_inspection)

    assert result.verdict == "ready_with_history_warnings"
    assert {finding.code for finding in result.findings} == {"historical_identity_gap"}


def test_pending_handoff_can_be_allowed_only_for_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    init_project(tmp_path)
    monkeypatch.setattr(
        "meeting_ingest.doctor.find_issues",
        lambda _: [DoctorIssue("session_handoff_pending", "Pending response.", "request.json")],
    )

    blocked = assess_readiness(tmp_path, runtime_inspector=approved_runtime_inspection)
    resolving = assess_readiness(
        tmp_path,
        allow_pending_handoffs=True,
        runtime_inspector=approved_runtime_inspection,
    )

    assert blocked.verdict == "blocked"
    assert resolving.verdict == "ready"


def test_runtime_blocked_handoff_blocks_unrelated_writes_but_allows_specialized_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    init_project(tmp_path)
    monkeypatch.setattr(
        "meeting_ingest.doctor.find_issues",
        lambda _: [DoctorIssue("session_handoff_runtime_blocked", "Bound runtime mismatch.", "request.json")],
    )

    blocked = assess_readiness(tmp_path, runtime_inspector=approved_runtime_inspection)
    resolving = assess_readiness(
        tmp_path,
        operation="ingest",
        allow_pending_handoffs=True,
        runtime_inspector=approved_runtime_inspection,
    )

    assert blocked.verdict == "blocked"
    assert blocked.findings[0].code == "session_handoff_runtime_blocked"
    assert resolving.verdict == "ready"


def test_validate_response_uses_ingest_incomplete_reconcile_exemption(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    init_project(tmp_path)
    monkeypatch.setattr(
        "meeting_ingest.doctor.find_issues",
        lambda _: [DoctorIssue("incomplete_reconcile", "Prior reconcile is pending.", "source.txt")],
    )

    result = assess_readiness(
        tmp_path,
        operation="validate-response",
        runtime_inspector=approved_runtime_inspection,
    )

    assert result.verdict == "ready"
    assert result.findings == ()


def test_symlinked_config_is_unsafe(tmp_path: Path) -> None:
    external = tmp_path / "external.toml"
    external.write_text('schema_version = "1.0"\n', encoding="utf-8")
    config = tmp_path / "_local/project-context/meetings/meeting-ingest.toml"
    config.parent.mkdir(parents=True)
    config.symlink_to(external)

    result = assess_readiness(tmp_path, operation="init", runtime_inspector=approved_runtime_inspection)

    assert result.verdict == "blocked"
    assert {finding.code for finding in result.findings} == {"readiness_path_unsafe"}


def test_malformed_config_is_blocked_without_creating_runtime_paths(tmp_path: Path) -> None:
    config = tmp_path / "_local/project-context/meetings/meeting-ingest.toml"
    config.parent.mkdir(parents=True)
    config.write_text('schema_version = "1.0"\n[privacy]\nallow_session_provider = "yes"\n', encoding="utf-8")

    result = assess_readiness(tmp_path, operation="init", runtime_inspector=approved_runtime_inspection)

    assert result.verdict == "blocked"
    assert {finding.code for finding in result.findings} == {"readiness_config_invalid"}
    assert not (config.parent / "_cache").exists()


def test_blocked_init_guard_has_zero_side_effects_and_ignores_test_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "new-project"
    inspection = _runtime_with_finding(target, _runtime_blocker("runtime_install_unknown"))
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "pretend-approved")
    monkeypatch.setattr("meeting_ingest.readiness._RUNTIME_INSPECTOR", lambda _: inspection)

    with pytest.raises(RuntimeReadinessError) as exc:
        require_write_readiness(
            target,
            operation="init",
        )

    assert exc.value.exit_code == EXIT_RUNTIME_READINESS
    assert not target.exists()


def test_readiness_summary_preserves_full_json_findings_and_grouped_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    init_project(tmp_path)
    monkeypatch.setattr(
        "meeting_ingest.doctor.find_issues",
        lambda _: [DoctorIssue("low_confidence_meeting_date", "Date needs review.", "meeting.md")],
    )

    summary = readiness_summary(tmp_path, runtime_inspector=approved_runtime_inspection)
    data = summary.to_dict()

    assert data["verdict"] == "ready_with_history_warnings"
    assert data["finding_counts"] == {
        "by_category": {"history": 1},
        "by_severity": {"warning": 1},
    }
    assert data["findings"][0]["path"] == "meeting.md"


def test_readiness_summary_match_uses_the_pin_comparison(tmp_path: Path) -> None:
    init_project(tmp_path)
    inspection = approved_runtime_inspection(tmp_path)
    inspection = replace(inspection, pin={**inspection.pin, "match": False})

    summary = readiness_summary(tmp_path, runtime_inspector=lambda _: inspection)

    assert summary.details["match"] is False


def test_read_only_project_surfaces_remain_available_while_runtime_is_blocked(
    tmp_path: Path,
) -> None:
    from meeting_ingest import pipeline

    paths = init_project(tmp_path)
    inspection = _runtime_with_finding(
        tmp_path, _runtime_blocker("runtime_package_integrity_failed")
    )

    blocked = readiness_summary(tmp_path, runtime_inspector=lambda _: inspection)
    doctor = pipeline.doctor(tmp_path)
    status = pipeline.status(tmp_path)

    assert blocked.exit_code == EXIT_RUNTIME_READINESS
    assert doctor.details["command"] == "doctor"
    assert status.details["command"] == "status"
    assert not (paths.cache / "meeting-ingest.lock").exists()


def test_every_public_mutation_reaches_the_shared_guard_before_lock_or_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from meeting_ingest import pipeline, playbook, playbook_review, session_inbox

    paths = init_project(tmp_path)
    config_text = paths.config_path.read_text(encoding="utf-8").replace(
        "allow_session_provider = false", "allow_session_provider = true"
    )
    paths.config_path.write_text(config_text, encoding="utf-8")
    source = paths.inbox / "meeting.txt"
    source.write_text("Ken: hello\n", encoding="utf-8")
    ledger_before = paths.ledger.read_bytes()

    class GuardCalled(Exception):
        pass

    def deny(*_args, **_kwargs):
        raise GuardCalled

    monkeypatch.setattr(pipeline, "require_write_readiness", deny)
    monkeypatch.setattr(playbook, "require_write_readiness", deny)
    monkeypatch.setattr(playbook_review, "require_write_readiness", deny)
    monkeypatch.setattr(session_inbox, "require_write_readiness", deny)

    calls = [
        lambda: pipeline.ingest(source, start=tmp_path),
        lambda: pipeline.provider_request(source, start=tmp_path),
        lambda: pipeline.ingest_inbox(tmp_path),
        lambda: pipeline.repair_date("missing", date="2026-07-01", start=tmp_path),
        lambda: pipeline.reconcile(tmp_path),
        lambda: session_inbox.process_session_inbox(tmp_path),
        lambda: playbook.update(tmp_path),
        lambda: playbook.repair_index(tmp_path),
        lambda: playbook.cleanup_uncommitted(tmp_path),
        lambda: playbook_review.mutate_review(
            tmp_path,
            action="suppress_signal",
            target={"source_id": "src-a1b2c3d4e5f6", "signal_id": "sig-a1b2c3d4e5f6-91aa2c80b731"},
            reason="test guard",
        ),
    ]
    for call in calls:
        with pytest.raises(GuardCalled):
            call()

    assert paths.ledger.read_bytes() == ledger_before
    assert not (paths.cache / "meeting-ingest.lock").exists()


def test_development_override_requires_a_non_empty_reason() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        DevelopmentOverride("   ")
