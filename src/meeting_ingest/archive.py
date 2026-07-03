"""Processed-source archive and inbox reconciliation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil

from meeting_ingest.errors import EXIT_ARCHIVE_RECONCILE, MeetingIngestError
from meeting_ingest.paths import ProjectPaths


@dataclass(frozen=True)
class ArchiveResult:
    processed_path: Path
    reconcile: dict[str, str]


@dataclass(frozen=True)
class QuarantineResult:
    path: Path
    reason: str


def archive_and_reconcile(source: Path, source_sha256: str, paths: ProjectPaths) -> ArchiveResult:
    processed_path = processed_path_for_source(source, source_sha256, paths)
    try:
        shutil.copy2(source, processed_path)
    except OSError as exc:
        raise MeetingIngestError(
            phase="archive",
            code="archive_write_failed",
            message=f"Could not archive processed source: {source}",
            exit_code=EXIT_ARCHIVE_RECONCILE,
            recoverable=True,
            details={"source": str(source), "processed_path": str(processed_path)},
        ) from exc

    reconcile = _reconcile_inbox_source(source, paths)
    return ArchiveResult(processed_path=processed_path, reconcile=reconcile)


def repair_duplicate_source(source: Path, source_sha256: str, paths: ProjectPaths) -> ArchiveResult:
    processed_path = processed_path_for_source(source, source_sha256, paths)
    archived = False
    if not processed_path.exists():
        try:
            shutil.copy2(source, processed_path)
            archived = True
        except OSError as exc:
            raise MeetingIngestError(
                phase="archive",
                code="archive_repair_failed",
                message=f"Could not repair processed source archive: {source}",
                exit_code=EXIT_ARCHIVE_RECONCILE,
                recoverable=True,
                details={"source": str(source), "processed_path": str(processed_path)},
            ) from exc
    reconcile = _reconcile_inbox_source(source, paths)
    return ArchiveResult(
        processed_path=processed_path,
        reconcile={**reconcile, "reason": "source_already_ingested", "archive_repaired": str(archived).lower()},
    )


def quarantine_source(source: Path, source_sha256: str, paths: ProjectPaths, *, reason: str) -> QuarantineResult:
    quarantine_path = _quarantine_path(source, source_sha256, paths)
    try:
        shutil.move(str(source), str(quarantine_path))
    except OSError as exc:
        raise MeetingIngestError(
            phase="quarantine",
            code="quarantine_failed",
            message=f"Could not quarantine source: {source}",
            exit_code=EXIT_ARCHIVE_RECONCILE,
            recoverable=True,
            details={"source": str(source), "quarantine_path": str(quarantine_path)},
        ) from exc
    return QuarantineResult(path=quarantine_path, reason=reason)


def processed_path_for_source(source: Path, source_sha256: str, paths: ProjectPaths) -> Path:
    safe_name = source.name.replace("/", "-")
    candidate = paths.processed / f"{source_sha256[:8]}-{safe_name}"
    if candidate.exists():
        return candidate
    counter = 2
    while candidate.exists():
        candidate = paths.processed / f"{source_sha256[:8]}-{counter}-{safe_name}"
        counter += 1
    return candidate


def _reconcile_inbox_source(source: Path, paths: ProjectPaths) -> dict[str, str]:
    try:
        source.relative_to(paths.inbox)
    except ValueError:
        return {"status": "skipped", "reason": "source_not_in_inbox"}

    if source.parent == paths.inbox_done or paths.inbox_done in source.parents:
        return {"status": "skipped", "reason": "source_already_in_done"}

    done_path = _done_path(source, paths)
    try:
        shutil.move(str(source), str(done_path))
    except OSError as exc:
        raise MeetingIngestError(
            phase="reconcile",
            code="inbox_reconcile_failed",
            message=f"Could not move source to inbox done: {source}",
            exit_code=EXIT_ARCHIVE_RECONCILE,
            recoverable=True,
            details={"source": str(source), "done_path": str(done_path)},
        ) from exc
    return {"status": "completed", "path": str(done_path.relative_to(paths.meetings_root))}


def _done_path(source: Path, paths: ProjectPaths) -> Path:
    candidate = paths.inbox_done / source.name
    counter = 2
    while candidate.exists():
        candidate = paths.inbox_done / f"{source.stem}-{counter}{source.suffix}"
        counter += 1
    return candidate


def _quarantine_path(source: Path, source_sha256: str, paths: ProjectPaths) -> Path:
    candidate = paths.quarantine / f"{source_sha256[:8]}-{source.name}"
    counter = 2
    while candidate.exists():
        candidate = paths.quarantine / f"{source_sha256[:8]}-{counter}-{source.name}"
        counter += 1
    return candidate
