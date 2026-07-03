"""Anthropic provider adapter."""

from __future__ import annotations

from dataclasses import fields
import json
import os
from typing import Any
from urllib import error, request

from meeting_ingest.errors import ProviderError
from meeting_ingest.identity import normalize_person
from meeting_ingest.provider import ProviderRequest
from meeting_ingest.schema import (
    ActionItem,
    Attendee,
    Decision,
    DependencyRisk,
    OpenQuestion,
    ProviderResponse,
    ProviderSignal,
    SignalEvidence,
    StakeholderAsk,
    Topic,
)


ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
MODEL_BY_QUALITY = {
    "fast": "claude-haiku-4-5",
    "balanced": "claude-sonnet-5",
    "deep": "claude-opus-4-8",
}


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, *, api_key_env: str = "ANTHROPIC_API_KEY", timeout_seconds: int = 90) -> None:
        self.api_key_env = api_key_env
        self.timeout_seconds = timeout_seconds
        self.model_id = MODEL_BY_QUALITY["balanced"]

    def extract(self, request_data: ProviderRequest) -> ProviderResponse:
        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            raise ProviderError(self.name, f"Missing API key environment variable {self.api_key_env}.")

        self.model_id = MODEL_BY_QUALITY.get(request_data.quality, MODEL_BY_QUALITY["balanced"])
        payload = {
            "model": self.model_id,
            "max_tokens": 8000,
            "temperature": 0,
            "system": _system_prompt(),
            "messages": [{"role": "user", "content": _user_prompt(request_data)}],
        }
        raw_response = self._post(payload, api_key)
        parsed = _parse_message_json(raw_response)
        return _provider_response_from_payload(parsed)

    def _post(self, payload: dict[str, Any], api_key: str) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        api_request = request.Request(
            ANTHROPIC_API_URL,
            data=body,
            headers={
                "content-type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": ANTHROPIC_VERSION,
            },
            method="POST",
        )
        try:
            with request.urlopen(api_request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")
            raise ProviderError(self.name, f"HTTP {exc.code}: {body_text}") from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise ProviderError(self.name, str(exc)) from exc


def _system_prompt() -> str:
    return (
        "You extract structured meeting information for deterministic rendering. "
        "Return only valid JSON. Do not return markdown or explanatory prose. "
        "Keep all claims grounded in the transcript."
    )


def _user_prompt(request_data: ProviderRequest) -> str:
    return f"""Extract this meeting transcript into the required JSON shape.

Rules:
- Return one JSON object and nothing else.
- Omit uncertain facts rather than inventing them.
- Use short stable IDs such as T1, D1, A1, Q1.
- communication_signals must use only these signal_type values: explicit_ask, stakeholder_priority, decision_rationale, commitment, risk_or_concern.
- communication_signals evidence.kind must be quote, paraphrase, or timestamp_only.
- inference_level must be explicit, strong_inference, or weak_inference.
- confidence must be high, medium, or low.
- recurrence should be unknown unless the transcript itself establishes recurrence.
- attendee person_id values may be null when uncertain.

Required JSON keys:
title, tl_dr, meeting_type, attendees, topics, decisions, action_items,
stakeholder_asks, dependencies_risks, communication_signals, open_questions,
cross_references

Source name: {request_data.source_name}
Meeting ID: {request_data.meeting_id}
Effective date: {request_data.effective_date}

Transcript:
{request_data.transcript}
"""


def _parse_message_json(raw_response: dict[str, Any]) -> dict[str, Any]:
    content = raw_response.get("content")
    if not isinstance(content, list):
        raise ProviderError("anthropic", "Response content is not a list.")
    text_parts = [block.get("text", "") for block in content if isinstance(block, dict) and block.get("type") == "text"]
    text = "\n".join(part for part in text_parts if part).strip()
    if not text:
        raise ProviderError("anthropic", "Response did not contain text JSON.")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProviderError("anthropic", f"Response text was not valid JSON: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise ProviderError("anthropic", "Response JSON root must be an object.")
    return parsed


def _provider_response_from_payload(payload: dict[str, Any]) -> ProviderResponse:
    return ProviderResponse(
        title=_string(payload.get("title")),
        tl_dr=_string(payload.get("tl_dr")),
        meeting_type=_string(payload.get("meeting_type"), default="unknown"),
        attendees=[_attendee(item) for item in _list(payload.get("attendees"))],
        topics=[_dataclass_from_dict(Topic, item) for item in _list(payload.get("topics"))],
        decisions=[_dataclass_from_dict(Decision, item) for item in _list(payload.get("decisions"))],
        action_items=[_dataclass_from_dict(ActionItem, item) for item in _list(payload.get("action_items"))],
        stakeholder_asks=[_dataclass_from_dict(StakeholderAsk, item) for item in _list(payload.get("stakeholder_asks"))],
        dependencies_risks=[
            _dataclass_from_dict(DependencyRisk, item) for item in _list(payload.get("dependencies_risks"))
        ],
        communication_signals=[_provider_signal(item) for item in _list(payload.get("communication_signals"))],
        open_questions=[_dataclass_from_dict(OpenQuestion, item) for item in _list(payload.get("open_questions"))],
        cross_references=[_string(item) for item in _list(payload.get("cross_references"))],
    )


def _attendee(item: dict[str, Any]) -> Attendee:
    display_name = _optional_string(item.get("display_name"))
    person_id = _optional_string(item.get("person_id"))
    if person_id is None and display_name:
        person_id = normalize_person(display_name).person_id
    return Attendee(
        person_id=person_id,
        display_name=display_name,
        raw_labels=[_string(label) for label in _list(item.get("raw_labels"))],
        role_context=_string(item.get("role_context"), default="Unknown"),
        confidence=_string(item.get("confidence"), default="medium"),
    )


def _provider_signal(item: dict[str, Any]) -> ProviderSignal:
    evidence_payload = item.get("evidence") if isinstance(item.get("evidence"), dict) else {}
    return ProviderSignal(
        signal_type=_string(item.get("signal_type")),
        stakeholder_id=_optional_string(item.get("stakeholder_id")),
        stakeholder_name=_string(item.get("stakeholder_name")),
        summary=_string(item.get("summary")),
        evidence=SignalEvidence(
            kind=_string(evidence_payload.get("kind")),
            text=_string(evidence_payload.get("text")),
            speaker=_optional_string(evidence_payload.get("speaker")),
            timestamp=_optional_string(evidence_payload.get("timestamp")),
        ),
        inference_level=_string(item.get("inference_level")),
        confidence=_string(item.get("confidence")),
        topics=[_string(value) for value in _list(item.get("topics"))],
        project_refs=[_string(value) for value in _list(item.get("project_refs"))],
        recurrence=_string(item.get("recurrence"), default="unknown"),
        status=_string(item.get("status"), default="active"),
    )


def _dataclass_from_dict(cls: type, item: dict[str, Any]) -> Any:
    kwargs: dict[str, Any] = {}
    for field in fields(cls):
        if field.name in item:
            kwargs[field.name] = item[field.name]
    return cls(**kwargs)


def _list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def _string(value: object, *, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
