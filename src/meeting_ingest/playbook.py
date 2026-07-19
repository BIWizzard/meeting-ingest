"""Deterministic stakeholder briefing derivation and immutable generation commits."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from meeting_ingest.clock import Clock, SystemClock, default_suffix, format_iso_timestamp, format_timestamp
from meeting_ingest.errors import EXIT_ARTIFACT_WRITE, EXIT_LEDGER_WRITE, MeetingIngestError
from meeting_ingest.hashing import sha256_file
from meeting_ingest.ids import canonical_json, mint_source_id
from meeting_ingest.ledger import read_records
from meeting_ingest.locking import ProjectLock, lock_path
from meeting_ingest.paths import ProjectPaths, load_project
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
RENDERER_VERSION = "briefing-markdown-v1"
RULESET_VALUES = {
    "min_recurrent_source_events": 2,
    "tracked_verify_after_days": 30,
    "priority_concern_stale_after_days": 60,
    "preference_behavior_response_stale_after_days": 90,
}

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
        return _update_locked(paths, clock=active_clock, suffix_factory=suffix_factory, trigger=trigger)


def _update_locked(
    paths: ProjectPaths,
    *,
    clock: Clock,
    suffix_factory: Callable[[], str],
    trigger: str,
) -> RunSummary:
    now = clock.now_utc()
    recorded_at = format_iso_timestamp(now)
    suffix = suffix_factory()[:4]
    run_id = f"derive-{now:%Y%m%d}-{format_timestamp(now)}-{suffix}"
    derived_relative = _relative_to_meetings_root(paths, paths.derived)
    generation_relative = derived_relative / "generations" / run_id
    generation_path = paths.meetings_root / generation_relative
    ledger_path = paths.playbook_state / "derivation-ledger.jsonl"

    inputs = discover_inputs(paths)
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
        "values": RULESET_VALUES,
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
    source_hash_by_meeting = {
        str(record["meeting_id"]): str(record["source_sha256"])
        for record in read_records(paths.ledger)
        if record.get("meeting_id") and isinstance(record.get("source_sha256"), str)
    }
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
            observation = _normalize_observation(signal, source_hash_by_meeting)
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
    ruleset_payload = {"id": RULESET_ID, "values": RULESET_VALUES}
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
        warnings=tuple(warnings),
    )


def _normalize_observation(
    signal: SignalRecord, source_hash_by_meeting: dict[str, str]
) -> NormalizedObservation | None:
    if signal.schema_version == "1.1" and signal.source is not None:
        source_id = signal.source.source_id
        source_kind = signal.source.source_kind
        artifact_path = signal.source.artifact_path
        occurred_at = signal.timing.occurred.value if signal.timing is not None else signal.effective_at
    else:
        source_hash = source_hash_by_meeting.get(signal.meeting_id or "")
        if source_hash is None:
            return None
        try:
            source_id = mint_source_id(source_hash)
        except ValueError:
            return None
        source_kind = "meeting_transcript"
        artifact_path = ""
        occurred_at = signal.effective_at
    return NormalizedObservation(signal, source_id, source_kind, artifact_path, occurred_at)


def _build_profile(
    person: Stakeholder,
    observations: list[NormalizedObservation],
    *,
    run_id: str,
    generated_at: str,
    input_fingerprint: str,
    today: date,
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
    }
    for observation in observations:
        signal = observation.signal
        category, entry_kind = _CATEGORY_BY_SIGNAL[signal.signal_type]
        entry = _entry_from_observation(person.person_id, observation, entry_kind=entry_kind, today=today)
        if signal.inference_level == "weak_inference" or signal.confidence == "low":
            profile["unresolved_observations"].append(entry)
        else:
            profile[category].append(entry)
        if entry["freshness_state"] != "current":
            profile["stale_items"].append(entry["entry_id"])
    return profile


def _entry_from_observation(
    person_id: str, observation: NormalizedObservation, *, entry_kind: str, today: date
) -> dict[str, Any]:
    signal = observation.signal
    reference = {"source_id": observation.source_id, "signal_id": signal.signal_id}
    anchor = hashlib.sha256(
        canonical_json({"person_id": person_id, "entry_kind": entry_kind, **reference}).encode("utf-8")
    ).hexdigest()[:12]
    occurred = _date_part(observation.occurred_at)
    age_days = (today - date.fromisoformat(occurred)).days if occurred else None
    freshness = _freshness_state(signal.signal_type, age_days)
    entry: dict[str, Any] = {
        "entry_id": f"entry-{person_id}-{entry_kind}-{anchor}",
        "entry_kind": entry_kind,
        "statement": signal.summary,
        "scope": {
            "project_refs": sorted(signal.project_refs),
            "topics": sorted(signal.topics),
            "channel": signal.source.channel if signal.source is not None else None,
        },
        "confidence": signal.confidence,
        "confidence_rationale": f"One {signal.inference_level.replace('_', ' ')} observation from one source.",
        "supporting_observations": [reference],
        "contradicting_observations": [],
        "distinct_source_count": 1,
        "first_observed_at": occurred,
        "last_observed_at": occurred,
        "lifecycle_state": "active",
        "review_state": "unreviewed",
        "freshness_state": freshness,
    }
    if signal.signal_type in {"explicit_ask", "commitment"}:
        entry.update(
            {
                "originating_observation": reference,
                "observed_at": occurred,
                "age_days": age_days,
                "last_lifecycle_evidence_at": occurred,
                "resolution_state": "unknown",
                "resolution_source": None,
            }
        )
    return entry


def _freshness_state(signal_type: str, age_days: int | None) -> str:
    if age_days is None:
        return "verify_before_citing"
    if signal_type in {"explicit_ask", "commitment"}:
        return "verify_before_citing" if age_days > RULESET_VALUES["tracked_verify_after_days"] else "current"
    if signal_type in {"stakeholder_priority", "risk_or_concern", "decision_rationale"}:
        return "stale" if age_days > RULESET_VALUES["priority_concern_stale_after_days"] else "current"
    return "stale" if age_days > RULESET_VALUES["preference_behavior_response_stale_after_days"] else "current"


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
        entries = profile[key]
        lines.extend(_render_entries(entries))
    lines.extend(["", "## Communication Cues", "", "Not available in Briefing V1."])
    lines.extend(["", "## Emerging And Established Patterns", "", "Not available in Briefing V1."])
    lines.extend(["", "## Recent Changes", "", "None identified."])
    lines.extend(["", "## Contradictions And Cautions", "", "None identified."])
    lines.extend(["", "## Unresolved Or Low-Confidence Observations", ""])
    lines.extend(_render_entries(profile["unresolved_observations"]))
    lines.extend(["", "## Evidence Index", ""])
    all_entries = [entry for key in _PROFILE_LISTS for entry in profile[key]] + profile["unresolved_observations"]
    if not all_entries:
        lines.append("None identified.")
    else:
        for entry in all_entries:
            ref = entry["supporting_observations"][0]
            lines.append(f"- `{ref['source_id']}/{ref['signal_id']}` — `{entry['entry_id']}`")
    return "\n".join(lines) + "\n"


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
