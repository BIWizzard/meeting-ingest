"""Live playbook freshness and durable-state diagnostics."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from meeting_ingest.paths import ProjectPaths
from meeting_ingest.playbook import discover_inputs, read_derivation_records
from meeting_ingest.playbook_review import read_review_state


def live_playbook_status(paths: ProjectPaths) -> dict[str, object]:
    inputs = discover_inputs(paths)
    records, _ = read_derivation_records(paths.playbook_state / "derivation-ledger.jsonl")
    latest_attempt = records[-1] if records else None
    index = _read_json_object(paths.derived / "playbook-index.json")
    committed_run_ids = {
        record["derivation_run_id"] for record in records if record.get("status") == "success"
    }
    usable_index = (
        index
        if _index_is_usable(paths, index) and index.get("derivation_run_id") in committed_run_ids
        else None
    )
    if usable_index is None:
        status = "failed" if latest_attempt is not None and latest_attempt.get("status") == "failed" else "missing"
        stored_fingerprint = None
        derivation_run_id = None
        profile_count = 0
        unresolved_count = 0
    else:
        stored_fingerprint = usable_index.get("input_fingerprint")
        status = "current" if stored_fingerprint == inputs.input_fingerprint else "stale"
        derivation_run_id = usable_index.get("derivation_run_id")
        profiles = usable_index.get("profiles", {})
        profile_count = len(profiles) if isinstance(profiles, dict) else 0
        unresolved_count = usable_index.get("unresolved_identity_count", 0)
    review_state = read_review_state(paths.playbook_state / "overrides.jsonl")
    return {
        "status": status,
        "derivation_run_id": derivation_run_id,
        "input_fingerprint": stored_fingerprint,
        "current_input_fingerprint": inputs.input_fingerprint,
        "profile_count": profile_count,
        "unresolved_identity_count": unresolved_count,
        "rejected_or_suppressed_count": review_state.rejected_or_suppressed_count,
        "guidance_status": "not_available_in_briefing_v1",
        "latest_attempt_status": latest_attempt.get("status") if latest_attempt is not None else None,
    }


def playbook_issues(paths: ProjectPaths) -> list[dict[str, str | None]]:
    issues: list[dict[str, str | None]] = []
    if not paths.playbook_state.exists():
        return [_issue("playbook_state_missing", "Durable playbook state directory is missing.", "_playbook-state")]

    review_state = read_review_state(paths.playbook_state / "overrides.jsonl")
    for issue in review_state.issues:
        issues.append(
            _issue(
                "review_event_malformed",
                issue.message,
                f"_playbook-state/overrides.jsonl:line:{issue.line_number}",
            )
        )

    ledger_path = paths.playbook_state / "derivation-ledger.jsonl"
    records, ledger_issues = read_derivation_records(ledger_path)
    for line_number, message in ledger_issues:
        issues.append(
            _issue(
                "derivation_ledger_malformed",
                message,
                f"_playbook-state/derivation-ledger.jsonl:line:{line_number}",
            )
        )
    committed = {
        str(record["derivation_run_id"]): record
        for record in records
        if record.get("status") == "success"
    }
    generations_path = paths.derived / "generations"
    if generations_path.exists():
        for generation in sorted(path for path in generations_path.iterdir() if path.is_dir()):
            if generation.name not in committed:
                issues.append(
                    _issue(
                        "derivation_generation_uncommitted",
                        "Generation directory has no successful derivation-ledger commit.",
                        str(generation.relative_to(paths.meetings_root)),
                    )
                )

    index_path = paths.derived / "playbook-index.json"
    index = _read_json_object(index_path)
    if index is not None:
        run_id = index.get("derivation_run_id")
        latest_success = next((record for record in reversed(records) if record.get("status") == "success"), None)
        if run_id not in committed or (
            latest_success is not None and run_id != latest_success.get("derivation_run_id")
        ):
            issues.append(
                _issue(
                    "derivation_index_mismatch",
                    "Playbook index does not point to the latest committed generation.",
                    str(index_path.relative_to(paths.meetings_root)),
                )
            )
        issues.extend(_profile_issues(paths, index))
    elif committed:
        issues.append(
            _issue(
                "derivation_index_mismatch",
                "A committed playbook generation exists but the current index is missing or invalid.",
                str(index_path.relative_to(paths.meetings_root)),
            )
        )

    status = live_playbook_status(paths)
    if status["status"] == "stale":
        issues.append(
            _issue(
                "playbook_stale",
                "Current playbook generation does not match the current derivation inputs.",
                str(index_path.relative_to(paths.meetings_root)),
            )
        )
    issues.extend(_orphaned_review_issues(paths, review_state.valid_events, index))
    return issues


def _profile_issues(paths: ProjectPaths, index: dict[str, Any]) -> list[dict[str, str | None]]:
    issues: list[dict[str, str | None]] = []
    profiles = index.get("profiles")
    if not isinstance(profiles, dict):
        return [_issue("playbook_profile_invalid", "Playbook index profiles must be an object.", None)]
    for record in profiles.values():
        if not isinstance(record, dict) or not all(
            isinstance(record.get(key), str) for key in ("profile_path", "briefing_path")
        ):
            issues.append(_issue("playbook_profile_invalid", "Playbook profile index record is invalid.", None))
            continue
        relative = str(record["profile_path"])
        path = _safe_meetings_path(paths, relative)
        if path is None:
            issues.append(_issue("playbook_profile_invalid", "Indexed profile path escapes the meetings root.", relative))
            continue
        if not path.exists():
            issues.append(_issue("playbook_profile_missing", "Indexed playbook profile is missing.", relative))
            continue
        payload = _read_json_object(path)
        if payload is None or payload.get("schema_version") != "1.0" or payload.get("profile_kind") != "stakeholder_briefing":
            issues.append(_issue("playbook_profile_invalid", "Indexed playbook profile is invalid.", relative))
        briefing_relative = str(record["briefing_path"])
        briefing_path = _safe_meetings_path(paths, briefing_relative)
        if briefing_path is None:
            issues.append(
                _issue("playbook_profile_invalid", "Indexed briefing path escapes the meetings root.", briefing_relative)
            )
        elif not briefing_path.exists():
            issues.append(_issue("playbook_profile_missing", "Indexed stakeholder briefing is missing.", briefing_relative))
    return issues


def _orphaned_review_issues(
    paths: ProjectPaths, events: list[dict[str, Any]], index: dict[str, Any] | None
) -> list[dict[str, str | None]]:
    entry_ids: set[str] = set()
    signal_refs: set[tuple[str, str]] = set()
    if index is not None:
        profiles = index.get("profiles", {})
        if isinstance(profiles, dict):
            for record in profiles.values():
                if not isinstance(record, dict) or not isinstance(record.get("profile_path"), str):
                    continue
                profile_path = _safe_meetings_path(paths, str(record["profile_path"]))
                profile = _read_json_object(profile_path) if profile_path is not None else None
                if profile is None:
                    continue
                for entry in _profile_entries(profile):
                    entry_ids.add(str(entry["entry_id"]))
                    for reference in entry.get("supporting_observations", []):
                        if isinstance(reference, dict):
                            source_id = reference.get("source_id")
                            signal_id = reference.get("signal_id")
                            if isinstance(source_id, str) and isinstance(signal_id, str):
                                signal_refs.add((source_id, signal_id))
    try:
        for observation in discover_inputs(paths).observations:
            signal_refs.add((observation.source_id, observation.signal.signal_id))
    except Exception:
        pass
    issues: list[dict[str, str | None]] = []
    for event in events:
        target = event["target"]
        if "entry_id" in target and target["entry_id"] not in entry_ids:
            issues.append(
                _issue(
                    "review_event_orphaned",
                    f"Review event references a non-current entry: {target['entry_id']}.",
                    "_playbook-state/overrides.jsonl",
                )
            )
        elif "source_id" in target and (target["source_id"], target["signal_id"]) not in signal_refs:
            issues.append(
                _issue(
                    "review_event_orphaned",
                    "Review event references an observation that is no longer present.",
                    "_playbook-state/overrides.jsonl",
                )
            )
    return issues


def _profile_entries(profile: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for value in profile.values():
        if isinstance(value, list):
            entries.extend(item for item in value if isinstance(item, dict) and "entry_id" in item)
    return entries


def _index_is_usable(paths: ProjectPaths, index: dict[str, Any] | None) -> bool:
    if index is None or index.get("schema_version") != "1.0" or index.get("status") != "current":
        return False
    generation_path = index.get("generation_path")
    profiles = index.get("profiles")
    resolved_generation = _safe_meetings_path(paths, generation_path) if isinstance(generation_path, str) else None
    if resolved_generation is None or not resolved_generation.is_dir():
        return False
    if not isinstance(profiles, dict):
        return False
    return not _profile_issues(paths, index)


def _read_json_object(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return None
    return value if isinstance(value, dict) else None


def _safe_meetings_path(paths: ProjectPaths, relative_path: str) -> Path | None:
    candidate = (paths.meetings_root / relative_path).resolve()
    root = paths.meetings_root.resolve()
    if candidate != root and root not in candidate.parents:
        return None
    return candidate


def _issue(code: str, message: str, path: str | None) -> dict[str, str | None]:
    return {"code": code, "message": message, "path": path}
