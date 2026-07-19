"""Project path discovery and layout creation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from meeting_ingest.config import MeetingIngestConfig, load_config, write_default_config
from meeting_ingest.errors import ConfigError


DEFAULT_MEETINGS_ROOT = Path("_local/project-context/meetings")
DEFAULT_CONFIG_RELATIVE = DEFAULT_MEETINGS_ROOT / "meeting-ingest.toml"


@dataclass(frozen=True)
class ProjectPaths:
    project_root: Path
    config_path: Path
    meetings_root: Path
    inbox: Path
    inbox_done: Path
    processed: Path
    quarantine: Path
    signals: Path
    playbook_state: Path
    derived: Path
    cache: Path
    ledger: Path

    @classmethod
    def from_config(cls, project_root: Path, config_path: Path, config: MeetingIngestConfig) -> "ProjectPaths":
        meetings_root = project_root / config.paths.root
        inbox = meetings_root / config.paths.inbox
        return cls(
            project_root=project_root,
            config_path=config_path,
            meetings_root=meetings_root,
            inbox=inbox,
            inbox_done=inbox / "_done",
            processed=meetings_root / config.paths.processed,
            quarantine=meetings_root / config.paths.quarantine,
            signals=meetings_root / config.paths.signals,
            playbook_state=meetings_root / "_playbook-state",
            derived=meetings_root / config.paths.derived,
            cache=meetings_root / config.paths.cache,
            ledger=meetings_root / config.paths.ledger,
        )

    def runtime_directories(self) -> list[Path]:
        return [
            self.meetings_root,
            self.inbox,
            self.inbox_done,
            self.processed,
            self.quarantine,
            self.signals,
            self.playbook_state,
            self.derived,
            self.cache,
        ]


def infer_project_root_from_config(config_path: Path) -> Path:
    resolved = config_path.resolve()
    default_suffix = DEFAULT_CONFIG_RELATIVE.parts
    if resolved.parts[-len(default_suffix) :] == default_suffix:
        return resolved.parents[len(default_suffix) - 1]
    return resolved.parent


def discover_config(start: Path) -> Path:
    current = start.resolve()
    if current.is_file():
        current = current.parent

    for parent in [current, *current.parents]:
        direct_config = parent / "meeting-ingest.toml"
        if direct_config.exists():
            return direct_config

        default_config = parent / DEFAULT_CONFIG_RELATIVE
        if default_config.exists():
            return default_config

    raise ConfigError(
        f"No meeting-ingest config found from {start}. Run `meeting-ingest init` first.",
        code="config_not_found",
    )


def load_project(start: Path) -> tuple[MeetingIngestConfig, ProjectPaths]:
    config_path = discover_config(start)
    config = load_config(config_path)
    project_root = infer_project_root_from_config(config_path)
    return config, ProjectPaths.from_config(project_root, config_path, config)


def init_project(project_root: Path) -> ProjectPaths:
    project_root = project_root.resolve()
    config_path = project_root / DEFAULT_CONFIG_RELATIVE
    meetings_root = config_path.parent

    config_path.parent.mkdir(parents=True, exist_ok=True)
    if not config_path.exists():
        write_default_config(config_path)

    config = load_config(config_path)
    paths = ProjectPaths.from_config(project_root, config_path, config)
    for directory in paths.runtime_directories():
        directory.mkdir(parents=True, exist_ok=True)
    _ensure_cache_gitignored(project_root, paths.cache)
    if not paths.ledger.exists():
        paths.ledger.write_text("", encoding="utf-8")
    return paths


def _ensure_cache_gitignored(project_root: Path, cache_path: Path) -> None:
    gitignore = project_root / ".gitignore"
    try:
        relative_cache = cache_path.relative_to(project_root).as_posix()
        pattern = f"/{relative_cache}/"
        existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
        if pattern in {line.strip() for line in existing.splitlines()}:
            return
        suffix = "" if not existing or existing.endswith("\n") else "\n"
        gitignore.write_text(f"{existing}{suffix}\n# Meeting Ingest runtime cache\n{pattern}\n", encoding="utf-8")
    except (OSError, ValueError):
        return
