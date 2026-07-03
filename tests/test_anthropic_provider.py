import json

import pytest

from meeting_ingest.errors import ProviderError
from meeting_ingest.provider import ProviderRequest
from meeting_ingest.providers import anthropic
from meeting_ingest.providers.anthropic import AnthropicProvider
from meeting_ingest.schema import validate_provider_response


class FakeHTTPResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeHTTPResponse":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_anthropic_provider_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    provider = AnthropicProvider()

    with pytest.raises(ProviderError) as exc:
        provider.extract(_request())

    assert exc.value.code == "provider_failed"
    assert "ANTHROPIC_API_KEY" in exc.value.message


def test_anthropic_provider_posts_messages_request_and_parses_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):  # noqa: ANN001
        captured["timeout"] = timeout
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return FakeHTTPResponse(
            {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "title": "Synthetic Stakeholder Sync",
                                "tl_dr": "Discussed source clarity.",
                                "meeting_type": "one-on-one",
                                "attendees": [
                                    {
                                        "display_name": "Kushali G",
                                        "raw_labels": ["Kushali G"],
                                        "confidence": "high",
                                    }
                                ],
                                "topics": [
                                    {
                                        "id": "T1",
                                        "topic": "Source clarity",
                                        "summary": "Reviewed source clarity.",
                                        "evidence": "Synthetic fixture.",
                                    }
                                ],
                                "decisions": [],
                                "action_items": [],
                                "stakeholder_asks": [],
                                "dependencies_risks": [],
                                "communication_signals": [
                                    {
                                        "signal_type": "explicit_ask",
                                        "stakeholder_id": "person-kushali-g",
                                        "stakeholder_name": "Kushali G",
                                        "summary": "Asked for source clarity.",
                                        "evidence": {
                                            "kind": "paraphrase",
                                            "text": "Asked for source clarity.",
                                            "speaker": "Kushali G",
                                        },
                                        "inference_level": "explicit",
                                        "confidence": "high",
                                    }
                                ],
                                "open_questions": [],
                                "cross_references": [],
                            }
                        ),
                    }
                ]
            }
        )

    monkeypatch.setattr(anthropic.request, "urlopen", fake_urlopen)
    provider = AnthropicProvider()

    response = provider.extract(_request(quality="fast"))

    validate_provider_response(response)
    assert provider.model_id == "claude-haiku-4-5"
    assert response.title == "Synthetic Stakeholder Sync"
    assert response.attendees[0].person_id == "person-kushali-g"
    assert response.communication_signals[0].signal_type == "explicit_ask"
    assert captured["url"] == "https://api.anthropic.com/v1/messages"
    assert captured["timeout"] == 90
    body = captured["body"]
    assert isinstance(body, dict)
    assert body["model"] == "claude-haiku-4-5"
    assert body["temperature"] == 0
    headers = captured["headers"]
    assert isinstance(headers, dict)
    assert headers["X-api-key"] == "test-key"
    assert headers["Anthropic-version"] == "2023-06-01"


def _request(*, quality: str = "balanced") -> ProviderRequest:
    return ProviderRequest(
        transcript="Ken: Hello\nKushali G: Please clarify the source.\n",
        source_name="synthetic.txt",
        meeting_id="mtg-20260703-abcdef12",
        effective_date="2026-07-03",
        quality=quality,
    )
