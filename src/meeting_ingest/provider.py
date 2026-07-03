"""Provider interface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from meeting_ingest.schema import ProviderResponse


@dataclass(frozen=True)
class ProviderRequest:
    transcript: str
    source_name: str
    meeting_id: str
    effective_date: str
    quality: str = "balanced"


class Provider(Protocol):
    name: str
    model_id: str

    def extract(self, request: ProviderRequest) -> ProviderResponse:
        """Return structured meeting data for deterministic rendering."""
