"""JSON parsing helpers for provider payloads."""

from __future__ import annotations

from dataclasses import fields
from typing import Any

from meeting_ingest.identity import normalize_person
from meeting_ingest.schema import (
    ActionItem,
    Attendee,
    Decision,
    DependencyRisk,
    OpenQuestion,
    ProviderResponse,
    ProviderSignal,
    ProviderValidationError,
    SignalEvidence,
    StakeholderAsk,
    Topic,
)


def provider_response_from_payload(payload: dict[str, Any]) -> ProviderResponse:
    try:
        return ProviderResponse(
            title=_required_string(payload, "title"),
            tl_dr=_required_string(payload, "tl_dr"),
            meeting_type=_optional_field_string(payload, "meeting_type", default="unknown"),
            attendees=[_attendee(item) for item in _dict_list(payload.get("attendees"))],
            topics=[_dataclass_from_dict(Topic, item) for item in _dict_list(payload.get("topics"))],
            decisions=[_dataclass_from_dict(Decision, item) for item in _dict_list(payload.get("decisions"))],
            action_items=[_dataclass_from_dict(ActionItem, item) for item in _dict_list(payload.get("action_items"))],
            stakeholder_asks=[
                _dataclass_from_dict(StakeholderAsk, item) for item in _dict_list(payload.get("stakeholder_asks"))
            ],
            dependencies_risks=[
                _dataclass_from_dict(DependencyRisk, item) for item in _dict_list(payload.get("dependencies_risks"))
            ],
            communication_signals=[_provider_signal(item) for item in _dict_list(payload.get("communication_signals"))],
            open_questions=[_dataclass_from_dict(OpenQuestion, item) for item in _dict_list(payload.get("open_questions"))],
            cross_references=[_array_string("cross_references", item) for item in _list(payload.get("cross_references"))],
        )
    except (TypeError, ValueError) as exc:
        raise ProviderValidationError(f"Provider response payload could not be parsed: {exc}") from exc


def _attendee(item: dict[str, Any]) -> Attendee:
    display_name = _optional_string(item.get("display_name"))
    person_id = _optional_string(item.get("person_id"))
    if person_id is None and display_name:
        person_id = normalize_person(display_name).person_id
    return Attendee(
        person_id=person_id,
        display_name=display_name,
        raw_labels=[_array_string("attendees.raw_labels", label) for label in _list(item.get("raw_labels"))],
        role_context=_optional_field_string(item, "role_context", default="Unknown"),
        confidence=_optional_field_string(item, "confidence", default="medium"),
    )


def _provider_signal(item: dict[str, Any]) -> ProviderSignal:
    evidence_payload = item.get("evidence") if isinstance(item.get("evidence"), dict) else {}
    enriched_keys = {"signal_id", "meeting_id", "ingest_run_id", "recorded_at", "effective_at", "schema_version"}
    unexpected = enriched_keys.intersection(item)
    if unexpected:
        raise ProviderValidationError(
            "Provider communication_signals must not contain enriched fields: "
            + ", ".join(sorted(unexpected))
        )
    return ProviderSignal(
        signal_type=_required_string(item, "signal_type"),
        stakeholder_id=_optional_string(item.get("stakeholder_id")),
        stakeholder_name=_required_string(item, "stakeholder_name"),
        summary=_required_string(item, "summary"),
        evidence=SignalEvidence(
            kind=_required_string(evidence_payload, "kind"),
            text=_required_string(evidence_payload, "text"),
            speaker=_optional_string(evidence_payload.get("speaker")),
            timestamp=_optional_string(evidence_payload.get("timestamp")),
        ),
        inference_level=_required_string(item, "inference_level"),
        confidence=_required_string(item, "confidence"),
        topics=[_array_string("communication_signals.topics", value) for value in _list(item.get("topics"))],
        project_refs=[_array_string("communication_signals.project_refs", value) for value in _list(item.get("project_refs"))],
        recurrence=_optional_field_string(item, "recurrence", default="unknown"),
        status=_optional_field_string(item, "status", default="active"),
    )


def _dataclass_from_dict(cls: type, item: dict[str, Any]) -> Any:
    kwargs: dict[str, Any] = {}
    for field in fields(cls):
        if field.name in item:
            kwargs[field.name] = _required_string(item, field.name)
    return cls(**kwargs)


def _dict_list(value: object) -> list[dict[str, Any]]:
    items = _list(value)
    for item in items:
        if not isinstance(item, dict):
            raise ProviderValidationError("Provider response arrays must contain objects.")
    return items


def _list(value: object) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ProviderValidationError("Provider response array fields must be arrays.")
    return value


def _required_string(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str):
        raise ProviderValidationError(f"Provider response field {field!r} must be a string.")
    return value


def _optional_field_string(payload: dict[str, Any], field: str, *, default: str) -> str:
    value = payload.get(field)
    if value is None:
        return default
    if not isinstance(value, str):
        raise ProviderValidationError(f"Provider response field {field!r} must be a string.")
    return value


def _array_string(field: str, value: object) -> str:
    if not isinstance(value, str):
        raise ProviderValidationError(f"Provider response field {field!r} array items must be strings.")
    return value


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ProviderValidationError("Provider response optional string fields must be strings when present.")
    text = str(value).strip()
    return text or None
