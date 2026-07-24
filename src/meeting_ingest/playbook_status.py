"""Live playbook freshness and durable-state diagnostics."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from meeting_ingest.ids import normalize_identity_actor, normalize_identity_evidence
from meeting_ingest.paths import ProjectPaths
from meeting_ingest.playbook import (
    DERIVATION_PROVENANCE_INVALID_MESSAGE,
    DerivationInputs,
    NormalizedObservation,
    discover_inputs,
    read_derivation_records,
)
from meeting_ingest.playbook_review import ReviewState, read_review_state, suppression_match
from meeting_ingest.provider_handoff import valid_runtime_provenance_binding


_PROFILE_ENTRY_LISTS = (
    "tracked_asks",
    "tracked_commitments_by_stakeholder",
    "tracked_commitments_to_stakeholder",
    "priorities",
    "concerns_and_risks",
    "decision_rationales",
    "communication_preferences",
    "communication_behaviors",
    "interaction_responses",
    "unresolved_observations",
)
_SIGNAL_TYPE_BY_ENTRY_KIND = {
    "ask": "explicit_ask",
    "commitment": "commitment",
    "priority": "stakeholder_priority",
    "concern": "risk_or_concern",
    "decision-rationale": "decision_rationale",
    "communication-preference": "communication_preference",
    "communication-behavior": "communication_behavior",
    "interaction-response": "interaction_response",
}


def live_playbook_status(paths: ProjectPaths, *, inputs: DerivationInputs | None = None) -> dict[str, object]:
    current_inputs = inputs or discover_inputs(paths)
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
        status = "current" if stored_fingerprint == current_inputs.input_fingerprint else "stale"
        derivation_run_id = usable_index.get("derivation_run_id")
        profiles = usable_index.get("profiles", {})
        profile_count = len(profiles) if isinstance(profiles, dict) else 0
        unresolved_count = usable_index.get("unresolved_identity_count", 0)
    review_state = read_review_state(paths.playbook_state / "overrides.jsonl")
    return {
        "status": status,
        "derivation_run_id": derivation_run_id,
        "input_fingerprint": stored_fingerprint,
        "current_input_fingerprint": current_inputs.input_fingerprint,
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
        provenance_invalid = message == DERIVATION_PROVENANCE_INVALID_MESSAGE
        issues.append(
            _issue(
                "playbook_provenance_invalid"
                if provenance_invalid
                else "derivation_ledger_malformed",
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
        if index.get("schema_version") == "2.0" and not valid_runtime_provenance_binding(
            index.get("runtime_provenance_schema"),
            index.get("runtime_provenance_sha256"),
            index.get("runtime_provenance"),
        ):
            issues.append(
                _issue(
                    "playbook_provenance_invalid",
                    "Playbook index 2.0 runtime-provenance binding is invalid.",
                    str(index_path.relative_to(paths.meetings_root)),
                )
            )
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
        committed_record = committed.get(str(run_id))
        if (
            index.get("schema_version") == "2.0"
            and committed_record is not None
            and valid_runtime_provenance_binding(
                index.get("runtime_provenance_schema"),
                index.get("runtime_provenance_sha256"),
                index.get("runtime_provenance"),
            )
        ):
            issues.extend(_generation_provenance_issues(paths, index, committed_record))
    elif committed:
        issues.append(
            _issue(
                "derivation_index_mismatch",
                "A committed playbook generation exists but the current index is missing or invalid.",
                str(index_path.relative_to(paths.meetings_root)),
            )
        )

    inputs = discover_inputs(paths)
    status = live_playbook_status(paths, inputs=inputs)
    if status["status"] == "stale":
        issues.append(
            _issue(
                "playbook_stale",
                "Current playbook generation does not match the current derivation inputs.",
                str(index_path.relative_to(paths.meetings_root)),
            )
        )
    issues.extend(_suppression_reemergence_issues(paths, review_state, records, inputs.observations))
    issues.extend(_orphaned_review_issues(paths, review_state.valid_events, index, records, inputs.observations))
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
        if (
            payload is None
            or payload.get("schema_version") not in {"1.0", "2.0"}
            or payload.get("profile_kind") != "stakeholder_briefing"
        ):
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


def _generation_provenance_issues(
    paths: ProjectPaths,
    index: dict[str, Any],
    committed: dict[str, Any] | None,
) -> list[dict[str, str | None]]:
    expected = index.get("runtime_provenance_sha256")
    run_id = index.get("derivation_run_id")
    members: list[tuple[str, dict[str, Any] | None]] = [
        ("playbook index", index),
        ("committing derivation record", committed),
    ]
    for label, key in (
        ("generation manifest", "generation_manifest_path"),
        ("identity candidates", "identity_candidates_path"),
    ):
        relative = index.get(key)
        payload = (
            _read_json_object(_safe_meetings_path(paths, str(relative)))
            if isinstance(relative, str)
            else None
        )
        members.append((label, payload))
    profiles = index.get("profiles")
    briefing_members: list[tuple[str, str | None, str | None]] = []
    if isinstance(profiles, dict):
        for person_id, record in profiles.items():
            if not isinstance(record, dict):
                continue
            profile_relative = record.get("profile_path")
            profile_path = (
                _safe_meetings_path(paths, str(profile_relative))
                if isinstance(profile_relative, str)
                else None
            )
            if profile_path is not None:
                members.append((f"profile {person_id}", _read_json_object(profile_path)))
            briefing_relative = record.get("briefing_path")
            briefing_path = (
                _safe_meetings_path(paths, str(briefing_relative))
                if isinstance(briefing_relative, str)
                else None
            )
            briefing_members.append(
                (f"briefing {person_id}", *_briefing_provenance(briefing_path))
            )
    mismatches: list[str] = []
    for label, payload in members:
        if (
            payload is None
            or payload.get("schema_version") != "2.0"
            or payload.get("derivation_run_id") != run_id
            or payload.get("runtime_provenance_sha256") != expected
            or not valid_runtime_provenance_binding(
                payload.get("runtime_provenance_schema"),
                payload.get("runtime_provenance_sha256"),
                payload.get("runtime_provenance"),
            )
        ):
            mismatches.append(label)
    for label, briefing_run_id, fingerprint in briefing_members:
        if briefing_run_id != run_id or fingerprint != expected:
            mismatches.append(label)
    if not mismatches:
        return []
    return [
        _issue(
            "playbook_provenance_invalid",
            "Playbook generation members do not share the committing runtime provenance: "
            + ", ".join(mismatches)
            + ".",
            str(index.get("generation_path")) if index.get("generation_path") else None,
        )
    ]


def _briefing_provenance(path: Path | None) -> tuple[str | None, str | None]:
    if path is None:
        return None, None
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return None, None
    if not lines or lines[0] != "---":
        return None, None
    for line in lines[1:]:
        if line == "---":
            break
        if line.startswith(("derivation_run_id: ", "runtime_provenance_sha256: ")):
            key, value = line.split(": ", 1)
            values[key] = value.strip().strip('"')
    return values.get("derivation_run_id"), values.get("runtime_provenance_sha256")


def _orphaned_review_issues(
    paths: ProjectPaths,
    events: list[dict[str, Any]],
    index: dict[str, Any] | None,
    records: list[dict[str, Any]],
    observations: tuple[NormalizedObservation, ...],
) -> list[dict[str, str | None]]:
    entry_ids: set[str] = set()
    signal_refs: set[tuple[str, str]] = set()
    current_entries: dict[str, tuple[str, dict[str, Any]]] = {}
    if index is not None:
        profiles = index.get("profiles", {})
        if isinstance(profiles, dict):
            for person_id, record in profiles.items():
                if not isinstance(record, dict) or not isinstance(record.get("profile_path"), str):
                    continue
                profile_path = _safe_meetings_path(paths, str(record["profile_path"]))
                profile = _read_json_object(profile_path) if profile_path is not None else None
                if profile is None:
                    continue
                for entry in _profile_entries(profile):
                    entry_id = str(entry["entry_id"])
                    entry_ids.add(entry_id)
                    current_entries[entry_id] = (str(person_id), entry)
                    for reference in entry.get("supporting_observations", []):
                        if isinstance(reference, dict):
                            source_id = reference.get("source_id")
                            signal_id = reference.get("signal_id")
                            if isinstance(source_id, str) and isinstance(signal_id, str):
                                signal_refs.add((source_id, signal_id))
    for observation in observations:
        signal_refs.add((observation.source_id, observation.signal.signal_id))
    orphaned_entry_ids = {
        str(event["target"]["entry_id"])
        for event in events
        if "entry_id" in event["target"] and event["target"]["entry_id"] not in entry_ids
    }
    historical_entries = _historical_entries(paths, records, orphaned_entry_ids)
    issues: list[dict[str, str | None]] = []
    for event in events:
        target = event["target"]
        if "entry_id" in target and target["entry_id"] not in entry_ids:
            successor = _nearest_successor(target["entry_id"], historical_entries, current_entries)
            hint = f" Nearest current successor: {successor}." if successor is not None else ""
            issues.append(
                _issue(
                    "review_event_orphaned",
                    f"Review event references a non-current entry: {target['entry_id']}.{hint}",
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


def _suppression_reemergence_issues(
    paths: ProjectPaths,
    review_state: ReviewState,
    records: list[dict[str, Any]],
    observations: tuple[NormalizedObservation, ...],
) -> list[dict[str, str | None]]:
    expected_matches = dict(review_state.suppressed_signal_matches)
    missing_matches = review_state.suppressed_signals - expected_matches.keys()
    if missing_matches:
        expected_matches.update(_historical_suppression_matches(paths, records, missing_matches))
    if not expected_matches:
        return []
    issues: list[dict[str, str | None]] = []
    reported: set[tuple[tuple[str, str], tuple[str, str]]] = set()
    for observation in observations:
        current_reference = (observation.source_id, observation.signal.signal_id)
        if current_reference in review_state.suppressed_signals:
            continue
        current_match = suppression_match(observation.signal)
        for suppressed_reference, expected_match in expected_matches.items():
            pair = (suppressed_reference, current_reference)
            if (
                current_reference != suppressed_reference
                and observation.source_id == suppressed_reference[0]
                and current_match == expected_match
                and pair not in reported
            ):
                reported.add(pair)
                issues.append(
                    _issue(
                        "signal_suppression_reemerged",
                        "Suppressed observation re-emerged under a new signal ID: "
                        f"{suppressed_reference[1]} -> {current_reference[1]}.",
                        "_playbook-state/overrides.jsonl",
                    )
                )
    return issues


def _historical_suppression_matches(
    paths: ProjectPaths,
    records: list[dict[str, Any]],
    suppressed_signals: set[tuple[str, str]],
) -> dict[tuple[str, str], dict[str, str]]:
    matches: dict[tuple[str, str], dict[str, str]] = {}
    if not suppressed_signals:
        return matches
    for derivation in reversed(records):
        if derivation.get("status") != "success":
            continue
        profiles = derivation.get("profiles", [])
        if not isinstance(profiles, list):
            continue
        for record in profiles:
            if not isinstance(record, dict) or not isinstance(record.get("profile_path"), str):
                continue
            profile_path = _safe_meetings_path(paths, record["profile_path"])
            profile = _read_json_object(profile_path) if profile_path is not None else None
            if profile is None:
                continue
            evidence_index = profile.get("evidence_index", {})
            if not isinstance(evidence_index, dict):
                continue
            for entry in _profile_entries(profile):
                signal_type = _SIGNAL_TYPE_BY_ENTRY_KIND.get(str(entry.get("entry_kind")))
                if signal_type is None:
                    continue
                for reference in _entry_references(entry) & suppressed_signals:
                    if reference in matches:
                        continue
                    evidence = evidence_index.get(f"{reference[0]}/{reference[1]}")
                    match = _evidence_suppression_match(signal_type, evidence)
                    if match is not None:
                        matches[reference] = match
        if suppressed_signals <= matches.keys():
            break
    return matches


def _evidence_suppression_match(signal_type: str, evidence: object) -> dict[str, str] | None:
    if not isinstance(evidence, dict) or not isinstance(evidence.get("speaker"), str):
        return None
    locator = evidence.get("locator")
    if not isinstance(locator, dict) or not isinstance(locator.get("scheme"), str):
        return None
    value = locator.get("value")
    if value is not None and not isinstance(value, str):
        return None
    return {
        "signal_type": signal_type,
        "raw_actor": normalize_identity_actor(evidence["speaker"]),
        "locator_scheme": normalize_identity_actor(locator["scheme"]),
        "locator_value": normalize_identity_evidence(value) if value is not None else "",
    }


def _historical_entries(
    paths: ProjectPaths,
    records: list[dict[str, Any]],
    target_entry_ids: set[str],
) -> dict[str, tuple[str, dict[str, Any]]]:
    entries: dict[str, tuple[str, dict[str, Any]]] = {}
    if not target_entry_ids:
        return entries
    for derivation in reversed(records):
        if derivation.get("status") != "success":
            continue
        profiles = derivation.get("profiles", [])
        if not isinstance(profiles, list):
            continue
        for record in profiles:
            if not isinstance(record, dict):
                continue
            person_id = record.get("person_id")
            relative = record.get("profile_path")
            if not isinstance(person_id, str) or not isinstance(relative, str):
                continue
            profile_path = _safe_meetings_path(paths, relative)
            profile = _read_json_object(profile_path) if profile_path is not None else None
            if profile is None:
                continue
            for entry in _profile_entries(profile):
                entry_id = str(entry["entry_id"])
                if entry_id in target_entry_ids:
                    entries.setdefault(entry_id, (person_id, entry))
        if target_entry_ids <= entries.keys():
            break
    return entries


def _nearest_successor(
    orphaned_entry_id: str,
    historical_entries: dict[str, tuple[str, dict[str, Any]]],
    current_entries: dict[str, tuple[str, dict[str, Any]]],
) -> str | None:
    historical = historical_entries.get(orphaned_entry_id)
    if historical is None:
        return None
    person_id, old_entry = historical
    old_references = _entry_references(old_entry)
    candidates: list[tuple[int, int, str]] = []
    for entry_id, (candidate_person_id, candidate) in current_entries.items():
        if candidate_person_id != person_id or candidate.get("entry_kind") != old_entry.get("entry_kind"):
            continue
        scope_score = _compatible_scope_score(old_entry.get("scope"), candidate.get("scope"))
        overlap = len(old_references & _entry_references(candidate))
        if scope_score is not None and overlap:
            candidates.append((-overlap, -scope_score, entry_id))
    return min(candidates)[2] if candidates else None


def _entry_references(entry: dict[str, Any]) -> set[tuple[str, str]]:
    references: set[tuple[str, str]] = set()
    for reference in entry.get("supporting_observations", []):
        if not isinstance(reference, dict):
            continue
        source_id = reference.get("source_id")
        signal_id = reference.get("signal_id")
        if isinstance(source_id, str) and isinstance(signal_id, str):
            references.add((source_id, signal_id))
    return references


def _compatible_scope_score(old_scope: object, new_scope: object) -> int | None:
    if not isinstance(old_scope, dict) or not isinstance(new_scope, dict):
        return None
    if old_scope.get("channel") != new_scope.get("channel"):
        return None
    score = 0
    for field in ("project_refs", "topics"):
        old_values = {str(value) for value in old_scope.get(field, [])}
        new_values = {str(value) for value in new_scope.get(field, [])}
        if old_values and new_values and not old_values & new_values:
            return None
        score += len(old_values & new_values)
    return score


def _profile_entries(profile: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for key in _PROFILE_ENTRY_LISTS:
        value = profile.get(key)
        if isinstance(value, list):
            entries.extend(item for item in value if isinstance(item, dict) and "entry_id" in item)
    return entries


def _index_is_usable(paths: ProjectPaths, index: dict[str, Any] | None) -> bool:
    if index is None or index.get("schema_version") not in {"1.0", "2.0"} or index.get("status") != "current":
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
