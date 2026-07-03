from pathlib import Path
import os
from zipfile import ZipFile

import pytest

from meeting_ingest.errors import UnsupportedSourceFormatError
from meeting_ingest.extract import extract_source, infer_effective_date


def test_extract_txt_normalizes_text_and_infers_filename_date(tmp_path: Path) -> None:
    source = tmp_path / "2026-07-03-team-meeting.txt"
    source.write_text("Ken:   Hello\r\n\r\nKushali:  Hi\n", encoding="utf-8")

    result = extract_source(source)

    assert result.source_format == "txt"
    assert result.normalized_text == "Ken: Hello\n\nKushali: Hi\n"
    assert result.effective_date.value == "2026-07-03"
    assert result.effective_date.confidence == "high"
    assert result.effective_date.source == "filename"


def test_extract_vtt_strips_headers_cues_and_timing(tmp_path: Path) -> None:
    source = tmp_path / "meeting.vtt"
    source.write_text(
        "WEBVTT\n\n1\n00:00:01.000 --> 00:00:02.000\nKen: Hello\n\n2\n00:00:03.000 --> 00:00:04.000\nKushali: Hi\n",
        encoding="utf-8",
    )

    result = extract_source(source)

    assert result.source_format == "vtt"
    assert result.normalized_text == "Ken: Hello\n\nKushali: Hi\n"


def test_extract_vtt_converts_voice_tags_to_speaker_lines(tmp_path: Path) -> None:
    source = tmp_path / "meeting.vtt"
    source.write_text(
        "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n<v Ken Graham>Hello there</v>\n",
        encoding="utf-8",
    )

    result = extract_source(source)

    assert result.normalized_text == "**Ken Graham** (00:01): Hello there\n"


def test_extract_vtt_strips_teams_cue_ids_and_joins_multiline_voice_tags(tmp_path: Path) -> None:
    source = tmp_path / "meeting.vtt"
    source.write_text(
        "WEBVTT\n\n953680fb-6edd-433a-8b2f-f229ee593292/59-0\n"
        "00:05:05.847 --> 00:05:08.647\n"
        "<v Ken Graham>Hang out with the kids on Father's Day,\n"
        "and that's awesome.</v>\n",
        encoding="utf-8",
    )

    result = extract_source(source)

    assert result.normalized_text == "**Ken Graham** (05:05): Hang out with the kids on Father's Day, and that's awesome.\n"


def test_extract_docx_reads_document_paragraphs(tmp_path: Path) -> None:
    source = tmp_path / "20260703-meeting.docx"
    document_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>First paragraph.</w:t></w:r></w:p>
    <w:p><w:r><w:t>Second paragraph.</w:t></w:r></w:p>
  </w:body>
</w:document>
"""
    with ZipFile(source, "w") as docx:
        docx.writestr("word/document.xml", document_xml)

    result = extract_source(source)

    assert result.source_format == "docx"
    assert result.normalized_text == "First paragraph.\nSecond paragraph.\n"
    assert result.effective_date.value == "2026-07-03"


def test_extract_docx_normalizes_teams_speaker_timestamps(tmp_path: Path) -> None:
    source = tmp_path / "20260703-meeting.docx"
    document_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>Chandra McCrary 0:05Is anybody else coming?</w:t></w:r></w:p>
    <w:p><w:r><w:t>John Wilson 12:31That works.</w:t></w:r></w:p>
  </w:body>
</w:document>
"""
    with ZipFile(source, "w") as docx:
        docx.writestr("word/document.xml", document_xml)

    result = extract_source(source)

    assert result.normalized_text == "**Chandra McCrary** (0:05): Is anybody else coming?\n**John Wilson** (12:31): That works.\n"


def test_extract_docx_attaches_paragraphs_after_split_teams_speaker_lines(tmp_path: Path) -> None:
    source = tmp_path / "20260703-meeting.docx"
    document_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>Chandra McCrary   0:05</w:t></w:r></w:p>
    <w:p><w:r><w:t>Is anybody else coming?</w:t></w:r></w:p>
    <w:p><w:r><w:t>John Wilson   0:07</w:t></w:r></w:p>
    <w:p><w:r><w:t>I don't think so.</w:t></w:r></w:p>
    <w:p><w:r><w:t>Another sentence.</w:t></w:r></w:p>
  </w:body>
</w:document>
"""
    with ZipFile(source, "w") as docx:
        docx.writestr("word/document.xml", document_xml)

    result = extract_source(source)

    assert result.normalized_text == (
        "**Chandra McCrary** (0:05): Is anybody else coming?\n"
        "**John Wilson** (0:07): I don't think so. Another sentence.\n"
    )


def test_extract_docx_uses_content_date_duration_and_removes_export_chrome(tmp_path: Path) -> None:
    source = tmp_path / "Spelman College - Data as Infrastructure.docx"
    document_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>Spelman College - Data as Infrastructure -20260701_143044-Meeting Transcript</w:t></w:r></w:p>
    <w:p><w:r><w:t>July 1, 2026, 6:30PM</w:t></w:r></w:p>
    <w:p><w:r><w:t>43m 0s</w:t></w:r></w:p>
    <w:p><w:r><w:t>started transcription</w:t></w:r></w:p>
    <w:p><w:r><w:t>John Wilson 5:58OK, thanks.</w:t></w:r></w:p>
    <w:p><w:r><w:t>Naser Hannoon stopped transcription</w:t></w:r></w:p>
  </w:body>
</w:document>
"""
    with ZipFile(source, "w") as docx:
        docx.writestr("word/document.xml", document_xml)

    result = extract_source(source)

    assert result.effective_date.value == "2026-07-01"
    assert result.effective_date.confidence == "high"
    assert result.effective_date.source == "content"
    assert result.duration == "PT43M"
    assert result.normalized_text == "**John Wilson** (5:58): OK, thanks.\n"


def test_extract_docx_preserves_soft_line_breaks(tmp_path: Path) -> None:
    source = tmp_path / "20260703-meeting.docx"
    document_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>standing up Snowflake from ground.</w:t><w:br/><w:t>from ground zero</w:t></w:r></w:p>
  </w:body>
</w:document>
"""
    with ZipFile(source, "w") as docx:
        docx.writestr("word/document.xml", document_xml)

    result = extract_source(source)

    assert result.normalized_text == "standing up Snowflake from ground.\nfrom ground zero\n"


def test_infer_effective_date_falls_back_to_file_mtime(tmp_path: Path) -> None:
    source = tmp_path / "meeting.txt"
    source.write_text("No date here", encoding="utf-8")
    timestamp = 1783036800
    os.utime(source, (timestamp, timestamp))

    effective_date = infer_effective_date(source)

    assert effective_date.value == "2026-07-03"
    assert effective_date.confidence == "low"
    assert effective_date.source == "file_mtime"


def test_infer_effective_date_ignores_invalid_filename_date(tmp_path: Path) -> None:
    source = tmp_path / "2026-99-99-meeting.txt"
    source.write_text("No valid date here", encoding="utf-8")
    timestamp = 1783036800
    os.utime(source, (timestamp, timestamp))

    effective_date = infer_effective_date(source)

    assert effective_date.value == "2026-07-03"
    assert effective_date.confidence == "low"
    assert effective_date.source == "file_mtime"


def test_extract_source_rejects_unsupported_format(tmp_path: Path) -> None:
    source = tmp_path / "meeting.pdf"
    source.write_text("not supported", encoding="utf-8")

    with pytest.raises(UnsupportedSourceFormatError):
        extract_source(source)
