import json
from pathlib import Path
from ingest_meeting import paths


def _path(project_root: Path | str) -> Path:
    """Get the ledger file path."""
    return paths.project_paths(project_root)["ledger"]


def _entries(project_root: Path | str) -> dict:
    """
    Load all ledger entries from file into memory.

    Returns a dict keyed by source_sha256 for O(1) membership checking.
    """
    f = _path(project_root)
    out = {}
    if not f.exists():
        return out
    for line in f.read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            out[r["source_sha256"]] = r
    return out


def already_ingested(project_root: Path | str, sha256: str) -> str | None:
    """
    Check if a source (by SHA256) has been ingested.

    Args:
        project_root: Root of the project directory.
        sha256: Source content SHA256 hash.

    Returns:
        meeting_id if previously ingested, None otherwise.
    """
    r = _entries(project_root).get(sha256)
    return r["meeting_id"] if r else None


def record(project_root: Path | str, sha256: str, meeting_id: str, ingest_run_id: str) -> None:
    """
    Record a source ingestion in the ledger (idempotent).

    Keyed by source_sha256 → meeting_id. If the same source is seen again,
    no duplicate entry is written (resumable).

    Args:
        project_root: Root of the project directory.
        sha256: Source content SHA256 hash.
        meeting_id: Deterministic meeting identifier.
        ingest_run_id: Run ID for provenance/audit (not part of deduplication key).
    """
    if already_ingested(project_root, sha256):
        return
    with open(_path(project_root), "a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "source_sha256": sha256,
                    "meeting_id": meeting_id,
                    "ingest_run_id": ingest_run_id,
                }
            )
            + "\n"
        )
