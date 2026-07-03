"""Reusable pipeline entry points.

Milestone 1 owns initialization and clear stubs. Later milestones fill in the
actual ingest, status, doctor, and reconcile behavior behind this API.
"""

from __future__ import annotations

from pathlib import Path

from meeting_ingest.errors import PipelineNotImplementedError
from meeting_ingest.paths import init_project
from meeting_ingest.run_summary import RunSummary


def initialize(project_root: Path) -> RunSummary:
    paths = init_project(project_root)
    return RunSummary(
        status="success",
        exit_code=0,
        details={
            "command": "init",
            "config_path": str(paths.config_path),
            "meetings_root": str(paths.meetings_root),
        },
    )


def ingest(source: Path) -> RunSummary:
    raise PipelineNotImplementedError("ingest")


def doctor(start: Path) -> RunSummary:
    raise PipelineNotImplementedError("doctor")


def status(start: Path) -> RunSummary:
    raise PipelineNotImplementedError("status")


def reconcile(start: Path) -> RunSummary:
    raise PipelineNotImplementedError("reconcile")
