"""Explicit approved-runtime publication, pinning, and update checks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any, Mapping

from meeting_ingest._build_info import BUILD_INFO
from meeting_ingest.errors import EXIT_RUNTIME_READINESS, MeetingIngestError
from meeting_ingest.run_summary import RunSummary
from meeting_ingest.runtime_config import (
    RUNTIME_PIN_RELATIVE_PATH,
    RuntimeConfigError,
    read_channel,
    read_pin,
    serialize_channel,
    serialize_pin,
    sha256_bytes,
    sha256_file,
    validate_build_id,
)


DEFAULT_CHANNEL = "private-alpha"
APPROVED_EXECUTABLE_MARKER = "{{MEETING_INGEST_APPROVED_EXECUTABLE}}"
CLAUDE_SKILL_PATH = Path(".claude/skills/meeting-ingest/SKILL.md")
CLAUDE_AGENT_PATH = Path(".claude/agents/meeting-ingest-session-provider.md")
_RECEIPT_KEYS = frozenset(
    {"schema_version", "build", "workflow", "verification", "approved_by", "approved_at"}
)
_BUILD_KEYS = frozenset(
    {
        "semantic_version",
        "build_id",
        "source_commit",
        "source_tree_sha256",
        "wheel_filename",
        "wheel_sha256",
    }
)
_WORKFLOW_KEYS = frozenset(
    {"contract_version", "claude_skill_template_sha256", "claude_agent_sha256"}
)


class RuntimeReleaseError(MeetingIngestError):
    """Raised when explicit release evidence cannot be verified safely."""

    def __init__(self, message: str, *, code: str = "runtime_release_invalid") -> None:
        super().__init__(
            phase="runtime_release",
            code=code,
            message=message,
            exit_code=EXIT_RUNTIME_READINESS,
            recoverable=True,
        )


@dataclass(frozen=True)
class PublishedRuntime:
    build_id: str
    release_directory: Path
    wheel_path: Path
    receipt_path: Path
    channel_path: Path
    previous_build_ids: tuple[str, ...]


@dataclass(frozen=True)
class PinnedRuntime:
    build_id: str
    pin_path: Path
    pin_sha256: str


def default_application_data_root() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/meeting-ingest"
    xdg_data = os.environ.get("XDG_DATA_HOME")
    return (Path(xdg_data) if xdg_data else Path.home() / ".local/share") / "meeting-ingest"


def _require_exact_keys(value: Mapping[str, Any], expected: frozenset[str], label: str) -> None:
    if set(value) != expected:
        unknown = set(value) - expected
        missing = expected - set(value)
        details = []
        if unknown:
            details.append(f"unknown keys: {', '.join(sorted(unknown))}")
        if missing:
            details.append(f"missing keys: {', '.join(sorted(missing))}")
        raise RuntimeReleaseError(f"{label} has {'; '.join(details)}")


def _is_digest(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 71
        and value.startswith("sha256:")
        and all(character in "0123456789abcdef" for character in value[7:])
    )


def _is_commit(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 40
        and all(character in "0123456789abcdef" for character in value)
    )


def read_receipt(path: Path) -> tuple[dict[str, Any], str]:
    unresolved = path.expanduser().absolute()
    resolved = unresolved.resolve(strict=False)
    if unresolved.is_symlink() or not resolved.is_file():
        raise RuntimeReleaseError(
            f"Approved receipt is missing or invalid: {unresolved}", code="runtime_receipt_invalid"
        )
    try:
        payload = resolved.read_bytes()
        value = json.loads(payload)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeReleaseError(
            f"Unable to read approved receipt: {exc}", code="runtime_receipt_invalid"
        ) from exc
    if not isinstance(value, dict):
        raise RuntimeReleaseError("Approved receipt must contain an object", code="runtime_receipt_invalid")
    _require_exact_keys(value, _RECEIPT_KEYS, "Approved receipt")
    if value["schema_version"] != "1.0":
        raise RuntimeReleaseError("Approved receipt schema_version must be 1.0")
    build = value["build"]
    workflow = value["workflow"]
    if not isinstance(build, dict):
        raise RuntimeReleaseError("Approved receipt build must be an object")
    if not isinstance(workflow, dict):
        raise RuntimeReleaseError("Approved receipt workflow must be an object")
    _require_exact_keys(build, _BUILD_KEYS, "Approved receipt build")
    _require_exact_keys(workflow, _WORKFLOW_KEYS, "Approved receipt workflow")
    if not _is_commit(build["source_commit"]):
        raise RuntimeReleaseError("Approved receipt source_commit is invalid")
    for field_name in ("source_tree_sha256", "wheel_sha256"):
        if not _is_digest(build[field_name]):
            raise RuntimeReleaseError(f"Approved receipt {field_name} is invalid")
    for field_name in ("claude_skill_template_sha256", "claude_agent_sha256"):
        if not _is_digest(workflow[field_name]):
            raise RuntimeReleaseError(f"Approved receipt {field_name} is invalid")
    string_values = (
        build["semantic_version"],
        build["build_id"],
        build["wheel_filename"],
        workflow["contract_version"],
        value["approved_by"],
        value["approved_at"],
    )
    if not all(isinstance(item, str) and item for item in string_values):
        raise RuntimeReleaseError("Approved receipt contains an empty identity field")
    try:
        validate_build_id(
            build["build_id"],
            semantic_version=build["semantic_version"],
            source_commit=build["source_commit"],
            source_tree_sha256=build["source_tree_sha256"],
        )
    except RuntimeConfigError as exc:
        raise RuntimeReleaseError(f"Approved receipt {exc}") from exc
    if Path(build["wheel_filename"]).name != build["wheel_filename"]:
        raise RuntimeReleaseError("Approved receipt wheel_filename must be a basename")
    if value["verification"] != {
        "source_commit_reviewed": True,
        "full_suite_passed": True,
        "reproducible_wheel_verified": True,
    }:
        raise RuntimeReleaseError("Approved receipt verification evidence is incomplete")
    try:
        approved = datetime.fromisoformat(value["approved_at"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeReleaseError("Approved receipt approved_at is invalid") from exc
    if approved.tzinfo is None or approved.utcoffset() != UTC.utcoffset(approved):
        raise RuntimeReleaseError("Approved receipt approved_at must identify a UTC instant")
    return value, sha256_bytes(payload)


def _verified_wheel(receipt_path: Path, receipt: Mapping[str, Any], wheel_path: Path | None) -> Path:
    build = receipt["build"]
    unresolved = (wheel_path or receipt_path.parent / build["wheel_filename"]).expanduser().absolute()
    selected = unresolved.resolve(strict=False)
    if unresolved.is_symlink() or not selected.is_file():
        raise RuntimeReleaseError(
            f"Approved wheel is missing or invalid: {unresolved}", code="runtime_wheel_invalid"
        )
    if selected.name != build["wheel_filename"]:
        raise RuntimeReleaseError(
            "Approved wheel filename does not match the receipt", code="runtime_wheel_invalid"
        )
    if sha256_file(selected) != build["wheel_sha256"]:
        raise RuntimeReleaseError(
            "Approved wheel hash does not match the receipt", code="runtime_wheel_invalid"
        )
    return selected


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".pending", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _copy_immutable(source: Path, destination: Path, expected_sha256: str) -> None:
    if destination.exists() or destination.is_symlink():
        if destination.is_symlink() or not destination.is_file():
            raise RuntimeReleaseError(f"Release artifact target is not a regular file: {destination}")
        if sha256_file(destination) != expected_sha256:
            raise RuntimeReleaseError(f"Release artifact already exists with different bytes: {destination}")
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, pending_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".pending", dir=destination.parent
    )
    os.close(descriptor)
    pending = Path(pending_name)
    try:
        shutil.copyfile(source, pending, follow_symlinks=False)
        if sha256_file(pending) != expected_sha256:
            raise RuntimeReleaseError(f"Copied release artifact failed verification: {destination.name}")
        with pending.open("r+b") as copied:
            os.fsync(copied.fileno())
        try:
            os.link(pending, destination)
        except FileExistsError:
            if destination.is_symlink() or not destination.is_file() or sha256_file(destination) != expected_sha256:
                raise RuntimeReleaseError(
                    f"Release artifact already exists with different bytes: {destination}"
                )
        _fsync_directory(destination.parent)
    except BaseException:
        pending.unlink(missing_ok=True)
        raise
    else:
        pending.unlink(missing_ok=True)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@contextmanager
def _channel_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise RuntimeReleaseError(
            f"Another publish is advancing this channel: {path}. If no publish is active, inspect and remove the stale lock.",
            code="runtime_channel_locked",
        ) from exc
    try:
        os.write(descriptor, f"pid={os.getpid()}\n".encode())
        os.fsync(descriptor)
        yield
    finally:
        try:
            os.close(descriptor)
        except OSError:
            pass
        path.unlink(missing_ok=True)


def publish_approved_runtime(
    receipt_path: Path,
    *,
    wheel_path: Path | None = None,
    application_data_root: Path | None = None,
    channel: str = DEFAULT_CHANNEL,
    published_at: str,
) -> PublishedRuntime:
    """Copy immutable artifacts and atomically advance one advisory channel."""

    source_receipt = receipt_path.expanduser().absolute()
    receipt, receipt_sha256 = read_receipt(source_receipt)
    source_wheel = _verified_wheel(source_receipt, receipt, wheel_path)
    build = receipt["build"]
    app_root = (application_data_root or default_application_data_root()).expanduser().resolve(strict=False)
    release_directory = app_root / "releases" / build["build_id"]
    if release_directory.is_symlink():
        raise RuntimeReleaseError(f"Release directory cannot be a symlink: {release_directory}")
    final_wheel = release_directory / build["wheel_filename"]
    final_receipt = release_directory / "receipt.json"
    latest = {
        "build_id": build["build_id"],
        "source_commit": build["source_commit"],
        "wheel_sha256": build["wheel_sha256"],
        "receipt_path": final_receipt.relative_to(app_root).as_posix(),
        "receipt_sha256": receipt_sha256,
    }
    channel_path = app_root / "channels" / f"{channel}.json"
    with _channel_lock(channel_path.with_suffix(".lock")):
        existing = read_channel(app_root, channel)
        if existing.error not in {None, "missing"}:
            raise RuntimeReleaseError(
                f"Existing channel manifest is invalid: {existing.error}",
                code="runtime_channel_invalid",
            )
        previous: list[dict[str, str]] = []
        if existing.valid:
            old_latest = existing.values["latest"]
            if old_latest["build_id"] != build["build_id"]:
                previous.append(
                    {
                        "build_id": old_latest["build_id"],
                        "receipt_path": old_latest["receipt_path"],
                        "receipt_sha256": old_latest["receipt_sha256"],
                    }
                )
            previous.extend(existing.values["previous"])
        deduplicated: list[dict[str, str]] = []
        seen = {build["build_id"]}
        for entry in previous:
            if entry["build_id"] not in seen:
                deduplicated.append(dict(entry))
                seen.add(entry["build_id"])
        manifest = {
            "schema_version": "1.0",
            "channel": channel,
            "latest": latest,
            "previous": deduplicated,
            "published_at": published_at,
        }
        try:
            payload = serialize_channel(manifest)
        except RuntimeConfigError as exc:
            raise RuntimeReleaseError(str(exc), code="runtime_channel_invalid") from exc
        release_directory.mkdir(parents=True, exist_ok=True)
        _copy_immutable(source_wheel, final_wheel, build["wheel_sha256"])
        _copy_immutable(source_receipt, final_receipt, receipt_sha256)
        _write_atomic(channel_path, payload)
    return PublishedRuntime(
        build_id=build["build_id"],
        release_directory=release_directory,
        wheel_path=final_wheel,
        receipt_path=final_receipt,
        channel_path=channel_path,
        previous_build_ids=tuple(entry["build_id"] for entry in deduplicated),
    )


def _resolve_executable(value: str | Path | None) -> Path:
    raw = os.fspath(value) if value is not None else sys.argv[0]
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute() and candidate.parent == Path("."):
        found = shutil.which(raw)
        if found:
            candidate = Path(found)
    return candidate.resolve(strict=False)


def pin_runtime(
    root: Path,
    receipt_path: Path,
    *,
    approved_executable: str | Path | None = None,
    invoked_executable: str | Path | None = None,
    application_data_root: Path | None = None,
    channel: str = DEFAULT_CHANNEL,
    installed_skill_path: Path | None = None,
    claude_agent_path: Path | None = None,
) -> PinnedRuntime:
    """Verify the running approved build and atomically select it for one consumer."""

    root = root.expanduser().resolve(strict=False)
    receipt_file = receipt_path.expanduser().absolute()
    receipt, receipt_sha256 = read_receipt(receipt_file)
    build = receipt["build"]
    workflow = receipt["workflow"]
    embedded_pairs = {
        "semantic_version": BUILD_INFO["semantic_version"],
        "build_id": BUILD_INFO["build_id"],
        "source_commit": BUILD_INFO["source_commit"],
        "source_tree_sha256": BUILD_INFO["source_tree_sha256"],
    }
    mismatches = [field for field, actual in embedded_pairs.items() if build[field] != actual]
    if BUILD_INFO["build_kind"] != "approved-candidate" or mismatches:
        detail = f": {', '.join(mismatches)}" if mismatches else ""
        raise RuntimeReleaseError(
            f"Running embedded build does not match the approved receipt{detail}",
            code="runtime_build_mismatch",
        )
    wheel_candidate = receipt_file.parent / build["wheel_filename"]
    if wheel_candidate.exists() or wheel_candidate.is_symlink():
        _verified_wheel(receipt_file, receipt, wheel_candidate)

    executable = _resolve_executable(approved_executable)
    invoked = _resolve_executable(invoked_executable)
    if not executable.is_absolute() or not executable.is_file():
        raise RuntimeReleaseError(
            f"Approved executable is missing or invalid: {executable}",
            code="runtime_executable_mismatch",
        )
    if executable != invoked:
        raise RuntimeReleaseError(
            f"Approved executable does not match the invoked command: {executable} != {invoked}",
            code="runtime_executable_mismatch",
        )
    app_root = (application_data_root or default_application_data_root()).expanduser().resolve(strict=False)
    installed_receipt = app_root / "releases" / build["build_id"] / "receipt.json"
    if installed_receipt.is_symlink() or not installed_receipt.is_file():
        raise RuntimeReleaseError(
            f"Published receipt is missing for the approved build: {installed_receipt}",
            code="runtime_receipt_invalid",
        )
    if sha256_file(installed_receipt) != receipt_sha256:
        raise RuntimeReleaseError(
            "Published receipt does not match the selected approved receipt",
            code="runtime_receipt_invalid",
        )
    skill = (installed_skill_path or root / CLAUDE_SKILL_PATH).expanduser().absolute()
    agent = (claude_agent_path or root / CLAUDE_AGENT_PATH).expanduser().absolute()
    for label, path in (("Claude skill", skill), ("Claude agent", agent)):
        if path.is_symlink() or not path.is_file():
            raise RuntimeReleaseError(f"{label} is missing or invalid: {path}")
    installed_skill_bytes = skill.read_bytes()
    skill_sha256 = sha256_bytes(installed_skill_bytes)
    agent_sha256 = sha256_file(agent)
    executable_bytes = str(executable).encode("utf-8")
    if installed_skill_bytes.count(executable_bytes) != 1:
        raise RuntimeReleaseError(
            "Installed Claude skill must contain the approved executable exactly once",
            code="workflow_hash_mismatch",
        )
    reconstructed_template = installed_skill_bytes.replace(
        executable_bytes, APPROVED_EXECUTABLE_MARKER.encode("utf-8"), 1
    )
    if sha256_bytes(reconstructed_template) != workflow["claude_skill_template_sha256"]:
        raise RuntimeReleaseError(
            "Installed Claude skill differs from the approved template beyond its executable marker",
            code="workflow_hash_mismatch",
        )
    if agent_sha256 != workflow["claude_agent_sha256"]:
        raise RuntimeReleaseError(
            "Installed Claude agent does not match the approved receipt", code="workflow_hash_mismatch"
        )
    if workflow["contract_version"] != BUILD_INFO["workflow_contract_version"]:
        raise RuntimeReleaseError(
            "Workflow contract does not match the running build", code="workflow_contract_mismatch"
        )

    values = {
        "schema_version": "1.0",
        "channel": channel,
        "approved_build_id": build["build_id"],
        "approved_source_commit": build["source_commit"],
        "approved_source_tree_sha256": build["source_tree_sha256"],
        "approved_wheel_sha256": build["wheel_sha256"],
        "approved_receipt_sha256": receipt_sha256,
        "approved_executable": str(executable),
        "workflow_contract_version": workflow["contract_version"],
        "claude_skill_template_sha256": workflow["claude_skill_template_sha256"],
        "installed_claude_skill_sha256": skill_sha256,
        "claude_agent_sha256": agent_sha256,
        "approved_at": receipt["approved_at"],
    }
    try:
        payload = serialize_pin(values)
    except RuntimeConfigError as exc:
        raise RuntimeReleaseError(str(exc)) from exc
    pin_path = root / RUNTIME_PIN_RELATIVE_PATH
    _write_atomic(pin_path, payload)
    return PinnedRuntime(build_id=build["build_id"], pin_path=pin_path, pin_sha256=sha256_bytes(payload))


def update_check(
    root: Path,
    *,
    application_data_root: Path | None = None,
) -> RunSummary:
    """Compare channel, consumer selection, and running build without side effects."""

    root = root.expanduser().resolve(strict=False)
    pin = read_pin(root)
    channel_name = str(pin.values.get("channel", DEFAULT_CHANNEL)) if pin.valid else DEFAULT_CHANNEL
    channel = read_channel(application_data_root or default_application_data_root(), channel_name)
    latest = channel.values.get("latest", {}) if channel.valid else {}
    comparisons = {
        "channel_to_pin_build": bool(
            channel.valid and pin.valid and latest.get("build_id") == pin.values.get("approved_build_id")
        ),
        "channel_to_pin_wheel": bool(
            channel.valid
            and pin.valid
            and latest.get("wheel_sha256") == pin.values.get("approved_wheel_sha256")
        ),
        "channel_to_pin_receipt": bool(
            channel.valid
            and pin.valid
            and latest.get("receipt_sha256") == pin.values.get("approved_receipt_sha256")
        ),
        "installed_to_pin_build": bool(
            pin.valid and BUILD_INFO["build_id"] == pin.values.get("approved_build_id")
        ),
        "installed_to_pin_commit": bool(
            pin.valid and BUILD_INFO["source_commit"] == pin.values.get("approved_source_commit")
        ),
        "installed_to_pin_tree": bool(
            pin.valid
            and BUILD_INFO["source_tree_sha256"] == pin.values.get("approved_source_tree_sha256")
        ),
    }
    update_available = bool(
        channel.valid and pin.valid and latest.get("build_id") != pin.values.get("approved_build_id")
    )
    warnings: list[str] = []
    if not pin.valid:
        warnings.append(f"Runtime pin unavailable or invalid: {pin.error}")
    if not channel.valid:
        warnings.append(f"Channel manifest unavailable or invalid: {channel.error}")
    return RunSummary(
        status="success",
        warnings=warnings,
        details={
            "command": "runtime_update_check",
            "pin": {
                "path": pin.path,
                "valid": pin.valid,
                "sha256": pin.sha256,
                "error": pin.error,
                "build_id": pin.values.get("approved_build_id"),
            },
            "channel": {
                "name": channel_name,
                "path": channel.path,
                "available": channel.valid,
                "error": channel.error,
                "latest_build_id": latest.get("build_id"),
            },
            "installed_build_id": BUILD_INFO["build_id"],
            "comparisons": comparisons,
            "update_available": update_available,
        },
    )


def pin_runtime_summary(root: Path, receipt_path: Path, **kwargs: Any) -> RunSummary:
    result = pin_runtime(root, receipt_path, **kwargs)
    return RunSummary(
        details={
            "command": "runtime_pin",
            "build_id": result.build_id,
            "pin_path": str(result.pin_path),
            "pin_sha256": result.pin_sha256,
        }
    )
