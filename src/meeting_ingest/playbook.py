"""Deterministic stakeholder briefing derivation and immutable generation commits."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from meeting_ingest.clock import Clock, SystemClock, default_suffix, format_iso_timestamp, format_timestamp
from meeting_ingest.config import load_config
from meeting_ingest.errors import EXIT_ARTIFACT_WRITE, EXIT_GENERAL_FAILURE, EXIT_LEDGER_WRITE, MeetingIngestError
from meeting_ingest.hashing import sha256_file
from meeting_ingest.ids import canonical_json, mint_source_id
from meeting_ingest.ledger import read_records
from meeting_ingest.locking import ProjectLock, lock_path
from meeting_ingest.paths import ProjectPaths, load_project
from meeting_ingest.playbook_review import ReviewState, read_review_state
from meeting_ingest.run_summary import RunSummary
from meeting_ingest.schema import SUPPORTED_SIGNAL_SCHEMA_VERSIONS, SignalRecord
from meeting_ingest.signals import read_signal_jsonl
from meeting_ingest.stakeholders import (
    Stakeholder,
    collect_identity_candidates,
    read_stakeholder_registry,
    write_identity_candidates,
)


DERIVATION_SCHEMA_VERSION = "1.0"
PROFILE_SCHEMA_VERSION = "1.0"
RULESET_ID = "briefing-rules-v1"
RENDERER_VERSION = "briefing-markdown-v2"

_CATEGORY_BY_SIGNAL = {
    "explicit_ask": ("tracked_asks", "ask"),
    "commitment": ("tracked_commitments_by_stakeholder", "commitment"),
    "stakeholder_priority": ("priorities", "priority"),
    "risk_or_concern": ("concerns_and_risks", "concern"),
    "decision_rationale": ("decision_rationales", "decision-rationale"),
    "communication_preference": ("communication_preferences", "communication-preference"),
    "communication_behavior": ("communication_behaviors", "communication-behavior"),
    "interaction_response": ("interaction_responses", "interaction-response"),
}
_PROFILE_LISTS = (
    "tracked_asks",
    "tracked_commitments_by_stakeholder",
    "tracked_commitments_to_stakeholder",
    "priorities",
    "concerns_and_risks",
    "decision_rationales",
    "communication_preferences",
    "communication_behaviors",
    "interaction_responses",
)


@dataclass(frozen=True)
class NormalizedObservation:
    signal: SignalRecord
    source_id: str
    source_kind: str
    artifact_path: str
    occurred_at: str | None


@dataclass(frozen=True)
class DerivationInputs:
    eligible_files: tuple[dict[str, str], ...]
    observations: tuple[NormalizedObservation, ...]
    all_signals: tuple[SignalRecord, ...]
    input_fingerprint: str
    registry_fingerprint: str
    overrides_fingerprint: str
    ruleset_fingerprint: str
    ruleset_values: dict[str, int]
    warnings: tuple[str, ...]


def update(
    start: Path,
    *,
    clock: Clock | None = None,
    suffix_factory: Callable[[], str] = default_suffix,
    trigger: str = "explicit_cli",
) -> RunSummary:
    """Build and commit a complete immutable stakeholder briefing generation."""
    if trigger not in {"explicit_cli", "agent_wrapper"}:
        raise ValueError(f"Unsupported playbook trigger: {trigger}")
    _, paths = load_project(start)
    active_clock = clock or SystemClock()
    with ProjectLock(lock_path(paths.cache), clock=active_clock):
        now = active_clock.now_utc()
        suffix = suffix_factory()[:4]
        run_id = f"derive-{now:%Y%m%d}-{format_timestamp(now)}-{suffix}"
        try:
            return _update_locked(paths, now=now, run_id=run_id, trigger=trigger)
        except MeetingIngestError as exc:
            if not _derivation_is_committed(paths, run_id):
                _record_failed_derivation(paths, run_id=run_id, now=now, trigger=trigger, error=exc)
            raise


def _update_locked(
    paths: ProjectPaths,
    *,
    now: datetime,
    run_id: str,
    trigger: str,
) -> RunSummary:
    recorded_at = format_iso_timestamp(now)
    derived_relative = _relative_to_meetings_root(paths, paths.derived)
    generation_relative = derived_relative / "generations" / run_id
    generation_path = paths.meetings_root / generation_relative
    ledger_path = paths.playbook_state / "derivation-ledger.jsonl"

    inputs = discover_inputs(paths)
    review_state = read_review_state(paths.playbook_state / "overrides.jsonl")
    previous_profiles = _load_current_profiles(paths)
    registry_path = paths.playbook_state / "stakeholders.toml"
    registry = read_stakeholder_registry(registry_path)
    invalid_registry = [issue for issue in registry.issues if issue.code == "identity_registry_invalid"]
    if invalid_registry:
        raise MeetingIngestError(
            phase="playbook_derivation",
            code="identity_registry_invalid",
            message="Stakeholder registry is invalid; briefing derivation was not committed.",
            exit_code=EXIT_ARTIFACT_WRITE,
            recoverable=True,
            details={"path": str(registry_path)},
        )

    try:
        generation_path.mkdir(parents=True, exist_ok=False)
    except OSError as exc:
        raise MeetingIngestError(
            phase="playbook_generation",
            code="generation_create_failed",
            message=f"Could not create immutable generation: {generation_path}",
            exit_code=EXIT_ARTIFACT_WRITE,
            recoverable=True,
            details={"path": str(generation_path)},
        ) from exc

    candidates = collect_identity_candidates(list(inputs.all_signals), registry)
    identity_candidates_relative = generation_relative / "identity-candidates.json"
    write_identity_candidates(
        paths.meetings_root / identity_candidates_relative,
        candidates,
        generated_at=recorded_at,
    )

    observations_by_person: dict[str, list[NormalizedObservation]] = defaultdict(list)
    people_by_id = {person.person_id: person for person in registry.people}
    for observation in inputs.observations:
        reference = (observation.source_id, observation.signal.signal_id)
        if reference in review_state.suppressed_signals:
            continue
        raw_name = _raw_stakeholder_name(observation.signal)
        resolution = registry.resolve(raw_name)
        if resolution.status == "reviewed" and resolution.person_id is not None:
            observations_by_person[resolution.person_id].append(observation)

    profile_records: list[dict[str, str]] = []
    index_profiles: dict[str, dict[str, str]] = {}
    for person_id in sorted(observations_by_person):
        person = people_by_id[person_id]
        observations = sorted(observations_by_person[person_id], key=_observation_sort_key)
        profile = _build_profile(
            person,
            observations,
            run_id=run_id,
            generated_at=recorded_at,
            input_fingerprint=inputs.input_fingerprint,
            today=now.date(),
            review_state=review_state,
            previous_profile=previous_profiles.get(person_id),
            ruleset_values=inputs.ruleset_values,
        )
        stakeholder_relative = generation_relative / "stakeholders" / person_id
        profile_relative = stakeholder_relative / "profile.json"
        briefing_relative = stakeholder_relative / "briefing.md"
        _write_json_atomic(paths.meetings_root / profile_relative, profile)
        _write_text_atomic(paths.meetings_root / briefing_relative, _render_briefing(profile))
        _validate_generation_profile(paths.meetings_root / profile_relative, paths.meetings_root / briefing_relative)
        record = {
            "person_id": person_id,
            "profile_path": profile_relative.as_posix(),
            "briefing_path": briefing_relative.as_posix(),
        }
        profile_records.append(record)
        index_profiles[person_id] = {
            "profile_path": record["profile_path"],
            "briefing_path": record["briefing_path"],
        }

    ruleset = {
        "id": RULESET_ID,
        "fingerprint": inputs.ruleset_fingerprint,
        "values": inputs.ruleset_values,
    }
    warnings = [*inputs.warnings, *(issue.message for issue in registry.issues)]
    ledger_record: dict[str, Any] = {
        "schema_version": DERIVATION_SCHEMA_VERSION,
        "event": "briefing_derivation_completed",
        "derivation_run_id": run_id,
        "status": "success",
        "trigger": trigger,
        "input_fingerprint": inputs.input_fingerprint,
        "registry_fingerprint": inputs.registry_fingerprint,
        "overrides_fingerprint": inputs.overrides_fingerprint,
        "ruleset": ruleset,
        "provider": "none",
        "generation_path": generation_relative.as_posix(),
        "profiles": profile_records,
        "unresolved_identity_count": len(candidates),
        "warnings": warnings,
        "errors": [],
        "recorded_at": recorded_at,
    }
    _append_derivation_record(ledger_path, ledger_record)

    index = {
        "schema_version": DERIVATION_SCHEMA_VERSION,
        "status": "current",
        "derivation_run_id": run_id,
        "generation_path": generation_relative.as_posix(),
        "input_fingerprint": inputs.input_fingerprint,
        "registry_fingerprint": inputs.registry_fingerprint,
        "overrides_fingerprint": inputs.overrides_fingerprint,
        "ruleset_id": RULESET_ID,
        "ruleset_fingerprint": inputs.ruleset_fingerprint,
        "profiles": index_profiles,
        "identity_candidates_path": identity_candidates_relative.as_posix(),
        "unresolved_identity_count": len(candidates),
        "committed_at": recorded_at,
    }
    index_relative = derived_relative / "playbook-index.json"
    _write_json_atomic(paths.meetings_root / index_relative, index)

    return RunSummary(
        status="success",
        exit_code=0,
        artifacts=[{"kind": "playbook_index", "status": "ready", "path": index_relative.as_posix()}],
        warnings=warnings,
        details={
            "command": "playbook_update",
            "derivation_run_id": run_id,
            "generation_path": generation_relative.as_posix(),
            "input_fingerprint": inputs.input_fingerprint,
            "profiles_written": len(profile_records),
            "unresolved_identity_count": len(candidates),
        },
    )


def discover_inputs(paths: ProjectPaths) -> DerivationInputs:
    """Discover eligible signal files and compute the frozen derivation fingerprint."""
    source_by_meeting = _legacy_source_details(read_records(paths.ledger))
    eligible_files: list[dict[str, str]] = []
    observations: list[NormalizedObservation] = []
    all_signals: list[SignalRecord] = []
    warnings: list[str] = []
    for signal_path in sorted(paths.signals.glob("*.jsonl")):
        relative = signal_path.relative_to(paths.meetings_root).as_posix()
        try:
            signals = read_signal_jsonl(signal_path)
        except MeetingIngestError as exc:
            warnings.append(f"excluded {relative}: {exc.code}")
            continue
        if not signals:
            continue
        normalized: list[NormalizedObservation] = []
        identity_error = False
        for signal in signals:
            observation = _normalize_observation(signal, source_by_meeting)
            if observation is None:
                identity_error = True
                break
            normalized.append(observation)
        if identity_error:
            warnings.append(f"excluded {relative}: signal_identity_invalid")
            continue
        eligible_files.append({"path": relative, "sha256": f"sha256:{sha256_file(signal_path)}"})
        observations.extend(normalized)
        all_signals.extend(signals)

    registry_path = paths.playbook_state / "stakeholders.toml"
    overrides_path = paths.playbook_state / "overrides.jsonl"
    registry_fingerprint = _path_fingerprint(registry_path)
    overrides_fingerprint = _path_fingerprint(overrides_path)
    config_values = asdict(load_config(paths.config_path).playbook)
    ruleset_payload = {"id": RULESET_ID, "values": config_values}
    ruleset_fingerprint = _canonical_fingerprint(ruleset_payload)
    fingerprint_payload = {
        "eligible_signal_files": eligible_files,
        "stakeholder_registry_sha256": registry_fingerprint,
        "review_overlay_ledger_sha256": overrides_fingerprint,
        "ruleset": ruleset_payload,
        "supported_schema_versions": list(SUPPORTED_SIGNAL_SCHEMA_VERSIONS),
        "renderer_version": RENDERER_VERSION,
    }
    return DerivationInputs(
        eligible_files=tuple(eligible_files),
        observations=tuple(observations),
        all_signals=tuple(all_signals),
        input_fingerprint=_canonical_fingerprint(fingerprint_payload),
        registry_fingerprint=registry_fingerprint,
        overrides_fingerprint=overrides_fingerprint,
        ruleset_fingerprint=ruleset_fingerprint,
        ruleset_values=config_values,
        warnings=tuple(warnings),
    )


def show(start: Path, selector: str, *, output_format: str = "markdown") -> RunSummary:
    if output_format not in {"markdown", "json"}:
        raise ValueError(f"Unsupported playbook output format: {output_format}")
    _, paths = load_project(start)
    person_id, record = _resolve_current_profile(paths, selector)
    relative = record["briefing_path"] if output_format == "markdown" else record["profile_path"]
    path = _safe_artifact_path(paths, relative)
    try:
        content: object = path.read_text(encoding="utf-8")
        if output_format == "json":
            content = json.loads(str(content))
    except (OSError, json.JSONDecodeError, UnicodeError) as exc:
        raise _playbook_read_error(f"Current playbook artifact could not be read: {relative}") from exc
    if output_format == "json" and (
        not isinstance(content, dict) or content.get("profile_kind") != "stakeholder_briefing"
    ):
        raise _playbook_read_error("Current stakeholder profile is invalid.")
    return RunSummary(
        status="success",
        exit_code=0,
        details={
            "command": "playbook_show",
            "person_id": person_id,
            "format": output_format,
            "content": content,
        },
    )


def brief(start: Path, selector: str, *, output_format: str = "markdown") -> RunSummary:
    if output_format not in {"markdown", "json"}:
        raise ValueError(f"Unsupported playbook output format: {output_format}")
    _, paths = load_project(start)
    person_id, record = _resolve_current_profile(paths, selector)
    try:
        profile = json.loads(_safe_artifact_path(paths, record["profile_path"]).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError) as exc:
        raise _playbook_read_error("Current stakeholder profile could not be read.") from exc
    if not isinstance(profile, dict) or profile.get("profile_kind") != "stakeholder_briefing":
        raise _playbook_read_error("Current stakeholder profile is invalid.")
    projection = _brief_projection(profile)
    content: object = projection if output_format == "json" else _render_brief_projection(projection)
    return RunSummary(
        status="success",
        exit_code=0,
        details={
            "command": "playbook_brief",
            "person_id": person_id,
            "format": output_format,
            "content": content,
        },
    )


def repair_index(start: Path, *, clock: Clock | None = None) -> RunSummary:
    _, paths = load_project(start)
    active_clock = clock or SystemClock()
    with ProjectLock(lock_path(paths.cache), clock=active_clock):
        records, _ = read_derivation_records(paths.playbook_state / "derivation-ledger.jsonl")
        committed = next((record for record in reversed(records) if record.get("status") == "success"), None)
        if committed is None:
            raise _playbook_read_error("No successfully committed derivation exists for index repair.")
        generation_relative = Path(str(committed["generation_path"]))
        generation_path = _safe_artifact_path(paths, generation_relative.as_posix())
        if not generation_path.is_dir():
            raise _playbook_read_error("Latest committed derivation generation is missing.")
        profiles: dict[str, dict[str, str]] = {}
        for record in committed["profiles"]:
            if not isinstance(record, dict) or not all(
                isinstance(record.get(key), str) for key in ("person_id", "profile_path", "briefing_path")
            ):
                raise _playbook_read_error("Latest derivation ledger profile manifest is invalid.")
            profile_path = _safe_artifact_path(paths, record["profile_path"])
            briefing_path = _safe_artifact_path(paths, record["briefing_path"])
            _validate_generation_profile(profile_path, briefing_path)
            profiles[record["person_id"]] = {
                "profile_path": record["profile_path"],
                "briefing_path": record["briefing_path"],
            }
        ruleset = committed.get("ruleset", {})
        index = {
            "schema_version": DERIVATION_SCHEMA_VERSION,
            "status": "current",
            "derivation_run_id": committed["derivation_run_id"],
            "generation_path": committed["generation_path"],
            "input_fingerprint": committed["input_fingerprint"],
            "registry_fingerprint": committed["registry_fingerprint"],
            "overrides_fingerprint": committed["overrides_fingerprint"],
            "ruleset_id": ruleset.get("id"),
            "ruleset_fingerprint": ruleset.get("fingerprint"),
            "profiles": profiles,
            "identity_candidates_path": (generation_relative / "identity-candidates.json").as_posix(),
            "unresolved_identity_count": committed.get("unresolved_identity_count", 0),
            "committed_at": committed["recorded_at"],
        }
        index_relative = _relative_to_meetings_root(paths, paths.derived) / "playbook-index.json"
        _write_json_atomic(paths.meetings_root / index_relative, index)
    return RunSummary(
        status="success",
        exit_code=0,
        artifacts=[{"kind": "playbook_index", "status": "ready", "path": index_relative.as_posix()}],
        details={
            "command": "playbook_repair_index",
            "derivation_run_id": committed["derivation_run_id"],
            "changed": True,
        },
    )


def _resolve_current_profile(paths: ProjectPaths, selector: str) -> tuple[str, dict[str, str]]:
    index_path = paths.derived / "playbook-index.json"
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError) as exc:
        raise _playbook_read_error("No readable current playbook index exists; run `playbook update`.") from exc
    if not isinstance(index, dict):
        raise _playbook_read_error("Current playbook index is invalid.")
    profiles = index.get("profiles")
    if not isinstance(profiles, dict):
        raise _playbook_read_error("Current playbook index is invalid.")
    person_id = selector if selector in profiles else None
    if person_id is None:
        resolution = read_stakeholder_registry(paths.playbook_state / "stakeholders.toml").resolve(selector)
        person_id = resolution.person_id if resolution.status == "reviewed" else None
    record = profiles.get(person_id) if person_id is not None else None
    if not isinstance(record, dict) or not all(
        isinstance(record.get(key), str) for key in ("profile_path", "briefing_path")
    ):
        raise _playbook_read_error(f"No current stakeholder profile matches {selector!r}.")
    return person_id, record


def _brief_projection(profile: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "tracked_asks",
        "tracked_commitments_by_stakeholder",
        "tracked_commitments_to_stakeholder",
        "priorities",
        "concerns_and_risks",
        "communication_preferences",
        "communication_behaviors",
        "interaction_responses",
        "recent_changes",
        "stale_items",
    )
    return {
        "schema_version": "1.0",
        "profile_kind": "stakeholder_brief",
        "stakeholder": profile["stakeholder"],
        "coverage": profile["coverage"],
        **{key: profile.get(key, []) for key in keys},
    }


def _render_brief_projection(projection: dict[str, Any]) -> str:
    stakeholder = projection["stakeholder"]
    coverage = projection["coverage"]
    sections = (
        ("Tracked Asks", "tracked_asks"),
        ("Commitments By The Stakeholder", "tracked_commitments_by_stakeholder"),
        ("Commitments To The Stakeholder", "tracked_commitments_to_stakeholder"),
        ("Current Priorities", "priorities"),
        ("Concerns And Risks", "concerns_and_risks"),
        ("Explicit Communication Preferences", "communication_preferences"),
        ("Observed Communication Behaviors", "communication_behaviors"),
        ("Interaction Responses", "interaction_responses"),
    )
    lines = [
        f"# Stakeholder Brief: {stakeholder['display_name']}",
        "",
        f"Evidence coverage: {coverage['source_count']} source(s), "
        f"{coverage['first_observed_at'] or 'unknown'} to {coverage['last_observed_at'] or 'unknown'}.",
    ]
    for heading, key in sections:
        lines.extend(["", f"## {heading}", ""])
        entries = [entry for entry in projection[key] if entry.get("review_state") != "rejected"]
        lines.extend(_render_entries(entries))
    if projection["stale_items"]:
        lines.extend(["", "## Freshness Warnings", ""])
        lines.extend(f"- `{entry_id}` requires freshness review." for entry_id in projection["stale_items"])
    return "\n".join(lines) + "\n"


def _playbook_read_error(message: str) -> MeetingIngestError:
    return MeetingIngestError(
        phase="playbook_read",
        code="playbook_not_available",
        message=message,
        exit_code=EXIT_GENERAL_FAILURE,
        recoverable=True,
    )


def _safe_artifact_path(paths: ProjectPaths, relative_path: str) -> Path:
    candidate = (paths.meetings_root / relative_path).resolve()
    root = paths.meetings_root.resolve()
    if candidate != root and root not in candidate.parents:
        raise _playbook_read_error("Playbook artifact path escapes the meetings root.")
    return candidate


def _normalize_observation(
    signal: SignalRecord, source_by_meeting: dict[str, tuple[str, str]]
) -> NormalizedObservation | None:
    if signal.schema_version == "1.1" and signal.source is not None:
        source_id = signal.source.source_id
        source_kind = signal.source.source_kind
        artifact_path = signal.source.artifact_path
        occurred_at = signal.timing.occurred.value if signal.timing is not None else signal.effective_at
    else:
        source_details = source_by_meeting.get(signal.meeting_id or "")
        if source_details is None:
            return None
        source_hash, artifact_path = source_details
        try:
            source_id = mint_source_id(source_hash)
        except ValueError:
            return None
        source_kind = "meeting_transcript"
        occurred_at = signal.effective_at
    return NormalizedObservation(signal, source_id, source_kind, artifact_path, occurred_at)


def _legacy_source_details(records: list[dict[str, object]]) -> dict[str, tuple[str, str]]:
    details: dict[str, tuple[str, str]] = {}
    for record in records:
        meeting_id = record.get("meeting_id")
        source_hash = record.get("source_sha256")
        if not isinstance(meeting_id, str) or not isinstance(source_hash, str):
            continue
        artifact_path = _markdown_artifact_path(record.get("artifacts"))
        if not artifact_path and meeting_id in details:
            artifact_path = details[meeting_id][1]
        details[meeting_id] = (source_hash, artifact_path)
    return details


def _markdown_artifact_path(value: object) -> str:
    artifacts: list[object]
    if isinstance(value, dict):
        artifacts = list(value.values())
    elif isinstance(value, list):
        artifacts = value
    else:
        return ""
    for artifact in artifacts:
        if (
            isinstance(artifact, dict)
            and artifact.get("kind") == "markdown"
            and isinstance(artifact.get("path"), str)
        ):
            return artifact["path"]
    return ""


def _build_profile(
    person: Stakeholder,
    observations: list[NormalizedObservation],
    *,
    run_id: str,
    generated_at: str,
    input_fingerprint: str,
    today: date,
    review_state: ReviewState,
    previous_profile: dict[str, Any] | None,
    ruleset_values: dict[str, int],
) -> dict[str, Any]:
    observed_dates = [value for item in observations if (value := _date_part(item.occurred_at))]
    source_kinds = Counter(item.source_kind for item in observations)
    profile: dict[str, Any] = {
        "schema_version": PROFILE_SCHEMA_VERSION,
        "profile_kind": "stakeholder_briefing",
        "stakeholder": {
            "person_id": person.person_id,
            "display_name": person.display_name,
            "aliases": list(person.aliases),
            "identity_status": "reviewed",
        },
        "derivation_run_id": run_id,
        "generated_at": generated_at,
        "input_fingerprint": input_fingerprint,
        "coverage": {
            "source_count": len({item.source_id for item in observations}),
            "source_kinds": dict(sorted(source_kinds.items())),
            "first_observed_at": min(observed_dates) if observed_dates else None,
            "last_observed_at": max(observed_dates) if observed_dates else None,
        },
        **{name: [] for name in _PROFILE_LISTS},
        "patterns": {"status": "not_available_in_briefing_v1", "items": []},
        "guidance": {"status": "not_available_in_briefing_v1", "items": []},
        "recent_changes": [],
        "contradiction_candidates": [],
        "unresolved_observations": [],
        "stale_items": [],
        "evidence_index": _build_evidence_index(observations),
    }
    grouped = _group_observations(observations)
    for group in grouped:
        signal = group[0].signal
        category, entry_kind = _CATEGORY_BY_SIGNAL[signal.signal_type]
        entry = _entry_from_observations(
            person.person_id,
            group,
            entry_kind=entry_kind,
            today=today,
            ruleset_values=ruleset_values,
        )
        entry["review_state"] = review_state.entry_review_states.get(entry["entry_id"], "unreviewed")
        if entry["entry_id"] in review_state.resolutions and signal.signal_type in {"explicit_ask", "commitment"}:
            entry.update(review_state.resolutions[entry["entry_id"]])
        if any(item.signal.inference_level == "weak_inference" for item in group) or entry["confidence"] == "low":
            profile["unresolved_observations"].append(entry)
        else:
            profile[category].append(entry)
        if entry["freshness_state"] != "current":
            profile["stale_items"].append(entry["entry_id"])
    profile["recent_changes"] = _recent_changes(profile, previous_profile)
    return profile


def _entry_from_observations(
    person_id: str,
    observations: list[NormalizedObservation],
    *,
    entry_kind: str,
    today: date,
    ruleset_values: dict[str, int],
) -> dict[str, Any]:
    observation = observations[0]
    signal = observation.signal
    references = [
        {"source_id": item.source_id, "signal_id": item.signal.signal_id}
        for item in observations
    ]
    reference = references[0]
    anchor = hashlib.sha256(
        canonical_json({"person_id": person_id, "entry_kind": entry_kind, **reference}).encode("utf-8")
    ).hexdigest()[:12]
    observed_dates = [value for item in observations if (value := _date_part(item.occurred_at))]
    first_observed = min(observed_dates) if observed_dates else None
    last_observed = max(observed_dates) if observed_dates else None
    age_days = (today - date.fromisoformat(first_observed)).days if first_observed else None
    freshness_age = (today - date.fromisoformat(last_observed)).days if last_observed else None
    freshness = _freshness_state(signal.signal_type, freshness_age, ruleset_values)
    source_count = len({item.source_id for item in observations})
    confidence = min((item.signal.confidence for item in observations), key=_confidence_rank)
    recurrence = (
        "recurring"
        if source_count >= ruleset_values["min_recurrent_source_events"]
        else "one_off"
    )
    entry: dict[str, Any] = {
        "entry_id": f"entry-{person_id}-{entry_kind}-{anchor}",
        "entry_kind": entry_kind,
        "statement": signal.summary,
        "scope": {
            "project_refs": sorted(signal.project_refs),
            "topics": sorted(signal.topics),
            "channel": signal.source.channel if signal.source is not None else None,
        },
        "confidence": confidence,
        "confidence_rationale": (
            f"{len(observations)} compatible observation(s) from {source_count} distinct source(s); "
            "confidence does not exceed the lowest-confidence observation."
        ),
        "supporting_observations": references,
        "contradicting_observations": [],
        "distinct_source_count": source_count,
        "first_observed_at": first_observed,
        "last_observed_at": last_observed,
        "recurrence": recurrence,
        "lifecycle_state": "active",
        "review_state": "unreviewed",
        "freshness_state": freshness,
    }
    if signal.signal_type in {"explicit_ask", "commitment"}:
        entry.update(
            {
                "originating_observation": reference,
                "observed_at": first_observed,
                "age_days": age_days,
                "last_lifecycle_evidence_at": last_observed,
                "resolution_state": "unknown",
                "resolution_source": None,
            }
        )
    return entry


def _build_evidence_index(observations: list[NormalizedObservation]) -> dict[str, dict[str, Any]]:
    evidence_index: dict[str, dict[str, Any]] = {}
    for observation in observations:
        signal = observation.signal
        citation = f"{observation.source_id}/{signal.signal_id}"
        locator = signal.evidence.locator
        if locator is not None:
            rendered_locator: dict[str, str | None] = {"scheme": locator.scheme, "value": locator.value}
        elif signal.evidence.timestamp:
            rendered_locator = {"scheme": "timestamp", "value": signal.evidence.timestamp}
        else:
            rendered_locator = {"scheme": "none", "value": None}
        evidence_index[citation] = {
            "source_artifact_path": observation.artifact_path,
            "observation_id": signal.signal_id,
            "evidence_kind": signal.evidence.kind,
            "excerpt": signal.evidence.text,
            "speaker": signal.evidence.speaker,
            "locator": rendered_locator,
        }
    return dict(sorted(evidence_index.items()))


def _group_observations(observations: list[NormalizedObservation]) -> list[list[NormalizedObservation]]:
    groups: dict[tuple[object, ...], list[NormalizedObservation]] = defaultdict(list)
    for observation in observations:
        signal = observation.signal
        if signal.signal_type in {"explicit_ask", "commitment", "decision_rationale"}:
            key: tuple[object, ...] = (signal.signal_type, observation.source_id, signal.signal_id)
        else:
            key = (
                signal.signal_type,
                " ".join(signal.summary.split()).casefold(),
                tuple(sorted(signal.topics)),
                tuple(sorted(signal.project_refs)),
                signal.source.channel if signal.source is not None else None,
            )
        groups[key].append(observation)
    return [sorted(group, key=_observation_sort_key) for _, group in sorted(groups.items(), key=lambda item: repr(item[0]))]


def _confidence_rank(value: str) -> int:
    return {"low": 0, "medium": 1, "high": 2}[value]


def _recent_changes(profile: dict[str, Any], previous_profile: dict[str, Any] | None) -> list[dict[str, Any]]:
    if previous_profile is None:
        return []
    previous_entries = {entry["entry_id"]: entry for entry in _all_profile_entries(previous_profile)}
    changes: list[dict[str, Any]] = []
    for entry in _all_profile_entries(profile):
        prior = previous_entries.get(entry["entry_id"])
        if prior is None:
            changes.append({"entry_id": entry["entry_id"], "change_kinds": ["first_observed"]})
            continue
        item: dict[str, Any] = {"entry_id": entry["entry_id"], "change_kinds": []}
        for field, kind in (
            ("lifecycle_state", "lifecycle_state_changed"),
            ("review_state", "review_state_changed"),
            ("freshness_state", "freshness_state_changed"),
        ):
            if prior.get(field) != entry.get(field):
                item["change_kinds"].append(kind)
                item[field] = {"prior": prior.get(field), "current": entry.get(field)}
        if item["change_kinds"]:
            changes.append(item)
    return changes


def _all_profile_entries(profile: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for key in (*_PROFILE_LISTS, "unresolved_observations"):
        value = profile.get(key, [])
        if isinstance(value, list):
            entries.extend(item for item in value if isinstance(item, dict) and "entry_id" in item)
    return entries


def _load_current_profiles(paths: ProjectPaths) -> dict[str, dict[str, Any]]:
    index_path = paths.derived / "playbook-index.json"
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    if not isinstance(index, dict):
        return {}
    profiles = index.get("profiles")
    if not isinstance(profiles, dict):
        return {}
    loaded: dict[str, dict[str, Any]] = {}
    for person_id, record in profiles.items():
        if not isinstance(person_id, str) or not isinstance(record, dict):
            continue
        relative_path = record.get("profile_path")
        if not isinstance(relative_path, str):
            continue
        try:
            payload = json.loads(_safe_artifact_path(paths, relative_path).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError, MeetingIngestError):
            continue
        if isinstance(payload, dict):
            loaded[person_id] = payload
    return loaded


def _freshness_state(signal_type: str, age_days: int | None, ruleset_values: dict[str, int]) -> str:
    if age_days is None:
        return "verify_before_citing"
    if signal_type in {"explicit_ask", "commitment"}:
        return "verify_before_citing" if age_days > ruleset_values["tracked_verify_after_days"] else "current"
    if signal_type in {"stakeholder_priority", "risk_or_concern", "decision_rationale"}:
        return "stale" if age_days > ruleset_values["priority_concern_stale_after_days"] else "current"
    return "stale" if age_days > ruleset_values["preference_behavior_response_stale_after_days"] else "current"


def _render_briefing(profile: dict[str, Any]) -> str:
    headings = (
        ("Tracked Asks", "tracked_asks"),
        ("Commitments By The Stakeholder", "tracked_commitments_by_stakeholder"),
        ("Commitments To The Stakeholder", "tracked_commitments_to_stakeholder"),
        ("Current Priorities", "priorities"),
        ("Concerns And Risks", "concerns_and_risks"),
        ("Decision Rationale History", "decision_rationales"),
        ("Explicit Communication Preferences", "communication_preferences"),
        ("Observed Communication Behaviors", "communication_behaviors"),
        ("Interaction Responses", "interaction_responses"),
    )
    stakeholder = profile["stakeholder"]
    coverage = profile["coverage"]
    lines = [
        f"# Stakeholder Briefing: {stakeholder['display_name']}",
        "",
        "## Identity And Evidence Coverage",
        "",
        f"- Person ID: `{stakeholder['person_id']}`",
        f"- Sources: {coverage['source_count']}",
        f"- Observed: {coverage['first_observed_at'] or 'unknown'} to {coverage['last_observed_at'] or 'unknown'}",
    ]
    for heading, key in headings:
        lines.extend(["", f"## {heading}", ""])
        entries = [entry for entry in profile[key] if entry.get("review_state") != "rejected"]
        lines.extend(_render_entries(entries))
    lines.extend(["", "## Communication Cues", "", "Not available in Briefing V1."])
    lines.extend(["", "## Emerging And Established Patterns", "", "Not available in Briefing V1."])
    lines.extend(["", "## Recent Changes", ""])
    if profile["recent_changes"]:
        for change in profile["recent_changes"]:
            lines.append(f"- `{change['entry_id']}`: {', '.join(change['change_kinds'])}")
    else:
        lines.append("None identified.")
    lines.extend(["", "## Contradictions And Cautions", "", "None identified."])
    lines.extend(["", "## Unresolved Or Low-Confidence Observations", ""])
    lines.extend(_render_entries(profile["unresolved_observations"]))
    lines.extend(["", "## Evidence Index", ""])
    evidence_index = profile.get("evidence_index", {})
    if not evidence_index:
        lines.append("None identified.")
    else:
        for citation, evidence in evidence_index.items():
            locator = evidence["locator"]
            locator_text = locator["scheme"]
            if locator["value"] is not None:
                locator_text += f":{locator['value']}"
            speaker = _single_line(evidence["speaker"] or "unknown speaker")
            artifact = evidence["source_artifact_path"] or "unknown artifact"
            excerpt = _single_line(evidence["excerpt"])
            lines.append(
                f"- `{citation}` — `{artifact}`; {evidence['evidence_kind']}; "
                f"{speaker}; {locator_text}; {excerpt}"
            )
    return "\n".join(lines) + "\n"


def _single_line(value: str) -> str:
    return " ".join(value.split())


def _render_entries(entries: list[dict[str, Any]]) -> list[str]:
    if not entries:
        return ["None identified."]
    rendered = []
    for entry in entries:
        reference = entry["supporting_observations"][0]
        freshness = "" if entry["freshness_state"] == "current" else f" [{entry['freshness_state']}]"
        rendered.append(
            f"- {entry['statement']}{freshness} (`{entry['entry_id']}`; "
            f"`{reference['source_id']}/{reference['signal_id']}`)"
        )
    return rendered


def _observation_sort_key(observation: NormalizedObservation) -> tuple[str, str, str]:
    return (observation.occurred_at or "9999-99-99", observation.source_id, observation.signal.signal_id)


def _raw_stakeholder_name(signal: SignalRecord) -> str:
    return signal.stakeholder_name_raw if signal.schema_version == "1.1" else signal.stakeholder_name


def _date_part(value: str | None) -> str | None:
    if not value or len(value) < 10:
        return None
    candidate = value[:10]
    try:
        date.fromisoformat(candidate)
    except ValueError:
        return None
    return candidate


def _path_fingerprint(path: Path) -> str:
    if not path.exists():
        return f"sha256:{hashlib.sha256(b'').hexdigest()}"
    return f"sha256:{sha256_file(path)}"


def _relative_to_meetings_root(paths: ProjectPaths, path: Path) -> Path:
    try:
        return path.relative_to(paths.meetings_root)
    except ValueError as exc:
        raise MeetingIngestError(
            phase="playbook_derivation",
            code="derived_path_outside_meetings_root",
            message="Configured derived path must be inside the meetings root.",
            exit_code=EXIT_ARTIFACT_WRITE,
            recoverable=True,
            details={"path": str(path)},
        ) from exc


def _canonical_fingerprint(value: object) -> str:
    return f"sha256:{hashlib.sha256(canonical_json(value).encode('utf-8')).hexdigest()}"


def _write_json_atomic(path: Path, payload: object) -> None:
    _write_text_atomic(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _write_text_atomic(path: Path, content: str) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(path)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise MeetingIngestError(
            phase="playbook_generation",
            code="artifact_write_failed",
            message=f"Could not write playbook artifact: {path}",
            exit_code=EXIT_ARTIFACT_WRITE,
            recoverable=True,
            details={"path": str(path)},
        ) from exc


def _append_derivation_record(path: Path, record: dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as ledger:
            ledger.write(json.dumps(record, sort_keys=True) + "\n")
            ledger.flush()
    except OSError as exc:
        raise MeetingIngestError(
            phase="playbook_ledger",
            code="derivation_ledger_write_failed",
            message=f"Could not append derivation ledger: {path}",
            exit_code=EXIT_LEDGER_WRITE,
            recoverable=True,
            details={"path": str(path)},
        ) from exc


def read_derivation_records(path: Path) -> tuple[list[dict[str, Any]], list[tuple[int, str]]]:
    records: list[dict[str, Any]] = []
    issues: list[tuple[int, str]] = []
    if not path.exists():
        return records, issues
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        return records, [(0, f"Derivation ledger could not be read: {exc}")]
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            issues.append((line_number, f"Derivation ledger line is not valid JSON: {exc.msg}"))
            continue
        if not _valid_derivation_record(record):
            issues.append((line_number, "Derivation ledger line is missing required contract fields."))
            continue
        records.append(record)
    return records, issues


def _valid_derivation_record(value: object) -> bool:
    if not isinstance(value, dict) or value.get("schema_version") != DERIVATION_SCHEMA_VERSION:
        return False
    if value.get("event") not in {"briefing_derivation_completed", "briefing_derivation_failed"}:
        return False
    if value.get("status") not in {"success", "failed"}:
        return False
    common_fields_valid = all(isinstance(value.get(key), expected) for key, expected in (
        ("derivation_run_id", str),
        ("input_fingerprint", str),
        ("registry_fingerprint", str),
        ("overrides_fingerprint", str),
        ("ruleset", dict),
        ("profiles", list),
        ("warnings", list),
        ("errors", list),
        ("recorded_at", str),
    ))
    if not common_fields_valid:
        return False
    ruleset = value["ruleset"]
    if not all(isinstance(ruleset.get(key), expected) for key, expected in (
        ("id", str),
        ("fingerprint", str),
        ("values", dict),
    )):
        return False
    if value["status"] == "failed":
        return value.get("generation_path") is None and value["event"] == "briefing_derivation_failed"
    if value["event"] != "briefing_derivation_completed" or not isinstance(value.get("generation_path"), str):
        return False
    return all(
        isinstance(profile, dict)
        and all(isinstance(profile.get(key), str) for key in ("person_id", "profile_path", "briefing_path"))
        for profile in value["profiles"]
    )


def _derivation_is_committed(paths: ProjectPaths, run_id: str) -> bool:
    records, _ = read_derivation_records(paths.playbook_state / "derivation-ledger.jsonl")
    return any(record["derivation_run_id"] == run_id and record["status"] == "success" for record in records)


def _record_failed_derivation(
    paths: ProjectPaths, *, run_id: str, now: datetime, trigger: str, error: MeetingIngestError
) -> None:
    try:
        inputs = discover_inputs(paths)
        record = {
            "schema_version": DERIVATION_SCHEMA_VERSION,
            "event": "briefing_derivation_failed",
            "derivation_run_id": run_id,
            "status": "failed",
            "trigger": trigger,
            "input_fingerprint": inputs.input_fingerprint,
            "registry_fingerprint": inputs.registry_fingerprint,
            "overrides_fingerprint": inputs.overrides_fingerprint,
            "ruleset": {
                "id": RULESET_ID,
                "fingerprint": inputs.ruleset_fingerprint,
                "values": inputs.ruleset_values,
            },
            "provider": "none",
            "generation_path": None,
            "profiles": [],
            "unresolved_identity_count": 0,
            "warnings": list(inputs.warnings),
            "errors": [error.to_error_block()],
            "recorded_at": format_iso_timestamp(now),
        }
        _append_derivation_record(paths.playbook_state / "derivation-ledger.jsonl", record)
    except Exception:
        # Preserve the original derivation failure when the failure audit cannot be written.
        return


def _validate_generation_profile(profile_path: Path, briefing_path: Path) -> None:
    try:
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        briefing = briefing_path.read_text(encoding="utf-8")
    except (OSError, json.JSONDecodeError) as exc:
        raise MeetingIngestError(
            phase="playbook_generation",
            code="generation_validation_failed",
            message="Generated stakeholder profile could not be validated.",
            exit_code=EXIT_ARTIFACT_WRITE,
            recoverable=True,
        ) from exc
    if profile.get("schema_version") != PROFILE_SCHEMA_VERSION or not briefing.startswith("# Stakeholder Briefing:"):
        raise MeetingIngestError(
            phase="playbook_generation",
            code="generation_validation_failed",
            message="Generated stakeholder profile failed contract validation.",
            exit_code=EXIT_ARTIFACT_WRITE,
            recoverable=True,
        )
