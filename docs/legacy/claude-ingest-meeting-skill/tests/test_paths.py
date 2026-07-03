from pathlib import Path
from ingest_meeting import paths

def test_project_paths_created(tmp_path):
    p = paths.project_paths(tmp_path)
    assert p["inbox"] == tmp_path / "_local/project-context/meetings/_inbox"
    assert p["signals"].name == "_signals"
    for key in ("inbox", "processed", "signals", "quarantine"):
        assert p[key].is_dir(), f"{key} should be created"
    assert p["ledger"] == tmp_path / "_local/project-context/meetings/_ledger.jsonl"

def test_global_paths_created(tmp_path):
    g = paths.global_paths(home=tmp_path)
    assert g["roster"] == tmp_path / ".claude/people/roster.md"
    assert g["roster"].parent.is_dir()
