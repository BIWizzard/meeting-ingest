from pathlib import Path
from ingest_meeting import pipeline, paths, ledger, roster

FX = Path(__file__).parent / "fixtures"

def _stub(clean_text, mtype):
    return {
        "markdown": "# Stand-Up\n\n## TL;DR\n- did things\n",
        "observations": [
            {"signal_id": "s1", "person_id": "ken", "kind": "stable-preference",
             "text": "metric-led updates", "speaker": "Ken Graham"},
        ],
    }

def _seed_roster(tmp):
    r = roster.Roster.load(tmp, home=tmp)
    r.classify("Ken Graham", person_id="ken", tier="self")
    r.save()

def test_ingest_writes_md_and_events(tmp_path):
    _seed_roster(tmp_path)
    res = pipeline.ingest_transcript(FX / "standup.txt", tmp_path, _stub,
                                     ingest_run_id="run1", home=tmp_path)
    md = Path(res["markdown_path"])
    assert md.exists() and md.name.endswith(".md")
    assert "standup" in md.name
    log = Path(res["signals_path"])
    assert log.exists() and log.read_text().count('"event": "observation"') == 1
    assert ledger.already_ingested(tmp_path, res["source_sha256"]) == res["meeting_id"]

def test_idempotent_reingest_renamed_copy(tmp_path):
    _seed_roster(tmp_path)
    a = pipeline.ingest_transcript(FX / "standup.txt", tmp_path, _stub,
                                   ingest_run_id="run1", home=tmp_path)
    copy = tmp_path / "renamed.txt"
    copy.write_bytes((FX / "standup.txt").read_bytes())
    b = pipeline.ingest_transcript(copy, tmp_path, _stub,
                                   ingest_run_id="run2", home=tmp_path)
    assert b["skipped"] is True and b["meeting_id"] == a["meeting_id"]
    log = Path(a["signals_path"])
    assert log.read_text().count('"event": "observation"') == 1  # no double append

def test_dry_run_writes_nothing(tmp_path):
    _seed_roster(tmp_path)
    res = pipeline.ingest_transcript(FX / "standup.txt", tmp_path, _stub,
                                     dry_run=True, ingest_run_id="run1", home=tmp_path)
    assert res["dry_run"] is True
    assert not any(paths.project_paths(tmp_path)["signals"].glob("*.jsonl"))
    assert ledger.already_ingested(tmp_path, res["source_sha256"]) is None

def test_unresolved_person_collected_not_written_global(tmp_path):
    _seed_roster(tmp_path)  # only Ken known; "ken" obs resolves, add an unknown obs
    def stub2(t, m):
        d = _stub(t, m)
        d["observations"].append({"signal_id": "s2", "person_id": None,
            "kind": "project-specific", "text": "x", "speaker": "Dilip Jayavelu"})
        return d
    res = pipeline.ingest_transcript(FX / "standup.txt", tmp_path, stub2,
                                     ingest_run_id="run1", home=tmp_path)
    assert "Dilip Jayavelu" in [u["raw"] for u in res["unresolved"]]
