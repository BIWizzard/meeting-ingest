"""Explicit approved-runtime publication, pinning, and update checks."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from contextlib import contextmanager
from importlib import resources
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Callable, Mapping, Sequence

from meeting_ingest._build_info import BUILD_INFO
from meeting_ingest.errors import EXIT_RUNTIME_READINESS, MeetingIngestError
from meeting_ingest.readiness import assess_readiness, with_runtime_provenance
from meeting_ingest.run_summary import RESERVED_KEYS, RunSummary
from meeting_ingest.runtime import (
    CONSOLE_SCRIPT_NAME,
    ReadinessResult,
    RuntimeInspection,
    inspect_runtime,
)
from meeting_ingest.runtime_config import (
    RUNTIME_PIN_RELATIVE_PATH,
    ConsumerPin,
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
WORKFLOW_TEMPLATE_DIRECTORY = "workflow_templates"
SKILL_TEMPLATE_NAME = "SKILL.md"
CLAUDE_AGENT_TEMPLATE_NAME = "meeting-ingest-session-provider.md"
PUBLISH_REMEDIATION = (
    "Ask the maintainer to build and publish an approved runtime "
    "(scripts/build-approved-runtime.py, then scripts/publish-approved-runtime.py)."
)
INIT_REMEDIATION = (
    "Run `meeting-ingest init` from this consumer root to select and pin the approved runtime."
)
_INIT_EDITABLE_REMEDIATION = (
    "Install the approved frozen wheel and run `meeting-ingest init` from it, or rerun "
    "with --development-override <reason> to scaffold without an approved runtime."
)
_UPDATE_EDITABLE_REMEDIATION = (
    "Run `meeting-ingest update` from the approved frozen installation; update never installs "
    "over a development runtime."
)
_INIT_SHADOW_REMEDIATION = (
    "Remove the shadowing copy this session resolves and run `meeting-ingest init` again."
)
_UPDATE_SHADOW_REMEDIATION = "Remove the shadowing copy this session resolves."
UV_TOOL_INSTALL_COMMAND = ("uv", "tool", "install", "--reinstall")
UV_TOOL_BIN_COMMAND = ("uv", "tool", "dir", "--bin")
UPDATE_DELEGATION_MARKER = "MEETING_INGEST_UPDATE_DELEGATED"
CommandRunner = Callable[..., "subprocess.CompletedProcess[str]"]
_BOOTSTRAP_BLOCKING_CODES = (
    "runtime_editable_blocked",
    "runtime_install_unknown",
    "runtime_package_integrity_failed",
    "runtime_git_uninspectable",
)
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
_RECEIPT_BUILD_FIELDS = frozenset(
    {
        "semantic_version",
        "build_id",
        "source_commit",
        "source_tree_sha256",
        "workflow_contract_version",
    }
)


class RuntimeReleaseError(MeetingIngestError):
    """Raised when explicit release evidence cannot be verified safely."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "runtime_release_invalid",
        remediation: str | None = None,
    ) -> None:
        super().__init__(
            phase="runtime_release",
            code=code,
            message=message,
            exit_code=EXIT_RUNTIME_READINESS,
            recoverable=True,
            details={"remediation": remediation} if remediation else {},
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


@dataclass(frozen=True)
class WorkflowInstallResult:
    build_id: str
    skill_destination: Path
    rendered_skill_sha256: str
    agent_destination: Path | None
    agent_sha256: str | None


@dataclass(frozen=True)
class PackagedWorkflowTemplates:
    skill_template: Path
    claude_agent: Path


@dataclass(frozen=True)
class BootstrappedRuntime:
    build_id: str
    receipt_path: Path
    pin_path: Path
    pin_sha256: str
    skill_destination: Path
    agent_destination: Path
    executable: Path


@dataclass(frozen=True)
class InstalledRuntime:
    build_id: str
    executable: Path
    command: tuple[str, ...]


def default_application_data_root() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/meeting-ingest"
    xdg_data = os.environ.get("XDG_DATA_HOME")
    return (Path(xdg_data) if xdg_data else Path.home() / ".local/share") / "meeting-ingest"


def packaged_workflow_templates() -> PackagedWorkflowTemplates:
    """Locate the workflow templates shipped inside the running installation."""

    try:
        directory = resources.files("meeting_ingest").joinpath(WORKFLOW_TEMPLATE_DIRECTORY)
        skill = Path(os.fspath(directory.joinpath(SKILL_TEMPLATE_NAME)))
        agent = Path(os.fspath(directory.joinpath(CLAUDE_AGENT_TEMPLATE_NAME)))
    except (ModuleNotFoundError, TypeError, OSError) as exc:
        raise RuntimeReleaseError(
            f"Packaged workflow templates are unavailable: {exc}",
            code="workflow_templates_unavailable",
            remediation="Reinstall the approved Meeting Ingest wheel and run the command again.",
        ) from exc
    for label, path in (("Claude skill template", skill), ("Claude agent", agent)):
        if path.is_symlink() or not path.is_file():
            raise RuntimeReleaseError(
                f"Packaged {label} is missing or invalid: {path}",
                code="workflow_templates_unavailable",
                remediation="Reinstall the approved Meeting Ingest wheel and run the command again.",
            )
    return PackagedWorkflowTemplates(skill_template=skill, claude_agent=agent)


def runtime_pin_present(root: Path) -> bool:
    """Report whether a consumer already carries a runtime pin of any state."""

    path = root.expanduser().resolve(strict=False) / RUNTIME_PIN_RELATIVE_PATH
    return path.exists() or path.is_symlink()


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


def _reread_receipt(path: Path, expected_sha256: str | None) -> tuple[dict[str, Any], str]:
    """Re-open a receipt and refuse any stage that no longer sees the selected bytes."""
    receipt, receipt_sha256 = read_receipt(path)
    if expected_sha256 is not None and receipt_sha256 != expected_sha256:
        raise RuntimeReleaseError(
            f"Approved receipt changed between verification stages: {path}",
            code="runtime_receipt_invalid",
            remediation="Re-run the command; if it repeats, republish the approved runtime.",
        )
    return receipt, receipt_sha256


def _require_unsymlinked_descent(base: Path, path: Path, label: str) -> None:
    """Reject a symlink at any component between base and path, path included."""
    try:
        relative = path.relative_to(base)
    except ValueError as exc:
        raise RuntimeReleaseError(
            f"{label} is not contained by {base}: {path}",
            code="runtime_path_unsafe",
            remediation="Remove the redirected path and run the command again.",
        ) from exc
    current = base
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise RuntimeReleaseError(
                f"{label} traverses a symbolic link: {current}",
                code="runtime_path_unsafe",
                remediation="Replace the symbolic link with a reviewed regular directory or file.",
            )


def _require_contained(base: Path, path: Path, label: str) -> Path:
    """Require a resolved path to stay under a resolved base directory."""
    resolved_base = base.resolve(strict=False)
    resolved = path.resolve(strict=False)
    try:
        resolved.relative_to(resolved_base)
    except ValueError as exc:
        raise RuntimeReleaseError(
            f"{label} resolves outside {resolved_base}: {resolved}",
            code="runtime_path_unsafe",
            remediation="Republish the approved runtime into an unredirected application data root.",
        ) from exc
    return resolved


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


def _stage_atomic(path: Path, payload: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".pending", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return temporary


def _create_atomic_exclusive(path: Path, payload: bytes) -> None:
    """Create a file that must not already exist, durably and without clobbering."""
    temporary = _stage_atomic(path, payload)
    try:
        os.link(temporary, path)
        _fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def _write_atomic_pair(
    first_path: Path,
    first_payload: bytes,
    second_path: Path,
    second_payload: bytes,
) -> None:
    first_temporary: Path | None = None
    second_temporary: Path | None = None
    first_backup: Path | None = None
    second_backup: Path | None = None
    first_existed = first_path.exists() or first_path.is_symlink()
    second_existed = second_path.exists() or second_path.is_symlink()
    first_replaced = False
    second_replaced = False
    try:
        first_temporary = _stage_atomic(first_path, first_payload)
        second_temporary = _stage_atomic(second_path, second_payload)
        if first_existed:
            first_backup = _stage_atomic(first_path, first_path.read_bytes())
        if second_existed:
            second_backup = _stage_atomic(second_path, second_path.read_bytes())

        try:
            os.replace(first_temporary, first_path)
            first_temporary = None
            first_replaced = True
            _fsync_directory(first_path.parent)
            os.replace(second_temporary, second_path)
            second_temporary = None
            second_replaced = True
            _fsync_directory(second_path.parent)
        except BaseException:
            if second_replaced:
                if second_backup is not None:
                    os.replace(second_backup, second_path)
                    second_backup = None
                else:
                    second_path.unlink(missing_ok=True)
                _fsync_directory(second_path.parent)
            if first_replaced:
                if first_backup is not None:
                    os.replace(first_backup, first_path)
                    first_backup = None
                else:
                    first_path.unlink(missing_ok=True)
                _fsync_directory(first_path.parent)
            raise
    finally:
        for temporary in (
            first_temporary,
            second_temporary,
            first_backup,
            second_backup,
        ):
            if temporary is not None:
                temporary.unlink(missing_ok=True)


def install_workflow_artifacts(
    receipt_path: Path,
    *,
    template_path: Path,
    executable: str | Path,
    skill_destination: Path,
    agent_path: Path | None = None,
    agent_destination: Path | None = None,
    expected_receipt_sha256: str | None = None,
) -> WorkflowInstallResult:
    """Render and install receipt-verified workflow artifacts atomically."""

    receipt, _ = _reread_receipt(receipt_path, expected_receipt_sha256)
    workflow = receipt["workflow"]
    if (agent_path is None) != (agent_destination is None):
        raise RuntimeReleaseError(
            "Claude agent source and destination must be provided together",
            code="workflow_agent_arguments_invalid",
        )

    template = template_path.expanduser().absolute()
    try:
        template_bytes = template.read_bytes()
    except OSError as exc:
        raise RuntimeReleaseError(
            f"Unable to read Claude skill template: {exc}",
            code="workflow_template_hash_mismatch",
        ) from exc
    if sha256_bytes(template_bytes) != workflow["claude_skill_template_sha256"]:
        raise RuntimeReleaseError(
            "Claude skill template does not match the approved receipt",
            code="workflow_template_hash_mismatch",
        )
    marker_bytes = APPROVED_EXECUTABLE_MARKER.encode("utf-8")
    if template_bytes.count(marker_bytes) != 1:
        raise RuntimeReleaseError(
            "Claude skill template must contain the approved executable marker exactly once",
            code="workflow_template_marker_invalid",
        )

    executable_candidate = Path(executable).expanduser()
    if not executable_candidate.is_absolute():
        raise RuntimeReleaseError(
            f"Workflow executable must be an absolute path: {executable_candidate}",
            code="workflow_executable_invalid",
        )
    resolved_executable = _resolve_executable(executable_candidate)
    executable_text = str(resolved_executable)
    if APPROVED_EXECUTABLE_MARKER in executable_text:
        raise RuntimeReleaseError(
            "Workflow executable must not contain the approved executable marker",
            code="workflow_executable_invalid",
        )
    try:
        executable_bytes = executable_text.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise RuntimeReleaseError(
            "Workflow executable must be representable as UTF-8",
            code="workflow_executable_invalid",
        ) from exc
    rendered_skill = template_bytes.replace(marker_bytes, executable_bytes, 1)

    agent_bytes: bytes | None = None
    verified_agent_sha256: str | None = None
    final_agent_destination: Path | None = None
    if agent_path is not None and agent_destination is not None:
        agent = agent_path.expanduser().absolute()
        try:
            agent_bytes = agent.read_bytes()
        except OSError as exc:
            raise RuntimeReleaseError(
                f"Unable to read Claude agent: {exc}",
                code="workflow_agent_hash_mismatch",
            ) from exc
        verified_agent_sha256 = sha256_bytes(agent_bytes)
        if verified_agent_sha256 != workflow["claude_agent_sha256"]:
            raise RuntimeReleaseError(
                "Claude agent does not match the approved receipt",
                code="workflow_agent_hash_mismatch",
            )
        if marker_bytes in agent_bytes:
            raise RuntimeReleaseError(
                "Claude agent must not contain the approved executable marker",
                code="workflow_agent_marker_unexpected",
            )
        final_agent_destination = agent_destination.expanduser().absolute()

    final_skill_destination = skill_destination.expanduser().absolute()
    if final_agent_destination == final_skill_destination:
        raise RuntimeReleaseError(
            "Claude skill and agent destinations must be different",
            code="workflow_agent_arguments_invalid",
        )

    if final_agent_destination is not None and agent_bytes is not None:
        _write_atomic_pair(
            final_skill_destination,
            rendered_skill,
            final_agent_destination,
            agent_bytes,
        )
    else:
        _write_atomic(final_skill_destination, rendered_skill)
    return WorkflowInstallResult(
        build_id=receipt["build"]["build_id"],
        skill_destination=final_skill_destination,
        rendered_skill_sha256=sha256_bytes(rendered_skill),
        agent_destination=final_agent_destination,
        agent_sha256=verified_agent_sha256,
    )


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


def _require_expected_wheel_digest(
    receipt: Mapping[str, Any], expected_wheel_sha256: str | None
) -> None:
    """Bind a receipt to the wheel digest its producer reported, not just to its own claim."""

    if expected_wheel_sha256 is not None and receipt["build"]["wheel_sha256"] != expected_wheel_sha256:
        raise RuntimeReleaseError(
            "Approved receipt does not name the expected wheel digest",
            code="runtime_wheel_invalid",
            remediation="Rebuild the approved runtime and publish the receipt that build produced.",
        )


def publish_approved_runtime(
    receipt_path: Path,
    *,
    wheel_path: Path | None = None,
    application_data_root: Path | None = None,
    channel: str = DEFAULT_CHANNEL,
    published_at: str,
    expected_receipt_sha256: str | None = None,
    expected_wheel_sha256: str | None = None,
) -> PublishedRuntime:
    """Copy immutable artifacts and atomically advance one advisory channel."""

    source_receipt = receipt_path.expanduser().absolute()
    receipt, receipt_sha256 = _reread_receipt(source_receipt, expected_receipt_sha256)
    _require_expected_wheel_digest(receipt, expected_wheel_sha256)
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
    expected_receipt_sha256: str | None = None,
    exclusive: bool = False,
) -> PinnedRuntime:
    """Verify the running approved build and atomically select it for one consumer."""

    root = root.expanduser().resolve(strict=False)
    receipt_file = receipt_path.expanduser().absolute()
    receipt, receipt_sha256 = _reread_receipt(receipt_file, expected_receipt_sha256)
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
    if exclusive:
        _create_atomic_exclusive(pin_path, payload)
    else:
        _write_atomic(pin_path, payload)
    return PinnedRuntime(build_id=build["build_id"], pin_path=pin_path, pin_sha256=sha256_bytes(payload))


def _latest_published_receipt(app_root: Path, channel: str) -> tuple[Path, str]:
    """Select the newest published approved receipt without touching any pin."""

    _require_unsymlinked_descent(app_root, app_root / "channels", "Release channel directory")
    manifest = read_channel(app_root, channel)
    if not manifest.valid:
        raise RuntimeReleaseError(
            f"No approved Meeting Ingest runtime is published for channel {channel!r} "
            f"in {app_root} ({manifest.error}).",
            code="approved_runtime_unavailable",
            remediation=PUBLISH_REMEDIATION,
        )
    latest = manifest.values["latest"]
    receipt_path = app_root / latest["receipt_path"]
    _require_unsymlinked_descent(app_root, receipt_path, "Published receipt")
    _require_contained(app_root, receipt_path, "Published receipt")
    try:
        _, receipt_sha256 = read_receipt(receipt_path)
    except RuntimeReleaseError as exc:
        raise RuntimeReleaseError(
            f"The approved runtime published in {app_root} is unusable: {exc.message}",
            code="approved_runtime_unavailable",
            remediation=PUBLISH_REMEDIATION,
        ) from exc
    if receipt_sha256 != latest["receipt_sha256"]:
        raise RuntimeReleaseError(
            f"The approved receipt published in {app_root} does not match its channel manifest.",
            code="approved_runtime_unavailable",
            remediation=PUBLISH_REMEDIATION,
        )
    return receipt_path, receipt_sha256


def _require_published_wheel(app_root: Path, receipt_path: Path, receipt: Mapping[str, Any]) -> Path:
    """Require the receipt's own wheel beside it, hash-verified, before any write."""

    wheel_path = receipt_path.parent / receipt["build"]["wheel_filename"]
    _require_unsymlinked_descent(app_root, wheel_path, "Published wheel")
    _require_contained(app_root, wheel_path, "Published wheel")
    if not wheel_path.is_file():
        raise RuntimeReleaseError(
            f"The approved wheel is not published beside its receipt: {wheel_path}",
            code="approved_runtime_unavailable",
            remediation=PUBLISH_REMEDIATION,
        )
    return _verified_wheel(receipt_path, receipt, wheel_path)


def _require_frozen_install(
    inspection: RuntimeInspection,
    *,
    editable_remediation: str = _INIT_EDITABLE_REMEDIATION,
) -> None:
    """Refuse to act from anything but a verifiable frozen install, receipt aside."""

    blocking = next(
        (finding for finding in inspection.findings if finding.code in _BOOTSTRAP_BLOCKING_CODES),
        None,
    )
    if blocking is not None and blocking.code == "runtime_editable_blocked":
        raise RuntimeReleaseError(
            "The running Meeting Ingest distribution is an editable development install.",
            code="runtime_editable_blocked",
            remediation=editable_remediation,
        )
    if blocking is not None:
        raise RuntimeReleaseError(
            blocking.message, code=blocking.code, remediation=blocking.remediation
        )
    if inspection.install.mode != "frozen_unapproved":
        raise RuntimeReleaseError(
            f"The running Meeting Ingest install mode is not a verifiable frozen install: "
            f"{inspection.install.mode}.",
            code="runtime_install_unknown",
            remediation="Invoke Meeting Ingest from the approved frozen installation.",
        )


def _require_approved_frozen_install(inspection: RuntimeInspection, receipt_path: Path) -> None:
    """Refuse to bootstrap from anything but a frozen install of the receipt's wheel."""

    _require_frozen_install(inspection)
    if not inspection.receipt["match"]:
        raise RuntimeReleaseError(
            "The running Meeting Ingest build does not match the latest approved receipt.",
            code="runtime_build_mismatch",
            remediation=(
                f"Install the approved wheel named by {receipt_path} and run `meeting-ingest init` again."
            ),
        )


def _approved_console_script(inspection: RuntimeInspection) -> Path:
    """Identify the executable by the console script the verified distribution ships."""

    recorded = inspection.executable.get("console_script")
    if not recorded:
        raise RuntimeReleaseError(
            "The running distribution does not record an installed meeting-ingest console script.",
            code="runtime_executable_unidentified",
            remediation="Reinstall Meeting Ingest from the approved wheel so its console script is recorded.",
        )
    script = Path(recorded).resolve(strict=False)
    invoked = Path(inspection.executable["invoked"]).resolve(strict=False)
    if invoked != script:
        raise RuntimeReleaseError(
            f"The invoked command is not the approved console script: {invoked} != {script}",
            code="runtime_executable_mismatch",
            remediation=f"Run {script} directly instead of a wrapper that imports the package.",
        )
    return script


def _require_writable_destination(root: Path, destination: Path, label: str) -> None:
    """Refuse to write through a symlinked directory between the project root and a target."""

    _require_unsymlinked_descent(root, destination.parent, label)


def _require_resolved_workflow_matches(
    inspection: RuntimeInspection,
    installed: WorkflowInstallResult,
    *,
    remediation: str = _INIT_SHADOW_REMEDIATION,
) -> None:
    """Require host resolution to reach the exact artifacts this command just wrote."""

    expected = (
        ("Claude skill", installed.skill_destination, installed.rendered_skill_sha256,
         inspection.workflow.skill_path, inspection.workflow.skill_sha256),
        ("Claude agent", installed.agent_destination, installed.agent_sha256,
         inspection.workflow.agent_path, inspection.workflow.agent_sha256),
    )
    for label, destination, digest, resolved_path, resolved_digest in expected:
        if destination is None:
            continue
        if Path(resolved_path) != destination.resolve(strict=False) or resolved_digest != digest:
            raise RuntimeReleaseError(
                f"The installed {label} is not what this session resolves: {resolved_path}",
                code="workflow_hash_mismatch",
                remediation=remediation,
            )


def _require_installed_workflow_resolves(
    inspection: RuntimeInspection,
    installed: WorkflowInstallResult,
    receipt_path: Path,
) -> None:
    """Require an approved frozen install to resolve the artifacts this bootstrap wrote."""

    _require_approved_frozen_install(inspection, receipt_path)
    _require_resolved_workflow_matches(inspection, installed)


def bootstrap_consumer_runtime(
    root: Path,
    *,
    application_data_root: Path | None = None,
    channel: str = DEFAULT_CHANNEL,
    invoked_executable: str | Path | None = None,
    runtime_inspector: Callable[..., RuntimeInspection] = inspect_runtime,
) -> BootstrappedRuntime:
    """Select, install, and pin the latest approved runtime for an unpinned consumer."""

    root = root.expanduser().resolve(strict=False)
    if runtime_pin_present(root):
        raise RuntimeReleaseError(
            f"This consumer already carries a runtime pin: {root / RUNTIME_PIN_RELATIVE_PATH}",
            code="runtime_pin_present",
            remediation="Repin explicitly with `meeting-ingest runtime pin` when a new build is approved.",
        )
    app_root = (application_data_root or default_application_data_root()).expanduser().resolve(
        strict=False
    )
    receipt_path, receipt_sha256 = _latest_published_receipt(app_root, channel)
    receipt, _ = _reread_receipt(receipt_path, receipt_sha256)

    def inspect(invoked: Path) -> RuntimeInspection:
        return runtime_inspector(
            root,
            invoked_path=invoked,
            application_data_root=app_root,
            receipt_path=receipt_path,
        )

    inspection = inspect(_resolve_executable(invoked_executable))
    _require_approved_frozen_install(inspection, receipt_path)
    executable = _approved_console_script(inspection)
    _require_published_wheel(app_root, receipt_path, receipt)

    templates = packaged_workflow_templates()
    skill_destination = root / CLAUDE_SKILL_PATH
    agent_destination = root / CLAUDE_AGENT_PATH
    pin_path = root / RUNTIME_PIN_RELATIVE_PATH
    _require_writable_destination(root, skill_destination, "Claude skill destination")
    _require_writable_destination(root, agent_destination, "Claude agent destination")
    _require_writable_destination(root, pin_path, "Runtime pin destination")

    installed = install_workflow_artifacts(
        receipt_path,
        template_path=templates.skill_template,
        executable=executable,
        skill_destination=skill_destination,
        agent_path=templates.claude_agent,
        agent_destination=agent_destination,
        expected_receipt_sha256=receipt_sha256,
    )
    _require_installed_workflow_resolves(inspect(executable), installed, receipt_path)

    try:
        pinned = pin_runtime(
            root,
            receipt_path,
            approved_executable=executable,
            invoked_executable=executable,
            application_data_root=app_root,
            channel=channel,
            installed_skill_path=skill_destination,
            claude_agent_path=agent_destination,
            expected_receipt_sha256=receipt_sha256,
            exclusive=True,
        )
    except FileExistsError as exc:
        raise RuntimeReleaseError(
            f"This consumer already carries a runtime pin: {pin_path}",
            code="runtime_pin_present",
            remediation="Repin explicitly with `meeting-ingest runtime pin` when a new build is approved.",
        ) from exc
    return BootstrappedRuntime(
        build_id=pinned.build_id,
        receipt_path=receipt_path,
        pin_path=pinned.pin_path,
        pin_sha256=pinned.pin_sha256,
        skill_destination=skill_destination,
        agent_destination=agent_destination,
        executable=executable,
    )


def _receipt_build_mismatches(inspection: RuntimeInspection) -> tuple[str, ...]:
    """Name the receipt-versus-running-build fields that disagree, the consumer pin aside."""

    comparisons = [
        item
        for item in inspection.receipt["comparisons"]
        if item["field"] in _RECEIPT_BUILD_FIELDS
    ]
    if inspection.receipt["error"] or len(comparisons) != len(_RECEIPT_BUILD_FIELDS):
        return tuple(sorted(_RECEIPT_BUILD_FIELDS))
    return tuple(sorted(item["field"] for item in comparisons if not item["match"]))


def _require_receipt_build_is_running(inspection: RuntimeInspection, receipt_path: Path) -> None:
    """Require the running build to be the receipt's own; the pin still names the old one."""

    mismatched = _receipt_build_mismatches(inspection)
    if mismatched:
        raise RuntimeReleaseError(
            f"The running Meeting Ingest build does not match the approved receipt: "
            f"{', '.join(mismatched)}.",
            code="runtime_build_mismatch",
            remediation=(
                f"Install the approved wheel named by {receipt_path} and run "
                "`meeting-ingest update` from it."
            ),
        )


def _require_existing_pin(root: Path) -> ConsumerPin:
    """Require a prior explicit selection: update moves a consumer, it never adopts one."""

    pin = read_pin(root)
    if not runtime_pin_present(root):
        raise RuntimeReleaseError(
            f"This consumer carries no runtime pin: {pin.path}",
            code="runtime_pin_missing",
            remediation=INIT_REMEDIATION,
        )
    if not pin.valid:
        raise RuntimeReleaseError(
            f"This consumer's runtime pin is unreadable ({pin.error}): {pin.path}",
            code="runtime_pin_invalid",
            remediation=(
                "Inspect it with `meeting-ingest runtime inspect`, then repin explicitly with "
                "`meeting-ingest runtime pin --receipt <path> --root <consumer-root>`."
            ),
        )
    return pin


def _install_published_wheel(
    wheel_path: Path, *, expected_sha256: str, runner: CommandRunner
) -> tuple[str, ...]:
    """Install one wheel staged under its verified bytes; the store copy may change after."""

    if not wheel_path.is_absolute() or wheel_path.name.startswith("-"):
        raise RuntimeReleaseError(
            f"Approved wheel path is not safe to install: {wheel_path}",
            code="runtime_path_unsafe",
            remediation="Republish the approved runtime into an unredirected application data root.",
        )
    reported = (*UV_TOOL_INSTALL_COMMAND, str(wheel_path))
    with tempfile.TemporaryDirectory(prefix="meeting-ingest-approved-wheel-") as staging:
        staged = Path(staging) / wheel_path.name
        _copy_immutable(wheel_path, staged, expected_sha256)
        try:
            runner(
                [*UV_TOOL_INSTALL_COMMAND, str(staged)],
                check=True,
                capture_output=True,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            detail = str(getattr(exc, "stderr", None) or exc).strip()
            raise RuntimeReleaseError(
                f"Installing the approved wheel failed: {detail}",
                code="runtime_install_failed",
                remediation=f"Run `{' '.join(reported)}` directly, then run the command again.",
            ) from exc
    return reported


def _update_command(executable: Path, root: Path) -> list[str]:
    return [str(executable), "update", "--root", str(root), "--json"]


@contextmanager
def _converging_update(root: Path, previous_build_id: str):
    """Keep the failing step's own next action and add the rerun that converges from it."""
    try:
        yield
    except RuntimeReleaseError as exc:
        original = exc.details.get("remediation") if isinstance(exc.details, dict) else None
        rerun = (
            f"run `meeting-ingest update --root {root}` again; this consumer still selects "
            f"{previous_build_id}."
        )
        raise RuntimeReleaseError(
            exc.message,
            code=exc.code,
            remediation=(
                f"{original} Then {rerun}" if original else f"{rerun[0].upper()}{rerun[1:]}"
            ),
        ) from exc


def _update_readiness(root: Path, inspection: RuntimeInspection) -> ReadinessResult:
    """Diagnose whatever this consumer is left with without discarding a completed update."""

    return assess_readiness(root, operation="update", runtime_inspector=lambda _: inspection)


def _update_summary(
    *,
    updated: bool,
    build_id: str,
    previous_build_id: str,
    receipt_path: Path,
    pin_path: Path,
    pin_sha256: str | None,
    executable: Path,
    installed: WorkflowInstallResult | None,
    readiness: ReadinessResult,
) -> RunSummary:
    severity_counts = Counter(finding.severity for finding in readiness.findings)
    blocked = readiness.verdict == "blocked"
    return with_runtime_provenance(
        RunSummary(
            status="blocked" if blocked else ("success" if updated else "no_op"),
            exit_code=readiness.exit_code,
            details={
                "command": "runtime_update",
                "updated": updated,
                "delegated": False,
                "build_id": build_id,
                "previous_build_id": previous_build_id,
                "receipt_path": str(receipt_path),
                "pin_path": str(pin_path),
                "pin_sha256": pin_sha256,
                "executable": str(executable),
                "skill_destination": (
                    str(installed.skill_destination) if installed is not None else None
                ),
                "agent_destination": (
                    str(installed.agent_destination)
                    if installed is not None and installed.agent_destination is not None
                    else None
                ),
                "verdict": readiness.verdict,
                "finding_counts": {"by_severity": dict(sorted(severity_counts.items()))},
                "findings": [finding.to_dict() for finding in readiness.findings],
            },
        ),
        readiness,
    )


def _relayed_summary(payload: Mapping[str, Any]) -> RunSummary:
    """Carry a delegated child's own result, verdict and exit code included, unedited."""

    details = {key: value for key, value in payload.items() if key not in RESERVED_KEYS}
    provenance = payload.get("runtime_provenance")
    if details.get("command") == "runtime_update":
        details["delegated"] = True
    return RunSummary(
        schema_version=str(payload.get("schema_version", "1.1")),
        status=str(payload["status"]),
        exit_code=int(payload["exit_code"]),
        warnings=list(payload.get("warnings") or []),
        errors=list(payload.get("errors") or []),
        runtime_provenance=provenance if isinstance(provenance, dict) else None,
        details=details,
    )


def _delegate_update(root: Path, executable: Path, *, runner: CommandRunner) -> RunSummary:
    """Hand the rest of this update to the build that ships the receipt's own templates."""

    command = _update_command(executable, root)
    remediation = f"Run `{' '.join(command)}` directly to see what the new build reports."
    try:
        completed = runner(
            command,
            check=False,
            capture_output=True,
            text=True,
            env={**os.environ, UPDATE_DELEGATION_MARKER: "1"},
        )
        payload = json.loads(completed.stdout)
    except (OSError, json.JSONDecodeError, UnicodeError) as exc:
        detail = str(getattr(exc, "stderr", None) or exc).strip()
        raise RuntimeReleaseError(
            f"The installed Meeting Ingest build did not report an update result: {detail}",
            code="runtime_update_delegation_failed",
            remediation=remediation,
        ) from exc
    if (
        not isinstance(payload, dict)
        or not isinstance(payload.get("status"), str)
        or not isinstance(payload.get("exit_code"), int)
    ):
        raise RuntimeReleaseError(
            "The installed Meeting Ingest build reported an unusable update result",
            code="runtime_update_delegation_failed",
            remediation=remediation,
        )
    if completed.returncode != payload["exit_code"]:
        raise RuntimeReleaseError(
            f"The installed Meeting Ingest build exited with {completed.returncode} but "
            f"reported exit code {payload['exit_code']}",
            code="runtime_update_delegation_failed",
            remediation=remediation,
        )
    return _relayed_summary(payload)


def _complete_update(
    root: Path,
    inspection: RuntimeInspection,
    *,
    inspect: Callable[[Path], RuntimeInspection],
    receipt_path: Path,
    receipt_sha256: str,
    application_data_root: Path,
    channel: str,
    previous_build_id: str,
) -> RunSummary:
    """Render, install, and select the running build for one consumer, then diagnose it."""

    with _converging_update(root, previous_build_id):
        executable = _approved_console_script(inspection)
        templates = packaged_workflow_templates()
        skill_destination = root / CLAUDE_SKILL_PATH
        agent_destination = root / CLAUDE_AGENT_PATH
        pin_path = root / RUNTIME_PIN_RELATIVE_PATH
        _require_writable_destination(root, skill_destination, "Claude skill destination")
        _require_writable_destination(root, agent_destination, "Claude agent destination")
        _require_writable_destination(root, pin_path, "Runtime pin destination")

        installed = install_workflow_artifacts(
            receipt_path,
            template_path=templates.skill_template,
            executable=executable,
            skill_destination=skill_destination,
            agent_path=templates.claude_agent,
            agent_destination=agent_destination,
            expected_receipt_sha256=receipt_sha256,
        )
        _require_resolved_workflow_matches(
            inspect(executable), installed, remediation=_UPDATE_SHADOW_REMEDIATION
        )

        pinned = pin_runtime(
            root,
            receipt_path,
            approved_executable=executable,
            invoked_executable=executable,
            application_data_root=application_data_root,
            channel=channel,
            installed_skill_path=skill_destination,
            claude_agent_path=agent_destination,
            expected_receipt_sha256=receipt_sha256,
        )
    return _update_summary(
        updated=True,
        build_id=pinned.build_id,
        previous_build_id=previous_build_id,
        receipt_path=receipt_path,
        pin_path=pinned.pin_path,
        pin_sha256=pinned.pin_sha256,
        executable=executable,
        installed=installed,
        readiness=_update_readiness(root, inspect(executable)),
    )


def update_consumer_runtime(
    root: Path,
    *,
    application_data_root: Path | None = None,
    invoked_executable: str | Path | None = None,
    runtime_inspector: Callable[..., RuntimeInspection] = inspect_runtime,
    command_runner: CommandRunner = subprocess.run,
) -> RunSummary:
    """Move one explicitly named pinned consumer to the channel-latest approved runtime."""

    root = root.expanduser().resolve(strict=False)
    pin = _require_existing_pin(root)
    previous_build_id = str(pin.values["approved_build_id"])
    channel = str(pin.values["channel"])
    app_root = (application_data_root or default_application_data_root()).expanduser().resolve(
        strict=False
    )
    receipt_path, receipt_sha256 = _latest_published_receipt(app_root, channel)
    receipt, _ = _reread_receipt(receipt_path, receipt_sha256)
    wheel_path = _require_published_wheel(app_root, receipt_path, receipt)
    build_id = receipt["build"]["build_id"]

    def inspect(invoked: Path) -> RuntimeInspection:
        return runtime_inspector(
            root,
            invoked_path=invoked,
            application_data_root=app_root,
            receipt_path=receipt_path,
        )

    selected = inspect(_resolve_executable(invoked_executable))
    if previous_build_id == build_id and selected.runtime_mode == "approved":
        return _update_summary(
            updated=False,
            build_id=build_id,
            previous_build_id=previous_build_id,
            receipt_path=receipt_path,
            pin_path=Path(pin.path),
            pin_sha256=pin.sha256,
            executable=Path(selected.executable["invoked"]),
            installed=None,
            readiness=_update_readiness(root, selected),
        )
    _require_frozen_install(selected, editable_remediation=_UPDATE_EDITABLE_REMEDIATION)

    if not _receipt_build_mismatches(selected):
        return _complete_update(
            root,
            selected,
            inspect=inspect,
            receipt_path=receipt_path,
            receipt_sha256=receipt_sha256,
            application_data_root=app_root,
            channel=channel,
            previous_build_id=previous_build_id,
        )
    # This process holds the previous build in memory and can never become the new one, so
    # a delegated run that still mismatches fails instead of installing and handing off again.
    if os.environ.get(UPDATE_DELEGATION_MARKER) == "1":
        _require_receipt_build_is_running(selected, receipt_path)

    # The wheel install is machine-global while the pin is this consumer's alone, so the
    # old pin survives until the new build renders and selects itself for this root.
    _install_published_wheel(
        wheel_path, expected_sha256=receipt["build"]["wheel_sha256"], runner=command_runner
    )
    with _converging_update(root, previous_build_id):
        executable = _locate_console_script(runner=command_runner)
        _require_installed_tool_matches(executable, receipt, runner=command_runner)
        return _delegate_update(root, executable, runner=command_runner)


def _inspect_installed_tool(executable: Path, *, runner: CommandRunner) -> Mapping[str, Any]:
    """Read runtime evidence from the installed console script, not from this process."""

    try:
        completed = runner(
            [str(executable), "runtime", "inspect", "--json"],
            check=True,
            capture_output=True,
            text=True,
        )
        evidence = json.loads(completed.stdout)
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError, UnicodeError) as exc:
        detail = str(getattr(exc, "stderr", None) or exc).strip()
        raise RuntimeReleaseError(
            f"The installed Meeting Ingest tool could not be inspected: {detail}",
            code="runtime_install_unverified",
            remediation=f"Run `{executable} runtime inspect --json` and repair the installation.",
        ) from exc
    if not isinstance(evidence, dict):
        raise RuntimeReleaseError(
            "The installed Meeting Ingest tool did not report an inspection object",
            code="runtime_install_unverified",
            remediation=f"Run `{executable} runtime inspect --json` and repair the installation.",
        )
    return evidence


def _locate_console_script(*, runner: CommandRunner) -> Path:
    """Locate the installed tool by its uv bin directory; PATH can resolve a dev shim first."""

    remediation = (
        "Run `uv tool dir --bin` to find the tool bin directory, then reinstall the approved "
        "wheel with `uv tool install --reinstall <published-wheel-path>`."
    )
    try:
        completed = runner(
            list(UV_TOOL_BIN_COMMAND), check=True, capture_output=True, text=True
        )
        directory = (completed.stdout or "").strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = str(getattr(exc, "stderr", None) or exc).strip()
        raise RuntimeReleaseError(
            f"The uv tool bin directory could not be resolved: {detail}",
            code="runtime_tool_bin_unresolved",
            remediation=remediation,
        ) from exc
    if not directory:
        raise RuntimeReleaseError(
            "uv reported no tool bin directory",
            code="runtime_tool_bin_unresolved",
            remediation=remediation,
        )
    executable = Path(directory).expanduser() / CONSOLE_SCRIPT_NAME
    if not executable.is_file():
        raise RuntimeReleaseError(
            f"The installed {CONSOLE_SCRIPT_NAME} console script is not in the uv tool bin "
            f"directory: {executable}",
            code="runtime_executable_unidentified",
            remediation=remediation,
        )
    return executable.resolve(strict=False)


def _require_installed_tool_matches(
    executable: Path, receipt: Mapping[str, Any], *, runner: CommandRunner
) -> None:
    """Verify the installed tool against the receipt out of process, not in this one."""

    evidence = _inspect_installed_tool(executable, runner=runner)
    build = evidence.get("build") if isinstance(evidence.get("build"), dict) else {}
    distribution = (
        evidence.get("distribution") if isinstance(evidence.get("distribution"), dict) else {}
    )
    reported = evidence.get("executable") if isinstance(evidence.get("executable"), dict) else {}
    mismatches = [
        label
        for label, expected, actual in (
            ("build_id", receipt["build"]["build_id"], build.get("build_id")),
            ("build_kind", "approved-candidate", build.get("build_kind")),
            ("record_integrity", "valid", distribution.get("record_integrity")),
            ("console_script", str(executable), reported.get("console_script")),
        )
        if expected != actual
    ]
    if mismatches:
        raise RuntimeReleaseError(
            f"The installed Meeting Ingest tool does not match the approved receipt: "
            f"{', '.join(mismatches)}",
            code="runtime_install_unverified",
            remediation=f"Reinstall the approved wheel and run `{executable} runtime inspect --json`.",
        )


def install_approved_wheel(
    receipt_path: Path,
    *,
    application_data_root: Path | None = None,
    expected_receipt_sha256: str | None = None,
    expected_wheel_sha256: str | None = None,
    command_runner: CommandRunner = subprocess.run,
) -> InstalledRuntime:
    """Install one published receipt's wheel machine-globally and verify the tool it leaves."""

    app_root = (application_data_root or default_application_data_root()).expanduser().resolve(
        strict=False
    )
    receipt_file = receipt_path.expanduser().absolute()
    _require_unsymlinked_descent(app_root, receipt_file, "Published receipt")
    _require_contained(app_root, receipt_file, "Published receipt")
    receipt, _ = _reread_receipt(receipt_file, expected_receipt_sha256)
    _require_expected_wheel_digest(receipt, expected_wheel_sha256)
    wheel = _require_published_wheel(app_root, receipt_file, receipt)
    command = _install_published_wheel(
        wheel, expected_sha256=receipt["build"]["wheel_sha256"], runner=command_runner
    )

    executable = _locate_console_script(runner=command_runner)
    _require_installed_tool_matches(executable, receipt, runner=command_runner)
    return InstalledRuntime(
        build_id=receipt["build"]["build_id"],
        executable=executable,
        command=command,
    )


def update_consumer_roots(
    consumer_roots: Sequence[Path],
    *,
    executable: Path,
    command_runner: CommandRunner = subprocess.run,
) -> list[dict[str, Any]]:
    """Run the consumer update command, once per explicitly named consumer root."""

    results: list[dict[str, Any]] = []
    for consumer_root in consumer_roots:
        resolved = Path(consumer_root).expanduser().resolve(strict=False)
        command = _update_command(executable, resolved)
        try:
            completed = command_runner(command, check=False, capture_output=True, text=True)
        except OSError as exc:
            results.append(
                {"root": str(resolved), "status": "failed", "summary": None, "error": str(exc)}
            )
            continue
        try:
            summary = json.loads(completed.stdout)
        except (json.JSONDecodeError, UnicodeError):
            summary = None
        # The child's own status never overrides its exit code: a nonzero exit is a failure
        # even when the summary it printed reports otherwise.
        failed = (
            completed.returncode != 0
            or not isinstance(summary, dict)
            or not isinstance(summary.get("status"), str)
        )
        results.append(
            {
                "root": str(resolved),
                "status": "failed" if failed else str(summary["status"]),
                "summary": summary,
                "error": ((completed.stderr or "").strip() or None) if failed else None,
            }
        )
    return results


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
