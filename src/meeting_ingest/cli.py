"""Command-line interface for meeting-ingest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from meeting_ingest import pipeline, playbook
from meeting_ingest.playbook_review import mutate_review
from meeting_ingest.errors import EXIT_GENERAL_FAILURE, MeetingIngestError
from meeting_ingest.run_summary import RunSummary
from meeting_ingest.runtime import inspect_runtime_summary
from meeting_ingest.session_inbox import process_session_inbox


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="meeting-ingest")
    subparsers = parser.add_subparsers(dest="command", required=True)

    runtime_parser = subparsers.add_parser("runtime")
    runtime_subparsers = runtime_parser.add_subparsers(dest="runtime_command", required=True)
    runtime_inspect_parser = runtime_subparsers.add_parser("inspect")
    runtime_inspect_parser.add_argument("--root", default=".", help="Consumer project root to inspect.")
    runtime_inspect_parser.add_argument("--json", action="store_true", help="Emit machine-readable runtime evidence.")

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("--root", default=".", help="Project root to initialize.")
    init_parser.add_argument("--json", action="store_true", help="Emit a machine-readable run summary.")

    ingest_parser = subparsers.add_parser("ingest")
    ingest_parser.add_argument("source")
    ingest_parser.add_argument("--mode")
    ingest_parser.add_argument("--provider")
    ingest_parser.add_argument("--quality")
    ingest_parser.add_argument("--provider-response")
    ingest_parser.add_argument(
        "--meeting-date",
        dest="meeting_date",
        help="Known meeting occurrence date (YYYY-MM-DD); overrides inferred dates.",
    )
    ingest_parser.add_argument("--json", action="store_true", help="Emit a machine-readable run summary.")

    provider_request_parser = subparsers.add_parser("provider-request")
    provider_request_parser.add_argument("source")
    provider_request_parser.add_argument("--mode")
    provider_request_parser.add_argument("--provider", default="session")
    provider_request_parser.add_argument("--quality")
    provider_request_parser.add_argument(
        "--meeting-date",
        dest="meeting_date",
        help="Known meeting occurrence date (YYYY-MM-DD); overrides inferred dates.",
    )
    provider_request_parser.add_argument("--json", action="store_true", help="Emit a machine-readable run summary.")

    validate_response_parser = subparsers.add_parser("validate-response")
    validate_response_parser.add_argument("response", help="Provider response JSON path to validate.")
    validate_response_parser.add_argument("--source", required=True, help="Original source file bound to the request.")
    validate_response_parser.add_argument("--root", default=".", help="Path used for project discovery.")
    validate_response_parser.add_argument("--json", action="store_true", help="Emit a machine-readable run summary.")

    ingest_inbox_parser = subparsers.add_parser("ingest-inbox")
    ingest_inbox_parser.add_argument("--root", default=".", help="Path used for project discovery.")
    ingest_inbox_parser.add_argument("--mode")
    ingest_inbox_parser.add_argument("--provider")
    ingest_inbox_parser.add_argument("--quality")
    ingest_inbox_parser.add_argument("--json", action="store_true", help="Emit a machine-readable run summary.")

    session_inbox_parser = subparsers.add_parser("session-inbox")
    session_inbox_parser.add_argument("--root", default=".", help="Path used for project discovery.")
    session_inbox_parser.add_argument("--mode")
    session_inbox_parser.add_argument("--quality")
    session_inbox_parser.add_argument("--json", action="store_true", help="Emit a machine-readable run summary.")

    repair_date_parser = subparsers.add_parser("repair-date")
    repair_date_parser.add_argument("selector", help="meeting_id or full source_sha256 of the ingest to repair.")
    repair_date_parser.add_argument("--date", required=True, help="Correct meeting occurrence date (YYYY-MM-DD).")
    repair_date_parser.add_argument("--root", default=".", help="Path used for project discovery.")
    repair_date_parser.add_argument("--json", action="store_true", help="Emit a machine-readable run summary.")

    playbook_parser = subparsers.add_parser("playbook")
    playbook_subparsers = playbook_parser.add_subparsers(dest="playbook_command", required=True)
    playbook_update_parser = playbook_subparsers.add_parser("update")
    playbook_update_parser.add_argument("--root", default=".", help="Path used for project discovery.")
    playbook_update_parser.add_argument("--json", action="store_true", help="Emit a machine-readable run summary.")
    reject_parser = playbook_subparsers.add_parser("reject")
    reject_parser.add_argument("entry_id")
    reject_parser.add_argument("--reason", required=True)
    _add_playbook_mutation_options(reject_parser)
    restore_parser = playbook_subparsers.add_parser("restore")
    restore_parser.add_argument("entry_id")
    restore_parser.add_argument("--note", required=True)
    _add_playbook_mutation_options(restore_parser)
    resolve_parser = playbook_subparsers.add_parser("resolve")
    resolve_parser.add_argument("entry_id")
    resolve_parser.add_argument(
        "--state",
        required=True,
        choices=("explicitly_outstanding", "resolved", "withdrawn", "superseded"),
    )
    resolve_parser.add_argument("--note", required=True)
    _add_playbook_mutation_options(resolve_parser)
    suppress_parser = playbook_subparsers.add_parser("suppress-signal")
    suppress_parser.add_argument("source_id")
    suppress_parser.add_argument("signal_id")
    suppress_parser.add_argument("--reason", required=True)
    _add_playbook_mutation_options(suppress_parser)
    unsuppress_parser = playbook_subparsers.add_parser("unsuppress-signal")
    unsuppress_parser.add_argument("source_id")
    unsuppress_parser.add_argument("signal_id")
    unsuppress_parser.add_argument("--note", required=True)
    _add_playbook_mutation_options(unsuppress_parser)
    for command in ("show", "brief"):
        read_parser = playbook_subparsers.add_parser(command)
        read_parser.add_argument("selector")
        read_parser.add_argument("--root", default=".", help="Path used for project discovery.")
        read_parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    repair_index_parser = playbook_subparsers.add_parser("repair-index")
    repair_index_parser.add_argument("--root", default=".", help="Path used for project discovery.")
    repair_index_parser.add_argument("--json", action="store_true", help="Emit a machine-readable run summary.")
    cleanup_parser = playbook_subparsers.add_parser("cleanup-uncommitted")
    cleanup_parser.add_argument("--root", default=".", help="Path used for project discovery.")
    cleanup_parser.add_argument("--dry-run", action="store_true", help="Report targets without deleting them.")
    cleanup_parser.add_argument("--json", action="store_true", help="Emit a machine-readable run summary.")

    for command in ("doctor", "status", "reconcile"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("--root", default=".", help="Path used for project discovery.")
        command_parser.add_argument("--json", action="store_true", help="Emit a machine-readable run summary.")

    return parser


def _add_playbook_mutation_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--root", default=".", help="Path used for project discovery.")
    parser.add_argument("--actor", default="user", help="Human or authorized agent recording the review event.")
    parser.add_argument("--json", action="store_true", help="Emit a machine-readable run summary.")


def run(args: argparse.Namespace) -> RunSummary:
    if args.command == "runtime" and args.runtime_command == "inspect":
        return inspect_runtime_summary(Path(args.root))
    if args.command == "init":
        return pipeline.initialize(Path(args.root))
    if args.command == "ingest":
        return pipeline.ingest(
            Path(args.source),
            start=Path.cwd(),
            mode=args.mode,
            provider=args.provider,
            quality=args.quality,
            provider_response=Path(args.provider_response) if args.provider_response else None,
            meeting_date=args.meeting_date,
        )
    if args.command == "provider-request":
        return pipeline.provider_request(
            Path(args.source),
            start=Path.cwd(),
            mode=args.mode,
            provider=args.provider,
            quality=args.quality,
            meeting_date=args.meeting_date,
        )
    if args.command == "validate-response":
        return pipeline.validate_response(
            Path(args.response),
            source=Path(args.source),
            start=Path(args.root),
        )
    if args.command == "ingest-inbox":
        return pipeline.ingest_inbox(
            Path(args.root),
            mode=args.mode,
            provider=args.provider,
            quality=args.quality,
        )
    if args.command == "session-inbox":
        return process_session_inbox(
            Path(args.root),
            mode=args.mode,
            quality=args.quality,
        )
    if args.command == "doctor":
        return pipeline.doctor(Path(args.root))
    if args.command == "status":
        return pipeline.status(Path(args.root))
    if args.command == "reconcile":
        return pipeline.reconcile(Path(args.root))
    if args.command == "repair-date":
        return pipeline.repair_date(args.selector, date=args.date, start=Path(args.root))
    if args.command == "playbook" and args.playbook_command == "update":
        return playbook.update(Path(args.root))
    if args.command == "playbook" and args.playbook_command == "show":
        return playbook.show(Path(args.root), args.selector, output_format=args.format)
    if args.command == "playbook" and args.playbook_command == "brief":
        return playbook.brief(Path(args.root), args.selector, output_format=args.format)
    if args.command == "playbook" and args.playbook_command == "repair-index":
        return playbook.repair_index(Path(args.root))
    if args.command == "playbook" and args.playbook_command == "cleanup-uncommitted":
        return playbook.cleanup_uncommitted(Path(args.root), dry_run=args.dry_run)
    if args.command == "playbook" and args.playbook_command in {
        "reject",
        "restore",
        "resolve",
        "suppress-signal",
        "unsuppress-signal",
    }:
        action = {
            "reject": "reject_entry",
            "restore": "restore_entry",
            "resolve": "resolve_tracked_item",
            "suppress-signal": "suppress_signal",
            "unsuppress-signal": "unsuppress_signal",
        }[args.playbook_command]
        target = (
            {"source_id": args.source_id, "signal_id": args.signal_id}
            if args.playbook_command in {"suppress-signal", "unsuppress-signal"}
            else {"entry_id": args.entry_id}
        )
        if args.playbook_command == "resolve":
            target["resolution_state"] = args.state
        return mutate_review(
            Path(args.root),
            action=action,
            target=target,
            reason=getattr(args, "reason", None),
            note=getattr(args, "note", None),
            actor=args.actor,
        )
    raise AssertionError(f"Unhandled command: {args.command}")


def emit(summary: RunSummary, *, as_json: bool) -> None:
    data = summary.to_dict()
    if as_json:
        print(json.dumps(data, indent=2, sort_keys=True))
        return

    if summary.status in {"success", "no_op"}:
        command = data.get("command", "command")
        if command == "runtime_inspect":
            print(f"Runtime: {data['runtime_mode']}")
            print(f"Build: {data['build']['build_id']}")
            print(f"Install: {data['install']['mode']}")
            print(f"Executable: {data['executable']['invoked']}")
            print(f"Package integrity: {data['distribution']['record_integrity']}")
            if data["findings"]:
                print("Findings:")
                for finding in data["findings"]:
                    print(f"- {finding['code']}: {finding['message']}")
            return
        if command in {"playbook_show", "playbook_brief"}:
            content = data["content"]
            print(content if isinstance(content, str) else json.dumps(content, indent=2, sort_keys=True))
            return
        print(f"{command} {summary.status}")
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
            exit_code=EXIT_GENERAL_FAILURE,
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
