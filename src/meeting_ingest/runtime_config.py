"""Strict, project-config-independent runtime pin and channel parsing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tomllib
from typing import Any, Mapping


RUNTIME_PIN_RELATIVE_PATH = Path(
    "_local/project-context/meetings/meeting-ingest-runtime.toml"
)
PIN_SCHEMA_VERSION = "1.0"
CHANNEL_SCHEMA_VERSION = "1.0"
PIN_KEYS = frozenset(
    {
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
)
_DIGEST_FIELDS = frozenset(
    {
        "approved_source_tree_sha256",
        "approved_wheel_sha256",
        "approved_receipt_sha256",
        "claude_skill_template_sha256",
        "installed_claude_skill_sha256",
        "claude_agent_sha256",
    }
)
_CHANNEL_KEYS = frozenset({"schema_version", "channel", "latest", "previous", "published_at"})
_LATEST_KEYS = frozenset(
    {"build_id", "source_commit", "wheel_sha256", "receipt_path", "receipt_sha256"}
)
_PREVIOUS_KEYS = frozenset({"build_id", "receipt_path", "receipt_sha256"})
_CHANNEL_NAME = re.compile(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?")
_BUILD_ID = re.compile(r"meeting-ingest-(?P<version>[0-9A-Za-z][0-9A-Za-z.+]*)-g(?P<commit>[0-9a-f]{12})-s(?P<tree>[0-9a-f]{12})")


class RuntimeConfigError(ValueError):
    """Raised when runtime selection metadata violates its frozen schema."""


@dataclass(frozen=True)
class ConsumerPin:
    path: str
    sha256: str | None
    values: Mapping[str, Any] = field(default_factory=dict)
    valid: bool = False
    error: str | None = None


@dataclass(frozen=True)
class ChannelManifest:
    path: str
    values: Mapping[str, Any] = field(default_factory=dict)
    valid: bool = False
    error: str | None = None


def sha256_bytes(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and value.startswith("sha256:")
        and len(value) == 71
        and all(character in "0123456789abcdef" for character in value[7:])
    )


def is_full_commit(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 40
        and all(character in "0123456789abcdef" for character in value)
    )


def validate_build_id(
    value: Any,
    *,
    semantic_version: str | None = None,
    source_commit: str | None = None,
    source_tree_sha256: str | None = None,
) -> str:
    if not isinstance(value, str):
        raise RuntimeConfigError("build_id is invalid")
    match = _BUILD_ID.fullmatch(value)
    if match is None:
        raise RuntimeConfigError("build_id is invalid")
    if semantic_version is not None and match.group("version") != semantic_version:
        raise RuntimeConfigError("build_id semantic version does not match")
    if source_commit is not None and match.group("commit") != source_commit[:12]:
        raise RuntimeConfigError("build_id source commit does not match")
    if source_tree_sha256 is not None and match.group("tree") != source_tree_sha256[7:19]:
        raise RuntimeConfigError("build_id source tree does not match")
    return value


def require_utc_timestamp(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise RuntimeConfigError(f"{field_name} must be a non-empty UTC RFC 3339 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeConfigError(f"{field_name} must be a UTC RFC 3339 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise RuntimeConfigError(f"{field_name} must identify a UTC instant")
    return parsed.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _require_exact_keys(values: Mapping[str, Any], expected: frozenset[str], label: str) -> None:
    unknown = set(values) - expected
    missing = expected - set(values)
    errors: list[str] = []
    if unknown:
        errors.append(f"unknown keys: {', '.join(sorted(unknown))}")
    if missing:
        errors.append(f"missing keys: {', '.join(sorted(missing))}")
    if errors:
        raise RuntimeConfigError(f"{label} has {'; '.join(errors)}")


def validate_pin(values: Mapping[str, Any]) -> dict[str, str]:
    _require_exact_keys(values, PIN_KEYS, "Runtime pin")
    if values.get("schema_version") != PIN_SCHEMA_VERSION:
        raise RuntimeConfigError(f"schema_version must be {PIN_SCHEMA_VERSION}")
    for field_name in _DIGEST_FIELDS:
        if not is_sha256(values.get(field_name)):
            raise RuntimeConfigError(f"{field_name} must be a sha256 digest")
    if not is_full_commit(values.get("approved_source_commit")):
        raise RuntimeConfigError("approved_source_commit must be a full lowercase Git commit")
    validate_build_id(
        values.get("approved_build_id"),
        source_commit=str(values.get("approved_source_commit")),
        source_tree_sha256=str(values.get("approved_source_tree_sha256")),
    )
    if _CHANNEL_NAME.fullmatch(str(values.get("channel"))) is None:
        raise RuntimeConfigError("channel must use lowercase letters, digits, and interior hyphens")
    executable = values.get("approved_executable")
    if not isinstance(executable, str) or not executable or not Path(executable).is_absolute():
        raise RuntimeConfigError("approved_executable must be absolute")
    string_fields = PIN_KEYS - _DIGEST_FIELDS - {"approved_source_commit", "approved_executable"}
    for field_name in string_fields:
        if not isinstance(values.get(field_name), str) or not values[field_name]:
            raise RuntimeConfigError(f"{field_name} must be a non-empty string")
    normalized = {key: str(values[key]) for key in PIN_KEYS}
    normalized["approved_at"] = require_utc_timestamp(values["approved_at"], "approved_at")
    return normalized


def parse_pin(payload: bytes) -> dict[str, str]:
    try:
        values = tomllib.loads(payload.decode("utf-8"))
    except (UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise RuntimeConfigError(f"Invalid runtime pin TOML: {exc}") from exc
    if not isinstance(values, dict):
        raise RuntimeConfigError("Runtime pin must contain a TOML table")
    return validate_pin(values)


def read_pin(root: Path) -> ConsumerPin:
    path = root.expanduser().resolve(strict=False) / RUNTIME_PIN_RELATIVE_PATH
    if path.is_symlink() or not path.is_file():
        return ConsumerPin(path=str(path), sha256=None, error="missing")
    try:
        payload = path.read_bytes()
        values = parse_pin(payload)
    except (OSError, RuntimeConfigError) as exc:
        digest = None
        try:
            digest = sha256_file(path)
        except OSError:
            pass
        return ConsumerPin(path=str(path), sha256=digest, error=str(exc))
    return ConsumerPin(path=str(path), sha256=sha256_bytes(payload), values=values, valid=True)


def serialize_pin(values: Mapping[str, Any]) -> bytes:
    normalized = validate_pin(values)
    ordered = [
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
    ]
    return ("\n".join(f"{key} = {json.dumps(normalized[key])}" for key in ordered) + "\n").encode(
        "utf-8"
    )


def _validate_receipt_path(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise RuntimeConfigError(f"{field_name} must be an application-data-relative POSIX path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise RuntimeConfigError(f"{field_name} must be an application-data-relative POSIX path")
    if len(path.parts) != 3 or path.parts[0] != "releases" or path.name != "receipt.json":
        raise RuntimeConfigError(f"{field_name} must identify releases/<build-id>/receipt.json")
    return path.as_posix()


def _validate_channel_entry(value: Any, *, latest: bool) -> dict[str, str]:
    label = "Channel latest" if latest else "Channel previous entry"
    if not isinstance(value, dict):
        raise RuntimeConfigError(f"{label} must be an object")
    expected = _LATEST_KEYS if latest else _PREVIOUS_KEYS
    _require_exact_keys(value, expected, label)
    for field_name in expected:
        if not isinstance(value.get(field_name), str) or not value[field_name]:
            raise RuntimeConfigError(f"{label} {field_name} must be a non-empty string")
    if latest and not is_full_commit(value["source_commit"]):
        raise RuntimeConfigError("Channel latest source_commit must be a full lowercase Git commit")
    for field_name in ({"wheel_sha256", "receipt_sha256"} if latest else {"receipt_sha256"}):
        if not is_sha256(value[field_name]):
            raise RuntimeConfigError(f"Channel {field_name} must be a sha256 digest")
    result = {key: str(value[key]) for key in expected}
    validate_build_id(
        result["build_id"],
        source_commit=result.get("source_commit"),
    )
    result["receipt_path"] = _validate_receipt_path(value["receipt_path"], f"{label} receipt_path")
    if PurePosixPath(result["receipt_path"]).parts[1] != result["build_id"]:
        raise RuntimeConfigError(f"{label} receipt_path must use its build_id directory")
    return result


def validate_channel(values: Mapping[str, Any], *, expected_channel: str | None = None) -> dict[str, Any]:
    _require_exact_keys(values, _CHANNEL_KEYS, "Channel manifest")
    if values.get("schema_version") != CHANNEL_SCHEMA_VERSION:
        raise RuntimeConfigError(f"Channel schema_version must be {CHANNEL_SCHEMA_VERSION}")
    channel = values.get("channel")
    if not isinstance(channel, str) or _CHANNEL_NAME.fullmatch(channel) is None:
        raise RuntimeConfigError("Channel name must use lowercase letters, digits, and interior hyphens")
    if expected_channel is not None and channel != expected_channel:
        raise RuntimeConfigError(f"Channel manifest names {channel!r}, expected {expected_channel!r}")
    previous = values.get("previous")
    if not isinstance(previous, list):
        raise RuntimeConfigError("Channel previous must be an array")
    latest = _validate_channel_entry(values.get("latest"), latest=True)
    normalized_previous = [_validate_channel_entry(entry, latest=False) for entry in previous]
    identifiers = [latest["build_id"], *(entry["build_id"] for entry in normalized_previous)]
    if len(identifiers) != len(set(identifiers)):
        raise RuntimeConfigError("Channel entries must have unique build_id values")
    return {
        "schema_version": CHANNEL_SCHEMA_VERSION,
        "channel": channel,
        "latest": latest,
        "previous": normalized_previous,
        "published_at": require_utc_timestamp(values.get("published_at"), "published_at"),
    }


def parse_channel(payload: bytes, *, expected_channel: str | None = None) -> dict[str, Any]:
    try:
        value = json.loads(payload)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeConfigError(f"Invalid channel JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeConfigError("Channel manifest must contain an object")
    return validate_channel(value, expected_channel=expected_channel)


def read_channel(application_data_root: Path, channel: str) -> ChannelManifest:
    if _CHANNEL_NAME.fullmatch(channel) is None:
        path = application_data_root.expanduser().resolve(strict=False) / "channels"
        return ChannelManifest(path=str(path), error="invalid channel name")
    path = (application_data_root.expanduser().resolve(strict=False) / "channels" / f"{channel}.json")
    if path.is_symlink() or not path.is_file():
        return ChannelManifest(path=str(path), error="missing")
    try:
        values = parse_channel(path.read_bytes(), expected_channel=channel)
    except (OSError, RuntimeConfigError) as exc:
        return ChannelManifest(path=str(path), error=str(exc))
    return ChannelManifest(path=str(path), values=values, valid=True)


def serialize_channel(values: Mapping[str, Any]) -> bytes:
    normalized = validate_channel(values)
    return (json.dumps(normalized, indent=2, sort_keys=True) + "\n").encode("utf-8")
