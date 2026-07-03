from pathlib import Path
import json
from ingest_meeting import pipeline, roster, paths, ledger, bootstrap

FX = Path(__file__).parent.parent / "fixtures"

def _stub(text, mtype):
    return {"markdown": "# Stand-Up\n\n## TL;DR\n- x\n## Communication Signals (by person)\n- Ken\n",
            "observations": [
                {"signal_id": "s1", "speaker": "Ken Graham", "person_id": "ken",
                 "kind": "stable-preference", "text": "metric-led"},
                {"signal_id": "s2", "speaker": "Dilip Jayavelu", "person_id": "dilip",
                 "kind": "project-specific", "text": "DECISION: 30-min cadence"},
            ]}

def _roster(tmp):
    r = roster.Roster.load(tmp, home=tmp)
    r.classify("Ken Graham", "ken", "self")
    r.classify("Dilip Jayavelu", "dilip", "client")
    r.save()

def test_T1_scoping_invariant_no_signal_in_global(tmp_path):
    _roster(tmp_path)
    pipeline.ingest_transcript(FX / "standup.txt", tmp_path, _stub,
                               ingest_run_id="r1", home=tmp_path)
    sig = list(paths.project_paths(tmp_path)["signals"].glob("*.jsonl"))
    assert sig
    gp = paths.global_paths(tmp_path)["people"]
    assert {p.name for p in gp.glob("*")} <= {"roster.json"}
    assert "metric-led" not in (gp / "roster.json").read_text()

def test_T2_portability_second_project_empty_client_roster(tmp_path):
    _roster(tmp_path)
    proj2 = tmp_path / "proj2"; proj2.mkdir()
    res = pipeline.ingest_transcript(FX / "standup.txt", proj2, _stub,
                                     ingest_run_id="r1", home=tmp_path)
    assert Path(res["signals_path"]).exists()

def test_T4_person_resolution_alias_and_convergence(tmp_path):
    r = roster.Roster.load(tmp_path, home=tmp_path)
    r.classify("Jean Francois Hardan", "jf", "colleague", aliases=["John Francois"])
    r.save()
    pid, st = roster.Roster.load(tmp_path, home=tmp_path).resolve("John Francois")
    assert (pid, st) == ("jf", "matched")

def test_T5_idempotency_by_content(tmp_path):
    _roster(tmp_path)
    a = pipeline.ingest_transcript(FX / "standup.txt", tmp_path, _stub,
                                   ingest_run_id="r1", home=tmp_path)
    cp = tmp_path / "z.txt"; cp.write_bytes((FX / "standup.txt").read_bytes())
    b = pipeline.ingest_transcript(cp, tmp_path, _stub,
                                   ingest_run_id="r2", home=tmp_path)
    assert b["skipped"] and b["meeting_id"] == a["meeting_id"]

def test_T6_resumable_partial_batch(tmp_path):
    _roster(tmp_path)
    a = pipeline.ingest_transcript(FX / "standup.txt", tmp_path, _stub,
                                   ingest_run_id="r1", home=tmp_path)
    pipeline.ingest_transcript(FX / "standup.txt", tmp_path, _stub,
                               ingest_run_id="r2", home=tmp_path)
    log = Path(a["signals_path"]).read_text()
    assert log.count('"event": "observation"') == 2

def test_T9_template_fidelity_and_facets(tmp_path):
    _roster(tmp_path)
    res = pipeline.ingest_transcript(FX / "standup.txt", tmp_path, _stub,
                                     ingest_run_id="r1", home=tmp_path)
    md = Path(res["markdown_path"]).read_text()
    assert "## Communication Signals (by person)" in md
    log = Path(res["signals_path"]).read_text()
    assert "DECISION: 30-min cadence" in log

def test_T10_migration_safety_collision_flagged(tmp_path):
    base = paths.project_paths(tmp_path)["base"]
    (base / "2026-05-04-standup.md").write_text("a")
    (base / "2026-05-04-standup-daily.md").write_text("b")
    m = bootstrap.plan_mapping(tmp_path)
    assert any("2026-05-04" in c["collision"] for c in m["collisions"])
    assert not list(paths.project_paths(tmp_path)["signals"].glob("*.jsonl"))

def test_T17_bootstrap_event_contract(tmp_path):
    base = paths.project_paths(tmp_path)["base"]
    (base / "stakeholder-comms-playbook.md").write_text(
        "## Dilip Jayavelu — CLIENT VOICE\n- terse\n")
    m = bootstrap.plan_mapping(tmp_path)
    bootstrap.apply_mapping(tmp_path, m, "bootstrap1", home=tmp_path)
    evs = []
    for f in paths.project_paths(tmp_path)["signals"].glob("*.jsonl"):
        evs += [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
    assert evs and all(e["origin"] == "bootstrap" for e in evs)
    assert all(e["event"] in ("observation", "reclassification") for e in evs)
