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

    assert result.normalized_text == "Ken Graham: Hello there\n"


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
