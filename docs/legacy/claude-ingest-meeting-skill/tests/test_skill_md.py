from pathlib import Path

SKILL = Path(__file__).parent.parent / "SKILL.md"

def test_skill_md_exists_and_has_contract():
    t = SKILL.read_text()
    for token in ("name: ingest-meeting", "## Workflow", "## LLM Extraction Contract",
                  '"observations"', "standup variant", "end-of-batch classification",
                  "subagent"):
        assert token in t, f"SKILL.md missing: {token}"
