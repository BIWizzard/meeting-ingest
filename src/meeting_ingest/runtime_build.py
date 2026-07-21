"""Reproducible approved-runtime build and receipt tooling."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from email.parser import BytesParser
from email.policy import default as email_policy
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Sequence

import base64
import csv
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import time
import tomllib
import zipfile


BUILD_INFO_SCHEMA_VERSION = "1.0"
RECEIPT_SCHEMA_VERSION = "1.0"
WORKFLOW_CONTRACT_VERSION = "claude-code-session-v1"
BUILD_KIND = "approved-candidate"
SOURCE_DIRECTORY = PurePosixPath("src/meeting_ingest")
BUILD_INFO_PATH = SOURCE_DIRECTORY / "_build_info.py"
REQUIRED_SOURCE_PATHS = (
    PurePosixPath("pyproject.toml"),
    PurePosixPath("docs/artifact-contract.md"),
    PurePosixPath("docs/provider-handoff-contract.md"),
    PurePosixPath("docs/claude-skills/meeting-ingest/SKILL.md"),
    PurePosixPath("docs/claude-agents/meeting-ingest-session-provider.md"),
)
SKILL_TEMPLATE_PATH = PurePosixPath("docs/claude-skills/meeting-ingest/SKILL.md")
CLAUDE_AGENT_PATH = PurePosixPath("docs/claude-agents/meeting-ingest-session-provider.md")
_EXACT_COMMIT = re.compile(r"[0-9a-f]{40}")


class RuntimeBuildError(RuntimeError):
    """Raised when approval evidence cannot be established."""


@dataclass(frozen=True)
class BuildIdentity:
    schema_version: str
    semantic_version: str
    build_id: str
    source_commit: str
    source_tree_sha256: str
    workflow_contract_version: str
    build_kind: str

    def as_dict(self) -> dict[str, str]:
        return {
            "schema_version": self.schema_version,
            "semantic_version": self.semantic_version,
            "build_id": self.build_id,
            "source_commit": self.source_commit,
            "source_tree_sha256": self.source_tree_sha256,
            "workflow_contract_version": self.workflow_contract_version,
            "build_kind": self.build_kind,
        }


@dataclass(frozen=True)
class ArchivedSource:
    root: Path
    identity: BuildIdentity
    source_date_epoch: int
    claude_skill_template_sha256: str
    claude_agent_sha256: str


@dataclass(frozen=True)
class ApprovedBuildResult:
    identity: BuildIdentity
    wheel_path: Path
    wheel_sha256: str
    receipt_path: Path
    receipt_sha256: str


@dataclass(frozen=True)
class VerificationEvidence:
    source_commit_reviewed: bool
    full_suite_passed: bool
    reproducible_wheel_verified: bool

    def require_approval_ready(self) -> None:
        missing = [
            name
            for name, value in (
                ("source_commit_reviewed", self.source_commit_reviewed),
                ("full_suite_passed", self.full_suite_passed),
                ("reproducible_wheel_verified", self.reproducible_wheel_verified),
            )
            if not value
        ]
        if missing:
            raise RuntimeBuildError(f"Approval evidence is incomplete: {', '.join(missing)}")


CommandRunner = Callable[..., subprocess.CompletedProcess[Any]]


def _run(
    args: Sequence[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    runner: CommandRunner = subprocess.run,
) -> subprocess.CompletedProcess[str]:
    try:
        return runner(
            list(args),
            cwd=cwd,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        stderr = getattr(exc, "stderr", "") or ""
        detail = stderr.strip() or str(exc)
        raise RuntimeBuildError(f"Command failed: {' '.join(args)}: {detail}") from exc


def _git_text(repo_root: Path, *args: str, runner: CommandRunner = subprocess.run) -> str:
    result = _run(("git", *args), cwd=repo_root, runner=runner)
    return result.stdout.strip()


def validate_exact_commit(
    repo_root: Path,
    source_commit: str,
    *,
    runner: CommandRunner = subprocess.run,
) -> int:
    """Require a literal full commit hash and return its commit timestamp."""

    if _EXACT_COMMIT.fullmatch(source_commit) is None:
        raise RuntimeBuildError("source_commit must be a literal 40-character lowercase Git commit hash")
    resolved = _git_text(repo_root, "rev-parse", f"{source_commit}^{{commit}}", runner=runner)
    if resolved != source_commit:
        raise RuntimeBuildError(f"Git resolved {source_commit!r} to unexpected commit {resolved!r}")
    timestamp = _git_text(repo_root, "show", "-s", "--format=%ct", source_commit, runner=runner)
    try:
        epoch = int(timestamp)
    except ValueError as exc:
        raise RuntimeBuildError(f"Git returned an invalid commit timestamp: {timestamp!r}") from exc
    if epoch < 0:
        raise RuntimeBuildError("Git commit timestamp must be non-negative")
    return epoch


def _safe_archive_name(name: str) -> PurePosixPath:
    if not name or name.startswith("/") or "\\" in name:
        raise RuntimeBuildError(f"Unsafe archive path: {name!r}")
    normalized = name[:-1] if name.endswith("/") else name
    path = PurePosixPath(normalized)
    if normalized in {"", "."} or any(part in {"", ".", ".."} for part in path.parts):
        raise RuntimeBuildError(f"Unsafe archive path: {name!r}")
    if path.as_posix() != normalized:
        raise RuntimeBuildError(f"Non-normalized archive path: {name!r}")
    return path


def extract_git_archive(
    repo_root: Path,
    source_commit: str,
    destination: Path,
    *,
    runner: CommandRunner = subprocess.run,
) -> None:
    """Extract one exact Git archive while rejecting unsafe or special entries."""

    try:
        archive = runner(
            ["git", "archive", "--format=tar", source_commit],
            cwd=repo_root,
            check=True,
            capture_output=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        stderr = getattr(exc, "stderr", b"") or b""
        detail = (
            stderr.decode("utf-8", errors="replace").strip()
            if isinstance(stderr, bytes)
            else str(stderr).strip()
        ) or str(exc)
        raise RuntimeBuildError(f"Unable to archive commit {source_commit}: {detail}") from exc

    destination.mkdir(parents=True, exist_ok=False)
    seen: set[PurePosixPath] = set()
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as source:
        for member in source:
            relative = _safe_archive_name(member.name)
            if relative in seen:
                raise RuntimeBuildError(f"Duplicate archive path: {relative.as_posix()}")
            seen.add(relative)
            target = destination.joinpath(*relative.parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                raise RuntimeBuildError(f"Archive contains non-regular entry: {relative.as_posix()}")
            payload = source.extractfile(member)
            if payload is None:
                raise RuntimeBuildError(f"Archive entry has no payload: {relative.as_posix()}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as output:
                shutil.copyfileobj(payload, output)
            target.chmod(member.mode & 0o777)


def _regular_file(root: Path, relative: PurePosixPath) -> Path:
    path = root.joinpath(*relative.parts)
    if path.is_symlink() or not path.is_file():
        raise RuntimeBuildError(f"Required tracked regular file is missing or invalid: {relative.as_posix()}")
    return path


def source_tree_paths(root: Path) -> tuple[PurePosixPath, ...]:
    """Return the frozen, validated source-fingerprint path set."""

    selected = list(REQUIRED_SOURCE_PATHS)
    for relative in REQUIRED_SOURCE_PATHS:
        _regular_file(root, relative)
    source_root = root.joinpath(*SOURCE_DIRECTORY.parts)
    if source_root.is_symlink() or not source_root.is_dir():
        raise RuntimeBuildError(f"Required tracked directory is missing or invalid: {SOURCE_DIRECTORY}")
    package_files: list[PurePosixPath] = []
    for path in source_root.rglob("*"):
        relative = PurePosixPath(path.relative_to(root).as_posix())
        if path.is_symlink():
            raise RuntimeBuildError(f"Symlink below required directory: {relative.as_posix()}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise RuntimeBuildError(f"Non-regular entry below required directory: {relative.as_posix()}")
        if "__pycache__" in relative.parts or path.suffix in {".pyc", ".pyo"}:
            raise RuntimeBuildError(f"Unexpected generated path below required directory: {relative.as_posix()}")
        if any(part.endswith(".egg-info") for part in relative.parts):
            raise RuntimeBuildError(f"Unexpected build metadata below required directory: {relative.as_posix()}")
        package_files.append(relative)
    if not package_files:
        raise RuntimeBuildError(f"Required tracked directory is empty: {SOURCE_DIRECTORY}")
    selected.extend(package_files)
    if len(selected) != len(set(selected)):
        raise RuntimeBuildError("Duplicate normalized source-fingerprint path")
    return tuple(sorted(selected, key=lambda item: item.as_posix().encode("utf-8")))


def source_tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for relative in source_tree_paths(root):
        payload = _regular_file(root, relative).read_bytes()
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(len(payload)).encode("ascii"))
        digest.update(b"\0")
        digest.update(payload)
    return f"sha256:{digest.hexdigest()}"


def _file_sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _semantic_version(root: Path) -> str:
    data = tomllib.loads(_regular_file(root, PurePosixPath("pyproject.toml")).read_text(encoding="utf-8"))
    try:
        version = data["project"]["version"]
    except (KeyError, TypeError) as exc:
        raise RuntimeBuildError("pyproject.toml does not contain project.version") from exc
    if not isinstance(version, str) or not version.strip():
        raise RuntimeBuildError("project.version must be a non-empty string")
    return version


def make_build_identity(root: Path, source_commit: str) -> BuildIdentity:
    tree_digest = source_tree_sha256(root)
    version = _semantic_version(root)
    build_id = f"meeting-ingest-{version}-g{source_commit[:12]}-s{tree_digest[7:19]}"
    return BuildIdentity(
        schema_version=BUILD_INFO_SCHEMA_VERSION,
        semantic_version=version,
        build_id=build_id,
        source_commit=source_commit,
        source_tree_sha256=tree_digest,
        workflow_contract_version=WORKFLOW_CONTRACT_VERSION,
        build_kind=BUILD_KIND,
    )


def render_build_info(identity: BuildIdentity) -> bytes:
    payload = json.dumps(identity.as_dict(), indent=4, ensure_ascii=False)
    return (
        '"""Embedded immutable runtime build identity. Generated in an isolated build tree."""\n\n'
        "from __future__ import annotations\n\n\n"
        f"BUILD_INFO = {payload}\n"
    ).encode("utf-8")


def prepare_archived_source(
    repo_root: Path,
    source_commit: str,
    destination: Path,
    *,
    runner: CommandRunner = subprocess.run,
) -> ArchivedSource:
    epoch = validate_exact_commit(repo_root, source_commit, runner=runner)
    extract_git_archive(repo_root, source_commit, destination, runner=runner)
    identity = make_build_identity(destination, source_commit)
    skill_hash = _file_sha256(_regular_file(destination, SKILL_TEMPLATE_PATH))
    agent_hash = _file_sha256(_regular_file(destination, CLAUDE_AGENT_PATH))
    _regular_file(destination, BUILD_INFO_PATH).write_bytes(render_build_info(identity))
    return ArchivedSource(destination, identity, epoch, skill_hash, agent_hash)


def _normalized_env(source_date_epoch: int) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "LC_ALL": "C",
            "PYTHONHASHSEED": "0",
            "SOURCE_DATE_EPOCH": str(source_date_epoch),
            "TZ": "UTC",
        }
    )
    return env


def run_full_suite(source: ArchivedSource, *, runner: CommandRunner = subprocess.run) -> None:
    _run(
        ("uv", "run", "--frozen", "--extra", "dev", "pytest", "-q"),
        cwd=source.root,
        env=_normalized_env(source.source_date_epoch),
        runner=runner,
    )


def build_wheel(
    source: ArchivedSource,
    output_dir: Path,
    *,
    runner: CommandRunner = subprocess.run,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=False)
    _run(
        ("uv", "build", "--wheel", "--out-dir", str(output_dir), str(source.root)),
        cwd=source.root,
        env=_normalized_env(source.source_date_epoch),
        runner=runner,
    )
    wheels = tuple(output_dir.glob("*.whl"))
    if len(wheels) != 1:
        raise RuntimeBuildError(f"Expected exactly one wheel, found {len(wheels)}")
    verify_wheel(wheels[0], source.identity, source.source_date_epoch)
    return wheels[0]


def _record_hash(payload: bytes) -> str:
    encoded = base64.urlsafe_b64encode(hashlib.sha256(payload).digest()).rstrip(b"=").decode("ascii")
    return f"sha256={encoded}"


def verify_wheel(wheel_path: Path, identity: BuildIdentity, source_date_epoch: int) -> None:
    """Verify wheel paths, metadata, embedded identity, and RECORD integrity."""

    normalized_epoch = max(source_date_epoch, 315532800)
    normalized_epoch -= normalized_epoch % 2  # ZIP timestamps have two-second precision.
    expected_timestamp = time.gmtime(normalized_epoch)[:6]
    expected_dist_info = f"meeting_ingest-{identity.semantic_version}.dist-info"
    expected_filename = f"meeting_ingest-{identity.semantic_version}-py3-none-any.whl"
    if wheel_path.name not in {expected_filename, f".{expected_filename}.pending"}:
        raise RuntimeBuildError(f"Unexpected wheel filename: {wheel_path.name}")
    with zipfile.ZipFile(wheel_path) as wheel:
        infos = wheel.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)):
            raise RuntimeBuildError("Wheel contains duplicate paths")
        for info in infos:
            relative = _safe_archive_name(info.filename)
            if relative.as_posix() != info.filename:
                raise RuntimeBuildError(f"Invalid wheel path: {info.filename!r}")
            if info.is_dir():
                raise RuntimeBuildError(f"Unexpected directory entry in wheel: {info.filename}")
            file_type = (info.external_attr >> 16) & 0o170000
            if file_type not in {0, 0o100000}:
                raise RuntimeBuildError(f"Non-regular wheel entry: {info.filename}")
            if info.date_time != expected_timestamp:
                raise RuntimeBuildError(
                    f"Wheel timestamp is not normalized for {info.filename}: {info.date_time!r}"
                )
        embedded_name = BUILD_INFO_PATH.relative_to("src").as_posix()
        if embedded_name not in names:
            raise RuntimeBuildError("Wheel does not contain embedded build identity")
        if wheel.read(embedded_name) != render_build_info(identity):
            raise RuntimeBuildError("Wheel embedded build identity does not match staged identity")
        metadata_name = f"{expected_dist_info}/METADATA"
        wheel_metadata_name = f"{expected_dist_info}/WHEEL"
        if metadata_name not in names or wheel_metadata_name not in names:
            raise RuntimeBuildError("Wheel does not contain the expected distribution metadata")
        metadata = BytesParser(policy=email_policy).parsebytes(wheel.read(metadata_name))
        if metadata.get("Name") != "meeting-ingest" or metadata.get("Version") != identity.semantic_version:
            raise RuntimeBuildError("Wheel METADATA name or version does not match build identity")
        wheel_metadata = BytesParser(policy=email_policy).parsebytes(wheel.read(wheel_metadata_name))
        if wheel_metadata.get("Root-Is-Purelib") != "true" or "py3-none-any" not in wheel_metadata.get_all(
            "Tag", []
        ):
            raise RuntimeBuildError("Wheel compatibility metadata does not match a pure Python universal wheel")
        record_names = [name for name in names if name.endswith(".dist-info/RECORD")]
        if len(record_names) != 1 or names[-1] != record_names[0]:
            raise RuntimeBuildError("Wheel must contain one final RECORD entry")
        record_name = record_names[0]
        rows = list(csv.reader(io.StringIO(wheel.read(record_name).decode("utf-8"))))
        if any(len(row) != 3 for row in rows):
            raise RuntimeBuildError("Wheel RECORD contains a malformed row")
        if [row[0] for row in rows] != names:
            raise RuntimeBuildError("Wheel RECORD ordering does not match ZIP entry ordering")
        for row in rows:
            name, recorded_hash, recorded_size = row
            if name == record_name:
                if recorded_hash or recorded_size:
                    raise RuntimeBuildError("Wheel RECORD self-entry must omit hash and size")
                continue
            payload = wheel.read(name)
            if recorded_hash != _record_hash(payload) or recorded_size != str(len(payload)):
                raise RuntimeBuildError(f"Wheel RECORD mismatch for {name}")


def _normalize_approved_at(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeBuildError("approved_at must be an RFC 3339 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise RuntimeBuildError("approved_at must identify a UTC instant")
    return parsed.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def create_receipt(
    source: ArchivedSource,
    wheel_path: Path,
    *,
    verification: VerificationEvidence,
    approved_by: str,
    approved_at: str,
) -> dict[str, Any]:
    verification.require_approval_ready()
    approver = approved_by.strip()
    if not approver:
        raise RuntimeBuildError("approved_by must be non-empty")
    wheel_digest = _file_sha256(wheel_path)
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "build": {
            "semantic_version": source.identity.semantic_version,
            "build_id": source.identity.build_id,
            "source_commit": source.identity.source_commit,
            "source_tree_sha256": source.identity.source_tree_sha256,
            "wheel_filename": wheel_path.name,
            "wheel_sha256": wheel_digest,
        },
        "workflow": {
            "contract_version": source.identity.workflow_contract_version,
            "claude_skill_template_sha256": source.claude_skill_template_sha256,
            "claude_agent_sha256": source.claude_agent_sha256,
        },
        "verification": {
            "source_commit_reviewed": verification.source_commit_reviewed,
            "full_suite_passed": verification.full_suite_passed,
            "reproducible_wheel_verified": verification.reproducible_wheel_verified,
        },
        "approved_by": approver,
        "approved_at": _normalize_approved_at(approved_at),
    }


def _json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def build_approved_runtime(
    repo_root: Path,
    source_commit: str,
    output_dir: Path,
    *,
    approved_by: str,
    approved_at: str,
    source_commit_reviewed: bool,
    runner: CommandRunner = subprocess.run,
) -> ApprovedBuildResult:
    """Test and build one exact archive twice, then emit its wheel and receipt."""

    if not source_commit_reviewed:
        raise RuntimeBuildError("Refusing approval without explicit source-commit review confirmation")
    repo_root = repo_root.resolve()
    output_dir = output_dir.resolve()
    if not repo_root.is_dir():
        raise RuntimeBuildError(f"Repository root does not exist: {repo_root}")
    if output_dir.exists():
        if not output_dir.is_dir() or any(output_dir.iterdir()):
            raise RuntimeBuildError(f"Output directory must be absent or empty: {output_dir}")

    with tempfile.TemporaryDirectory(prefix="meeting-ingest-approved-build-") as temporary:
        temp_root = Path(temporary)
        test_source = prepare_archived_source(repo_root, source_commit, temp_root / "test-source", runner=runner)
        run_full_suite(test_source, runner=runner)

        candidates: list[tuple[ArchivedSource, Path]] = []
        for label in ("a", "b"):
            source = prepare_archived_source(
                repo_root,
                source_commit,
                temp_root / f"build-{label}" / "source",
                runner=runner,
            )
            if source.identity != test_source.identity:
                raise RuntimeBuildError("Isolated archives produced different build identities")
            wheel = build_wheel(source, temp_root / f"build-{label}" / "dist", runner=runner)
            candidates.append((source, wheel))

        first_source, first_wheel = candidates[0]
        second_source, second_wheel = candidates[1]
        first_bytes = first_wheel.read_bytes()
        if first_bytes != second_wheel.read_bytes():
            raise RuntimeBuildError("Two isolated normalized builds produced different wheel bytes")
        first_evidence = (
            first_source.identity,
            first_source.source_date_epoch,
            first_source.claude_skill_template_sha256,
            first_source.claude_agent_sha256,
        )
        second_evidence = (
            second_source.identity,
            second_source.source_date_epoch,
            second_source.claude_skill_template_sha256,
            second_source.claude_agent_sha256,
        )
        if first_evidence != second_evidence:
            raise RuntimeBuildError("Two isolated normalized builds produced different source evidence")

        receipt = create_receipt(
            first_source,
            first_wheel,
            verification=VerificationEvidence(
                source_commit_reviewed=source_commit_reviewed,
                # Reaching receipt construction proves both raising gates above completed.
                full_suite_passed=True,
                reproducible_wheel_verified=True,
            ),
            approved_by=approved_by,
            approved_at=approved_at,
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        final_wheel = output_dir / first_wheel.name
        final_receipt = output_dir / "receipt.json"
        pending_wheel = output_dir / f".{first_wheel.name}.pending"
        pending_receipt = output_dir / ".receipt.json.pending"
        wheel_published = False
        try:
            pending_wheel.write_bytes(first_bytes)
            pending_receipt.write_bytes(_json_bytes(receipt))
            verify_wheel(pending_wheel, first_source.identity, first_source.source_date_epoch)
            if _file_sha256(pending_wheel) != receipt["build"]["wheel_sha256"]:
                raise RuntimeBuildError("Emitted receipt does not match emitted wheel")
            os.replace(pending_wheel, final_wheel)
            wheel_published = True
            os.replace(pending_receipt, final_receipt)
        except BaseException:
            pending_wheel.unlink(missing_ok=True)
            pending_receipt.unlink(missing_ok=True)
            if wheel_published and not final_receipt.exists():
                final_wheel.unlink(missing_ok=True)
            raise
        return ApprovedBuildResult(
            identity=first_source.identity,
            wheel_path=final_wheel,
            wheel_sha256=_file_sha256(final_wheel),
            receipt_path=final_receipt,
            receipt_sha256=_file_sha256(final_receipt),
        )
