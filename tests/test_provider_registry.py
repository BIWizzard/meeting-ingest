import pytest

from meeting_ingest.providers import get_provider


def test_get_provider_returns_mock_provider() -> None:
    provider = get_provider("mock")

    assert provider.name == "mock"
    assert provider.model_id == "none"


def test_get_provider_rejects_unknown_provider() -> None:
    with pytest.raises(KeyError):
        get_provider("anthropic")
