from pathlib import Path

import pytest

from meeting_ingest.config import load_config
from meeting_ingest.errors import ConfigError
from meeting_ingest.paths import DEFAULT_CONFIG_RELATIVE, discover_config, init_project, load_project


def test_init_project_creates_default_layout(tmp_path: Path) -> None:
    paths = init_project(tmp_path)

    assert paths.config_path == tmp_path / DEFAULT_CONFIG_RELATIVE
    assert paths.meetings_root.is_dir()
    assert paths.inbox.is_dir()
    assert paths.inbox_done.is_dir()
    assert paths.processed.is_dir()
    assert paths.quarantine.is_dir()
    assert paths.signals.is_dir()
    assert paths.derived.is_dir()
    assert paths.cache.is_dir()
    assert paths.ledger.read_text(encoding="utf-8") == ""
    assert "/_local/project-context/meetings/_cache/" in (tmp_path / ".gitignore").read_text(encoding="utf-8")


def test_load_project_discovers_config_from_nested_directory(tmp_path: Path) -> None:
    initialized = init_project(tmp_path)
    nested = initialized.inbox / "nested"
    nested.mkdir()

    config, paths = load_project(nested)

    assert config.schema_version == "1.0"
    assert paths.project_root == tmp_path.resolve()
    assert paths.config_path == initialized.config_path
    assert config.privacy.allow_session_provider is False


def test_discover_config_fails_clearly_without_init(tmp_path: Path) -> None:
    with pytest.raises(ConfigError) as exc:
        discover_config(tmp_path)

    assert exc.value.code == "config_not_found"


def test_load_config_rejects_unsupported_schema(tmp_path: Path) -> None:
    config_path = tmp_path / "meeting-ingest.toml"
    config_path.write_text('schema_version = "9.9"\n', encoding="utf-8")

    with pytest.raises(ConfigError) as exc:
        load_config(config_path)

    assert exc.value.code == "unsupported_schema_version"


def test_load_config_rejects_unknown_section_keys(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    paths.config_path.write_text(
        """schema_version = "1.0"

[paths]
unknown = "value"
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError) as exc:
        load_config(paths.config_path)

    assert exc.value.code == "unknown_config_key"
