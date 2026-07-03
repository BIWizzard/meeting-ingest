"""Provider registry."""

from __future__ import annotations

from meeting_ingest.provider import Provider
from meeting_ingest.providers.anthropic import AnthropicProvider
from meeting_ingest.providers.mock import MockProvider


def get_provider(name: str) -> Provider:
    if name == "mock":
        return MockProvider()
    if name == "anthropic":
        return AnthropicProvider()
    raise KeyError(name)
