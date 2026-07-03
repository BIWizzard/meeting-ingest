"""Deterministic transcript cleanup helpers."""

from __future__ import annotations

from dataclasses import dataclass
import re


_WEBVTT_TIMING = re.compile(r"^(?P<start>\d{2}:\d{2}:\d{2})\.\d{3}\s+-->\s+\d{2}:\d{2}:\d{2}\.\d{3}")
_WEBVTT_CUE_ID = re.compile(r"^[0-9A-Za-z_-]+/\d+-\d+$")
_VOICE_TAG_START = re.compile(r"^<v(?:\.[^ >]+)*\s+([^>]+)>(.*)$")
_TEAMS_DOCX_SPEAKER = re.compile(
    r"^([A-Z][A-Za-z'.-]*(?:,\s*[A-Z][A-Za-z'.-]*)?(?:\s+\([^)]+\))?(?:\s+[A-Z][A-Za-z'.-]*){0,4})\s+"
    r"(\d{1,2}:\d{2}(?::\d{2})?)(?:([A-Za-z].*)|$)"
)
_TEAMS_DOCX_SPEAKER_NORMALIZED = re.compile(r"^(.+?) \((\d{1,2}:\d{2}(?::\d{2})?)\):\s*(.*)$")
_DOCX_EXPORT_STAMP = re.compile(r".*-20\d{6}_\d{6}-Meeting Transcript$")
_DOCX_DATE_LINE = re.compile(r"^[A-Z][a-z]+ \d{1,2}, 20\d{2}, \d{1,2}:\d{2}(?:AM|PM)$")
_DOCX_DURATION = re.compile(r"^\d+h? ?\d*m ?\d*s$")
_TRANSCRIPTION_EVENT = re.compile(r"^(?:started transcription|.+ stopped transcription)$", re.IGNORECASE)


@dataclass(frozen=True)
class TranscriptTurn:
    speaker: str
    timestamp: str | None
    text: str


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [" ".join(line.strip().split()) for line in text.split("\n")]
    collapsed: list[str] = []
    previous_blank = False
    for line in lines:
        if not line:
            if not previous_blank:
                collapsed.append("")
            previous_blank = True
            continue
        collapsed.append(line)
        previous_blank = False
    return "\n".join(collapsed).strip() + "\n"


def strip_vtt_markup(text: str) -> str:
    turns: list[TranscriptTurn] = []
    kept: list[str] = []
    pending_speaker: str | None = None
    pending_timestamp: str | None = None
    pending_text: list[str] = []
    current_timestamp: str | None = None
    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw_line.strip()
        if pending_speaker is not None:
            timing_match = _WEBVTT_TIMING.match(line)
            if timing_match:
                turns.append(TranscriptTurn(pending_speaker, pending_timestamp, " ".join(pending_text).strip()))
                pending_speaker = None
                pending_timestamp = None
                pending_text = []
                current_timestamp = _compact_timestamp(timing_match.group("start"))
                continue
            if "</v>" in line:
                before_end = line.split("</v>", 1)[0].strip()
                if before_end:
                    pending_text.append(before_end)
                turns.append(TranscriptTurn(pending_speaker, pending_timestamp, " ".join(pending_text).strip()))
                pending_speaker = None
                pending_timestamp = None
                pending_text = []
            elif line:
                pending_text.append(line)
            continue

        if not line:
            kept.append("")
            continue
        if line == "WEBVTT" or line.startswith("NOTE "):
            continue
        if line.isdigit():
            continue
        if _WEBVTT_CUE_ID.match(line):
            continue
        timing_match = _WEBVTT_TIMING.match(line)
        if timing_match:
            current_timestamp = _compact_timestamp(timing_match.group("start"))
            continue
        voice_match = _VOICE_TAG_START.match(line)
        if voice_match:
            speaker = voice_match.group(1).strip()
            content = voice_match.group(2).strip()
            if "</v>" in content:
                turns.append(TranscriptTurn(speaker, current_timestamp, content.split("</v>", 1)[0].strip()))
                current_timestamp = None
                continue
            else:
                pending_speaker = speaker
                pending_timestamp = current_timestamp
                pending_text = [content] if content else []
                current_timestamp = None
                continue
        kept.append(line)
    if pending_speaker is not None:
        turns.append(TranscriptTurn(pending_speaker, pending_timestamp, " ".join(pending_text).strip()))
    rendered_turns = [_render_turn(turn) for turn in _merge_turns(turns)]
    return normalize_text("\n".join([*kept, *rendered_turns]))


def normalize_teams_docx_text(text: str) -> str:
    turns: list[TranscriptTurn] = []
    passthrough: list[str] = []
    active_speaker: str | None = None
    active_timestamp: str | None = None
    active_text: list[str] = []
    for raw_line in normalize_text(text).splitlines():
        if _is_docx_export_chrome(raw_line):
            continue
        match = _TEAMS_DOCX_SPEAKER.match(raw_line)
        if match:
            _append_active_docx_turn(turns, active_speaker, active_timestamp, active_text)
            speaker, timestamp, content = match.groups()
            active_speaker = speaker
            active_timestamp = timestamp
            content = content or ""
            active_text = [content.strip()] if content.strip() else []
            continue
        normalized_match = _TEAMS_DOCX_SPEAKER_NORMALIZED.match(raw_line)
        if normalized_match:
            _append_active_docx_turn(turns, active_speaker, active_timestamp, active_text)
            speaker, timestamp, content = normalized_match.groups()
            active_speaker = speaker
            active_timestamp = timestamp
            active_text = [content.strip()] if content.strip() else []
            continue
        if raw_line:
            if active_speaker is not None:
                active_text.append(raw_line)
            else:
                passthrough.append(raw_line)
    _append_active_docx_turn(turns, active_speaker, active_timestamp, active_text)
    rendered_turns = [_render_turn(turn) for turn in _merge_turns(turns)]
    return normalize_text("\n".join([*passthrough, *rendered_turns]))


def _append_active_docx_turn(
    turns: list[TranscriptTurn],
    speaker: str | None,
    timestamp: str | None,
    text_parts: list[str],
) -> None:
    if speaker is None:
        return
    turns.append(TranscriptTurn(speaker=speaker, timestamp=timestamp, text=" ".join(text_parts).strip()))


def _render_turn(turn: TranscriptTurn) -> str:
    if turn.timestamp:
        return f"**{turn.speaker}** ({turn.timestamp}): {turn.text}"
    return f"**{turn.speaker}**: {turn.text}"


def _merge_turns(turns: list[TranscriptTurn]) -> list[TranscriptTurn]:
    merged: list[TranscriptTurn] = []
    for turn in turns:
        if not turn.text:
            continue
        if merged and merged[-1].speaker == turn.speaker:
            previous = merged[-1]
            merged[-1] = TranscriptTurn(previous.speaker, previous.timestamp, f"{previous.text} {turn.text}")
            continue
        merged.append(turn)
    return merged


def _compact_timestamp(timestamp: str) -> str:
    if timestamp.startswith("00:"):
        return timestamp[3:]
    return timestamp


def _is_docx_export_chrome(line: str) -> bool:
    return bool(
        _DOCX_EXPORT_STAMP.match(line)
        or _DOCX_DATE_LINE.match(line)
        or _DOCX_DURATION.match(line)
        or _TRANSCRIPTION_EVENT.match(line)
    )
