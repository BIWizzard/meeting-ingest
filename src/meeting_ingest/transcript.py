"""Deterministic transcript cleanup helpers."""

from __future__ import annotations

import re


_WEBVTT_TIMING = re.compile(r"^\d{2}:\d{2}:\d{2}\.\d{3}\s+-->\s+\d{2}:\d{2}:\d{2}\.\d{3}")
_VOICE_TAG = re.compile(r"^<v\s+([^>]+)>(.*?)</v>$")


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
    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            kept.append("")
            continue
        if line == "WEBVTT" or line.startswith("NOTE "):
            continue
        if line.isdigit():
            continue
        if _WEBVTT_TIMING.match(line):
            continue
        voice_match = _VOICE_TAG.match(line)
        if voice_match:
            line = f"{voice_match.group(1).strip()}: {voice_match.group(2).strip()}"
        kept.append(line)
    return normalize_text("\n".join(kept))
