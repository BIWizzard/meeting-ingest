"""Command-line interface for meeting-ingest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from meeting_ingest import pipeline
from meeting_ingest.errors import EXIT_USAGE_OR_CONFIG, MeetingIngestError
from meeting_ingest.run_summary import RunSummary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="meeting-ingest")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("--root", default=".", help="Project root to initialize.")
    init_parser.add_argument("--json", action="store_true", help="Emit a machine-readable run summary.")

    ingest_parser = subparsers.add_parser("ingest")
    ingest_parser.add_argument("source")
    ingest_parser.add_argument("--mode", default="summary-plus-verbatim")
    ingest_parser.add_argument("--provider", default="mock")
    ingest_parser.add_argument("--quality", default="balanced")
    ingest_parser.add_argument("--json", action="store_true", help="Emit a machine-readable run summary.")

    for command in ("doctor", "status", "reconcile"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("--root", default=".", help="Path used for project discovery.")
        command_parser.add_argument("--json", action="store_true", help="Emit a machine-readable run summary.")

    return parser


def run(args: argparse.Namespace) -> RunSummary:
    if args.command == "init":
        return pipeline.initialize(Path(args.root))
    if args.command == "ingest":
        return pipeline.ingest(
            Path(args.source),
            start=Path.cwd(),
            mode=args.mode,
            provider=args.provider,
            quality=args.quality,
        )
    if args.command == "doctor":
        return pipeline.doctor(Path(args.root))
    if args.command == "status":
        return pipeline.status(Path(args.root))
    if args.command == "reconcile":
        return pipeline.reconcile(Path(args.root))
    raise AssertionError(f"Unhandled command: {args.command}")


def emit(summary: RunSummary, *, as_json: bool) -> None:
    data = summary.to_dict()
    if as_json:
        print(json.dumps(data, indent=2, sort_keys=True))
        return

    if summary.status == "success":
        command = data.get("command", "command")
        print(f"{command} completed")
        if "meetings_root" in data:
            print(f"meetings_root: {data['meetings_root']}")
        if "project" in data:
            print(json.dumps(data["project"], indent=2, sort_keys=True))
        return

    if summary.status == "issues_found":
        print("doctor found issues", file=sys.stderr)
        return

    print(f"{summary.status}: exit {summary.exit_code}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        summary = run(args)
    except MeetingIngestError as exc:
        summary = RunSummary(
            status="failed",
            exit_code=exc.exit_code,
            warnings=[],
            errors=[exc.to_error_block()],
            details={"reason": exc.code},
        )
    except Exception as exc:
        summary = RunSummary(
            status="failed",
            exit_code=EXIT_USAGE_OR_CONFIG,
            warnings=[],
            errors=[
                {
                    "phase": "cli",
                    "code": "unexpected_error",
                    "message": str(exc),
                    "recoverable": False,
                }
            ],
            details={"reason": "unexpected_error"},
        )

    emit(summary, as_json=bool(getattr(args, "json", False)))
    return summary.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
