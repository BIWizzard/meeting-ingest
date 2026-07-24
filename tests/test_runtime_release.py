from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from meeting_ingest._build_info import BUILD_INFO
from meeting_ingest.runtime_config import read_channel, read_pin, sha256_file
from meeting_ingest.runtime_release import (
    APPROVED_EXECUTABLE_MARKER,
    RuntimeReleaseError,
    _channel_lock,
    install_workflow_artifacts,
    pin_runtime,
    publish_approved_runtime,
    update_check,
)


def _digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _release(
    root: Path,
    *,
    build_id: str = "meeting-ingest-0.1.0-gaaaaaaaaaaaa-sbbbbbbbbbbbb",
    commit: str = "a" * 40,
    tree_character: str = "b",
) -> tuple[Path, Path, Path, Path]:
    release = root / build_id
    release.mkdir(parents=True)
    wheel = release / "meeting_ingest-0.1.0-py3-none-any.whl"
    wheel.write_bytes(f"wheel:{build_id}".encode())
    skill = release / "SKILL.md"
    agent = release / "agent.md"
    skill.write_text(f"Run {APPROVED_EXECUTABLE_MARKER} session-inbox --json\n", encoding="utf-8")
    agent.write_text("approved agent\n", encoding="utf-8")
    receipt = {
        "schema_version": "1.0",
        "build": {
            "semantic_version": "0.1.0",
            "build_id": build_id,
            "source_commit": commit,
            "source_tree_sha256": "sha256:" + tree_character * 64,
            "wheel_filename": wheel.name,
            "wheel_sha256": _digest(wheel),
        },
        "workflow": {
            "contract_version": "claude-code-session-v1",
            "claude_skill_template_sha256": _digest(skill),
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
    receipt_path = release / "receipt.json"
    receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
    return receipt_path, wheel, skill, agent


def test_install_workflow_artifacts_renders_skill_and_copies_agent(tmp_path: Path) -> None:
    receipt, _, template, agent = _release(tmp_path / "artifacts")
    executable = tmp_path / "bin/meeting-ingest"
    skill_destination = tmp_path / "installed/skills/meeting-ingest/SKILL.md"
    agent_destination = tmp_path / "installed/agents/meeting-ingest.md"

    result = install_workflow_artifacts(
        receipt,
        template_path=template,
        executable=str(executable),
        skill_destination=skill_destination,
        agent_path=agent,
        agent_destination=agent_destination,
    )

    expected_skill = f"Run {executable} session-inbox --json\n".encode()
    assert skill_destination.read_bytes() == expected_skill
    assert agent_destination.read_bytes() == agent.read_bytes()
    assert result.build_id == "meeting-ingest-0.1.0-gaaaaaaaaaaaa-sbbbbbbbbbbbb"
    assert result.skill_destination == skill_destination
    assert result.rendered_skill_sha256 == "sha256:" + hashlib.sha256(expected_skill).hexdigest()
    assert result.agent_destination == agent_destination
    assert result.agent_sha256 == _digest(agent)


def test_install_workflow_artifacts_rejects_template_hash_mismatch(tmp_path: Path) -> None:
    receipt, _, template, agent = _release(tmp_path / "artifacts")
    template.write_text("changed\n", encoding="utf-8")
    skill_destination = tmp_path / "installed/SKILL.md"
    agent_destination = tmp_path / "installed/agent.md"

    with pytest.raises(RuntimeReleaseError) as error:
        install_workflow_artifacts(
            receipt,
            template_path=template,
            executable="/opt/meeting-ingest",
            skill_destination=skill_destination,
            agent_path=agent,
            agent_destination=agent_destination,
        )

    assert error.value.code == "workflow_template_hash_mismatch"
    assert not skill_destination.exists()
    assert not agent_destination.exists()


@pytest.mark.parametrize(
    "template_text",
    [
        "Run meeting-ingest session-inbox --json\n",
        (
            f"Run {APPROVED_EXECUTABLE_MARKER} session-inbox --json\n"
            f"Then {APPROVED_EXECUTABLE_MARKER} reconcile\n"
        ),
    ],
)
def test_install_workflow_artifacts_rejects_invalid_template_marker(
    tmp_path: Path, template_text: str
) -> None:
    receipt, _, template, agent = _release(tmp_path / "artifacts")
    template.write_text(template_text, encoding="utf-8")
    receipt_value = json.loads(receipt.read_text(encoding="utf-8"))
    receipt_value["workflow"]["claude_skill_template_sha256"] = _digest(template)
    receipt.write_text(json.dumps(receipt_value, sort_keys=True) + "\n", encoding="utf-8")
    skill_destination = tmp_path / "installed/SKILL.md"
    agent_destination = tmp_path / "installed/agent.md"

    with pytest.raises(RuntimeReleaseError) as error:
        install_workflow_artifacts(
            receipt,
            template_path=template,
            executable="/opt/meeting-ingest",
            skill_destination=skill_destination,
            agent_path=agent,
            agent_destination=agent_destination,
        )

    assert error.value.code == "workflow_template_marker_invalid"
    assert not skill_destination.exists()
    assert not agent_destination.exists()


def test_install_workflow_artifacts_rejects_relative_executable(tmp_path: Path) -> None:
    receipt, _, template, agent = _release(tmp_path / "artifacts")
    skill_destination = tmp_path / "installed/SKILL.md"
    agent_destination = tmp_path / "installed/agent.md"

    with pytest.raises(RuntimeReleaseError) as error:
        install_workflow_artifacts(
            receipt,
            template_path=template,
            executable="bin/meeting-ingest",
            skill_destination=skill_destination,
            agent_path=agent,
            agent_destination=agent_destination,
        )

    assert error.value.code == "workflow_executable_invalid"
    assert not skill_destination.exists()
    assert not agent_destination.exists()


def test_install_workflow_artifacts_validates_agent_before_writing_skill(tmp_path: Path) -> None:
    receipt, _, template, agent = _release(tmp_path / "artifacts")
    agent.write_text("changed agent\n", encoding="utf-8")
    skill_destination = tmp_path / "installed/SKILL.md"
    agent_destination = tmp_path / "installed/agent.md"

    with pytest.raises(RuntimeReleaseError) as error:
        install_workflow_artifacts(
            receipt,
            template_path=template,
            executable="/opt/meeting-ingest",
            skill_destination=skill_destination,
            agent_path=agent,
            agent_destination=agent_destination,
        )

    assert error.value.code == "workflow_agent_hash_mismatch"
    assert not skill_destination.exists()
    assert not agent_destination.exists()


def test_install_workflow_artifacts_requires_agent_destination(tmp_path: Path) -> None:
    receipt, _, template, agent = _release(tmp_path / "artifacts")
    skill_destination = tmp_path / "installed/SKILL.md"

    with pytest.raises(RuntimeReleaseError) as error:
        install_workflow_artifacts(
            receipt,
            template_path=template,
            executable="/opt/meeting-ingest",
            skill_destination=skill_destination,
            agent_path=agent,
        )

    assert error.value.code == "workflow_agent_arguments_invalid"
    assert not skill_destination.exists()


@pytest.mark.parametrize("existing_skill", [b"previous skill bytes\n", None])
def test_install_workflow_artifacts_rolls_back_skill_when_agent_replace_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    existing_skill: bytes | None,
) -> None:
    receipt, _, template, agent = _release(tmp_path / "artifacts")
    skill_destination = tmp_path / "installed/skills/SKILL.md"
    agent_destination = tmp_path / "installed/agents/agent.md"
    skill_destination.parent.mkdir(parents=True)
    if existing_skill is not None:
        skill_destination.write_bytes(existing_skill)
    original_replace = os.replace

    def fail_agent_replace(source: Path, destination: Path) -> None:
        if Path(destination) == agent_destination:
            raise PermissionError("agent destination is unwritable")
        original_replace(source, destination)

    monkeypatch.setattr(os, "replace", fail_agent_replace)

    with pytest.raises(PermissionError, match="agent destination is unwritable"):
        install_workflow_artifacts(
            receipt,
            template_path=template,
            executable="/opt/meeting-ingest",
            skill_destination=skill_destination,
            agent_path=agent,
            agent_destination=agent_destination,
        )

    if existing_skill is None:
        assert not skill_destination.exists()
    else:
        assert skill_destination.read_bytes() == existing_skill
    assert not agent_destination.exists()
    assert not any(path.name.endswith(".pending") for path in skill_destination.parent.iterdir())
    assert not any(path.name.endswith(".pending") for path in agent_destination.parent.iterdir())


def test_git_hooks_do_not_reinstall_global_tools() -> None:
    hook_root = Path(__file__).parents[1] / "scripts/git-hooks"
    forbidden = ("uv tool install", "pip install", "--reinstall")

    for hook in hook_root.iterdir():
        if hook.is_file():
            contents = hook.read_text(encoding="utf-8")
            assert all(command not in contents for command in forbidden), hook


def test_publish_retains_prior_release_and_atomically_advances_channel(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    first_receipt, _, _, _ = _release(artifacts)
    second_id = "meeting-ingest-0.1.0-gcccccccccccc-sdddddddddddd"
    second_receipt, _, _, _ = _release(
        artifacts, build_id=second_id, commit="c" * 40, tree_character="d"
    )
    app_root = tmp_path / "app-data"

    first = publish_approved_runtime(
        first_receipt, application_data_root=app_root, published_at="2026-07-20T00:00:00Z"
    )
    second = publish_approved_runtime(
        second_receipt, application_data_root=app_root, published_at="2026-07-21T00:00:00Z"
    )
    channel = read_channel(app_root, "private-alpha")

    assert channel.valid is True
    assert channel.values["latest"]["build_id"] == second_id
    assert channel.values["previous"] == [
        {
            "build_id": first.build_id,
            "receipt_path": first.receipt_path.relative_to(app_root).as_posix(),
            "receipt_sha256": sha256_file(first.receipt_path),
        }
    ]
    assert first.receipt_path.is_file()
    assert first.wheel_path.is_file()
    assert second.previous_build_ids == (first.build_id,)


def test_publish_rejects_changed_bytes_for_existing_immutable_release(tmp_path: Path) -> None:
    receipt, _, _, _ = _release(tmp_path / "artifacts")
    app_root = tmp_path / "app-data"
    result = publish_approved_runtime(
        receipt, application_data_root=app_root, published_at="2026-07-20T00:00:00Z"
    )
    result.receipt_path.write_text("{}\n", encoding="utf-8")

    with pytest.raises(RuntimeReleaseError, match="different bytes"):
        publish_approved_runtime(
            receipt, application_data_root=app_root, published_at="2026-07-20T00:00:00Z"
        )


def test_publish_rejects_invalid_channel_before_copying_release_artifacts(tmp_path: Path) -> None:
    receipt, _, _, _ = _release(tmp_path / "artifacts")
    app_root = tmp_path / "app-data"
    channel_path = app_root / "channels/private-alpha.json"
    channel_path.parent.mkdir(parents=True)
    channel_path.write_text("{}\n", encoding="utf-8")

    with pytest.raises(RuntimeReleaseError) as error:
        publish_approved_runtime(
            receipt, application_data_root=app_root, published_at="2026-07-20T00:00:00Z"
        )

    assert error.value.code == "runtime_channel_invalid"
    assert not (app_root / "releases").exists()


def test_pin_bootstraps_only_pin_parent_after_verifying_build_and_workflow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipt, _, skill, agent = _release(tmp_path / "artifacts")
    receipt_value = json.loads(receipt.read_text(encoding="utf-8"))
    for key, value in {
        "semantic_version": receipt_value["build"]["semantic_version"],
        "build_id": receipt_value["build"]["build_id"],
        "source_commit": receipt_value["build"]["source_commit"],
        "source_tree_sha256": receipt_value["build"]["source_tree_sha256"],
        "workflow_contract_version": receipt_value["workflow"]["contract_version"],
        "build_kind": "approved-candidate",
    }.items():
        monkeypatch.setitem(BUILD_INFO, key, value)
    consumer = tmp_path / "consumer"
    app_root = tmp_path / "app-data"
    publish_approved_runtime(
        receipt, application_data_root=app_root, published_at="2026-07-20T00:00:00Z"
    )
    executable = tmp_path / "bin/meeting-ingest"
    executable.parent.mkdir()
    executable.write_text("#!/bin/sh\n", encoding="utf-8")
    skill.write_text(f"Run {executable.resolve()} session-inbox --json\n", encoding="utf-8")

    result = pin_runtime(
        consumer,
        receipt,
        approved_executable=executable,
        invoked_executable=executable,
        application_data_root=app_root,
        installed_skill_path=skill,
        claude_agent_path=agent,
    )
    pin = read_pin(consumer)

    assert pin.valid is True
    assert pin.values["approved_build_id"] == result.build_id
    assert pin.values["approved_executable"] == str(executable.resolve())
    assert pin.values["installed_claude_skill_sha256"] != pin.values["claude_skill_template_sha256"]
    assert list(consumer.iterdir()) == [consumer / "_local"]
    assert not (consumer / "_local/project-context/meetings/meeting-ingest.toml").exists()


def test_pin_rejects_running_build_mismatch_without_creating_consumer(tmp_path: Path) -> None:
    receipt, _, skill, agent = _release(tmp_path / "artifacts")
    consumer = tmp_path / "consumer"
    executable = tmp_path / "meeting-ingest"
    executable.write_text("#!/bin/sh\n", encoding="utf-8")

    with pytest.raises(RuntimeReleaseError, match="Running embedded build"):
        pin_runtime(
            consumer,
            receipt,
            approved_executable=executable,
            invoked_executable=executable,
            installed_skill_path=skill,
            claude_agent_path=agent,
        )

    assert not consumer.exists()


def test_pin_rejects_executable_that_did_not_invoke_the_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipt, _, skill, agent = _release(tmp_path / "artifacts")
    receipt_value = json.loads(receipt.read_text(encoding="utf-8"))
    for key, value in {
        "semantic_version": receipt_value["build"]["semantic_version"],
        "build_id": receipt_value["build"]["build_id"],
        "source_commit": receipt_value["build"]["source_commit"],
        "source_tree_sha256": receipt_value["build"]["source_tree_sha256"],
        "workflow_contract_version": receipt_value["workflow"]["contract_version"],
        "build_kind": "approved-candidate",
    }.items():
        monkeypatch.setitem(BUILD_INFO, key, value)
    app_root = tmp_path / "app-data"
    publish_approved_runtime(
        receipt, application_data_root=app_root, published_at="2026-07-20T00:00:00Z"
    )
    approved = tmp_path / "bin/approved"
    invoked = tmp_path / "bin/invoked"
    approved.parent.mkdir()
    approved.write_text("approved\n", encoding="utf-8")
    invoked.write_text("invoked\n", encoding="utf-8")

    with pytest.raises(RuntimeReleaseError) as error:
        pin_runtime(
            tmp_path / "consumer",
            receipt,
            approved_executable=approved,
            invoked_executable=invoked,
            application_data_root=app_root,
            installed_skill_path=skill,
            claude_agent_path=agent,
        )

    assert error.value.code == "runtime_executable_mismatch"


def test_pin_rejects_skill_changed_beyond_the_executable_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipt, _, skill, agent = _release(tmp_path / "artifacts")
    receipt_value = json.loads(receipt.read_text(encoding="utf-8"))
    for key, value in {
        "semantic_version": receipt_value["build"]["semantic_version"],
        "build_id": receipt_value["build"]["build_id"],
        "source_commit": receipt_value["build"]["source_commit"],
        "source_tree_sha256": receipt_value["build"]["source_tree_sha256"],
        "workflow_contract_version": receipt_value["workflow"]["contract_version"],
        "build_kind": "approved-candidate",
    }.items():
        monkeypatch.setitem(BUILD_INFO, key, value)
    app_root = tmp_path / "app-data"
    publish_approved_runtime(
        receipt, application_data_root=app_root, published_at="2026-07-20T00:00:00Z"
    )
    executable = tmp_path / "bin/meeting-ingest"
    executable.parent.mkdir()
    executable.write_text("#!/bin/sh\n", encoding="utf-8")
    skill.write_text(
        f"tampered\nRun {executable.resolve()} session-inbox --json\n", encoding="utf-8"
    )

    with pytest.raises(RuntimeReleaseError) as error:
        pin_runtime(
            tmp_path / "consumer",
            receipt,
            approved_executable=executable,
            invoked_executable=executable,
            application_data_root=app_root,
            installed_skill_path=skill,
            claude_agent_path=agent,
        )

    assert error.value.code == "workflow_hash_mismatch"
    assert not (tmp_path / "consumer").exists()


def test_publish_rejects_symlinked_receipt(tmp_path: Path) -> None:
    receipt, _, _, _ = _release(tmp_path / "artifacts")
    link = tmp_path / "receipt-link.json"
    link.symlink_to(receipt)

    with pytest.raises(RuntimeReleaseError) as error:
        publish_approved_runtime(
            link,
            application_data_root=tmp_path / "app-data",
            published_at="2026-07-20T00:00:00Z",
        )

    assert error.value.code == "runtime_receipt_invalid"


def test_publish_accumulates_three_generations_of_rollback_metadata(tmp_path: Path) -> None:
    app_root = tmp_path / "app-data"
    identifiers = [
        "meeting-ingest-0.1.0-gaaaaaaaaaaaa-sbbbbbbbbbbbb",
        "meeting-ingest-0.1.0-gcccccccccccc-sdddddddddddd",
        "meeting-ingest-0.1.0-geeeeeeeeeeee-sffffffffffff",
    ]
    for index, (build_id, commit, tree) in enumerate(
        zip(identifiers, ("a" * 40, "c" * 40, "e" * 40), ("b", "d", "f")), start=20
    ):
        receipt, _, _, _ = _release(
            tmp_path / f"artifacts-{index}", build_id=build_id, commit=commit, tree_character=tree
        )
        publish_approved_runtime(
            receipt,
            application_data_root=app_root,
            published_at=f"2026-07-{index:02d}T00:00:00Z",
        )

    channel = read_channel(app_root, "private-alpha")
    assert [entry["build_id"] for entry in channel.values["previous"]] == identifiers[1::-1]


def test_channel_lock_does_not_close_descriptors_opened_inside_critical_section(tmp_path: Path) -> None:
    victim_path = tmp_path / "victim.txt"
    with _channel_lock(tmp_path / "channel.lock"):
        victim = victim_path.open("wb")
        victim.write(b"before\n")

    victim.write(b"after\n")
    victim.close()
    assert victim_path.read_bytes() == b"before\nafter\n"


def test_update_check_is_read_only_and_reports_newer_channel(tmp_path: Path) -> None:
    consumer = tmp_path / "consumer"
    pin_path = consumer / "_local/project-context/meetings/meeting-ingest-runtime.toml"
    pin_path.parent.mkdir(parents=True)
    pin_values = {
        "schema_version": "1.0",
        "channel": "private-alpha",
        "approved_build_id": "meeting-ingest-0.1.0-gaaaaaaaaaaaa-sbbbbbbbbbbbb",
        "approved_source_commit": "a" * 40,
        "approved_source_tree_sha256": "sha256:" + "b" * 64,
        "approved_wheel_sha256": "sha256:" + "c" * 64,
        "approved_receipt_sha256": "sha256:" + "d" * 64,
        "approved_executable": "/opt/meeting-ingest",
        "workflow_contract_version": "claude-code-session-v1",
        "claude_skill_template_sha256": "sha256:" + "e" * 64,
        "installed_claude_skill_sha256": "sha256:" + "f" * 64,
        "claude_agent_sha256": "sha256:" + "1" * 64,
        "approved_at": "2026-07-20T00:00:00Z",
    }
    from meeting_ingest.runtime_config import serialize_pin

    pin_path.write_bytes(serialize_pin(pin_values))
    newer_receipt, _, _, _ = _release(
        tmp_path / "artifacts",
        build_id="meeting-ingest-0.1.0-gcccccccccccc-sdddddddddddd",
        commit="c" * 40,
        tree_character="d",
    )
    app_root = tmp_path / "app-data"
    publish_approved_runtime(
        newer_receipt, application_data_root=app_root, published_at="2026-07-21T00:00:00Z"
    )
    before = {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}

    summary = update_check(consumer, application_data_root=app_root)

    after = {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    assert summary.details["update_available"] is True
    assert summary.details["comparisons"]["channel_to_pin_build"] is False
    assert before == after
