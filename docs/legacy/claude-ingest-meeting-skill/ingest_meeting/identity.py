import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def source_sha256(path: Path) -> str:
    """
    Compute SHA256 hash of file content (not name).

    Args:
        path: File path to hash.

    Returns:
        64-character hex string of SHA256 digest.
    """
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def meeting_id(sha256: str, meeting_date: str, mtype: str) -> str:
    """
    Create deterministic, slugged meeting_id from stable identity source.

    Args:
        sha256: 64-char source content hash.
        meeting_date: Date in YYYY-MM-DD format.
        mtype: Meeting type (e.g., "standup", "sync").

    Returns:
        Meeting ID in format: YYYY-MM-DD-{mtype}-{8-char-hash}.
    """
    short = hashlib.sha256(f"{sha256}".encode()).hexdigest()[:8]
    return f"{meeting_date}-{mtype}-{short}"


def event_id(event_without_id: dict) -> str:
    """
    Create deterministic 16-char event_id from event content (excluding event_id field itself).

    Args:
        event_without_id: Event dict (event_id field is ignored if present).

    Returns:
        16-character hex string of SHA256 digest of canonical JSON.
    """
    ev = {k: v for k, v in event_without_id.items() if k != "event_id"}
    canon = json.dumps(ev, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canon.encode()).hexdigest()[:16]


def now_iso() -> str:
    """
    Get current UTC time in ISO 8601 format with Z suffix.

    Returns:
        ISO 8601 timestamp string (e.g., "2026-05-16T17:00:00Z").
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
