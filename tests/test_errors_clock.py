from datetime import UTC, datetime

from meeting_ingest.clock import FrozenClock, mint_ingest_run_id
from meeting_ingest.errors import ConfigError, EXIT_USAGE_OR_CONFIG


def test_config_error_renders_error_block() -> None:
    error = ConfigError("Missing config", code="config_not_found")

    assert error.exit_code == EXIT_USAGE_OR_CONFIG
    assert error.to_error_block() == {
        "phase": "config",
        "code": "config_not_found",
        "message": "Missing config",
        "recoverable": True,
    }


def test_mint_ingest_run_id_uses_injected_clock_and_suffix() -> None:
    clock = FrozenClock(datetime(2026, 7, 3, 12, 0, tzinfo=UTC))

    run_id = mint_ingest_run_id("20260703", clock=clock, suffix_factory=lambda: "abcd1234")

    assert run_id == "ingest-20260703-20260703T120000Z-abcd1234"
