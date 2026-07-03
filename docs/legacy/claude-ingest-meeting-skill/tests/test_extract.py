from pathlib import Path
from ingest_meeting import extract

FX = Path(__file__).parent / "fixtures"

def test_extract_txt():
    t = extract.extract_text(FX / "standup.txt")
    assert "Quick update on the pipelines" in t

def test_parse_header():
    t = extract.extract_text(FX / "standup.txt")
    h = extract.parse_header(t)
    assert h["meeting_date"] == "2026-05-15"
    assert h["title"].startswith("TRACE3")

def test_detect_type_standup():
    assert extract.detect_type("...", "TRACE3 Daily Stand Up - Post-MVP") == "standup"
    assert extract.detect_type("...", "Call with Gada, Hetal") == "generic"

def test_unknown_extension_raises():
    import pytest
    with pytest.raises(extract.UnsupportedFormat):
        extract.extract_text(Path("x.pdf"))
