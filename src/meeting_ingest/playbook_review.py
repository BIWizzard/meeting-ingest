"""Append-only stakeholder playbook review events and folded current state."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Any, Callable

from meeting_ingest.clock import Clock, SystemClock, default_suffix, format_iso_timestamp, format_timestamp
from meeting_ingest.errors import EXIT_LEDGER_WRITE, MeetingIngestError
from meeting_ingest.locking import ProjectLock, lock_path
from meeting_ingest.paths import ProjectPaths, load_project
from meeting_ingest.run_summary import RunSummary


REVIEW_SCHEMA_VERSION = "1.0"
REVIEW_ACTIONS = {
    "reject_entry",
    "restore_entry",
    "resolve_tracked_item",
    "suppress_signal",
    "unsuppress_signal",
}
RESOLUTION_STATES = {"explicitly_outstanding", "resolved", "withdrawn", "superseded"}
_REVIEW_ID = re.compile(r"^review-\d{8}T\d{6}Z-[a-z0-9]{4}$")


@dataclass(frozen=True)
class ReviewIssue:
    line_number: int
    code: str
    message: str


@dataclass
class ReviewState:
    entry_review_states: dict[str, str] = field(default_factory=dict)
    resolutions: dict[str, dict[str, str]] = field(default_factory=dict)
    suppressed_signals: set[tuple[str, str]] = field(default_factory=set)
    valid_events: list[dict[str, Any]] = field(default_factory=list)
    issues: list[ReviewIssue] = field(default_factory=list)

    @property
    def rejected_or_suppressed_count(self) -> int:
        rejected = sum(1 for state in self.entry_review_states.values() if state == "rejected")
        return rejected + len(self.suppressed_signals)


def read_review_state(path: Path) -> ReviewState:
    state = ReviewState()
    if not path.exists():
        return state
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        state.issues.append(ReviewIssue(0, "review_event_malformed", f"Review ledger could not be read: {exc}"))
        return state
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            state.issues.append(
                ReviewIssue(line_number, "review_event_malformed", f"Review event is not valid JSON: {exc.msg}")
            )
            continue
        issue = _validate_event(event)
        if issue is not None:
            state.issues.append(ReviewIssue(line_number, "review_event_malformed", issue))
            continue
        state.valid_events.append(event)
        _fold_event(state, event)
    return state


def mutate_review(
    start: Path,
    *,
    action: str,
    target: dict[str, str],
    reason: str | None = None,
    note: str | None = None,
    actor: str = "user",
    clock: Clock | None = None,
    suffix_factory: Callable[[], str] = default_suffix,
) -> RunSummary:
    if action not in REVIEW_ACTIONS:
        raise ValueError(f"Unsupported review action: {action}")
    _validate_new_event_fields(action=action, target=target, reason=reason, note=note, actor=actor)
    _, paths = load_project(start)
    active_clock = clock or SystemClock()
    with ProjectLock(lock_path(paths.cache), clock=active_clock):
        return _mutate_review_locked(
            paths,
            action=action,
            target=target,
            reason=reason,
            note=note,
            actor=actor,
            clock=active_clock,
            suffix_factory=suffix_factory,
        )


def _mutate_review_locked(
    paths: ProjectPaths,
    *,
    action: str,
    target: dict[str, str],
    reason: str | None,
    note: str | None,
    actor: str,
    clock: Clock,
    suffix_factory: Callable[[], str],
) -> RunSummary:
    ledger_path = paths.playbook_state / "overrides.jsonl"
    state = read_review_state(ledger_path)
    if _is_no_op(state, action, target):
        return RunSummary(
            status="no_op",
            exit_code=0,
            details={"command": "playbook_review", "action": action, "target": target, "changed": False},
        )
    now = clock.now_utc()
    suffix = suffix_factory()[:4]
    event = {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "review_event_id": f"review-{format_timestamp(now)}-{suffix}",
        "action": action,
        "target": target,
        "reason": reason,
        "note": note,
        "actor": actor,
        "recorded_at": format_iso_timestamp(now),
    }
    _append_review_event(ledger_path, event)
    return RunSummary(
        status="success",
        exit_code=0,
        details={
            "command": "playbook_review",
            "review_event_id": event["review_event_id"],
            "action": action,
            "target": target,
            "changed": True,
        },
    )


def _validate_event(value: object) -> str | None:
    if not isinstance(value, dict):
        return "Review event must be an object."
    if value.get("schema_version") != REVIEW_SCHEMA_VERSION:
        return "Review event schema_version must be '1.0'."
    event_id = value.get("review_event_id")
    if not isinstance(event_id, str) or not _REVIEW_ID.fullmatch(event_id):
        return "Review event review_event_id is invalid."
    action = value.get("action")
    target = value.get("target")
    actor = value.get("actor")
    recorded_at = value.get("recorded_at")
    if action not in REVIEW_ACTIONS:
        return "Review event action is invalid."
    if not isinstance(target, dict) or any(not isinstance(key, str) or not isinstance(item, str) for key, item in target.items()):
        return "Review event target must contain string fields."
    if not isinstance(actor, str) or not actor.strip():
        return "Review event actor is required."
    if not isinstance(recorded_at, str) or not recorded_at.endswith("Z"):
        return "Review event recorded_at is invalid."
    try:
        _validate_new_event_fields(
            action=action,
            target=target,
            reason=value.get("reason"),
            note=value.get("note"),
            actor=actor,
        )
    except ValueError as exc:
        return str(exc)
    return None


def _validate_new_event_fields(
    *, action: str, target: dict[str, str], reason: object, note: object, actor: str
) -> None:
    if not actor.strip():
        raise ValueError("Review actor is required.")
    if action in {"reject_entry", "restore_entry", "resolve_tracked_item"}:
        entry_id = target.get("entry_id")
        if not isinstance(entry_id, str) or not entry_id.startswith("entry-"):
            raise ValueError("Review target requires a valid entry_id.")
    if action in {"suppress_signal", "unsuppress_signal"}:
        if not target.get("source_id", "").startswith("src-") or not target.get("signal_id", "").startswith("sig-"):
            raise ValueError("Signal review target requires valid source_id and signal_id values.")
    if action in {"reject_entry", "suppress_signal"} and (not isinstance(reason, str) or not reason.strip()):
        raise ValueError("Reject and suppress actions require a reason.")
    if action in {"restore_entry", "unsuppress_signal", "resolve_tracked_item"} and (
        not isinstance(note, str) or not note.strip()
    ):
        raise ValueError("Restore, unsuppress, and resolve actions require a note.")
    if action == "resolve_tracked_item" and target.get("resolution_state") not in RESOLUTION_STATES:
        raise ValueError("Resolve target requires a supported resolution_state.")


def _fold_event(state: ReviewState, event: dict[str, Any]) -> None:
    action = str(event["action"])
    target = event["target"]
    if action == "reject_entry":
        state.entry_review_states[str(target["entry_id"])] = "rejected"
    elif action == "restore_entry":
        state.entry_review_states[str(target["entry_id"])] = "restored"
    elif action == "resolve_tracked_item":
        state.resolutions[str(target["entry_id"])] = {
            "resolution_state": str(target["resolution_state"]),
            "resolution_source": str(event["review_event_id"]),
        }
    elif action == "suppress_signal":
        state.suppressed_signals.add((str(target["source_id"]), str(target["signal_id"])))
    elif action == "unsuppress_signal":
        state.suppressed_signals.discard((str(target["source_id"]), str(target["signal_id"])))


def _is_no_op(state: ReviewState, action: str, target: dict[str, str]) -> bool:
    if action == "reject_entry":
        return state.entry_review_states.get(target["entry_id"]) == "rejected"
    if action == "restore_entry":
        return state.entry_review_states.get(target["entry_id"]) != "rejected"
    if action == "resolve_tracked_item":
        current = state.resolutions.get(target["entry_id"])
        return current is not None and current["resolution_state"] == target["resolution_state"]
    reference = (target["source_id"], target["signal_id"])
    if action == "suppress_signal":
        return reference in state.suppressed_signals
    return reference not in state.suppressed_signals


def _append_review_event(path: Path, event: dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as target:
            target.write(json.dumps(event, sort_keys=True) + "\n")
            target.flush()
    except OSError as exc:
        raise MeetingIngestError(
            phase="playbook_review",
            code="review_ledger_write_failed",
            message=f"Could not append review event: {path}",
            exit_code=EXIT_LEDGER_WRITE,
            recoverable=True,
            details={"path": str(path)},
        ) from exc
