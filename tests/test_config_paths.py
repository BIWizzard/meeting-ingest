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
    assert config.playbook.min_recurrent_source_events == 2
    assert config.playbook.tracked_verify_after_days == 30


def test_load_config_without_playbook_table_uses_defaults(tmp_path: Path) -> None:
    paths = init_project(tmp_path)
    config = paths.config_path.read_text(encoding="utf-8")
    paths.config_path.write_text(config.split("\n[playbook]\n", maxsplit=1)[0] + "\n", encoding="utf-8")

    loaded = load_config(paths.config_path)

    assert loaded.playbook.min_recurrent_source_events == 2
    assert loaded.playbook.tracked_verify_after_days == 30
    assert loaded.playbook.priority_concern_stale_after_days == 60
    assert loaded.playbook.preference_behavior_response_stale_after_days == 90


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


@pytest.mark.parametrize(
    ("setting", "value"),
    (
        ("min_recurrent_source_events", "1"),
        ("tracked_verify_after_days", "0"),
        ("priority_concern_stale_after_days", '"soon"'),
        ("preference_behavior_response_stale_after_days", "true"),
    ),
)
def test_load_config_rejects_invalid_playbook_thresholds(
    tmp_path: Path, setting: str, value: str
) -> None:
    paths = init_project(tmp_path)
    config = paths.config_path.read_text(encoding="utf-8")
    default = getattr(load_config(paths.config_path).playbook, setting)
    config = config.replace(f"{setting} = {default}", f"{setting} = {value}")
    paths.config_path.write_text(config, encoding="utf-8")

    with pytest.raises(ConfigError) as exc:
        load_config(paths.config_path)

    assert exc.value.code == "invalid_config_value"
