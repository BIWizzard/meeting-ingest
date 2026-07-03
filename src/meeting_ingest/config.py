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

    paths = _load_paths_config(data.get("paths", {}))
    privacy = _load_privacy_config(data.get("privacy", {}))
    return MeetingIngestConfig(
        schema_version=schema_version,
        default_mode=data.get("default_mode", "summary-plus-verbatim"),
        default_provider=data.get("default_provider", "mock"),
        default_quality=data.get("default_quality", "balanced"),
        auto_init=bool(data.get("auto_init", False)),
        reconcile_after_success=bool(data.get("reconcile_after_success", True)),
        cache_normalized_transcript=bool(data.get("cache_normalized_transcript", True)),
        paths=paths,
        privacy=privacy,
    )


def _load_paths_config(data: dict[str, object]) -> PathsConfig:
    defaults = PathsConfig().__dict__
    unknown = set(data) - set(defaults)
    if unknown:
        raise ConfigError(f"Unknown [paths] keys: {', '.join(sorted(unknown))}", code="unknown_config_key")
    return PathsConfig(**{**defaults, **data})


def _load_privacy_config(data: dict[str, object]) -> PrivacyConfig:
    defaults = PrivacyConfig().__dict__
    unknown = set(data) - set(defaults)
    if unknown:
        raise ConfigError(f"Unknown [privacy] keys: {', '.join(sorted(unknown))}", code="unknown_config_key")
    return PrivacyConfig(**{**defaults, **data})
