"""Machine-readable contract shipped with session provider requests."""

from __future__ import annotations

from typing import Any

from meeting_ingest.schema import (
    CONFIDENCE_VALUES,
    EVIDENCE_KINDS,
    INFERENCE_LEVELS,
    RECURRENCE_VALUES,
    SIGNAL_TYPES,
)


PROVIDER_CONTRACT = "meeting-ingest-provider-response-v1"
IDENTITY_COPY_FIELDS = (
    "meeting_id",
    "ingest_run_id",
    "source_sha256",
    "normalized_transcript_sha256",
)


def response_contract_for_request(request: dict[str, Any]) -> dict[str, Any]:
    """Return the complete response schema with request identity values bound."""
    string = {"type": "string"}
    non_empty_string = {"type": "string", "minLength": 1}

    def object_schema(
        properties: dict[str, Any], required: tuple[str, ...], *, additional_properties: bool = True
    ) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": properties,
            "required": list(required),
            "additionalProperties": additional_properties,
        }

    def array_of(item: dict[str, Any]) -> dict[str, Any]:
        return {"type": "array", "items": item}

    attendee = object_schema(
        {
            "person_id": {"type": ["string", "null"]},
            "display_name": {"type": ["string", "null"]},
            "raw_labels": array_of(string),
            "role_context": string,
            "confidence": string,
        },
        (),
    )
    topic = object_schema(
        {name: non_empty_string for name in ("id", "topic", "summary", "evidence")},
        ("id", "topic", "summary", "evidence"),
    )
    decision = object_schema(
        {name: non_empty_string for name in ("id", "decision", "owner_decider", "evidence", "status")},
        ("id", "decision", "owner_decider", "evidence"),
    )
    action_item = object_schema(
        {name: non_empty_string for name in ("id", "owner", "action", "due_timing", "evidence", "status")},
        ("id", "owner", "action", "due_timing", "evidence"),
    )
    stakeholder_ask = object_schema(
        {name: non_empty_string for name in ("id", "stakeholder", "ask", "directed_to", "evidence", "status")},
        ("id", "stakeholder", "ask", "directed_to", "evidence"),
    )
    dependency_risk = object_schema(
        {
            name: non_empty_string
            for name in ("id", "type", "description", "owner_related_party", "impact", "status")
        },
        ("id", "type", "description", "owner_related_party", "impact"),
    )
    evidence = object_schema(
        {
            "kind": {"type": "string", "enum": list(EVIDENCE_KINDS)},
            "text": non_empty_string,
            "speaker": {"type": ["string", "null"]},
            "timestamp": {"type": ["string", "null"]},
        },
        ("kind", "text"),
    )
    signal = object_schema(
        {
            "signal_type": {"type": "string", "enum": list(SIGNAL_TYPES)},
            "stakeholder_id": {"type": ["string", "null"]},
            "stakeholder_name": non_empty_string,
            "summary": non_empty_string,
            "evidence": evidence,
            "inference_level": {"type": "string", "enum": list(INFERENCE_LEVELS)},
            "confidence": {"type": "string", "enum": list(CONFIDENCE_VALUES)},
            "topics": array_of(string),
            "project_refs": array_of(string),
            "recurrence": {"type": "string", "enum": list(RECURRENCE_VALUES)},
            "status": string,
        },
        ("signal_type", "stakeholder_name", "summary", "evidence", "inference_level", "confidence"),
    )
    enriched_signal_fields = (
        "signal_id",
        "meeting_id",
        "ingest_run_id",
        "recorded_at",
        "effective_at",
        "schema_version",
    )
    signal["not"] = {"anyOf": [{"required": [field]} for field in enriched_signal_fields]}
    open_question = object_schema(
        {name: non_empty_string for name in ("id", "question", "owner_next_step", "evidence", "status")},
        ("id", "question", "owner_next_step", "evidence"),
    )
    response = object_schema(
        {
            "title": non_empty_string,
            "tl_dr": non_empty_string,
            "meeting_type": string,
            "attendees": array_of(attendee),
            "topics": array_of(topic),
            "decisions": array_of(decision),
            "action_items": array_of(action_item),
            "stakeholder_asks": array_of(stakeholder_ask),
            "dependencies_risks": array_of(dependency_risk),
            "communication_signals": array_of(signal),
            "open_questions": array_of(open_question),
            "cross_references": array_of(string),
        },
        (
            "title",
            "tl_dr",
            "meeting_type",
            "attendees",
            "topics",
            "decisions",
            "action_items",
            "stakeholder_asks",
            "dependencies_risks",
            "communication_signals",
            "open_questions",
            "cross_references",
        ),
    )
    provider = object_schema(
        {
            "name": {"const": "session"},
            "host": non_empty_string,
            "model_alias": {"const": request["quality"]},
            "model_id": non_empty_string,
            "generated_at": non_empty_string,
        },
        ("name", "model_alias"),
    )
    properties: dict[str, Any] = {
        "schema_version": {"const": "1.0"},
        "handoff_type": {"const": "provider_response"},
        "provider_contract": {"const": PROVIDER_CONTRACT},
        "provider": provider,
        "response": response,
    }
    for field in IDENTITY_COPY_FIELDS:
        properties[field] = {"const": request[field]}
    schema = object_schema(
        properties,
        (
            "schema_version",
            "handoff_type",
            "provider_contract",
            *IDENTITY_COPY_FIELDS,
            "provider",
            "response",
        ),
    )
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["title"] = "Meeting Ingest session provider response"
    return {
        "identity_copy_fields": list(IDENTITY_COPY_FIELDS),
        "json_schema": schema,
        "preflight_command": "meeting-ingest validate-response RESPONSE --source SOURCE --json",
    }
