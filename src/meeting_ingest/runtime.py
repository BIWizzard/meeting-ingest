"""Read-only inspection of the running Meeting Ingest installation."""

from __future__ import annotations

import base64
import csv
from dataclasses import asdict, dataclass, field
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib
from typing import Any, Callable, Mapping
from urllib.parse import unquote, urlparse

from meeting_ingest._build_info import BUILD_INFO
from meeting_ingest.run_summary import RunSummary


RUNTIME_PIN_RELATIVE_PATH = Path(
    "_local/project-context/meetings/meeting-ingest-runtime.toml"
)
CLAUDE_SKILL_PATH = Path(".claude/skills/meeting-ingest/SKILL.md")
CLAUDE_AGENT_PATH = Path(
    ".claude/agents/meeting-ingest-session-provider.md"
)
PIN_KEYS = {
    "schema_version",
    "channel",
    "approved_build_id",
    "approved_source_commit",
    "approved_source_tree_sha256",
    "approved_wheel_sha256",
    "approved_receipt_sha256",
    "approved_executable",
    "workflow_contract_version",
    "claude_skill_template_sha256",
    "installed_claude_skill_sha256",
    "claude_agent_sha256",
    "approved_at",
}
CommandRunner = Callable[..., subprocess.CompletedProcess[str]]
_AUTO_DISTRIBUTION = object()


@dataclass(frozen=True)
class BuildIdentity:
    schema_version: str
    semantic_version: str
    build_id: str
    source_commit: str | None
    source_tree_sha256: str | None
    workflow_contract_version: str
    build_kind: str

    @classmethod
    def embedded(cls) -> BuildIdentity:
        return cls(**BUILD_INFO)


@dataclass(frozen=True)
class InstallEvidence:
    mode: str
    editable_root: str | None = None
    git_commit: str | None = None
    git_dirty: bool | None = None
    inspection_status: str = "complete"
    inspection_error: str | None = None


@dataclass(frozen=True)
class WorkflowEvidence:
    contract_version: str
    skill_path: str
    skill_sha256: str | None
    agent_path: str
    agent_sha256: str | None
    match: bool


@dataclass(frozen=True)
class ConsumerPin:
    path: str
    sha256: str | None
    values: Mapping[str, Any] = field(default_factory=dict)
    valid: bool = False
    error: str | None = None


@dataclass(frozen=True)
class RuntimeProvenance:
    semantic_version: str
    build_id: str
    source_commit: str | None
    source_tree_sha256: str | None
    install_mode: str
    runtime_mode: str
    workflow_contract_version: str
    development_override_reason: str | None = None


@dataclass(frozen=True)
class ReadinessFinding:
    code: str
    category: str
    severity: str
    message: str
    path: str | None
    remediation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReadinessResult:
    verdict: str
    exit_code: int
    runtime_provenance: RuntimeProvenance
    findings: tuple[ReadinessFinding, ...] = ()


@dataclass(frozen=True)
class RuntimeInspection:
    executable: Mapping[str, str]
    build: BuildIdentity
    distribution: Mapping[str, Any]
    install: InstallEvidence
    receipt: Mapping[str, Any]
    pin: Mapping[str, Any]
    workflow: WorkflowEvidence
    channel: Mapping[str, Any]
    runtime_mode: str
    findings: tuple[ReadinessFinding, ...]
    runtime_provenance: RuntimeProvenance

    def to_dict(self) -> dict[str, Any]:
        return {
            "executable": dict(self.executable),
            "build": asdict(self.build),
            "distribution": dict(self.distribution),
            "install": asdict(self.install),
            "receipt": dict(self.receipt),
            "pin": dict(self.pin),
            "workflow": asdict(self.workflow),
            "channel": dict(self.channel),
            "runtime_mode": self.runtime_mode,
            "findings": [finding.to_dict() for finding in self.findings],
            "runtime_provenance": asdict(self.runtime_provenance),
        }


def _sha256_bytes(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and value.startswith("sha256:")
        and len(value) == 71
        and all(character in "0123456789abcdef" for character in value[7:])
    )


def _resolved_invoked_path(value: str | Path | None) -> Path:
    raw = os.fspath(value) if value is not None else sys.argv[0]
    candidate = Path(raw).expanduser()
    if candidate.parent != Path(".") or candidate.is_absolute():
        return candidate.resolve(strict=False)
    found = shutil.which(raw)
    return Path(found).resolve(strict=False) if found else candidate.resolve(strict=False)


def _distribution_path(distribution: Any) -> Path | None:
    private_path = getattr(distribution, "_path", None)
    if private_path is not None:
        return Path(private_path).resolve(strict=False)
    for package_path in distribution.files or ():
        if str(package_path).endswith(".dist-info/METADATA"):
            return Path(distribution.locate_file(package_path)).parent.resolve(strict=False)
    return None


def _read_direct_url(distribution: Any) -> tuple[dict[str, Any] | None, str | None]:
    raw = distribution.read_text("direct_url.json")
    if raw is None:
        return None, None
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        return None, f"Invalid direct_url.json: {exc}"
    if not isinstance(value, dict):
        return None, "Invalid direct_url.json: top-level value must be an object"
    return value, None


def _record_root(distribution: Any, dist_path: Path) -> Path:
    try:
        return Path(distribution.locate_file("")).resolve(strict=False)
    except (AttributeError, TypeError):
        return dist_path.parent


def _record_integrity(distribution: Any, dist_path: Path) -> tuple[str, list[str]]:
    record_path = dist_path / "RECORD"
    if record_path.is_symlink() or not record_path.is_file():
        return "missing", [f"Missing distribution RECORD: {record_path}"]
    root = _record_root(distribution, dist_path)
    errors: list[str] = []
    try:
        rows = list(csv.reader(record_path.read_text(encoding="utf-8").splitlines()))
    except (OSError, UnicodeError, csv.Error) as exc:
        return "invalid", [f"Unable to read distribution RECORD: {exc}"]
    if not rows:
        return "invalid", ["Distribution RECORD is empty"]
    for row in rows:
        if len(row) != 3 or not row[0]:
            errors.append("Distribution RECORD contains a malformed row")
            continue
        unresolved_target = root / Path(row[0])
        target = unresolved_target.resolve(strict=False)
        if unresolved_target.is_symlink() or not target.is_file():
            errors.append(f"Installed file is missing or invalid: {row[0]}")
            continue
        if not row[1]:
            if target != record_path.resolve(strict=False):
                errors.append(f"Installed file has no RECORD hash: {row[0]}")
            continue
        try:
            algorithm, encoded = row[1].split("=", 1)
            digest = hashlib.new(algorithm, target.read_bytes()).digest()
            actual = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
        except (ValueError, OSError) as exc:
            errors.append(f"Unable to verify installed file {row[0]}: {exc}")
            continue
        if actual != encoded:
            errors.append(f"RECORD hash mismatch: {row[0]}")
        if row[2]:
            try:
                expected_size = int(row[2])
            except ValueError:
                errors.append(f"Invalid RECORD size: {row[0]}")
            else:
                if target.stat().st_size != expected_size:
                    errors.append(f"RECORD size mismatch: {row[0]}")
    return ("invalid", errors) if errors else ("valid", [])


def _file_url_path(value: Any) -> Path | None:
    if not isinstance(value, str):
        return None
    parsed = urlparse(value)
    if parsed.scheme != "file" or parsed.netloc not in {"", "localhost"}:
        return None
    return Path(unquote(parsed.path)).resolve(strict=False)


def _inspect_git(
    editable_root: Path,
    *,
    runner: CommandRunner,
) -> InstallEvidence:
    try:
        repository = runner(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=editable_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        repository_path = Path(repository).resolve(strict=True)
        commit = runner(
            ["git", "rev-parse", "HEAD"],
            cwd=repository_path,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        status = runner(
            ["git", "status", "--porcelain", "--untracked-files=normal"],
            cwd=repository_path,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError, RuntimeError) as exc:
        detail = getattr(exc, "stderr", None) or str(exc)
        return InstallEvidence(
            mode="editable",
            editable_root=str(editable_root),
            inspection_status="error",
            inspection_error=str(detail).strip(),
        )
    if len(commit) != 40 or any(character not in "0123456789abcdef" for character in commit):
        return InstallEvidence(
            mode="editable",
            editable_root=str(repository_path),
            inspection_status="error",
            inspection_error="Git returned a non-canonical commit identifier",
        )
    return InstallEvidence(
        mode="editable",
        editable_root=str(repository_path),
        git_commit=commit,
        git_dirty=bool(status),
    )


def _read_pin(root: Path) -> ConsumerPin:
    path = (root / RUNTIME_PIN_RELATIVE_PATH).resolve(strict=False)
    if not path.is_file():
        return ConsumerPin(path=str(path), sha256=None, error="missing")
    try:
        payload = path.read_bytes()
        values = tomllib.loads(payload.decode("utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        return ConsumerPin(path=str(path), sha256=None, error=str(exc))
    if not isinstance(values, dict):
        return ConsumerPin(path=str(path), sha256=_sha256_bytes(payload), error="invalid")
    unknown = set(values) - PIN_KEYS
    missing = PIN_KEYS - set(values)
    validation_errors: list[str] = []
    if unknown:
        validation_errors.append(f"unknown keys: {', '.join(sorted(unknown))}")
    if missing:
        validation_errors.append(f"missing keys: {', '.join(sorted(missing))}")
    if values.get("schema_version") != "1.0":
        validation_errors.append("schema_version must be 1.0")
    digest_fields = {
        "approved_source_tree_sha256",
        "approved_wheel_sha256",
        "approved_receipt_sha256",
        "claude_skill_template_sha256",
        "installed_claude_skill_sha256",
        "claude_agent_sha256",
    }
    for field_name in digest_fields:
        if not _is_sha256(values.get(field_name)):
            validation_errors.append(f"{field_name} must be a sha256 digest")
    commit = values.get("approved_source_commit")
    if not (
        isinstance(commit, str)
        and len(commit) == 40
        and all(character in "0123456789abcdef" for character in commit)
    ):
        validation_errors.append("approved_source_commit must be a full lowercase Git commit")
    executable = values.get("approved_executable")
    if not isinstance(executable, str) or not Path(executable).is_absolute():
        validation_errors.append("approved_executable must be absolute")
    string_fields = PIN_KEYS - digest_fields - {"approved_source_commit", "approved_executable"}
    for field_name in string_fields:
        if not isinstance(values.get(field_name), str) or not values[field_name]:
            validation_errors.append(f"{field_name} must be a non-empty string")
    if validation_errors:
        return ConsumerPin(
            path=str(path),
            sha256=_sha256_bytes(payload),
            values=values,
            error="; ".join(validation_errors),
        )
    return ConsumerPin(
        path=str(path),
        sha256=_sha256_bytes(payload),
        values=values,
        valid=True,
    )


def _comparison(field: str, expected: Any, actual: Any) -> dict[str, Any]:
    return {
        "field": field,
        "expected": expected,
        "actual": actual,
        "match": expected == actual,
    }


def _executable_comparison(expected: Any, actual: str) -> dict[str, Any]:
    resolved_expected = (
        str(Path(expected).expanduser().resolve(strict=False))
        if isinstance(expected, str) and Path(expected).is_absolute()
        else None
    )
    return {
        "field": "approved_executable",
        "expected": expected,
        "resolved_expected": resolved_expected,
        "actual": actual,
        "match": resolved_expected == actual,
    }


def _default_application_data_root() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/meeting-ingest"
    xdg_data = os.environ.get("XDG_DATA_HOME")
    return (Path(xdg_data) if xdg_data else Path.home() / ".local/share") / "meeting-ingest"


def _read_channel(application_data_root: Path, channel_name: str) -> dict[str, Any]:
    path = application_data_root / "channels" / f"{channel_name}.json"
    result: dict[str, Any] = {
        "name": channel_name,
        "path": str(path.resolve(strict=False)),
        "available": False,
        "update_available": False,
    }
    if not path.is_file():
        return result
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        result["error"] = str(exc)
        return result
    if not isinstance(value, dict):
        result["error"] = "Channel manifest must contain an object"
        return result
    result.update({"available": True, "manifest": value})
    return result


def _locate_receipt(
    application_data_root: Path,
    channel: Mapping[str, Any],
    pin: ConsumerPin,
) -> Path | None:
    expected_digest = pin.values.get("approved_receipt_sha256") if pin.valid else None
    manifest = channel.get("manifest")
    candidates: list[Path] = []
    if isinstance(manifest, dict):
        entries = [manifest.get("latest"), *(manifest.get("previous") or [])]
        for entry in entries:
            if not isinstance(entry, dict) or not isinstance(entry.get("receipt_path"), str):
                continue
            candidate = (application_data_root / entry["receipt_path"]).resolve(strict=False)
            try:
                candidate.relative_to(application_data_root.resolve(strict=False))
            except ValueError:
                continue
            candidates.append(candidate)
    for candidate in candidates:
        if candidate.is_file() and (
            expected_digest is None or _sha256_file(candidate) == expected_digest
        ):
            return candidate
    releases = application_data_root / "releases"
    if expected_digest and releases.is_dir():
        for candidate in sorted(releases.glob("*/receipt.json")):
            if candidate.is_file() and _sha256_file(candidate) == expected_digest:
                return candidate.resolve(strict=False)
    return None


def _read_receipt(path: Path | None) -> tuple[dict[str, Any] | None, str | None, str | None]:
    if path is None:
        return None, None, "missing"
    try:
        payload = path.read_bytes()
        value = json.loads(payload)
    except (OSError, json.JSONDecodeError, UnicodeError) as exc:
        return None, None, str(exc)
    if not isinstance(value, dict):
        return None, _sha256_bytes(payload), "Receipt must contain an object"
    errors: list[str] = []
    if set(value) != {
        "schema_version",
        "build",
        "workflow",
        "verification",
        "approved_by",
        "approved_at",
    }:
        errors.append("Receipt top-level keys do not match schema 1.0")
    if value.get("schema_version") != "1.0":
        errors.append("Receipt schema_version must be 1.0")
    build = value.get("build")
    if not isinstance(build, dict) or set(build) != {
        "semantic_version",
        "build_id",
        "source_commit",
        "source_tree_sha256",
        "wheel_filename",
        "wheel_sha256",
    }:
        errors.append("Receipt build evidence is incomplete")
    elif not _is_sha256(build.get("source_tree_sha256")) or not _is_sha256(
        build.get("wheel_sha256")
    ):
        errors.append("Receipt build digests are invalid")
    workflow = value.get("workflow")
    if not isinstance(workflow, dict) or set(workflow) != {
        "contract_version",
        "claude_skill_template_sha256",
        "claude_agent_sha256",
    }:
        errors.append("Receipt workflow evidence is incomplete")
    elif not _is_sha256(workflow.get("claude_skill_template_sha256")) or not _is_sha256(
        workflow.get("claude_agent_sha256")
    ):
        errors.append("Receipt workflow digests are invalid")
    verification = value.get("verification")
    if verification != {
        "source_commit_reviewed": True,
        "full_suite_passed": True,
        "reproducible_wheel_verified": True,
    }:
        errors.append("Receipt verification evidence is incomplete")
    if not isinstance(value.get("approved_by"), str) or not value["approved_by"]:
        errors.append("Receipt approved_by is missing")
    if not isinstance(value.get("approved_at"), str) or not value["approved_at"]:
        errors.append("Receipt approved_at is missing")
    return value, _sha256_bytes(payload), "; ".join(errors) if errors else None


def _finding(
    code: str,
    message: str,
    remediation: str,
    *,
    path: str | None = None,
) -> ReadinessFinding:
    return ReadinessFinding(
        code=code,
        category="runtime",
        severity="blocker",
        message=message,
        path=path,
        remediation=remediation,
    )


def _advisory(code: str, message: str, remediation: str, *, path: str | None = None) -> ReadinessFinding:
    return ReadinessFinding(
        code=code,
        category="advisory",
        severity="advisory",
        message=message,
        path=path,
        remediation=remediation,
    )


def inspect_runtime(
    root: Path,
    *,
    invoked_path: str | Path | None = None,
    python_path: str | Path | None = None,
    module_path: str | Path | None = None,
    distribution: Any = _AUTO_DISTRIBUTION,
    application_data_root: Path | None = None,
    receipt_path: Path | None = None,
    skill_path: Path | None = None,
    agent_path: Path | None = None,
    runner: CommandRunner = subprocess.run,
) -> RuntimeInspection:
    """Inspect runtime evidence without changing install, Git, or project state."""

    root = root.expanduser().resolve(strict=False)
    invoked = _resolved_invoked_path(invoked_path)
    python = Path(python_path or sys.executable).expanduser().resolve(strict=False)
    module = Path(module_path or Path(__file__).with_name("__init__.py")).expanduser().resolve(strict=False)
    build = BuildIdentity.embedded()
    findings: list[ReadinessFinding] = []
    direct_url: dict[str, Any] | None = None
    record_status = "missing"
    record_errors: list[str] = []
    dist_path: Path | None = None
    dist_version: str | None = None
    dist_name: str | None = None
    module_matches_distribution = False
    direct_url_valid = True

    if distribution is _AUTO_DISTRIBUTION:
        try:
            distribution = metadata.distribution("meeting-ingest")
        except metadata.PackageNotFoundError:
            distribution = None
    elif distribution is False:
        distribution = None
    if distribution is not None:
        dist_path = _distribution_path(distribution)
        dist_name = distribution.metadata.get("Name")
        dist_version = distribution.metadata.get("Version")
        direct_url, direct_url_error = _read_direct_url(distribution)
        if direct_url_error:
            direct_url_valid = False
            findings.append(
                _finding(
                    "runtime_install_unknown",
                    direct_url_error,
                    "Reinstall Meeting Ingest from a verifiable wheel or editable checkout.",
                    path=str(dist_path) if dist_path else None,
                )
            )
        if dist_path is not None:
            record_status, record_errors = _record_integrity(distribution, dist_path)
            module_record = dist_path.parent / "meeting_ingest/__init__.py"
            module_matches_distribution = module_record.resolve(strict=False) == module
    metadata_matches_build = (
        isinstance(dist_name, str)
        and dist_name.lower().replace("_", "-") == "meeting-ingest"
        and dist_version == build.semantic_version
    )
    if record_status != "valid":
        findings.append(
            _finding(
                "runtime_package_integrity_failed",
                "Installed package integrity evidence is missing or invalid.",
                "Reinstall the selected Meeting Ingest distribution and inspect it again.",
                path=str(dist_path / "RECORD") if dist_path else None,
            )
        )

    editable = bool(
        direct_url
        and isinstance(direct_url.get("dir_info"), dict)
        and direct_url["dir_info"].get("editable") is True
    )
    if editable:
        editable_root = _file_url_path(direct_url.get("url")) if direct_url else None
        if editable_root is None:
            install = InstallEvidence(
                mode="editable",
                inspection_status="error",
                inspection_error="Editable direct URL does not name a local file path",
            )
        else:
            install = _inspect_git(editable_root, runner=runner)
            source_candidates = {
                (editable_root / "meeting_ingest/__init__.py").resolve(strict=False),
                (editable_root / "src/meeting_ingest/__init__.py").resolve(strict=False),
            }
            module_matches_distribution = module in source_candidates
        findings.append(
            _finding(
                "runtime_editable_blocked",
                "The running Meeting Ingest distribution is editable.",
                "Use an approved frozen installation or explicitly authorize development execution.",
                path=install.editable_root,
            )
        )
        if install.inspection_status != "complete":
            findings.append(
                _finding(
                    "runtime_git_uninspectable",
                    "Editable source Git state could not be inspected.",
                    "Restore Git access and inspect the editable source before development execution.",
                    path=install.editable_root,
                )
            )
        if not module_matches_distribution or not metadata_matches_build:
            install = InstallEvidence(
                mode="unknown",
                editable_root=install.editable_root,
                git_commit=install.git_commit,
                git_dirty=install.git_dirty,
                inspection_status="error",
                inspection_error="Imported module or package metadata does not match the distribution",
            )
            findings.append(
                _finding(
                    "runtime_install_unknown",
                    "The imported module or package metadata does not match the editable distribution.",
                    "Invoke Meeting Ingest from the editable distribution named by direct_url.json.",
                    path=str(module),
                )
            )
    elif (
        distribution is None
        or dist_path is None
        or not module_matches_distribution
        or not metadata_matches_build
        or not direct_url_valid
    ):
        install = InstallEvidence(
            mode="unknown",
            inspection_status="error",
            inspection_error="Imported module does not match the installed distribution",
        )
        if not any(finding.code == "runtime_install_unknown" for finding in findings):
            findings.append(
                _finding(
                    "runtime_install_unknown",
                    "The running Meeting Ingest install mode could not be verified.",
                    "Invoke Meeting Ingest from a verifiable frozen or editable installation.",
                    path=str(module),
                )
            )
    else:
        install = InstallEvidence(mode="frozen_unapproved")

    pin = _read_pin(root)
    if not pin.valid:
        findings.append(
            _finding(
                "runtime_pin_missing" if pin.error == "missing" else "runtime_pin_invalid",
                (
                    "The consumer runtime pin is missing."
                    if pin.error == "missing"
                    else "The consumer runtime pin is invalid."
                ),
                "Install and pin an approved Meeting Ingest receipt for this consumer.",
                path=pin.path,
            )
        )

    app_root = (application_data_root or _default_application_data_root()).expanduser().resolve(strict=False)
    channel_name = str(pin.values.get("channel", "private-alpha"))
    channel = _read_channel(app_root, channel_name)
    if not channel["available"]:
        findings.append(
            _advisory(
                "channel_unavailable",
                "The private runtime channel is unavailable.",
                "Publish a channel manifest to enable explicit update checks.",
                path=str(channel["path"]),
            )
        )
    selected_receipt_path = receipt_path or _locate_receipt(app_root, channel, pin)
    receipt, receipt_sha256, receipt_error = _read_receipt(selected_receipt_path)
    if receipt_error:
        findings.append(
            _finding(
                "runtime_receipt_invalid",
                "The approved-build receipt is missing or invalid.",
                "Publish or restore the receipt named by the consumer pin.",
                path=str(selected_receipt_path) if selected_receipt_path else None,
            )
        )

    home = Path.home()
    resolved_skill = (skill_path or home / CLAUDE_SKILL_PATH).expanduser().resolve(strict=False)
    resolved_agent = (agent_path or home / CLAUDE_AGENT_PATH).expanduser().resolve(strict=False)
    skill_sha = _sha256_file(resolved_skill) if resolved_skill.is_file() else None
    agent_sha = _sha256_file(resolved_agent) if resolved_agent.is_file() else None

    comparisons: list[dict[str, Any]] = []
    if pin.valid:
        comparisons.extend(
            [
                _comparison("approved_build_id", pin.values.get("approved_build_id"), build.build_id),
                _comparison("approved_source_commit", pin.values.get("approved_source_commit"), build.source_commit),
                _comparison(
                    "approved_source_tree_sha256",
                    pin.values.get("approved_source_tree_sha256"),
                    build.source_tree_sha256,
                ),
                _executable_comparison(pin.values.get("approved_executable"), str(invoked)),
                _comparison(
                    "workflow_contract_version",
                    pin.values.get("workflow_contract_version"),
                    build.workflow_contract_version,
                ),
                _comparison("approved_receipt_sha256", pin.values.get("approved_receipt_sha256"), receipt_sha256),
                _comparison(
                    "installed_claude_skill_sha256",
                    pin.values.get("installed_claude_skill_sha256"),
                    skill_sha,
                ),
                _comparison("claude_agent_sha256", pin.values.get("claude_agent_sha256"), agent_sha),
            ]
        )
    receipt_comparisons: list[dict[str, Any]] = []
    if receipt is not None:
        receipt_build = receipt.get("build") if isinstance(receipt.get("build"), dict) else {}
        receipt_workflow = receipt.get("workflow") if isinstance(receipt.get("workflow"), dict) else {}
        receipt_comparisons.extend(
            [
                _comparison("semantic_version", receipt_build.get("semantic_version"), build.semantic_version),
                _comparison("build_id", receipt_build.get("build_id"), build.build_id),
                _comparison("source_commit", receipt_build.get("source_commit"), build.source_commit),
                _comparison("source_tree_sha256", receipt_build.get("source_tree_sha256"), build.source_tree_sha256),
                _comparison(
                    "workflow_contract_version",
                    receipt_workflow.get("contract_version"),
                    build.workflow_contract_version,
                ),
            ]
        )
        if pin.valid:
            receipt_comparisons.extend(
                [
                    _comparison(
                        "approved_wheel_sha256",
                        pin.values.get("approved_wheel_sha256"),
                        receipt_build.get("wheel_sha256"),
                    ),
                    _comparison(
                        "claude_skill_template_sha256",
                        pin.values.get("claude_skill_template_sha256"),
                        receipt_workflow.get("claude_skill_template_sha256"),
                    ),
                    _comparison(
                        "receipt_agent_sha256",
                        pin.values.get("claude_agent_sha256"),
                        receipt_workflow.get("claude_agent_sha256"),
                    ),
                ]
            )
    pin_match = pin.valid and bool(comparisons) and all(item["match"] for item in comparisons)
    receipt_match = receipt is not None and receipt_error is None and bool(receipt_comparisons) and all(
        item["match"] for item in receipt_comparisons
    )
    workflow_match = (
        pin.valid
        and skill_sha is not None
        and agent_sha is not None
        and all(
            item["match"]
            for item in comparisons
            if item["field"]
            in {"workflow_contract_version", "installed_claude_skill_sha256", "claude_agent_sha256"}
        )
        and all(
            item["match"]
            for item in receipt_comparisons
            if item["field"] in {"workflow_contract_version", "claude_skill_template_sha256", "receipt_agent_sha256"}
        )
    )
    if pin.valid and not pin_match:
        if any(item["field"] == "approved_executable" and not item["match"] for item in comparisons):
            findings.append(
                _finding(
                    "runtime_executable_mismatch",
                    "The invoked executable does not match the consumer pin.",
                    "Invoke the absolute executable recorded in the consumer runtime pin.",
                    path=pin.path,
                )
            )
        findings.append(
            _finding(
                "runtime_pin_mismatch",
                "The running runtime evidence does not match the consumer pin.",
                "Install the pinned build or explicitly repin a verified approved receipt.",
                path=pin.path,
            )
        )
    if receipt is not None and receipt_error is None and not receipt_match:
        findings.append(
            _finding(
                "runtime_receipt_mismatch",
                "The approved-build receipt does not match the running build or pin.",
                "Restore the receipt and wheel selected by the consumer pin.",
                path=str(selected_receipt_path),
            )
        )
    contract_mismatch = any(
        not item["match"]
        for item in [*comparisons, *receipt_comparisons]
        if item["field"] == "workflow_contract_version"
    )
    if contract_mismatch:
        findings.append(
            _finding(
                "workflow_contract_mismatch",
                "The running workflow contract version does not match approved evidence.",
                "Install the Claude workflow selected by the approved receipt and consumer pin.",
                path=pin.path,
            )
        )
    if not workflow_match:
        findings.append(
            _finding(
                "workflow_hash_mismatch",
                "The installed Claude workflow does not match the approved runtime evidence.",
                "Install the pinned Claude skill and session-provider agent.",
                path=str(resolved_skill),
            )
        )

    approved = (
        install.mode == "frozen_unapproved"
        and build.build_kind == "approved-candidate"
        and record_status == "valid"
        and pin_match
        and receipt_match
        and workflow_match
    )
    if approved:
        install = InstallEvidence(mode="approved_frozen")
        runtime_mode = "approved"
    elif install.mode == "editable":
        runtime_mode = "development"
    else:
        runtime_mode = "unverified"
    if channel.get("available"):
        latest = channel.get("manifest", {}).get("latest", {})
        channel["update_available"] = bool(
            isinstance(latest, dict)
            and latest.get("build_id")
            and latest.get("build_id") != build.build_id
        )
        if channel["update_available"]:
            findings.append(
                _advisory(
                    "update_available",
                    "A newer approved runtime is available in the selected channel.",
                    "Review the newer receipt and explicitly install and pin it when ready.",
                    path=str(channel["path"]),
                )
            )

    provenance = RuntimeProvenance(
        semantic_version=build.semantic_version,
        build_id=build.build_id,
        source_commit=build.source_commit,
        source_tree_sha256=build.source_tree_sha256,
        install_mode=install.mode,
        runtime_mode=runtime_mode,
        workflow_contract_version=build.workflow_contract_version,
    )
    return RuntimeInspection(
        executable={"invoked": str(invoked), "python": str(python), "module": str(module)},
        build=build,
        distribution={
            "name": dist_name,
            "version": dist_version,
            "path": str(dist_path) if dist_path else None,
            "direct_url": direct_url,
            "record_integrity": record_status,
            "record_errors": record_errors,
            "module_matches_distribution": module_matches_distribution,
            "metadata_matches_build": metadata_matches_build,
        },
        install=install,
        receipt={
            "path": str(selected_receipt_path.resolve(strict=False)) if selected_receipt_path else None,
            "sha256": receipt_sha256,
            "match": receipt_match,
            "error": receipt_error,
            "comparisons": receipt_comparisons,
        },
        pin={
            "path": pin.path,
            "sha256": pin.sha256,
            "match": pin_match,
            "valid": pin.valid,
            "error": pin.error,
            "comparisons": comparisons,
        },
        workflow=WorkflowEvidence(
            contract_version=build.workflow_contract_version,
            skill_path=str(resolved_skill),
            skill_sha256=skill_sha,
            agent_path=str(resolved_agent),
            agent_sha256=agent_sha,
            match=workflow_match,
        ),
        channel=channel,
        runtime_mode=runtime_mode,
        findings=tuple(
            sorted(
                findings,
                key=lambda finding: (
                    {"blocker": 0, "warning": 1, "advisory": 2}[finding.severity],
                    finding.category,
                    finding.code,
                    finding.path or "",
                ),
            )
        ),
        runtime_provenance=provenance,
    )


def inspect_runtime_summary(root: Path, **kwargs: Any) -> RunSummary:
    inspection = inspect_runtime(root, **kwargs)
    details = inspection.to_dict()
    provenance = details.pop("runtime_provenance")
    return RunSummary(
        runtime_provenance=provenance,
        details={
            "command": "runtime_inspect",
            **details,
        }
    )
