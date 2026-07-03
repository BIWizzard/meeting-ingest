import json
from pathlib import Path
from ingest_meeting import bootstrap, paths


def _seed_meetings(tmp):
    base = paths.project_paths(tmp)["base"]
    (base / "2026-05-01-standup.md").write_text("# s1")
    (base / "2026-05-04-standup.md").write_text("# s4")
    (base / "2026-05-04-standup-daily.md").write_text("# s4 dup")
    (base / "stakeholder-comms-playbook.md").write_text(
        "## Dilip Jayavelu — CLIENT VOICE\n- terse\n"
        "## Jim Haley — peer (Trace3)\n- multi-front load\n")


def test_dry_run_mapping_flags_collision_no_writes(tmp_path):
    _seed_meetings(tmp_path)
    m = bootstrap.plan_mapping(tmp_path)
    assert any("2026-05-04" in c["collision"] for c in m["collisions"])
    assert not any(paths.project_paths(tmp_path)["signals"].glob("*.jsonl"))
    # supersede stays human-filled (empty in P1)
    assert m["supersede"] == []
    # both seeded headers match a known role pattern -> nothing flagged
    assert m["unrecognized_roles"] == []
    # full people structure: exactly two, correct names / slug derivation / tiers
    assert len(m["people"]) == 2
    by_id = {p["person_id"]: p for p in m["people"]}
    assert by_id["dilip-jayavelu"]["display_name"] == "Dilip Jayavelu"
    assert by_id["dilip-jayavelu"]["tier"] == "client"
    assert by_id["jim-haley"]["display_name"] == "Jim Haley"
    assert by_id["jim-haley"]["tier"] == "colleague"


def test_unrecognized_role_defaults_client_and_is_flagged(tmp_path):
    base = paths.project_paths(tmp_path)["base"]
    (base / "stakeholder-comms-playbook.md").write_text(
        "## Pat Vendor — External vendor\n- net 30\n")
    m = bootstrap.plan_mapping(tmp_path)
    assert m["people"][0]["tier"] == "client"  # privacy-conservative default
    assert m["unrecognized_roles"] == [
        {"display_name": "Pat Vendor", "role": "External vendor",
         "defaulted_tier": "client"}
    ]


def test_apply_emits_only_legal_bootstrap_events(tmp_path):
    _seed_meetings(tmp_path)
    m = bootstrap.plan_mapping(tmp_path)
    bootstrap.apply_mapping(tmp_path, m, ingest_run_id="bootstrap1", home=tmp_path)
    evs = []
    for f in paths.project_paths(tmp_path)["signals"].glob("*.jsonl"):
        evs += [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
    assert evs, "should emit events"
    assert all(e["origin"] == "bootstrap" for e in evs)
    assert all(e["event"] in ("observation", "reclassification") for e in evs)
    assert not any(e["event"] == "supersession" for e in evs)
    # apply_mapping must persist the roster to the global home
    roster_json = tmp_path / ".claude" / "people" / "roster.json"
    assert roster_json.exists(), "apply_mapping must save roster.json"
    persisted = json.loads(roster_json.read_text())
    ids = {p["person_id"] for p in persisted["people"]}
    assert {"dilip-jayavelu", "jim-haley"} <= ids
