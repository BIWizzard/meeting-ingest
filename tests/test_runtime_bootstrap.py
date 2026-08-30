from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
from pathlib import Path
from typing import Any

import pytest

from meeting_ingest import pipeline, runtime_release
from meeting_ingest._build_info import BUILD_INFO
from meeting_ingest.cli import emit, main
from meeting_ingest.paths import init_project
from meeting_ingest.runtime import inspect_runtime
from meeting_ingest.runtime_config import read_pin
from meeting_ingest.runtime_release import (
    APPROVED_EXECUTABLE_MARKER,
    RuntimeReleaseError,
    bootstrap_consumer_runtime,
    packaged_workflow_templates,
    publish_approved_runtime,
)

VERSION = BUILD_INFO["semantic_version"]
BUILD_ID = f"meeting-ingest-{VERSION}-gaaaaaaaaaaaa-sbbbbbbbbbbbb"
COMMIT = "a" * 40
TREE = "sha256:" + "b" * 64
PIN_RELATIVE = Path("_local/project-context/meetings/meeting-ingest-runtime.toml")


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


class _ApprovedRelease:
    """One published release whose receipt approves the real packaged templates."""

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

        self.templates = packaged_workflow_templates()
        artifacts = tmp_path / "artifacts"
        artifacts.mkdir()
        wheel = artifacts / f"meeting_ingest-{VERSION}-py3-none-any.whl"
        wheel.write_bytes(f"wheel:{BUILD_ID}".encode())
        receipt = {
            "schema_version": "1.0",
            "build": {
                "semantic_version": VERSION,
                "build_id": BUILD_ID,
                "source_commit": COMMIT,
                "source_tree_sha256": TREE,
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
        receipt_path = artifacts / "receipt.json"
        receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
        for key, value in {
            "build_id": BUILD_ID,
            "source_commit": COMMIT,
            "source_tree_sha256": TREE,
            "build_kind": "approved-candidate",
        }.items():
            monkeypatch.setitem(BUILD_INFO, key, value)

        self.app_root = tmp_path / "app-data"
        self.published = publish_approved_runtime(
            receipt_path, application_data_root=self.app_root, published_at="2026-08-30T00:00:00Z"
        )
        self.distribution, self.module, self.executable = _make_installation(
            tmp_path / "tool", direct_url=direct_url
        )

    def inspector(self, root: Path, **kwargs: Any):
        """Inspect with this release's install evidence and production path resolution."""
        arguments: dict[str, Any] = {
            "module_path": self.module,
            "distribution": self.distribution,
        }
        arguments.update(kwargs)
        return inspect_runtime(root, **arguments)

    def bootstrap(self, root: Path):
        return bootstrap_consumer_runtime(
            root,
            application_data_root=self.app_root,
            invoked_executable=self.executable,
            runtime_inspector=self.inspector,
        )

    def install_readiness_inspector(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Run the readiness guard against production workflow resolution."""
        monkeypatch.setattr("meeting_ingest.pipeline.bootstrap_consumer_runtime", self.bootstrap)
        monkeypatch.setattr(
            "meeting_ingest.readiness._RUNTIME_INSPECTOR",
            lambda root: self.inspector(
                root,
                invoked_path=self.executable,
                application_data_root=self.app_root,
                receipt_path=self.published.receipt_path,
            ),
        )

    def rendered_skill(self) -> bytes:
        return self.templates.skill_template.read_bytes().replace(
            APPROVED_EXECUTABLE_MARKER.encode("utf-8"),
            str(self.executable.resolve()).encode("utf-8"),
            1,
        )


def test_bootstrap_renders_pins_and_records_the_packaged_workflow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    release = _ApprovedRelease(tmp_path, monkeypatch)
    consumer = tmp_path / "consumer"

    result = release.bootstrap(consumer)
    pin = read_pin(consumer)

    assert result.build_id == BUILD_ID
    assert result.executable == release.executable.resolve()
    assert result.skill_destination == consumer / ".claude/skills/meeting-ingest/SKILL.md"
    assert result.skill_destination.read_bytes() == release.rendered_skill()
    assert result.agent_destination.read_bytes() == release.templates.claude_agent.read_bytes()
    assert pin.valid is True
    assert pin.values["approved_build_id"] == BUILD_ID
    assert pin.values["approved_executable"] == str(release.executable.resolve())
    assert pin.values["installed_claude_skill_sha256"] == _digest(result.skill_destination)
    assert pin.values["claude_agent_sha256"] == _digest(release.templates.claude_agent)


def test_init_bootstraps_a_virgin_project_under_production_workflow_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    release = _ApprovedRelease(tmp_path, monkeypatch)
    consumer = tmp_path / "consumer"
    release.install_readiness_inspector(monkeypatch)

    exit_code = main(["init", "--root", str(consumer), "--json"])
    summary = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert summary["verdict"] == "ready"
    assert summary["runtime_provenance"]["runtime_mode"] == "approved"
    assert summary["bootstrapped_runtime"] is True
    assert summary["approved_build_id"] == BUILD_ID
    assert (consumer / "_local/project-context/meetings/_inbox").is_dir()
    assert (consumer / ".claude/skills/meeting-ingest/SKILL.md").read_bytes() == release.rendered_skill()


def test_init_prints_the_ready_experience_and_the_pinned_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    release = _ApprovedRelease(tmp_path, monkeypatch)
    consumer = tmp_path / "consumer"
    release.install_readiness_inspector(monkeypatch)

    emit(pipeline.initialize(consumer), as_json=False)

    assert capsys.readouterr().out == (
        "Ready\n"
        f"Meetings root: {consumer / '_local/project-context/meetings'}\n"
        f"Approved build: {BUILD_ID}\n"
    )


def test_bootstrap_names_the_searched_store_when_nothing_is_published(tmp_path: Path) -> None:
    app_root = tmp_path / "app-data"
    consumer = tmp_path / "consumer"

    with pytest.raises(RuntimeReleaseError) as error:
        bootstrap_consumer_runtime(
            consumer,
            application_data_root=app_root,
            invoked_executable=tmp_path / "bin/meeting-ingest",
        )

    assert error.value.code == "approved_runtime_unavailable"
    assert str(app_root) in error.value.message
    assert "publish-approved-runtime" in error.value.details["remediation"]
    assert not consumer.exists()


def test_bootstrap_refuses_an_editable_install_without_writing_anything(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    (source / "src/meeting_ingest").mkdir(parents=True)
    release = _ApprovedRelease(
        tmp_path,
        monkeypatch,
        direct_url={"url": source.as_uri(), "dir_info": {"editable": True}},
    )
    consumer = tmp_path / "consumer"

    with pytest.raises(RuntimeReleaseError) as error:
        release.bootstrap(consumer)

    assert error.value.code == "runtime_editable_blocked"
    assert "--development-override" in error.value.details["remediation"]
    assert not consumer.exists()


def test_bootstrap_refuses_a_running_build_the_receipt_does_not_approve(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    release = _ApprovedRelease(tmp_path, monkeypatch)
    monkeypatch.setitem(BUILD_INFO, "source_commit", "c" * 40)
    consumer = tmp_path / "consumer"

    with pytest.raises(RuntimeReleaseError) as error:
        release.bootstrap(consumer)

    assert error.value.code == "runtime_build_mismatch"
    assert not consumer.exists()


def test_bootstrap_refuses_a_wrapper_that_is_not_the_approved_console_script(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    release = _ApprovedRelease(tmp_path, monkeypatch)
    wrapper = tmp_path / "wrapper/meeting-ingest"
    wrapper.parent.mkdir()
    wrapper.write_text("#!/bin/sh\nexec python -m meeting_ingest.cli \"$@\"\n", encoding="utf-8")
    consumer = tmp_path / "consumer"

    with pytest.raises(RuntimeReleaseError) as error:
        bootstrap_consumer_runtime(
            consumer,
            application_data_root=release.app_root,
            invoked_executable=wrapper,
            runtime_inspector=release.inspector,
        )

    assert error.value.code == "runtime_executable_mismatch"
    assert str(release.executable.resolve()) in error.value.message
    assert not consumer.exists()


def test_bootstrap_refuses_a_console_script_the_distribution_does_not_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    release = _ApprovedRelease(tmp_path, monkeypatch)
    record = Path(release.distribution._path) / "RECORD"
    kept = [row for row in record.read_text(encoding="utf-8").splitlines() if "bin/" not in row]
    record.write_text("\n".join(kept) + "\n", encoding="utf-8")
    consumer = tmp_path / "consumer"

    with pytest.raises(RuntimeReleaseError) as error:
        release.bootstrap(consumer)

    assert error.value.code == "runtime_executable_unidentified"
    assert not consumer.exists()


@pytest.mark.parametrize("damage", ["missing", "mismatched"])
def test_bootstrap_requires_the_published_wheel_beside_the_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, damage: str
) -> None:
    release = _ApprovedRelease(tmp_path, monkeypatch)
    wheel = release.published.wheel_path
    if damage == "missing":
        wheel.unlink()
    else:
        wheel.write_bytes(b"replaced wheel\n")
    consumer = tmp_path / "consumer"

    with pytest.raises(RuntimeReleaseError) as error:
        release.bootstrap(consumer)

    assert error.value.code in {"approved_runtime_unavailable", "runtime_wheel_invalid"}
    assert not consumer.exists()


def test_bootstrap_refuses_a_receipt_swapped_after_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    release = _ApprovedRelease(tmp_path, monkeypatch)
    receipt_path = release.published.receipt_path
    original = runtime_release.packaged_workflow_templates

    def swap_then_resolve():
        value = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt_path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        return original()

    monkeypatch.setattr(runtime_release, "packaged_workflow_templates", swap_then_resolve)
    consumer = tmp_path / "consumer"

    with pytest.raises(RuntimeReleaseError) as error:
        release.bootstrap(consumer)

    assert error.value.code == "runtime_receipt_invalid"
    assert "changed between verification stages" in error.value.message
    assert not (consumer / ".claude").exists()


def test_bootstrap_refuses_a_symlinked_release_store_component(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    release = _ApprovedRelease(tmp_path, monkeypatch)
    channels = release.app_root / "channels"
    relocated = tmp_path / "elsewhere-channels"
    channels.rename(relocated)
    channels.symlink_to(relocated)
    consumer = tmp_path / "consumer"

    with pytest.raises(RuntimeReleaseError) as error:
        release.bootstrap(consumer)

    assert error.value.code == "runtime_path_unsafe"
    assert not consumer.exists()


def test_bootstrap_refuses_a_symlinked_destination_ancestor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    release = _ApprovedRelease(tmp_path, monkeypatch)
    consumer = tmp_path / "consumer"
    outside = tmp_path / "outside-claude"
    outside.mkdir()
    consumer.mkdir()
    (consumer / ".claude").symlink_to(outside)

    with pytest.raises(RuntimeReleaseError) as error:
        release.bootstrap(consumer)

    assert error.value.code == "runtime_path_unsafe"
    assert not (consumer / PIN_RELATIVE).exists()
    assert list(outside.iterdir()) == []


def test_bootstrap_refuses_a_shadowing_copy_that_hides_the_installed_workflow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    release = _ApprovedRelease(tmp_path, monkeypatch)
    consumer = tmp_path / "consumer"

    def resolve_to_a_stale_user_copy(root: Path, **kwargs: Any):
        stale = release.home / ".claude/skills/meeting-ingest/SKILL.md"
        stale.parent.mkdir(parents=True, exist_ok=True)
        stale.write_text("stale user-level skill\n", encoding="utf-8")
        return release.inspector(root, skill_path=stale, **kwargs)

    with pytest.raises(RuntimeReleaseError) as error:
        bootstrap_consumer_runtime(
            consumer,
            application_data_root=release.app_root,
            invoked_executable=release.executable,
            runtime_inspector=resolve_to_a_stale_user_copy,
        )

    assert error.value.code == "workflow_hash_mismatch"
    assert not (consumer / PIN_RELATIVE).exists()


def test_bootstrap_does_not_clobber_a_pin_created_concurrently(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    release = _ApprovedRelease(tmp_path, monkeypatch)
    consumer = tmp_path / "consumer"
    concurrent = b'schema_version = "1.0"\n# written by another process\n'
    original = runtime_release.install_workflow_artifacts

    def install_then_race(*args: Any, **kwargs: Any):
        result = original(*args, **kwargs)
        pin_path = consumer / PIN_RELATIVE
        pin_path.parent.mkdir(parents=True, exist_ok=True)
        pin_path.write_bytes(concurrent)
        return result

    monkeypatch.setattr(runtime_release, "install_workflow_artifacts", install_then_race)

    with pytest.raises(RuntimeReleaseError) as error:
        release.bootstrap(consumer)

    assert error.value.code == "runtime_pin_present"
    assert (consumer / PIN_RELATIVE).read_bytes() == concurrent


def test_init_converges_after_a_run_that_installed_artifacts_without_a_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    release = _ApprovedRelease(tmp_path, monkeypatch)
    consumer = tmp_path / "consumer"
    release.install_readiness_inspector(monkeypatch)

    interrupt = {"active": True}
    real_pin_runtime = runtime_release.pin_runtime

    def fail_before_pinning(*args: Any, **kwargs: Any):
        if interrupt["active"]:
            raise OSError("interrupted before the pin was written")
        return real_pin_runtime(*args, **kwargs)

    monkeypatch.setattr(runtime_release, "pin_runtime", fail_before_pinning)
    with pytest.raises(OSError):
        pipeline.initialize(consumer)
    assert (consumer / ".claude/skills/meeting-ingest/SKILL.md").is_file()
    assert not (consumer / PIN_RELATIVE).exists()

    interrupt["active"] = False
    summary = pipeline.initialize(consumer)

    assert summary.details["bootstrapped_runtime"] is True
    assert read_pin(consumer).valid is True


def test_init_removes_its_own_pin_when_a_later_step_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    release = _ApprovedRelease(tmp_path, monkeypatch)
    consumer = tmp_path / "consumer"
    release.install_readiness_inspector(monkeypatch)

    def fail_after_pinning(project_root: Path):
        raise OSError("interrupted while scaffolding")

    monkeypatch.setattr("meeting_ingest.pipeline.init_project", fail_after_pinning)
    with pytest.raises(OSError):
        pipeline.initialize(consumer)
    assert not (consumer / PIN_RELATIVE).exists()

    monkeypatch.setattr("meeting_ingest.pipeline.init_project", init_project)
    summary = pipeline.initialize(consumer)

    assert summary.details["bootstrapped_runtime"] is True
    assert read_pin(consumer).valid is True


def test_init_rollback_spares_a_pin_replaced_by_another_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    release = _ApprovedRelease(tmp_path, monkeypatch)
    consumer = tmp_path / "consumer"
    release.install_readiness_inspector(monkeypatch)
    replaced = b'schema_version = "1.0"\n# explicit repin by another process\n'

    def swap_pin_then_fail(project_root: Path):
        (consumer / PIN_RELATIVE).write_bytes(replaced)
        raise OSError("interrupted while scaffolding")

    monkeypatch.setattr("meeting_ingest.pipeline.init_project", swap_pin_then_fail)
    with pytest.raises(OSError):
        pipeline.initialize(consumer)

    assert (consumer / PIN_RELATIVE).read_bytes() == replaced


def test_init_never_touches_an_existing_pin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    release = _ApprovedRelease(tmp_path, monkeypatch)
    consumer = tmp_path / "consumer"
    release.bootstrap(consumer)
    before = (consumer / PIN_RELATIVE).read_bytes()

    def forbidden(root: Path):
        raise AssertionError("init must not bootstrap over an existing pin")

    monkeypatch.setattr("meeting_ingest.pipeline.bootstrap_consumer_runtime", forbidden)
    summary = pipeline.initialize(consumer)

    assert summary.details["bootstrapped_runtime"] is False
    assert (consumer / PIN_RELATIVE).read_bytes() == before


def test_bootstrap_refuses_a_consumer_that_already_carries_a_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    release = _ApprovedRelease(tmp_path, monkeypatch)
    consumer = tmp_path / "consumer"
    release.bootstrap(consumer)
    before = (consumer / PIN_RELATIVE).read_bytes()

    with pytest.raises(RuntimeReleaseError) as error:
        release.bootstrap(consumer)

    assert error.value.code == "runtime_pin_present"
    assert (consumer / PIN_RELATIVE).read_bytes() == before


def test_development_override_scaffolds_without_selecting_a_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from meeting_ingest.readiness import DevelopmentOverride

    def forbidden(root: Path):
        raise AssertionError("--development-override must not auto-bootstrap")

    monkeypatch.setattr("meeting_ingest.pipeline.bootstrap_consumer_runtime", forbidden)
    summary = pipeline.initialize(tmp_path, development_override=DevelopmentOverride("local test"))
    emit(summary, as_json=False)

    assert summary.details["verdict"] == "development_override"
    assert summary.details["bootstrapped_runtime"] is False
    assert summary.details["approved_build_id"] is None
    assert not (tmp_path / PIN_RELATIVE).exists()
    assert (tmp_path / "_local/project-context/meetings/_inbox").is_dir()
    assert capsys.readouterr().out == (
        "Scaffolded (development override)\n"
        "Development reason: local test\n"
        f"Meetings root: {tmp_path / '_local/project-context/meetings'}\n"
    )


def test_packaged_workflow_templates_ship_the_marker_exactly_once() -> None:
    templates = packaged_workflow_templates()

    assert templates.skill_template.is_file()
    assert templates.claude_agent.is_file()
    assert templates.skill_template.read_text(encoding="utf-8").count(APPROVED_EXECUTABLE_MARKER) == 1
    assert APPROVED_EXECUTABLE_MARKER not in templates.claude_agent.read_text(encoding="utf-8")
