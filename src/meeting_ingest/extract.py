"""Source extraction for transcript-like files."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import re
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from meeting_ingest.errors import SourceExtractionError, UnsupportedSourceFormatError
from meeting_ingest.transcript import normalize_teams_docx_text, normalize_text, strip_vtt_markup


@dataclass(frozen=True)
class EffectiveDate:
    value: str
    confidence: str
    source: str


@dataclass(frozen=True)
class SourceExtraction:
    path: Path
    source_format: str
    raw_text: str
    normalized_text: str
    effective_date: EffectiveDate
    duration: str | None = None


_DATE_PATTERNS = (
    re.compile(r"(?P<year>20\d{2})[-_ .](?P<month>\d{2})[-_ .](?P<day>\d{2})"),
    re.compile(r"(?P<year>20\d{2})(?P<month>\d{2})(?P<day>\d{2})"),
)
_EXPORT_STAMP_DATE = re.compile(r"(?P<year>20\d{2})(?P<month>\d{2})(?P<day>\d{2})_\d{6}")
_HUMAN_DATE = re.compile(r"^(?P<month>[A-Z][a-z]+) (?P<day>\d{1,2}), (?P<year>20\d{2}), \d{1,2}:\d{2}(?:AM|PM)$", re.MULTILINE)
_DURATION = re.compile(r"^(?:(?P<hours>\d+)h\s*)?(?:(?P<minutes>\d+)m\s*)?(?:(?P<seconds>\d+)s)$", re.MULTILINE)


def infer_effective_date(path: Path, content: str = "") -> EffectiveDate:
    content_date = _date_from_content(content)
    if content_date is not None:
        return EffectiveDate(value=content_date, confidence="high", source="content")

    for pattern in _DATE_PATTERNS:
        match = pattern.search(path.name)
        if match:
            date_value = _valid_date(match.group("year"), match.group("month"), match.group("day"))
            if date_value is not None:
                return EffectiveDate(value=date_value, confidence="high", source="filename")

    modified = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    return EffectiveDate(value=modified.strftime("%Y-%m-%d"), confidence="low", source="file_mtime")


def extract_source(path: Path) -> SourceExtraction:
    suffix = path.suffix.lower()
    if suffix == ".txt":
        raw_text = _read_text(path)
        normalized = normalize_text(raw_text)
        source_format = "txt"
    elif suffix == ".vtt":
        raw_text = _read_text(path)
        normalized = strip_vtt_markup(raw_text)
        source_format = "vtt"
    elif suffix == ".docx":
        raw_text = _read_docx(path)
        normalized = normalize_teams_docx_text(raw_text)
        source_format = "docx"
    else:
        raise UnsupportedSourceFormatError(str(path))

    return SourceExtraction(
        path=path,
        source_format=source_format,
        raw_text=raw_text,
        normalized_text=normalized,
        effective_date=infer_effective_date(path, raw_text),
        duration=_duration_from_content(raw_text),
    )


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SourceExtractionError(str(path), f"Could not decode source as UTF-8: {path}") from exc
    except OSError as exc:
        raise SourceExtractionError(str(path), f"Could not read source: {path}") from exc


def _read_docx(path: Path) -> str:
    try:
        with ZipFile(path) as docx:
            document_xml = docx.read("word/document.xml")
    except (BadZipFile, KeyError, OSError) as exc:
        raise SourceExtractionError(str(path), f"Could not extract DOCX text: {path}") from exc

    try:
        root = ElementTree.fromstring(document_xml)
    except ElementTree.ParseError as exc:
        raise SourceExtractionError(str(path), f"DOCX document XML is invalid: {path}") from exc

    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    paragraphs: list[str] = []
    for paragraph in root.iter(f"{namespace}p"):
        text_parts: list[str] = []
        for node in paragraph.iter():
            if node.tag == f"{namespace}t":
                text_parts.append(node.text or "")
            elif node.tag == f"{namespace}br":
                text_parts.append("\n")
        paragraph_text = "".join(text_parts).strip()
        if paragraph_text:
            paragraphs.append(paragraph_text)
    return "\n".join(paragraphs)


def _date_from_content(content: str) -> str | None:
    export_match = _EXPORT_STAMP_DATE.search(content)
    if export_match:
        return _valid_date(export_match.group("year"), export_match.group("month"), export_match.group("day"))

    human_match = _HUMAN_DATE.search(content)
    if human_match:
        try:
            parsed = datetime.strptime(
                f"{human_match.group('month')} {human_match.group('day')} {human_match.group('year')}",
                "%B %d %Y",
            )
        except ValueError:
            return None
        return parsed.strftime("%Y-%m-%d")
    return None


def _duration_from_content(content: str) -> str | None:
    match = _DURATION.search(content)
    if not match:
        return None
    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes") or 0)
    seconds = int(match.group("seconds") or 0)
    parts = ["P", "T"]
    if hours:
        parts.append(f"{hours}H")
    if minutes:
        parts.append(f"{minutes}M")
    if seconds or (not hours and not minutes):
        parts.append(f"{seconds}S")
    return "".join(parts)


def _valid_date(year: str, month: str, day: str) -> str | None:
    value = f"{year}-{month}-{day}"
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None
    return value
