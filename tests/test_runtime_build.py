from __future__ import annotations

from pathlib import Path

import hashlib
import io
import json
import os
import subprocess
import tarfile
import tomllib
import zipfile

import pytest

import meeting_ingest.runtime_build as runtime_build
from meeting_ingest._build_info import BUILD_INFO
from meeting_ingest.runtime_build import (
    ArchivedSource,
    BUILD_INFO_PATH,
    BuildIdentity,
    RuntimeBuildError,
    VerificationEvidence,
    build_approved_runtime,
    build_wheel,
    create_receipt,
    extract_git_archive,
    make_build_identity,
    prepare_archived_source,
    render_build_info,
    run_full_suite,
    source_tree_paths,
    source_tree_sha256,
    validate_exact_commit,
    verify_wheel,
)


def _write(root: Path, relative: str, payload: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def _minimal_source(root: Path) -> None:
    _write(
        root,
        "pyproject.toml",
        """[build-system]
requires = ["setuptools==80.9.0"]
build-backend = "setuptools.build_meta"

[project]
name = "meeting-ingest"
version = "0.1.0"
""",
    )
    _write(root, "src/meeting_ingest/__init__.py", '"""Package."""\n')
    _write(root, "src/meeting_ingest/_build_info.py", "BUILD_INFO = {'build_id': 'development'}\n")
    _write(root, "docs/artifact-contract.md", "artifact contract\n")
    _write(root, "docs/provider-handoff-contract.md", "handoff contract\n")
    _write(root, "docs/claude-skills/meeting-ingest/SKILL.md", "skill template\n")
    _write(root, "docs/claude-agents/meeting-ingest-session-provider.md", "agent definition\n")


def _identity(root: Path) -> BuildIdentity:
    return make_build_identity(root, "a" * 40)


def _verification(**overrides: bool) -> VerificationEvidence:
    values = {
        "source_commit_reviewed": True,
        "full_suite_passed": True,
        "reproducible_wheel_verified": True,
    }
    values.update(overrides)
    return VerificationEvidence(**values)


def test_embedded_build_info_is_valid_for_its_context() -> None:
    project_root = Path(__file__).resolve().parents[1]
    project_version = tomllib.loads((project_root / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "version"
    ]
    assert BUILD_INFO["schema_version"] == "1.0"
    assert BUILD_INFO["semantic_version"] == project_version
    assert BUILD_INFO["workflow_contract_version"] == "claude-code-session-v1"
    if BUILD_INFO["build_kind"] == "development":
        assert BUILD_INFO["build_id"] == "development"
        assert BUILD_INFO["source_commit"] is None
        assert BUILD_INFO["source_tree_sha256"] is None
    else:
        assert BUILD_INFO["build_kind"] == "approved-candidate"
        assert BUILD_INFO["build_id"].startswith(f"meeting-ingest-{project_version}-g")
        assert len(BUILD_INFO["source_commit"]) == 40
        assert BUILD_INFO["source_tree_sha256"].startswith("sha256:")


def test_source_tree_digest_uses_frozen_sorted_path_length_bytes_shape(tmp_path: Path) -> None:
    _minimal_source(tmp_path)

    paths = source_tree_paths(tmp_path)
    digest = hashlib.sha256()
    for relative in paths:
        payload = (tmp_path / relative).read_bytes()
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(len(payload)).encode("ascii"))
        digest.update(b"\0")
        digest.update(payload)

    assert tuple(path.as_posix() for path in paths) == tuple(
        sorted((path.as_posix() for path in paths), key=lambda value: value.encode("utf-8"))
    )
    assert source_tree_sha256(tmp_path) == f"sha256:{digest.hexdigest()}"


def test_source_tree_digest_rejects_symlink_below_package(tmp_path: Path) -> None:
    _minimal_source(tmp_path)
    (tmp_path / "src/meeting_ingest/link.py").symlink_to(tmp_path / "src/meeting_ingest/__init__.py")

    with pytest.raises(RuntimeBuildError, match="Symlink below required directory"):
        source_tree_sha256(tmp_path)


def test_source_tree_digest_rejects_generated_package_content(tmp_path: Path) -> None:
    _minimal_source(tmp_path)
    _write(tmp_path, "src/meeting_ingest/__pycache__/module.pyc", "generated")

    with pytest.raises(RuntimeBuildError, match="Unexpected generated path"):
        source_tree_sha256(tmp_path)


def test_source_tree_digest_rejects_missing_required_input(tmp_path: Path) -> None:
    _minimal_source(tmp_path)
    (tmp_path / "docs/artifact-contract.md").unlink()

    with pytest.raises(RuntimeBuildError, match="Required tracked regular file"):
        source_tree_sha256(tmp_path)


def test_identity_and_generated_module_follow_frozen_contract(tmp_path: Path) -> None:
    _minimal_source(tmp_path)

    identity = _identity(tmp_path)

    assert identity.build_id == (
        f"meeting-ingest-0.1.0-gaaaaaaaaaaaa-s{identity.source_tree_sha256[7:19]}"
    )
    assert identity.build_kind == "approved-candidate"
    assert b'"source_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"' in render_build_info(identity)


def test_validate_exact_commit_rejects_symbolic_ref(tmp_path: Path) -> None:
    with pytest.raises(RuntimeBuildError, match="literal 40-character"):
        validate_exact_commit(tmp_path, "HEAD")


@pytest.mark.parametrize("name", ["../escape", "/absolute", "bad\\path", "a/../b", "a//b"])
def test_archive_name_rejects_unsafe_or_non_normalized_paths(name: str) -> None:
    with pytest.raises(RuntimeBuildError):
        runtime_build._safe_archive_name(name)


def test_git_archive_uses_injected_runner_and_rejects_symlink(tmp_path: Path) -> None:
    archive_bytes = io.BytesIO()
    with tarfile.open(fileobj=archive_bytes, mode="w") as archive:
        member = tarfile.TarInfo("unsafe-link")
        member.type = tarfile.SYMTYPE
        member.linkname = "target"
        archive.addfile(member)
    calls: list[list[str]] = []

    def fake_runner(args: list[str], **_: object) -> subprocess.CompletedProcess[bytes]:
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, stdout=archive_bytes.getvalue(), stderr=b"")

    with pytest.raises(RuntimeBuildError, match="non-regular entry"):
        extract_git_archive(tmp_path, "a" * 40, tmp_path / "archive", runner=fake_runner)

    assert calls == [["git", "archive", "--format=tar", "a" * 40]]


def test_prepare_archived_source_ignores_dirty_worktree(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _minimal_source(repo)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "test fixture"],
        cwd=repo,
        check=True,
        env={
            **os.environ,
            "GIT_AUTHOR_DATE": "2026-07-20T00:00:00Z",
            "GIT_COMMITTER_DATE": "2026-07-20T00:00:00Z",
        },
    )
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    committed_digest = source_tree_sha256(repo)
    _write(repo, "src/meeting_ingest/uncommitted.py", "must not be archived\n")

    archived = prepare_archived_source(repo, commit, tmp_path / "archive")

    assert archived.identity.source_tree_sha256 == committed_digest
    assert not (archived.root / "src/meeting_ingest/uncommitted.py").exists()
    assert (archived.root / BUILD_INFO_PATH).read_bytes() == render_build_info(archived.identity)


def test_real_setuptools_wheel_verifies_identity_record_and_metadata(tmp_path: Path) -> None:
    root = tmp_path / "source"
    _minimal_source(root)
    identity = _identity(root)
    (root / BUILD_INFO_PATH).write_bytes(render_build_info(identity))
    source = ArchivedSource(
        root=root,
        identity=identity,
        source_date_epoch=1784517600,
        claude_skill_template_sha256="sha256:" + "1" * 64,
        claude_agent_sha256="sha256:" + "2" * 64,
    )

    wheel = build_wheel(source, tmp_path / "dist")

    verify_wheel(wheel, identity, source.source_date_epoch)


def _rewrite_wheel_member(wheel: Path, member_name: str, transform: object) -> None:
    replacement = wheel.with_suffix(".replacement")
    with zipfile.ZipFile(wheel) as source, zipfile.ZipFile(replacement, "w") as target:
        for info in source.infolist():
            payload = source.read(info.filename)
            if info.filename == member_name:
                payload = transform(payload, info)  # type: ignore[operator]
            target.writestr(info, payload)
    os.replace(replacement, wheel)


def _built_wheel(tmp_path: Path) -> tuple[Path, BuildIdentity, ArchivedSource]:
    root = tmp_path / "source"
    _minimal_source(root)
    identity = _identity(root)
    (root / BUILD_INFO_PATH).write_bytes(render_build_info(identity))
    source = ArchivedSource(root, identity, 1784517600, "sha256:" + "1" * 64, "sha256:" + "2" * 64)
    return build_wheel(source, tmp_path / "dist"), identity, source


def test_wheel_verification_rejects_malformed_record(tmp_path: Path) -> None:
    wheel, identity, source = _built_wheel(tmp_path)
    record = f"meeting_ingest-{identity.semantic_version}.dist-info/RECORD"
    _rewrite_wheel_member(wheel, record, lambda payload, _: payload + b"\n")

    with pytest.raises(RuntimeBuildError, match="malformed row"):
        verify_wheel(wheel, identity, source.source_date_epoch)


def test_wheel_verification_rejects_record_hash_mismatch(tmp_path: Path) -> None:
    wheel, identity, source = _built_wheel(tmp_path)
    _rewrite_wheel_member(wheel, "meeting_ingest/__init__.py", lambda payload, _: payload + b"changed")

    with pytest.raises(RuntimeBuildError, match="RECORD mismatch"):
        verify_wheel(wheel, identity, source.source_date_epoch)


def test_wheel_verification_rejects_embedded_identity_mismatch(tmp_path: Path) -> None:
    wheel, identity, source = _built_wheel(tmp_path)
    _rewrite_wheel_member(wheel, "meeting_ingest/_build_info.py", lambda _payload, _: b"wrong")

    with pytest.raises(RuntimeBuildError, match="embedded build identity"):
        verify_wheel(wheel, identity, source.source_date_epoch)


def test_wheel_verification_rejects_distribution_metadata_mismatch(tmp_path: Path) -> None:
    wheel, identity, source = _built_wheel(tmp_path)
    metadata = f"meeting_ingest-{identity.semantic_version}.dist-info/METADATA"
    _rewrite_wheel_member(wheel, metadata, lambda payload, _: payload.replace(b"Version: 0.1.0", b"Version: 9.9.9"))

    with pytest.raises(RuntimeBuildError, match="METADATA name or version"):
        verify_wheel(wheel, identity, source.source_date_epoch)


def test_wheel_verification_rejects_non_normalized_timestamp(tmp_path: Path) -> None:
    wheel, identity, source = _built_wheel(tmp_path)

    def change_timestamp(payload: bytes, info: zipfile.ZipInfo) -> bytes:
        info.date_time = (2020, 1, 1, 0, 0, 0)
        return payload

    _rewrite_wheel_member(wheel, "meeting_ingest/__init__.py", change_timestamp)

    with pytest.raises(RuntimeBuildError, match="timestamp is not normalized"):
        verify_wheel(wheel, identity, source.source_date_epoch)


def test_wheel_verification_rejects_duplicate_entry(tmp_path: Path) -> None:
    root = tmp_path / "source"
    _minimal_source(root)
    identity = _identity(root)
    (root / BUILD_INFO_PATH).write_bytes(render_build_info(identity))
    source = ArchivedSource(root, identity, 1784517600, "sha256:" + "1" * 64, "sha256:" + "2" * 64)
    wheel = build_wheel(source, tmp_path / "dist")
    with pytest.warns(UserWarning, match="Duplicate name"):
        with zipfile.ZipFile(wheel, "a") as archive:
            archive.writestr("meeting_ingest/__init__.py", "duplicate")

    with pytest.raises(RuntimeBuildError, match="duplicate paths"):
        verify_wheel(wheel, identity, source.source_date_epoch)


def test_receipt_binds_wheel_identity_workflow_and_approval(tmp_path: Path) -> None:
    root = tmp_path / "source"
    _minimal_source(root)
    identity = _identity(root)
    (root / BUILD_INFO_PATH).write_bytes(render_build_info(identity))
    source = ArchivedSource(root, identity, 1784517600, "sha256:" + "1" * 64, "sha256:" + "2" * 64)
    wheel = build_wheel(source, tmp_path / "dist")

    receipt = create_receipt(
        source,
        wheel,
        verification=_verification(),
        approved_by="owner",
        approved_at="2026-07-20T00:00:00Z",
    )

    assert receipt["build"]["wheel_sha256"].startswith("sha256:")
    assert receipt["build"]["build_id"] == identity.build_id
    assert receipt["workflow"]["contract_version"] == "claude-code-session-v1"
    assert receipt["verification"] == {
        "source_commit_reviewed": True,
        "full_suite_passed": True,
        "reproducible_wheel_verified": True,
    }
    assert receipt["approved_at"] == "2026-07-20T00:00:00Z"
    json.dumps(receipt)


@pytest.mark.parametrize("approved_by, approved_at", [("", "2026-07-20T00:00:00Z"), ("owner", "2026-07-20")])
def test_receipt_rejects_incomplete_approval(
    tmp_path: Path, approved_by: str, approved_at: str
) -> None:
    root = tmp_path / "source"
    _minimal_source(root)
    identity = _identity(root)
    wheel = tmp_path / "runtime.whl"
    wheel.write_bytes(b"wheel")
    source = ArchivedSource(root, identity, 1784517600, "sha256:" + "1" * 64, "sha256:" + "2" * 64)

    with pytest.raises(RuntimeBuildError):
        create_receipt(
            source,
            wheel,
            verification=_verification(),
            approved_by=approved_by,
            approved_at=approved_at,
        )


@pytest.mark.parametrize(
    "missing",
    ["source_commit_reviewed", "full_suite_passed", "reproducible_wheel_verified"],
)
def test_receipt_rejects_incomplete_verification_evidence(tmp_path: Path, missing: str) -> None:
    root = tmp_path / "source"
    _minimal_source(root)
    source = ArchivedSource(root, _identity(root), 1784517600, "sha256:" + "1" * 64, "sha256:" + "2" * 64)
    wheel = tmp_path / "runtime.whl"
    wheel.write_bytes(b"wheel")

    with pytest.raises(RuntimeBuildError, match=missing):
        create_receipt(
            source,
            wheel,
            verification=_verification(**{missing: False}),
            approved_by="owner",
            approved_at="2026-07-20T00:00:00Z",
        )


def test_full_suite_failure_is_typed(tmp_path: Path) -> None:
    source = ArchivedSource(
        tmp_path,
        BuildIdentity("1.0", "0.1.0", "build", "a" * 40, "sha256:" + "0" * 64, "contract", "kind"),
        1784517600,
        "sha256:" + "1" * 64,
        "sha256:" + "2" * 64,
    )

    def failing_runner(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.CalledProcessError(1, ["pytest"], stderr="tests failed")

    with pytest.raises(RuntimeBuildError, match="tests failed"):
        run_full_suite(source, runner=failing_runner)


def _install_orchestrator_fakes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    wheel_payloads: tuple[bytes, bytes] = (b"same-wheel", b"same-wheel"),
    identities: tuple[BuildIdentity, BuildIdentity, BuildIdentity] | None = None,
    agent_hashes: tuple[str, str, str] | None = None,
) -> tuple[BuildIdentity, list[str]]:
    source_root = tmp_path / "identity-source"
    _minimal_source(source_root)
    identity = _identity(source_root)
    events: list[str] = []
    prepared = 0
    built = 0

    def fake_prepare(repo_root: Path, commit: str, destination: Path, **_: object) -> ArchivedSource:
        nonlocal prepared
        prepared += 1
        destination.mkdir(parents=True)
        events.append(f"prepare-{prepared}")
        selected_identity = identities[prepared - 1] if identities is not None else identity
        selected_agent_hash = agent_hashes[prepared - 1] if agent_hashes is not None else "sha256:" + "2" * 64
        return ArchivedSource(
            destination,
            selected_identity,
            1784517600,
            "sha256:" + "1" * 64,
            selected_agent_hash,
        )

    def fake_suite(source: ArchivedSource, **_: object) -> None:
        events.append("suite")

    def fake_build(source: ArchivedSource, output_dir: Path, **_: object) -> Path:
        nonlocal built
        output_dir.mkdir(parents=True)
        wheel = output_dir / "meeting_ingest-0.1.0-py3-none-any.whl"
        wheel.write_bytes(wheel_payloads[built])
        built += 1
        events.append(f"build-{built}")
        return wheel

    monkeypatch.setattr(runtime_build, "prepare_archived_source", fake_prepare)
    monkeypatch.setattr(runtime_build, "run_full_suite", fake_suite)
    monkeypatch.setattr(runtime_build, "build_wheel", fake_build)
    monkeypatch.setattr(runtime_build, "verify_wheel", lambda *args, **kwargs: None)
    return identity, events


def test_approval_orchestrator_requires_review_confirmation(tmp_path: Path) -> None:
    with pytest.raises(RuntimeBuildError, match="review confirmation"):
        build_approved_runtime(
            tmp_path,
            "a" * 40,
            tmp_path / "output",
            approved_by="owner",
            approved_at="2026-07-20T00:00:00Z",
            source_commit_reviewed=False,
        )


def test_approval_orchestrator_rejects_non_empty_output_directory(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    output = tmp_path / "output"
    output.mkdir()
    (output / "existing").write_text("keep", encoding="utf-8")

    with pytest.raises(RuntimeBuildError, match="absent or empty"):
        build_approved_runtime(
            repo,
            "a" * 40,
            output,
            approved_by="owner",
            approved_at="2026-07-20T00:00:00Z",
            source_commit_reviewed=True,
        )


def test_approval_orchestrator_runs_suite_then_two_builds_and_emits_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, events = _install_orchestrator_fakes(monkeypatch, tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()
    output = tmp_path / "output"

    result = build_approved_runtime(
        repo,
        "a" * 40,
        output,
        approved_by="owner",
        approved_at="2026-07-20T00:00:00Z",
        source_commit_reviewed=True,
    )

    assert events == ["prepare-1", "suite", "prepare-2", "build-1", "prepare-3", "build-2"]
    assert result.wheel_path.read_bytes() == b"same-wheel"
    receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))
    assert receipt["verification"] == {
        "source_commit_reviewed": True,
        "full_suite_passed": True,
        "reproducible_wheel_verified": True,
    }
    assert not tuple(output.glob("*.pending"))


def test_approval_orchestrator_rejects_different_wheels_without_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_orchestrator_fakes(monkeypatch, tmp_path, wheel_payloads=(b"wheel-a", b"wheel-b"))
    repo = tmp_path / "repo"
    repo.mkdir()
    output = tmp_path / "output"

    with pytest.raises(RuntimeBuildError, match="different wheel bytes"):
        build_approved_runtime(
            repo,
            "a" * 40,
            output,
            approved_by="owner",
            approved_at="2026-07-20T00:00:00Z",
            source_commit_reviewed=True,
        )

    assert not output.exists()


def test_approval_orchestrator_rejects_cross_archive_identity_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_root = tmp_path / "alternate-identity"
    _minimal_source(source_root)
    identity = _identity(source_root)
    different = BuildIdentity(
        **{**identity.as_dict(), "source_tree_sha256": "sha256:" + "9" * 64}
    )
    _install_orchestrator_fakes(monkeypatch, tmp_path, identities=(identity, identity, different))
    repo = tmp_path / "repo"
    repo.mkdir()

    with pytest.raises(RuntimeBuildError, match="different build identities"):
        build_approved_runtime(
            repo,
            "a" * 40,
            tmp_path / "output",
            approved_by="owner",
            approved_at="2026-07-20T00:00:00Z",
            source_commit_reviewed=True,
        )


def test_approval_orchestrator_rejects_cross_archive_workflow_evidence_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_orchestrator_fakes(
        monkeypatch,
        tmp_path,
        agent_hashes=("sha256:" + "2" * 64, "sha256:" + "2" * 64, "sha256:" + "3" * 64),
    )
    repo = tmp_path / "repo"
    repo.mkdir()

    with pytest.raises(RuntimeBuildError, match="different source evidence"):
        build_approved_runtime(
            repo,
            "a" * 40,
            tmp_path / "output",
            approved_by="owner",
            approved_at="2026-07-20T00:00:00Z",
            source_commit_reviewed=True,
        )


def test_approval_orchestrator_rejects_receipt_to_pending_wheel_digest_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_orchestrator_fakes(monkeypatch, tmp_path)
    hashes = iter(("sha256:" + "1" * 64, "sha256:" + "2" * 64))
    monkeypatch.setattr(runtime_build, "_file_sha256", lambda _: next(hashes))
    repo = tmp_path / "repo"
    repo.mkdir()
    output = tmp_path / "output"

    with pytest.raises(RuntimeBuildError, match="receipt does not match"):
        build_approved_runtime(
            repo,
            "a" * 40,
            output,
            approved_by="owner",
            approved_at="2026-07-20T00:00:00Z",
            source_commit_reviewed=True,
        )

    assert list(output.iterdir()) == []


def test_approval_orchestrator_cleans_pending_artifacts_after_final_verification_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_orchestrator_fakes(monkeypatch, tmp_path)
    monkeypatch.setattr(
        runtime_build,
        "verify_wheel",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeBuildError("final verification failed")),
    )
    repo = tmp_path / "repo"
    repo.mkdir()
    output = tmp_path / "output"

    with pytest.raises(RuntimeBuildError, match="final verification failed"):
        build_approved_runtime(
            repo,
            "a" * 40,
            output,
            approved_by="owner",
            approved_at="2026-07-20T00:00:00Z",
            source_commit_reviewed=True,
        )

    assert output.is_dir()
    assert list(output.iterdir()) == []


def test_approval_orchestrator_rolls_back_wheel_if_receipt_publish_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_orchestrator_fakes(monkeypatch, tmp_path)
    real_replace = os.replace
    replacements = 0

    def fail_second_replace(source: Path, destination: Path) -> None:
        nonlocal replacements
        replacements += 1
        if replacements == 2:
            raise OSError("receipt publish failed")
        real_replace(source, destination)

    monkeypatch.setattr(runtime_build.os, "replace", fail_second_replace)
    repo = tmp_path / "repo"
    repo.mkdir()
    output = tmp_path / "output"

    with pytest.raises(OSError, match="receipt publish failed"):
        build_approved_runtime(
            repo,
            "a" * 40,
            output,
            approved_by="owner",
            approved_at="2026-07-20T00:00:00Z",
            source_commit_reviewed=True,
        )

    assert list(output.iterdir()) == []
