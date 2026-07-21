from __future__ import annotations

import json
from pathlib import Path

import pytest

from meeting_ingest.runtime_config import (
    RuntimeConfigError,
    parse_channel,
    parse_pin,
    read_pin,
    serialize_channel,
    serialize_pin,
)


def _digest(character: str) -> str:
    return "sha256:" + character * 64


def _pin_values(executable: str = "/opt/meeting-ingest/bin/meeting-ingest") -> dict[str, str]:
    return {
        "schema_version": "1.0",
        "channel": "private-alpha",
        "approved_build_id": "meeting-ingest-0.1.0-gaaaaaaaaaaaa-sbbbbbbbbbbbb",
        "approved_source_commit": "a" * 40,
        "approved_source_tree_sha256": _digest("b"),
        "approved_wheel_sha256": _digest("c"),
        "approved_receipt_sha256": _digest("d"),
        "approved_executable": executable,
        "workflow_contract_version": "claude-code-session-v1",
        "claude_skill_template_sha256": _digest("e"),
        "installed_claude_skill_sha256": _digest("f"),
        "claude_agent_sha256": _digest("1"),
        "approved_at": "2026-07-20T00:00:00Z",
    }


def _channel_values() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "channel": "private-alpha",
        "latest": {
            "build_id": "meeting-ingest-0.1.0-gaaaaaaaaaaaa-sbbbbbbbbbbbb",
            "source_commit": "a" * 40,
            "wheel_sha256": _digest("c"),
            "receipt_path": "releases/meeting-ingest-0.1.0-gaaaaaaaaaaaa-sbbbbbbbbbbbb/receipt.json",
            "receipt_sha256": _digest("d"),
        },
        "previous": [
            {
                "build_id": "meeting-ingest-0.1.0-g111111111111-s222222222222",
                "receipt_path": "releases/meeting-ingest-0.1.0-g111111111111-s222222222222/receipt.json",
                "receipt_sha256": _digest("2"),
            }
        ],
        "published_at": "2026-07-20T00:00:00Z",
    }


def test_pin_round_trip_is_independent_of_normal_project_config(tmp_path: Path) -> None:
    payload = serialize_pin(_pin_values())
    pin_path = tmp_path / "_local/project-context/meetings/meeting-ingest-runtime.toml"
    pin_path.parent.mkdir(parents=True)
    pin_path.write_bytes(payload)

    parsed = read_pin(tmp_path)

    assert parsed.valid is True
    assert parsed.values == _pin_values()
    assert not (tmp_path / "_local/project-context/meetings/meeting-ingest.toml").exists()


@pytest.mark.parametrize(
    "mutation, message",
    [
        (lambda values: values.update(extra="no"), "unknown keys"),
        (lambda values: values.__setitem__("approved_wheel_sha256", "bad"), "sha256 digest"),
        (lambda values: values.__setitem__("approved_executable", "bin/meeting-ingest"), "absolute"),
        (lambda values: values.pop("approved_build_id"), "missing keys"),
    ],
)
def test_pin_rejects_unknown_malformed_relative_and_partial_identity(mutation, message: str) -> None:
    values = _pin_values()
    mutation(values)

    with pytest.raises(RuntimeConfigError, match=message):
        parse_pin("\n".join(f"{key} = {json.dumps(value)}" for key, value in values.items()).encode())


def test_channel_round_trip_strictly_validates_entries() -> None:
    values = _channel_values()
    payload = serialize_channel(values)

    assert parse_channel(payload, expected_channel="private-alpha") == values


@pytest.mark.parametrize(
    "mutation, message",
    [
        (lambda values: values.update(extra=True), "unknown keys"),
        (
            lambda values: values["latest"].__setitem__("receipt_path", "../../receipt.json"),
            "application-data-relative",
        ),
        (
            lambda values: values["latest"].__setitem__(
                "receipt_path", "releases/meeting-ingest-0.1.0-g111111111111-s222222222222/receipt.json"
            ),
            "build_id directory",
        ),
        (lambda values: values["latest"].pop("wheel_sha256"), "missing keys"),
        (lambda values: values.__setitem__("channel", "stable"), "expected 'private-alpha'"),
    ],
)
def test_channel_rejects_unknown_unsafe_partial_or_wrong_channel(mutation, message: str) -> None:
    values = _channel_values()
    mutation(values)

    with pytest.raises(RuntimeConfigError, match=message):
        parse_channel(json.dumps(values).encode(), expected_channel="private-alpha")
