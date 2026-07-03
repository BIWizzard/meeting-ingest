import re
from collections import defaultdict
from pathlib import Path
from ingest_meeting import paths, identity, events, roster

_PERSON_HDR = re.compile(r"^##\s+(.+?)\s+—\s+(.*)$", re.M)


def _classify_role(role: str) -> tuple[str, bool]:
    """
    Map a playbook role string to a tier.

    Returns ``(tier, recognized)``. A role is *recognized* only when it
    explicitly matches a known pattern (CLIENT -> client; trace3/peer ->
    colleague). Anything else falls back to the privacy-conservative
    ``client`` tier — client signals stay project-local and never travel
    cross-project, so an unknown person defaulting to ``client`` cannot
    leak into the global corpus (the spec's portability boundary). The
    fallback is reported as *not recognized* so the caller can surface it
    for human review rather than silently classifying.
    """
    if "CLIENT" in role.upper():
        return "client", True
    if "trace3" in role.lower() or "peer" in role.lower():
        return "colleague", True
    return "client", False  # conservative default; flagged for review


def plan_mapping(project_root: Path | str) -> dict:
    """
    Produce a reviewable dry-run mapping from the project's base directory.

    Scans all .md files (excluding the stakeholder-comms-playbook), detects
    same-date/same-type filename collisions, and parses the playbook for
    person entries.  No files are written.

    Returns a dict with keys:
      - meetings:            list of .md filenames (sorted)
      - collisions:          list of {"collision": "<date>-<type>", "files": [...]}
      - people:              list of {"display_name", "person_id", "tier"}
      - unrecognized_roles:  list of {"display_name", "role", "defaulted_tier"}
                             — playbook entries whose role did not match a
                             known pattern; defaulted conservatively to
                             ``client`` and surfaced here for human review
      - supersede:           empty list (filled by human review only)
    """
    base = paths.project_paths(project_root)["base"]
    mds = sorted(
        p for p in base.glob("*.md")
        if p.name != "stakeholder-comms-playbook.md"
    )
    by_key: dict[tuple[str, str], list[str]] = defaultdict(list)
    for p in mds:
        m = re.match(r"(\d{4}-\d{2}-\d{2})-([a-z]+)", p.name)
        if m:
            by_key[(m.group(1), m.group(2))].append(p.name)
    collisions = [
        {"collision": f"{k[0]}-{k[1]}", "files": v}
        for k, v in by_key.items()
        if len(v) > 1
    ]

    people: list[dict] = []
    unrecognized_roles: list[dict] = []
    pb = base / "stakeholder-comms-playbook.md"
    if pb.exists():
        for name, role in _PERSON_HDR.findall(pb.read_text()):
            tier, recognized = _classify_role(role)
            display_name = name.strip()
            if not recognized:
                unrecognized_roles.append({
                    "display_name": display_name,
                    "role": role.strip(),
                    "defaulted_tier": tier,
                })
            people.append({
                "display_name": display_name,
                "person_id": re.sub(r"[^a-z]+", "-", display_name.lower()).strip("-"),
                "tier": tier,
            })

    return {
        "meetings": [p.name for p in mds],
        "collisions": collisions,
        "people": people,
        "unrecognized_roles": unrecognized_roles,
        "supersede": [],  # supersede: filled by human review only
    }


def apply_mapping(
    project_root: Path | str,
    mapping: dict,
    ingest_run_id: str,
    home: Path | str | None = None,
) -> dict:
    """
    Apply a reviewed mapping: emit reclassification events for each person.

    Writes ONLY observation and reclassification events with origin:"bootstrap".
    No supersession events are generated; same-day/same-type collisions noted in
    mapping["collisions"] must be resolved manually by adding supersede: lines to
    the mapping before re-applying.

    Args:
        project_root: Root of the project tree.
        mapping:      Dict produced by plan_mapping (possibly with human edits).
        ingest_run_id: Opaque run identifier for traceability.
        home:         Override for the global ~/.claude home directory (tests only).

    Returns:
        Summary dict with applied status, people count, and collision list.
    """
    r = roster.Roster.load(project_root, home=home)
    recorded = identity.now_iso()

    for person in mapping["people"]:
        r.classify(person["display_name"], person["person_id"], person["tier"])
        ev = events.make_event(
            "reclassification",
            recorded[:10],
            recorded,
            "bootstrap",
            {"project": Path(project_root).name, "source": "bootstrap"},
            ingest_run_id,
            {
                "person_id": person["person_id"],
                "from_tier": "unknown",
                "to_tier": person["tier"],
                "reason": "bootstrap-from-playbook",
            },
        )
        events.append_events(
            f"bootstrap-{person['person_id']}", [ev], project_root
        )

    r.save()
    # NOTE: no supersession emitted; mapping["supersede"] requires reviewed
    # lines added by a human (P1: none generated automatically).
    return {
        "applied": True,
        "people": len(mapping["people"]),
        "collisions": mapping["collisions"],
    }
