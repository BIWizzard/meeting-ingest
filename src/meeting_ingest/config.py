"""Config loading and default config rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import tomllib

from meeting_ingest.errors import ConfigError


SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class PathsConfig:
    root: str = "_local/project-context/meetings"
    inbox: str = "_inbox"
    processed: str = "_processed"
    signals: str = "_signals"
    quarantine: str = "_quarantine"
    derived: str = "_derived"
    cache: str = "_cache"
    ledger: str = "_ledger.jsonl"


@dataclass(frozen=True)
class PrivacyConfig:
    allow_remote_provider: bool = False
    allow_session_provider: bool = False


@dataclass(frozen=True)
class PlaybookConfig:
    min_recurrent_source_events: int = 2
    tracked_verify_after_days: int = 30
    priority_concern_stale_after_days: int = 60
    preference_behavior_response_stale_after_days: int = 90


@dataclass(frozen=True)
class MeetingIngestConfig:
    schema_version: str = SCHEMA_VERSION
    default_mode: str = "summary-plus-verbatim"
    default_provider: str = "mock"
    default_quality: str = "balanced"
    auto_init: bool = False
    reconcile_after_success: bool = True
    cache_normalized_transcript: bool = True
    paths: PathsConfig = field(default_factory=PathsConfig)
    privacy: PrivacyConfig = field(default_factory=PrivacyConfig)
    playbook: PlaybookConfig = field(default_factory=PlaybookConfig)


def default_config_text() -> str:
    return """schema_version = "1.0"
default_mode = "summary-plus-verbatim"
default_provider = "mock"
default_quality = "balanced"
auto_init = false
reconcile_after_success = true
cache_normalized_transcript = true

[paths]
root = "_local/project-context/meetings"
inbox = "_inbox"
processed = "_processed"
signals = "_signals"
quarantine = "_quarantine"
derived = "_derived"
cache = "_cache"
ledger = "_ledger.jsonl"

[privacy]
allow_remote_provider = false
allow_session_provider = false

[playbook]
min_recurrent_source_events = 2
tracked_verify_after_days = 30
priority_concern_stale_after_days = 60
preference_behavior_response_stale_after_days = 90
"""


def write_default_config(path: Path) -> None:
    path.write_text(default_config_text(), encoding="utf-8")


def load_config(path: Path) -> MeetingIngestConfig:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"Config not found: {path}", code="config_not_found") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Config is not valid TOML: {path}", code="invalid_toml") from exc

    schema_version = data.get("schema_version")
    if schema_version != SCHEMA_VERSION:
        raise ConfigError(
            f"Unsupported schema_version {schema_version!r}; expected {SCHEMA_VERSION!r}.",
            code="unsupported_schema_version",
        )

    allowed_top_level = {
        "schema_version",
        "default_mode",
        "default_provider",
        "default_quality",
        "auto_init",
        "reconcile_after_success",
        "cache_normalized_transcript",
        "paths",
        "privacy",
        "playbook",
    }
    unknown = set(data) - allowed_top_level
    if unknown:
        raise ConfigError(f"Unknown config keys: {', '.join(sorted(unknown))}", code="unknown_config_key")
    for key in ("default_mode", "default_provider", "default_quality"):
        value = data.get(key)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ConfigError(f"{key} must be a non-empty string.", code="invalid_config_value")
    for key in ("auto_init", "reconcile_after_success", "cache_normalized_transcript"):
        value = data.get(key)
        if value is not None and not isinstance(value, bool):
            raise ConfigError(f"{key} must be a boolean.", code="invalid_config_value")
    for table_name in ("paths", "privacy", "playbook"):
        value = data.get(table_name, {})
        if not isinstance(value, dict):
            raise ConfigError(f"[{table_name}] must be a TOML table.", code="invalid_config_value")

    paths = _load_paths_config(data.get("paths", {}))
    privacy = _load_privacy_config(data.get("privacy", {}))
    playbook = _load_playbook_config(data.get("playbook", {}))
    return MeetingIngestConfig(
        schema_version=schema_version,
        default_mode=data.get("default_mode", "summary-plus-verbatim"),
        default_provider=data.get("default_provider", "mock"),
        default_quality=data.get("default_quality", "balanced"),
        auto_init=data.get("auto_init", False),
        reconcile_after_success=data.get("reconcile_after_success", True),
        cache_normalized_transcript=data.get("cache_normalized_transcript", True),
        paths=paths,
        privacy=privacy,
        playbook=playbook,
    )


def _load_paths_config(data: dict[str, object]) -> PathsConfig:
    defaults = PathsConfig().__dict__
    unknown = set(data) - set(defaults)
    if unknown:
        raise ConfigError(f"Unknown [paths] keys: {', '.join(sorted(unknown))}", code="unknown_config_key")
    for key, value in data.items():
        if not isinstance(value, str) or not value:
            raise ConfigError(f"[paths].{key} must be a non-empty string.", code="invalid_config_value")
    return PathsConfig(**{**defaults, **data})


def _load_privacy_config(data: dict[str, object]) -> PrivacyConfig:
    defaults = PrivacyConfig().__dict__
    unknown = set(data) - set(defaults)
    if unknown:
        raise ConfigError(f"Unknown [privacy] keys: {', '.join(sorted(unknown))}", code="unknown_config_key")
    for key, value in data.items():
        if not isinstance(value, bool):
            raise ConfigError(f"[privacy].{key} must be a boolean.", code="invalid_config_value")
    return PrivacyConfig(**{**defaults, **data})


def _load_playbook_config(data: dict[str, object]) -> PlaybookConfig:
    if not isinstance(data, dict):
        raise ConfigError("[playbook] must be a TOML table.", code="invalid_config_value")
    defaults = PlaybookConfig().__dict__
    unknown = set(data) - set(defaults)
    if unknown:
        raise ConfigError(f"Unknown [playbook] keys: {', '.join(sorted(unknown))}", code="unknown_config_key")
    values = {**defaults, **data}
    for key, value in values.items():
        minimum = 2 if key == "min_recurrent_source_events" else 1
        if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
            raise ConfigError(
                f"[playbook].{key} must be an integer greater than or equal to {minimum}.",
                code="invalid_config_value",
            )
    return PlaybookConfig(**values)
