"""Deterministic transcript cleanup helpers."""

from __future__ import annotations

import re


_WEBVTT_TIMING = re.compile(r"^\d{2}:\d{2}:\d{2}\.\d{3}\s+-->\s+\d{2}:\d{2}:\d{2}\.\d{3}")
_WEBVTT_CUE_ID = re.compile(r"^[0-9A-Za-z_-]+/\d+-\d+$")
_VOICE_TAG_START = re.compile(r"^<v(?:\.[^ >]+)*\s+([^>]+)>(.*)$")
_TEAMS_DOCX_SPEAKER = re.compile(r"^([A-Z][A-Za-z'.-]*(?:\s+[A-Z][A-Za-z'.-]*){1,5})\s+(\d{1,2}:\d{2})(.*)$")


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
    kept: list[str] = []
    pending_speaker: str | None = None
    pending_text: list[str] = []
    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw_line.strip()
        if pending_speaker is not None:
            if "</v>" in line:
                before_end = line.split("</v>", 1)[0].strip()
                if before_end:
                    pending_text.append(before_end)
                kept.append(f"{pending_speaker}: {' '.join(pending_text).strip()}")
                pending_speaker = None
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
        if _WEBVTT_TIMING.match(line):
            continue
        voice_match = _VOICE_TAG_START.match(line)
        if voice_match:
            speaker = voice_match.group(1).strip()
            content = voice_match.group(2).strip()
            if "</v>" in content:
                line = f"{speaker}: {content.split('</v>', 1)[0].strip()}"
            else:
                pending_speaker = speaker
                pending_text = [content] if content else []
                continue
        kept.append(line)
    return normalize_text("\n".join(kept))


def normalize_teams_docx_text(text: str) -> str:
    lines: list[str] = []
    for raw_line in normalize_text(text).splitlines():
        match = _TEAMS_DOCX_SPEAKER.match(raw_line)
        if match:
            speaker, timestamp, content = match.groups()
            lines.append(f"{speaker} ({timestamp}): {content.strip()}")
            continue
        lines.append(raw_line)
    return normalize_text("\n".join(lines))
