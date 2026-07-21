from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
from typing import Any

import pytest

from meeting_ingest._build_info import BUILD_INFO
from meeting_ingest.runtime import inspect_runtime


class StubDistribution:
    def __init__(self, root: Path, dist_info: Path, *, direct_url: dict[str, Any] | None = None) -> None:
        self.root = root
        self._path = dist_info
        self.metadata = {"Name": "meeting-ingest", "Version": "0.1.0"}
        self._direct_url = direct_url
        self.files: tuple[()] = ()

    def locate_file(self, path: str | Path) -> Path:
        return self.root / path

    def read_text(self, name: str) -> str | None:
        if name == "direct_url.json" and self._direct_url is not None:
            return json.dumps(self._direct_url)
        return None


def _record_hash(payload: bytes) -> str:
    digest = hashlib.sha256(payload).digest()
    encoded = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return f"sha256={encoded}"


def _make_distribution(
    tmp_path: Path,
    *,
    direct_url: dict[str, Any] | None = None,
) -> tuple[StubDistribution, Path, Path]:
    root = tmp_path / "site-packages"
    package = root / "meeting_ingest"
    dist_info = root / "meeting_ingest-0.1.0.dist-info"
    package.mkdir(parents=True)
    dist_info.mkdir()
    module = package / "__init__.py"
    metadata = dist_info / "METADATA"
    module.write_text("__version__ = '0.1.0'\n", encoding="utf-8")
    metadata.write_text("Name: meeting-ingest\nVersion: 0.1.0\n", encoding="utf-8")
    rows = [
        ["meeting_ingest/__init__.py", _record_hash(module.read_bytes()), str(module.stat().st_size)],
        [
            "meeting_ingest-0.1.0.dist-info/METADATA",
            _record_hash(metadata.read_bytes()),
            str(metadata.stat().st_size),
        ],
        ["meeting_ingest-0.1.0.dist-info/RECORD", "", ""],
    ]
    output = io.StringIO(newline="")
    csv.writer(output, lineterminator="\n").writerows(rows)
    (dist_info / "RECORD").write_text(output.getvalue(), encoding="utf-8")
    return StubDistribution(root, dist_info, direct_url=direct_url), module, dist_info


def _digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _approved_inspection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    distribution, module, _ = _make_distribution(tmp_path)
    executable = tmp_path / "bin/meeting-ingest"
    executable.parent.mkdir()
    executable.write_text("#!/bin/sh\n", encoding="utf-8")
    skill = tmp_path / "workflow/SKILL.md"
    agent = tmp_path / "workflow/agent.md"
    skill.parent.mkdir()
    skill.write_text("approved skill\n", encoding="utf-8")
    agent.write_text("approved agent\n", encoding="utf-8")
    commit = "a" * 40
    tree_digest = "sha256:" + "b" * 64
    build_id = "meeting-ingest-0.1.0-gaaaaaaaaaaaa-sbbbbbbbbbbbb"
    monkeypatch.setitem(BUILD_INFO, "build_id", build_id)
    monkeypatch.setitem(BUILD_INFO, "source_commit", commit)
    monkeypatch.setitem(BUILD_INFO, "source_tree_sha256", tree_digest)
    monkeypatch.setitem(BUILD_INFO, "build_kind", "approved-candidate")
    wheel_digest = "sha256:" + "c" * 64
    template_digest = "sha256:" + "d" * 64
    receipt = {
        "schema_version": "1.0",
        "build": {
            "semantic_version": "0.1.0",
            "build_id": build_id,
            "source_commit": commit,
            "source_tree_sha256": tree_digest,
            "wheel_filename": "meeting_ingest-0.1.0-py3-none-any.whl",
            "wheel_sha256": wheel_digest,
        },
        "workflow": {
            "contract_version": "claude-code-session-v1",
            "claude_skill_template_sha256": template_digest,
            "claude_agent_sha256": _digest(agent),
        },
        "verification": {
            "source_commit_reviewed": True,
            "full_suite_passed": True,
            "reproducible_wheel_verified": True,
        },
        "approved_by": "owner",
        "approved_at": "2026-07-20T00:00:00Z",
    }
    receipt_path = tmp_path / "release/receipt.json"
    receipt_path.parent.mkdir()
    receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
    consumer = tmp_path / "consumer"
    pin_path = consumer / "_local/project-context/meetings/meeting-ingest-runtime.toml"
    pin_path.parent.mkdir(parents=True)
    pin_path.write_text(
        "\n".join(
            [
                'schema_version = "1.0"',
                'channel = "private-alpha"',
                f'approved_build_id = "{build_id}"',
                f'approved_source_commit = "{commit}"',
                f'approved_source_tree_sha256 = "{tree_digest}"',
                f'approved_wheel_sha256 = "{wheel_digest}"',
                f'approved_receipt_sha256 = "{_digest(receipt_path)}"',
                f'approved_executable = "{executable}"',
                'workflow_contract_version = "claude-code-session-v1"',
                f'claude_skill_template_sha256 = "{template_digest}"',
                f'installed_claude_skill_sha256 = "{_digest(skill)}"',
                f'claude_agent_sha256 = "{_digest(agent)}"',
                'approved_at = "2026-07-20T00:00:00Z"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    return inspect_runtime(
        consumer,
        invoked_path=executable,
        module_path=module,
        distribution=distribution,
        application_data_root=tmp_path / "app-data",
        receipt_path=receipt_path,
        skill_path=skill,
        agent_path=agent,
    )


def _reinspect_approved(
    inspection,
    tmp_path: Path,
    *,
    invoked_path: Path | None = None,
    receipt_path: Path | None = None,
):
    dist_path = Path(inspection.distribution["path"])
    return inspect_runtime(
        Path(inspection.pin["path"]).parents[3],
        invoked_path=invoked_path or Path(inspection.executable["invoked"]),
        module_path=Path(inspection.executable["module"]),
        distribution=StubDistribution(dist_path.parent, dist_path),
        application_data_root=tmp_path / "app-data",
        receipt_path=receipt_path,
        skill_path=Path(inspection.workflow.skill_path),
        agent_path=Path(inspection.workflow.agent_path),
    )


def test_approved_frozen_runtime_requires_matching_integrity_receipt_pin_and_workflow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inspection = _approved_inspection(tmp_path, monkeypatch)

    assert inspection.install.mode == "approved_frozen"
    assert inspection.runtime_mode == "approved"
    assert inspection.distribution["record_integrity"] == "valid"
    assert inspection.receipt["match"] is True
    assert inspection.pin["match"] is True
    assert inspection.workflow.match is True
    assert {finding.code for finding in inspection.findings} == {"channel_unavailable"}


def test_approved_executable_comparison_normalizes_symlinked_pin_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inspection = _approved_inspection(tmp_path, monkeypatch)
    executable = Path(inspection.executable["invoked"])
    symlink = executable.with_name("meeting-ingest-link")
    symlink.symlink_to(executable)
    pin_path = Path(inspection.pin["path"])
    pin_path.write_text(
        pin_path.read_text(encoding="utf-8").replace(
            f'approved_executable = "{executable}"',
            f'approved_executable = "{symlink}"',
        ),
        encoding="utf-8",
    )

    second = _reinspect_approved(
        inspection,
        tmp_path,
        invoked_path=symlink,
        receipt_path=Path(inspection.receipt["path"]),
    )

    assert second.install.mode == "approved_frozen"
    comparison = next(
        item for item in second.pin["comparisons"] if item["field"] == "approved_executable"
    )
    assert comparison["expected"] == str(symlink)
    assert comparison["resolved_expected"] == str(executable)
    assert comparison["match"] is True


def test_valid_but_divergent_pin_reports_executable_and_pin_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inspection = _approved_inspection(tmp_path, monkeypatch)
    pin_path = Path(inspection.pin["path"])
    pin_path.write_text(
        pin_path.read_text(encoding="utf-8").replace(
            f'approved_executable = "{inspection.executable["invoked"]}"',
            f'approved_executable = "{tmp_path / "other-bin/meeting-ingest"}"',
        ),
        encoding="utf-8",
    )

    second = _reinspect_approved(
        inspection,
        tmp_path,
        receipt_path=Path(inspection.receipt["path"]),
    )
    codes = {finding.code for finding in second.findings}

    assert "runtime_executable_mismatch" in codes
    assert "runtime_pin_mismatch" in codes


def test_receipt_and_workflow_mismatches_report_stable_codes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inspection = _approved_inspection(tmp_path, monkeypatch)
    receipt_path = Path(inspection.receipt["path"])
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["build"]["build_id"] = "meeting-ingest-0.1.0-g000000000000-s000000000000"
    receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
    Path(inspection.workflow.skill_path).write_text("changed skill\n", encoding="utf-8")
    pin_path = Path(inspection.pin["path"])
    pin_path.write_text(
        pin_path.read_text(encoding="utf-8").replace(
            'workflow_contract_version = "claude-code-session-v1"',
            'workflow_contract_version = "claude-code-session-v2"',
        ),
        encoding="utf-8",
    )

    second = _reinspect_approved(inspection, tmp_path, receipt_path=receipt_path)
    codes = {finding.code for finding in second.findings}

    assert "runtime_receipt_mismatch" in codes
    assert "workflow_hash_mismatch" in codes
    assert "workflow_contract_mismatch" in codes


def test_noneditable_local_directory_install_is_frozen_but_unapproved(tmp_path: Path) -> None:
    distribution, module, _ = _make_distribution(
        tmp_path,
        direct_url={"url": tmp_path.as_uri(), "dir_info": {}},
    )

    inspection = inspect_runtime(
        tmp_path / "consumer",
        invoked_path=tmp_path / "bin/meeting-ingest",
        module_path=module,
        distribution=distribution,
        application_data_root=tmp_path / "app-data",
        skill_path=tmp_path / "missing-skill",
        agent_path=tmp_path / "missing-agent",
    )

    assert inspection.install.mode == "frozen_unapproved"
    assert inspection.runtime_mode == "unverified"


def test_malformed_direct_url_reports_one_unknown_install_finding(tmp_path: Path) -> None:
    distribution, module, _ = _make_distribution(tmp_path)
    distribution.read_text = lambda name: "{" if name == "direct_url.json" else None  # type: ignore[method-assign]

    inspection = inspect_runtime(
        tmp_path / "consumer",
        module_path=module,
        distribution=distribution,
        application_data_root=tmp_path / "app-data",
        skill_path=tmp_path / "missing-skill",
        agent_path=tmp_path / "missing-agent",
    )

    unknown_findings = [
        finding for finding in inspection.findings if finding.code == "runtime_install_unknown"
    ]
    assert inspection.install.mode == "unknown"
    assert len(unknown_findings) == 1


def test_nonlocal_editable_url_reports_uninspectable_git(tmp_path: Path) -> None:
    distribution, module, _ = _make_distribution(
        tmp_path,
        direct_url={"url": "https://example.test/meeting-ingest", "dir_info": {"editable": True}},
    )

    inspection = inspect_runtime(
        tmp_path / "consumer",
        module_path=module,
        distribution=distribution,
        application_data_root=tmp_path / "app-data",
        skill_path=tmp_path / "missing-skill",
        agent_path=tmp_path / "missing-agent",
    )

    assert inspection.install.inspection_status == "error"
    assert "runtime_git_uninspectable" in {finding.code for finding in inspection.findings}


@pytest.mark.parametrize("dirty", [False, True])
def test_editable_install_reports_clean_and_dirty_git_state(tmp_path: Path, dirty: bool) -> None:
    repository = tmp_path / "source"
    repository.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
    subprocess.run(["git", "config", "user.email", "runtime@example.test"], cwd=repository, check=True)
    subprocess.run(["git", "config", "user.name", "Runtime Test"], cwd=repository, check=True)
    tracked = repository / "tracked.txt"
    tracked.write_text("clean\n", encoding="utf-8")
    source_module = repository / "src/meeting_ingest/__init__.py"
    source_module.parent.mkdir(parents=True)
    source_module.write_text("", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-qm", "test"], cwd=repository, check=True)
    if dirty:
        (repository / "untracked.txt").write_text("dirty\n", encoding="utf-8")
    distribution, _, _ = _make_distribution(
        tmp_path / "install",
        direct_url={"url": repository.as_uri(), "dir_info": {"editable": True}},
    )
    inspection = inspect_runtime(
        tmp_path / "consumer",
        module_path=source_module,
        distribution=distribution,
        application_data_root=tmp_path / "app-data",
        skill_path=tmp_path / "missing-skill",
        agent_path=tmp_path / "missing-agent",
    )

    assert inspection.install.mode == "editable"
    assert inspection.install.git_dirty is dirty
    assert inspection.install.git_commit is not None
    assert inspection.runtime_mode == "development"


def test_editable_install_reports_missing_git_without_raising(tmp_path: Path) -> None:
    repository = tmp_path / "source"
    repository.mkdir()
    distribution, _, _ = _make_distribution(
        tmp_path / "install",
        direct_url={"url": repository.as_uri(), "dir_info": {"editable": True}},
    )
    source_module = repository / "src/meeting_ingest/__init__.py"
    source_module.parent.mkdir(parents=True)
    source_module.write_text("", encoding="utf-8")

    def missing_git(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("git not found")

    inspection = inspect_runtime(
        tmp_path / "consumer",
        module_path=source_module,
        distribution=distribution,
        application_data_root=tmp_path / "app-data",
        skill_path=tmp_path / "missing-skill",
        agent_path=tmp_path / "missing-agent",
        runner=missing_git,
    )

    assert inspection.install.inspection_status == "error"
    assert "runtime_git_uninspectable" in {finding.code for finding in inspection.findings}


def test_mismatched_module_and_distribution_is_unknown(tmp_path: Path) -> None:
    distribution, _, _ = _make_distribution(tmp_path)
    other_module = tmp_path / "other/meeting_ingest/__init__.py"
    other_module.parent.mkdir(parents=True)
    other_module.write_text("", encoding="utf-8")

    inspection = inspect_runtime(
        tmp_path / "consumer",
        module_path=other_module,
        distribution=distribution,
        application_data_root=tmp_path / "app-data",
        skill_path=tmp_path / "missing-skill",
        agent_path=tmp_path / "missing-agent",
    )

    assert inspection.install.mode == "unknown"
    assert "runtime_install_unknown" in {finding.code for finding in inspection.findings}


def test_corrupted_record_is_reported_as_package_integrity_failure(tmp_path: Path) -> None:
    distribution, module, _ = _make_distribution(tmp_path)
    module.write_text("corrupted\n", encoding="utf-8")

    inspection = inspect_runtime(
        tmp_path / "consumer",
        module_path=module,
        distribution=distribution,
        application_data_root=tmp_path / "app-data",
        skill_path=tmp_path / "missing-skill",
        agent_path=tmp_path / "missing-agent",
    )

    assert inspection.distribution["record_integrity"] == "invalid"
    assert "RECORD hash mismatch" in inspection.distribution["record_errors"][0]
    assert "runtime_package_integrity_failed" in {finding.code for finding in inspection.findings}


@pytest.mark.parametrize("record_state", ["missing", "symlink"])
def test_missing_or_symlinked_record_is_not_integrity_evidence(
    tmp_path: Path,
    record_state: str,
) -> None:
    distribution, module, dist_info = _make_distribution(tmp_path)
    record = dist_info / "RECORD"
    record.unlink()
    if record_state == "symlink":
        target = tmp_path / "outside-record"
        target.write_text("meeting_ingest-0.1.0.dist-info/RECORD,,\n", encoding="utf-8")
        record.symlink_to(target)

    inspection = inspect_runtime(
        tmp_path / "consumer",
        module_path=module,
        distribution=distribution,
        application_data_root=tmp_path / "app-data",
        skill_path=tmp_path / "missing-skill",
        agent_path=tmp_path / "missing-agent",
    )

    assert inspection.distribution["record_integrity"] == "missing"
    assert "runtime_package_integrity_failed" in {finding.code for finding in inspection.findings}


def test_blank_non_record_hash_fails_closed_for_approved_integrity(tmp_path: Path) -> None:
    distribution, module, dist_info = _make_distribution(tmp_path)
    record = dist_info / "RECORD"
    record.write_text(
        record.read_text(encoding="utf-8").replace(
            next(line for line in record.read_text(encoding="utf-8").splitlines() if line.startswith("meeting_ingest/__init__.py")),
            "meeting_ingest/__init__.py,,",
        ),
        encoding="utf-8",
    )

    inspection = inspect_runtime(
        tmp_path / "consumer",
        module_path=module,
        distribution=distribution,
        application_data_root=tmp_path / "app-data",
        skill_path=tmp_path / "missing-skill",
        agent_path=tmp_path / "missing-agent",
    )

    assert inspection.distribution["record_integrity"] == "invalid"
    assert inspection.distribution["record_errors"] == [
        "Installed file has no RECORD hash: meeting_ingest/__init__.py"
    ]


def test_partial_pin_is_invalid_even_when_present(tmp_path: Path) -> None:
    distribution, module, _ = _make_distribution(tmp_path)
    pin = tmp_path / "consumer/_local/project-context/meetings/meeting-ingest-runtime.toml"
    pin.parent.mkdir(parents=True)
    pin.write_text('schema_version = "1.0"\napproved_build_id = "development"\n', encoding="utf-8")

    inspection = inspect_runtime(
        tmp_path / "consumer",
        module_path=module,
        distribution=distribution,
        application_data_root=tmp_path / "app-data",
        skill_path=tmp_path / "missing-skill",
        agent_path=tmp_path / "missing-agent",
    )

    assert inspection.pin["valid"] is False
    assert "missing keys" in inspection.pin["error"]
    assert "runtime_pin_invalid" in {finding.code for finding in inspection.findings}


def test_structurally_incomplete_receipt_is_invalid(tmp_path: Path) -> None:
    distribution, module, _ = _make_distribution(tmp_path)
    receipt = tmp_path / "receipt.json"
    receipt.write_text('{"schema_version":"1.0","build":{}}\n', encoding="utf-8")

    inspection = inspect_runtime(
        tmp_path / "consumer",
        module_path=module,
        distribution=distribution,
        receipt_path=receipt,
        application_data_root=tmp_path / "app-data",
        skill_path=tmp_path / "missing-skill",
        agent_path=tmp_path / "missing-agent",
    )

    assert inspection.receipt["match"] is False
    assert "top-level keys" in inspection.receipt["error"]
    assert "runtime_receipt_invalid" in {finding.code for finding in inspection.findings}


def test_missing_receipt_keeps_approved_candidate_unapproved(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inspection = _approved_inspection(tmp_path, monkeypatch)
    receipt_path = Path(inspection.receipt["path"])
    receipt_path.unlink()

    second = inspect_runtime(
        Path(inspection.pin["path"]).parents[3],
        invoked_path=inspection.executable["invoked"],
        module_path=inspection.executable["module"],
        distribution=StubDistribution(
            Path(inspection.distribution["path"]).parent,
            Path(inspection.distribution["path"]),
        ),
        application_data_root=tmp_path / "app-data",
        skill_path=Path(inspection.workflow.skill_path),
        agent_path=Path(inspection.workflow.agent_path),
    )

    assert second.runtime_mode == "unverified"
    assert "runtime_receipt_invalid" in {finding.code for finding in second.findings}


def test_update_available_is_advisory_and_sorts_after_blockers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inspection = _approved_inspection(tmp_path, monkeypatch)
    channel_path = tmp_path / "app-data/channels/private-alpha.json"
    channel_path.parent.mkdir(parents=True)
    channel_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "channel": "private-alpha",
                "latest": {"build_id": "meeting-ingest-0.1.0-gffffffffffff-seeeeeeeeeeee"},
                "previous": [],
                "published_at": "2026-07-21T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    Path(inspection.workflow.skill_path).write_text("changed skill\n", encoding="utf-8")

    second = _reinspect_approved(
        inspection,
        tmp_path,
        receipt_path=Path(inspection.receipt["path"]),
    )

    assert second.channel["update_available"] is True
    assert [finding.code for finding in second.findings][-1] == "update_available"
    assert second.findings[-1].severity == "advisory"


def test_missing_distribution_reports_unknown_install(tmp_path: Path) -> None:
    inspection = inspect_runtime(
        tmp_path,
        distribution=False,
        module_path=tmp_path / "meeting_ingest/__init__.py",
        application_data_root=tmp_path / "app-data",
        skill_path=tmp_path / "missing-skill",
        agent_path=tmp_path / "missing-agent",
    )

    assert inspection.install.mode == "unknown"
    assert inspection.runtime_mode == "unverified"


def test_runtime_inspection_is_read_only_for_uninitialized_root(tmp_path: Path) -> None:
    root = tmp_path / "does-not-exist"
    before = set(tmp_path.rglob("*"))

    inspect_runtime(
        root,
        distribution=False,
        application_data_root=tmp_path / "app-data",
        skill_path=tmp_path / "missing-skill",
        agent_path=tmp_path / "missing-agent",
    )

    assert set(tmp_path.rglob("*")) == before
