from __future__ import annotations

import base64
import csv
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
from typing import Any

import pytest

from meeting_ingest._build_info import BUILD_INFO
from meeting_ingest.cli import emit, main
from meeting_ingest.errors import EXIT_RUNTIME_READINESS
from meeting_ingest.paths import init_project
from meeting_ingest.runtime import inspect_runtime
from meeting_ingest.runtime_config import read_pin
from meeting_ingest.runtime_release import (
    APPROVED_EXECUTABLE_MARKER,
    UPDATE_DELEGATION_MARKER,
    PublishedRuntime,
    RuntimeReleaseError,
    _require_frozen_install,
    bootstrap_consumer_runtime,
    install_approved_wheel,
    packaged_workflow_templates,
    publish_approved_runtime,
    update_consumer_roots,
    update_consumer_runtime,
)

VERSION = BUILD_INFO["semantic_version"]
BUILD_A = f"meeting-ingest-{VERSION}-gaaaaaaaaaaaa-sbbbbbbbbbbbb"
BUILD_B = f"meeting-ingest-{VERSION}-gcccccccccccc-sdddddddddddd"
COMMIT_A = "a" * 40
COMMIT_B = "c" * 40
TREE_A = "sha256:" + "b" * 64
TREE_B = "sha256:" + "d" * 64
PIN_RELATIVE = Path("_local/project-context/meetings/meeting-ingest-runtime.toml")
RELEASE_SCRIPT = Path(__file__).parents[1] / "scripts/release-approved-runtime.py"


class StubDistribution:
    def __init__(self, root: Path, dist_info: Path, *, direct_url: dict[str, Any] | None = None) -> None:
        self.root = root
        self._path = dist_info
        self.metadata = {"Name": "meeting-ingest", "Version": VERSION}
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
    return "sha256=" + base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _make_installation(
    prefix: Path,
    *,
    direct_url: dict[str, Any] | None = None,
) -> tuple[StubDistribution, Path, Path]:
    """Build a wheel-shaped install whose RECORD names its own console script."""
    site_packages = prefix / "lib/python3.11/site-packages"
    package = site_packages / "meeting_ingest"
    dist_info = site_packages / f"meeting_ingest-{VERSION}.dist-info"
    script = prefix / "bin/meeting-ingest"
    package.mkdir(parents=True)
    dist_info.mkdir()
    script.parent.mkdir(parents=True)
    module = package / "__init__.py"
    metadata = dist_info / "METADATA"
    module.write_text(f"__version__ = '{VERSION}'\n", encoding="utf-8")
    metadata.write_text(f"Name: meeting-ingest\nVersion: {VERSION}\n", encoding="utf-8")
    script.write_text("#!/usr/bin/env python3\nfrom meeting_ingest.cli import main\n", encoding="utf-8")
    rows = [
        ["../../../bin/meeting-ingest", _record_hash(script.read_bytes()), str(script.stat().st_size)],
        ["meeting_ingest/__init__.py", _record_hash(module.read_bytes()), str(module.stat().st_size)],
        [
            f"meeting_ingest-{VERSION}.dist-info/METADATA",
            _record_hash(metadata.read_bytes()),
            str(metadata.stat().st_size),
        ],
        [f"meeting_ingest-{VERSION}.dist-info/RECORD", "", ""],
    ]
    output = io.StringIO(newline="")
    csv.writer(output, lineterminator="\n").writerows(rows)
    (dist_info / "RECORD").write_text(output.getvalue(), encoding="utf-8")
    return StubDistribution(site_packages, dist_info, direct_url=direct_url), module, script


class _Machine:
    """One machine: a release store, one installed tool, and recorded tool commands."""

    def __init__(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        *,
        direct_url: dict[str, Any] | None = None,
    ) -> None:
        self.home = tmp_path / "home"
        (self.home / ".claude").mkdir(parents=True)
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: self.home))
        self.monkeypatch = monkeypatch
        self.templates = packaged_workflow_templates()
        self.app_root = tmp_path / "app-data"
        self.artifacts = tmp_path / "artifacts"
        self.artifacts.mkdir()
        self.commands: list[list[str]] = []
        self.environments: list[dict[str, str] | None] = []
        self.tool_build = (BUILD_A, COMMIT_A, TREE_A)
        self.latest = (BUILD_A, COMMIT_A, TREE_A)
        self.child_result: subprocess.CompletedProcess[str] | None = None
        self.distribution, self.module, self.executable = _make_installation(
            tmp_path / "tool", direct_url=direct_url
        )

    def publish(self, build_id: str, commit: str, tree: str) -> PublishedRuntime:
        """Publish one approved release whose receipt approves the packaged templates."""
        directory = self.artifacts / build_id
        directory.mkdir()
        wheel = directory / f"meeting_ingest-{VERSION}-py3-none-any.whl"
        wheel.write_bytes(f"wheel:{build_id}".encode())
        receipt = {
            "schema_version": "1.0",
            "build": {
                "semantic_version": VERSION,
                "build_id": build_id,
                "source_commit": commit,
                "source_tree_sha256": tree,
                "wheel_filename": wheel.name,
                "wheel_sha256": _digest(wheel),
            },
            "workflow": {
                "contract_version": BUILD_INFO["workflow_contract_version"],
                "claude_skill_template_sha256": _digest(self.templates.skill_template),
                "claude_agent_sha256": _digest(self.templates.claude_agent),
            },
            "verification": {
                "source_commit_reviewed": True,
                "full_suite_passed": True,
                "reproducible_wheel_verified": True,
            },
            "approved_by": "owner",
            "approved_at": "2026-08-30T00:00:00Z",
        }
        receipt_path = directory / "receipt.json"
        receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
        self.latest = (build_id, commit, tree)
        return publish_approved_runtime(
            receipt_path,
            application_data_root=self.app_root,
            published_at="2026-08-30T00:00:00Z",
        )

    def run_as(self, build_id: str, commit: str, tree: str) -> None:
        """Pretend this process is the console script of one approved build."""
        for key, value in {
            "build_id": build_id,
            "source_commit": commit,
            "source_tree_sha256": tree,
            "build_kind": "approved-candidate",
        }.items():
            self.monkeypatch.setitem(BUILD_INFO, key, value)

    def inspector(self, root: Path, **kwargs: Any):
        arguments: dict[str, Any] = {"module_path": self.module, "distribution": self.distribution}
        arguments.update(kwargs)
        return inspect_runtime(root, **arguments)

    def runner(self, command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        """Stand in for uv and for the console script this process cannot become."""
        self.commands.append(list(command))
        self.environments.append(kwargs.get("env"))
        if command[:3] == ["uv", "tool", "install"]:
            self.tool_build = self.latest
            return subprocess.CompletedProcess(command, 0, "", "")
        if command[1:3] == ["runtime", "inspect"]:
            evidence = {
                "build": {"build_id": self.tool_build[0], "build_kind": "approved-candidate"},
                "distribution": {"record_integrity": "valid"},
                "executable": {"console_script": str(self.executable)},
            }
            return subprocess.CompletedProcess(command, 0, json.dumps(evidence), "")
        if command[1:2] == ["update"]:
            return self.child_update(command)
        raise AssertionError(f"unexpected command: {command}")

    def child_update(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        """Run the delegated half the way the newly installed console script would."""
        if self.child_result is not None:
            return self.child_result
        self.run_as(*self.tool_build)
        os.environ[UPDATE_DELEGATION_MARKER] = "1"
        try:
            summary = self.update(Path(command[3]))
        finally:
            os.environ.pop(UPDATE_DELEGATION_MARKER, None)
        return subprocess.CompletedProcess(
            command, summary.exit_code, json.dumps(summary.to_dict(), sort_keys=True), ""
        )

    def prepare_consumer(self, root: Path) -> None:
        """Leave one consumer pinned to build A with a scaffolded project."""
        self.run_as(BUILD_A, COMMIT_A, TREE_A)
        bootstrap_consumer_runtime(
            root,
            application_data_root=self.app_root,
            invoked_executable=self.executable,
            runtime_inspector=self.inspector,
        )
        init_project(root)

    def update(self, root: Path):
        return update_consumer_runtime(
            root,
            application_data_root=self.app_root,
            invoked_executable=self.executable,
            runtime_inspector=self.inspector,
            command_runner=self.runner,
            executable_locator=lambda name: str(self.executable),
        )

    def rendered_skill(self) -> bytes:
        return self.templates.skill_template.read_bytes().replace(
            APPROVED_EXECUTABLE_MARKER.encode("utf-8"),
            str(self.executable.resolve()).encode("utf-8"),
            1,
        )


def _installed_wheels(machine: _Machine) -> list[str]:
    """Name the wheels handed to uv; each is a private staged copy, never the store path."""
    staged = []
    for command in machine.commands:
        if command[:4] == ["uv", "tool", "install", "--reinstall"]:
            assert Path(command[4]).parent != machine.app_root
            staged.append(Path(command[4]).name)
    return staged


def _delegations(machine: _Machine) -> list[list[str]]:
    return [command for command in machine.commands if command[1:2] == ["update"]]


def test_update_refuses_a_consumer_that_carries_no_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    machine = _Machine(tmp_path, monkeypatch)
    machine.publish(BUILD_A, COMMIT_A, TREE_A)
    consumer = tmp_path / "consumer"

    with pytest.raises(RuntimeReleaseError) as error:
        machine.update(consumer)

    assert error.value.code == "runtime_pin_missing"
    assert "meeting-ingest init" in error.value.details["remediation"]
    assert machine.commands == []
    assert not consumer.exists()


def test_update_is_a_no_op_when_the_pinned_build_is_already_current(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    machine = _Machine(tmp_path, monkeypatch)
    machine.publish(BUILD_A, COMMIT_A, TREE_A)
    consumer = tmp_path / "consumer"
    machine.prepare_consumer(consumer)
    before = (consumer / PIN_RELATIVE).read_bytes()

    summary = machine.update(consumer)

    assert summary.status == "no_op"
    assert summary.details["updated"] is False
    assert summary.details["build_id"] == BUILD_A
    assert summary.details["previous_build_id"] == BUILD_A
    assert summary.details["verdict"] == "ready"
    assert machine.commands == []
    assert (consumer / PIN_RELATIVE).read_bytes() == before


def test_update_completes_in_process_when_the_running_build_is_already_the_new_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    machine = _Machine(tmp_path, monkeypatch)
    machine.publish(BUILD_A, COMMIT_A, TREE_A)
    consumer = tmp_path / "consumer"
    machine.prepare_consumer(consumer)
    machine.publish(BUILD_B, COMMIT_B, TREE_B)
    machine.run_as(BUILD_B, COMMIT_B, TREE_B)

    summary = machine.update(consumer)
    pin = read_pin(consumer)

    assert summary.status == "success"
    assert summary.details["updated"] is True
    assert summary.details["delegated"] is False
    assert summary.details["build_id"] == BUILD_B
    assert summary.details["previous_build_id"] == BUILD_A
    assert summary.details["verdict"] == "ready"
    assert summary.details["pin_path"] == str(consumer / PIN_RELATIVE)
    assert machine.commands == []
    assert pin.valid is True
    assert pin.values["approved_build_id"] == BUILD_B
    assert pin.values["approved_source_commit"] == COMMIT_B
    assert (consumer / ".claude/skills/meeting-ingest/SKILL.md").read_bytes() == machine.rendered_skill()
    assert (consumer / ".claude/agents/meeting-ingest-session-provider.md").read_bytes() == (
        machine.templates.claude_agent.read_bytes()
    )


def test_update_installs_and_delegates_to_the_new_build_in_one_invocation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    machine = _Machine(tmp_path, monkeypatch)
    machine.publish(BUILD_A, COMMIT_A, TREE_A)
    consumer = tmp_path / "consumer"
    machine.prepare_consumer(consumer)
    published = machine.publish(BUILD_B, COMMIT_B, TREE_B)

    summary = machine.update(consumer)
    pin = read_pin(consumer)

    assert summary.status == "success"
    assert summary.details["updated"] is True
    assert summary.details["delegated"] is True
    assert summary.details["build_id"] == BUILD_B
    assert summary.details["previous_build_id"] == BUILD_A
    assert summary.details["verdict"] == "ready"
    assert _installed_wheels(machine) == [published.wheel_path.name]
    assert machine.commands[1] == [str(machine.executable), "runtime", "inspect", "--json"]
    assert _delegations(machine) == [
        [str(machine.executable), "update", "--root", str(consumer), "--json"]
    ]
    assert machine.environments[-1][UPDATE_DELEGATION_MARKER] == "1"
    assert pin.values["approved_build_id"] == BUILD_B
    assert (consumer / ".claude/skills/meeting-ingest/SKILL.md").read_bytes() == machine.rendered_skill()


def test_update_never_delegates_twice(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    machine = _Machine(tmp_path, monkeypatch)
    machine.publish(BUILD_A, COMMIT_A, TREE_A)
    consumer = tmp_path / "consumer"
    machine.prepare_consumer(consumer)
    machine.publish(BUILD_B, COMMIT_B, TREE_B)
    before = (consumer / PIN_RELATIVE).read_bytes()
    monkeypatch.setenv(UPDATE_DELEGATION_MARKER, "1")

    with pytest.raises(RuntimeReleaseError) as error:
        machine.update(consumer)

    assert error.value.code == "runtime_build_mismatch"
    assert machine.commands == []
    assert (consumer / PIN_RELATIVE).read_bytes() == before


def test_update_refuses_a_delegated_result_whose_exit_code_disagrees(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    machine = _Machine(tmp_path, monkeypatch)
    machine.publish(BUILD_A, COMMIT_A, TREE_A)
    consumer = tmp_path / "consumer"
    machine.prepare_consumer(consumer)
    before = (consumer / PIN_RELATIVE).read_bytes()
    machine.publish(BUILD_B, COMMIT_B, TREE_B)
    machine.child_result = subprocess.CompletedProcess(
        [],
        1,
        json.dumps(
            {
                "schema_version": "1.1",
                "status": "success",
                "exit_code": 0,
                "warnings": [],
                "errors": [],
                "command": "runtime_update",
            }
        ),
        "",
    )

    with pytest.raises(RuntimeReleaseError) as error:
        machine.update(consumer)

    assert error.value.code == "runtime_update_delegation_failed"
    assert (consumer / PIN_RELATIVE).read_bytes() == before


def test_update_refuses_a_published_wheel_that_does_not_match_its_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    machine = _Machine(tmp_path, monkeypatch)
    machine.publish(BUILD_A, COMMIT_A, TREE_A)
    consumer = tmp_path / "consumer"
    machine.prepare_consumer(consumer)
    before = (consumer / PIN_RELATIVE).read_bytes()
    published = machine.publish(BUILD_B, COMMIT_B, TREE_B)
    machine.run_as(BUILD_B, COMMIT_B, TREE_B)
    published.wheel_path.write_bytes(b"replaced wheel\n")

    with pytest.raises(RuntimeReleaseError) as error:
        machine.update(consumer)

    assert error.value.code == "runtime_wheel_invalid"
    assert machine.commands == []
    assert (consumer / PIN_RELATIVE).read_bytes() == before


def test_update_refuses_an_editable_runtime_before_installing_anything(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    (source / "src/meeting_ingest").mkdir(parents=True)
    machine = _Machine(tmp_path, monkeypatch)
    machine.publish(BUILD_A, COMMIT_A, TREE_A)
    consumer = tmp_path / "consumer"
    machine.prepare_consumer(consumer)
    before = (consumer / PIN_RELATIVE).read_bytes()
    machine.publish(BUILD_B, COMMIT_B, TREE_B)
    machine.distribution = StubDistribution(
        machine.distribution.root,
        machine.distribution._path,
        direct_url={"url": source.as_uri(), "dir_info": {"editable": True}},
    )

    with pytest.raises(RuntimeReleaseError) as error:
        machine.update(consumer)

    assert error.value.code == "runtime_editable_blocked"
    assert "meeting-ingest update" in error.value.details["remediation"]
    assert machine.commands == []
    assert (consumer / PIN_RELATIVE).read_bytes() == before


def test_update_keeps_the_old_pin_and_converges_on_the_rerun(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    machine = _Machine(tmp_path, monkeypatch)
    machine.publish(BUILD_A, COMMIT_A, TREE_A)
    consumer = tmp_path / "consumer"
    machine.prepare_consumer(consumer)
    before = (consumer / PIN_RELATIVE).read_bytes()
    published = machine.publish(BUILD_B, COMMIT_B, TREE_B)
    machine.child_result = subprocess.CompletedProcess(
        [],
        EXIT_RUNTIME_READINESS,
        json.dumps(
            {
                "schema_version": "1.1",
                "status": "failed",
                "exit_code": EXIT_RUNTIME_READINESS,
                "warnings": [],
                "errors": [{"phase": "runtime_release", "code": "lock_conflict", "message": "busy"}],
                "reason": "lock_conflict",
            }
        ),
        "",
    )

    interrupted = machine.update(consumer)

    assert interrupted.status == "failed"
    assert interrupted.exit_code == EXIT_RUNTIME_READINESS
    assert interrupted.errors[0]["code"] == "lock_conflict"
    assert (consumer / PIN_RELATIVE).read_bytes() == before

    machine.child_result = None
    summary = machine.update(consumer)

    assert summary.status == "success"
    assert summary.details["delegated"] is True
    assert read_pin(consumer).values["approved_build_id"] == BUILD_B
    assert _installed_wheels(machine) == [published.wheel_path.name] * 2


def test_update_prints_the_build_pin_and_readiness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    machine = _Machine(tmp_path, monkeypatch)
    machine.publish(BUILD_A, COMMIT_A, TREE_A)
    consumer = tmp_path / "consumer"
    machine.prepare_consumer(consumer)
    machine.publish(BUILD_B, COMMIT_B, TREE_B)
    machine.run_as(BUILD_B, COMMIT_B, TREE_B)

    emit(machine.update(consumer), as_json=False)
    updated = capsys.readouterr().out
    emit(machine.update(consumer), as_json=False)
    unchanged = capsys.readouterr().out

    assert updated == (
        f"Updated to {BUILD_B}\n"
        f"Pin: {consumer / PIN_RELATIVE}\n"
        "Readiness: Ready\n"
    )
    assert unchanged == (
        "Already up to date\n"
        f"Build: {BUILD_B}\n"
        f"Pin: {consumer / PIN_RELATIVE}\n"
        "Readiness: Ready\n"
    )


def test_update_reports_the_completed_update_before_a_blocked_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    machine = _Machine(tmp_path, monkeypatch)
    machine.publish(BUILD_A, COMMIT_A, TREE_A)
    consumer = tmp_path / "consumer"
    machine.run_as(BUILD_A, COMMIT_A, TREE_A)
    bootstrap_consumer_runtime(
        consumer,
        application_data_root=machine.app_root,
        invoked_executable=machine.executable,
        runtime_inspector=machine.inspector,
    )
    machine.publish(BUILD_B, COMMIT_B, TREE_B)
    machine.run_as(BUILD_B, COMMIT_B, TREE_B)

    summary = machine.update(consumer)
    emit(summary, as_json=False)
    captured = capsys.readouterr()

    assert summary.status == "blocked"
    assert summary.exit_code == EXIT_RUNTIME_READINESS
    assert summary.details["updated"] is True
    assert summary.details["verdict"] == "blocked"
    assert read_pin(consumer).values["approved_build_id"] == BUILD_B
    assert captured.out.startswith(f"Updated to {BUILD_B}\n")
    assert "Readiness: Blocked\n" in captured.out
    assert "readiness_config_invalid" in captured.err


def test_update_command_reports_a_missing_pin_on_the_human_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(["update", "--root", str(tmp_path / "consumer")])
    captured = capsys.readouterr()

    assert exit_code == EXIT_RUNTIME_READINESS
    assert "runtime_pin_missing" in captured.err
    assert "Next action: Run `meeting-ingest init`" in captured.err


def test_install_approved_wheel_stages_the_verified_bytes_and_verifies_the_tool(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    machine = _Machine(tmp_path, monkeypatch)
    published = machine.publish(BUILD_A, COMMIT_A, TREE_A)

    result = install_approved_wheel(
        published.receipt_path,
        application_data_root=machine.app_root,
        expected_wheel_sha256=_digest(published.wheel_path),
        command_runner=machine.runner,
        executable_locator=lambda name: str(machine.executable),
    )

    assert result.build_id == BUILD_A
    assert result.executable == machine.executable.resolve()
    assert result.command == ("uv", "tool", "install", "--reinstall", str(published.wheel_path))
    assert _installed_wheels(machine) == [published.wheel_path.name]
    assert machine.commands[1] == [str(machine.executable), "runtime", "inspect", "--json"]


def test_install_approved_wheel_refuses_a_tool_that_is_not_the_approved_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    machine = _Machine(tmp_path, monkeypatch)
    published = machine.publish(BUILD_A, COMMIT_A, TREE_A)
    machine.tool_build = (BUILD_B, COMMIT_B, TREE_B)

    def runner(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if command[:3] == ["uv", "tool", "install"]:
            return subprocess.CompletedProcess(command, 0, "", "")
        return machine.runner(command, **kwargs)

    with pytest.raises(RuntimeReleaseError) as error:
        install_approved_wheel(
            published.receipt_path,
            application_data_root=machine.app_root,
            command_runner=runner,
            executable_locator=lambda name: str(machine.executable),
        )

    assert error.value.code == "runtime_install_unverified"
    assert "build_id" in error.value.message


def test_install_approved_wheel_refuses_a_receipt_that_names_another_wheel_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    machine = _Machine(tmp_path, monkeypatch)
    published = machine.publish(BUILD_A, COMMIT_A, TREE_A)

    with pytest.raises(RuntimeReleaseError) as error:
        install_approved_wheel(
            published.receipt_path,
            application_data_root=machine.app_root,
            expected_wheel_sha256="sha256:" + "9" * 64,
            command_runner=machine.runner,
            executable_locator=lambda name: str(machine.executable),
        )

    assert error.value.code == "runtime_wheel_invalid"
    assert machine.commands == []


def test_frozen_install_guard_rejects_the_approved_mode_the_no_op_branch_returns_first(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    machine = _Machine(tmp_path, monkeypatch)
    published = machine.publish(BUILD_A, COMMIT_A, TREE_A)
    consumer = tmp_path / "consumer"
    machine.prepare_consumer(consumer)
    inspection = machine.inspector(
        consumer,
        invoked_path=machine.executable,
        application_data_root=machine.app_root,
        receipt_path=published.receipt_path,
    )

    assert inspection.install.mode == "approved_frozen"
    with pytest.raises(RuntimeReleaseError) as error:
        _require_frozen_install(inspection)

    assert error.value.code == "runtime_install_unknown"


def test_update_consumer_roots_drives_the_consumer_command_per_root(tmp_path: Path) -> None:
    commands: list[list[str]] = []
    first = tmp_path / "first"
    second = tmp_path / "second"

    def runner(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        commands.append(list(command))
        if command[3] == str(second):
            return subprocess.CompletedProcess(
                command, 4, json.dumps({"status": "blocked"}), "blocked\n"
            )
        return subprocess.CompletedProcess(
            command, 0, json.dumps({"status": "success", "build_id": BUILD_B}), "note\n"
        )

    results = update_consumer_roots(
        [first, second], executable=tmp_path / "bin/meeting-ingest", command_runner=runner
    )

    assert commands == [
        [str(tmp_path / "bin/meeting-ingest"), "update", "--root", str(first), "--json"],
        [str(tmp_path / "bin/meeting-ingest"), "update", "--root", str(second), "--json"],
    ]
    assert results[0] == {
        "root": str(first),
        "status": "success",
        "summary": {"status": "success", "build_id": BUILD_B},
        "error": None,
    }
    assert results[1]["status"] == "failed"
    assert results[1]["error"] == "blocked"


def _load_release_script():
    spec = importlib.util.spec_from_file_location("release_approved_runtime", RELEASE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _StubIdentity:
    def as_dict(self) -> dict[str, str]:
        return {"build_id": BUILD_B, "source_commit": COMMIT_B}


class _StubBuild:
    identity = _StubIdentity()
    wheel_path = Path("/artifacts/meeting_ingest.whl")
    wheel_sha256 = "sha256:" + "e" * 64
    receipt_path = Path("/artifacts/receipt.json")
    receipt_sha256 = "sha256:" + "f" * 64


def _stub_release_module(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, calls: dict[str, Any]):
    module = _load_release_script()
    published = PublishedRuntime(
        build_id=BUILD_B,
        release_directory=tmp_path / "releases" / BUILD_B,
        wheel_path=tmp_path / "releases" / BUILD_B / "meeting_ingest.whl",
        receipt_path=tmp_path / "releases" / BUILD_B / "receipt.json",
        channel_path=tmp_path / "channels/private-alpha.json",
        previous_build_ids=(BUILD_A,),
    )
    class _Installed:
        build_id = BUILD_B
        executable = tmp_path / "bin/meeting-ingest"
        command = ("uv", "tool", "install", "--reinstall", str(published.wheel_path))

    class _Workflow:
        skill_destination = tmp_path / "home/.claude/skills/meeting-ingest/SKILL.md"
        rendered_skill_sha256 = "sha256:" + "1" * 64
        agent_destination = tmp_path / "home/.claude/agents/meeting-ingest-session-provider.md"
        agent_sha256 = "sha256:" + "2" * 64

    def build(repo_root, commit, output_dir, **kwargs):
        calls["build"] = {"repo_root": repo_root, "commit": commit, "output_dir": output_dir, **kwargs}
        return _StubBuild()

    def publish(receipt_path, **kwargs):
        calls["publish"] = {"receipt_path": receipt_path, **kwargs}
        return published

    def install(receipt_path, **kwargs):
        calls["install"] = {"receipt_path": receipt_path, **kwargs}
        return _Installed()

    def install_artifacts(receipt_path, **kwargs):
        calls["workflow"] = {"receipt_path": receipt_path, **kwargs}
        return _Workflow()

    def update_roots(consumer_roots, **kwargs):
        calls["consumers"] = {"roots": list(consumer_roots), **kwargs}
        return [
            {"root": str(root), "status": "success", "summary": {"status": "success"}, "error": None}
            for root in consumer_roots
        ]

    monkeypatch.setattr(module, "build_approved_runtime", build)
    monkeypatch.setattr(module, "publish_approved_runtime", publish)
    monkeypatch.setattr(module, "install_approved_wheel", install)
    monkeypatch.setattr(module, "install_workflow_artifacts", install_artifacts)
    monkeypatch.setattr(module, "update_consumer_roots", update_roots)
    return module, published, _Installed


def test_release_script_composes_build_publish_install_and_consumer_updates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: dict[str, Any] = {}
    module, published, installed = _stub_release_module(monkeypatch, tmp_path, calls)
    consumer = tmp_path / "consumer"

    exit_code = module.main(
        [
            "--commit",
            COMMIT_B,
            "--output-dir",
            str(tmp_path / "out"),
            "--approved-by",
            "owner",
            "--source-commit-reviewed",
            "--consumer-root",
            str(consumer),
        ]
    )
    summary = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert calls["build"]["commit"] == COMMIT_B
    assert calls["build"]["source_commit_reviewed"] is True
    assert calls["build"]["approved_at"].endswith("Z")
    assert calls["publish"]["receipt_path"] == _StubBuild.receipt_path
    assert calls["publish"]["channel"] == "private-alpha"
    assert calls["publish"]["expected_receipt_sha256"] == _StubBuild.receipt_sha256
    assert calls["publish"]["expected_wheel_sha256"] == _StubBuild.wheel_sha256
    assert calls["install"]["receipt_path"] == published.receipt_path
    assert calls["install"]["expected_receipt_sha256"] == _StubBuild.receipt_sha256
    assert calls["install"]["expected_wheel_sha256"] == _StubBuild.wheel_sha256
    assert calls["workflow"]["receipt_path"] == published.receipt_path
    assert calls["workflow"]["executable"] == installed.executable
    assert calls["workflow"]["skill_destination"] == Path.home() / ".claude/skills/meeting-ingest/SKILL.md"
    assert calls["consumers"]["roots"] == [consumer]
    assert calls["consumers"]["executable"] == installed.executable
    assert summary["status"] == "success"
    assert summary["publish"]["build_id"] == BUILD_B
    assert summary["install"]["command"][:4] == ["uv", "tool", "install", "--reinstall"]
    assert summary["consumers"][0]["root"] == str(consumer)
    assert "meeting-ingest update" in summary["next_step"]


def test_release_script_never_defaults_the_review_attestation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: dict[str, Any] = {}
    module, _, _ = _stub_release_module(monkeypatch, tmp_path, calls)

    module.main(
        [
            "--commit",
            COMMIT_B,
            "--output-dir",
            str(tmp_path / "out"),
            "--approved-by",
            "owner",
        ]
    )

    assert calls["build"]["source_commit_reviewed"] is False


def test_release_script_names_the_consumer_command_when_no_root_is_given(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: dict[str, Any] = {}
    module, _, _ = _stub_release_module(monkeypatch, tmp_path, calls)

    exit_code = module.main(
        [
            "--commit",
            COMMIT_B,
            "--output-dir",
            str(tmp_path / "out"),
            "--approved-by",
            "owner",
            "--source-commit-reviewed",
        ]
    )
    summary = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert calls["consumers"]["roots"] == []
    assert summary["consumers"] == []
    assert "meeting-ingest update --root <consumer-root>" in summary["next_step"]
