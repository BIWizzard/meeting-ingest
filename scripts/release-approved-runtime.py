#!/usr/bin/env python3
"""Build, publish, install, and pin one approved Meeting Ingest runtime."""

from __future__ import annotations

from argparse import ArgumentParser
import json
from pathlib import Path

from meeting_ingest.clock import SystemClock, format_iso_timestamp
from meeting_ingest.runtime_build import RuntimeBuildError, build_approved_runtime
from meeting_ingest.runtime_release import (
    CLAUDE_AGENT_PATH,
    CLAUDE_SKILL_PATH,
    RuntimeReleaseError,
    install_approved_wheel,
    install_workflow_artifacts,
    packaged_workflow_templates,
    publish_approved_runtime,
    update_consumer_roots,
)


CONSUMER_NEXT_STEP = (
    "The wheel install is machine-global: run `meeting-ingest update --root <consumer-root>` "
    "in every consumer root on this machine that this run did not name."
)


def main(argv: list[str] | None = None) -> int:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--commit", required=True, help="Exact 40-character reviewed commit hash")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--approved-by", required=True)
    parser.add_argument("--approved-at", help="UTC RFC 3339 approval timestamp; defaults to now")
    parser.add_argument("--published-at", help="UTC RFC 3339 publication timestamp; defaults to now")
    parser.add_argument(
        "--source-commit-reviewed",
        action="store_true",
        help="Confirm that the exact source commit received owner-approved review",
    )
    parser.add_argument("--application-data-root", type=Path)
    parser.add_argument("--channel", default="private-alpha")
    parser.add_argument(
        "--consumer-root",
        type=Path,
        action="append",
        default=[],
        dest="consumer_roots",
        help="Consumer root to update explicitly; repeatable.",
    )
    args = parser.parse_args(argv)
    now = format_iso_timestamp(SystemClock().now_utc())
    try:
        built = build_approved_runtime(
            args.repo_root,
            args.commit,
            args.output_dir,
            approved_by=args.approved_by,
            approved_at=args.approved_at or now,
            source_commit_reviewed=args.source_commit_reviewed,
        )
    except RuntimeBuildError as exc:
        parser.exit(1, f"approved runtime build failed: {exc}\n")
    try:
        published = publish_approved_runtime(
            built.receipt_path,
            wheel_path=built.wheel_path,
            application_data_root=args.application_data_root,
            channel=args.channel,
            published_at=args.published_at or now,
            expected_receipt_sha256=built.receipt_sha256,
            expected_wheel_sha256=built.wheel_sha256,
        )
        installed = install_approved_wheel(
            published.receipt_path,
            application_data_root=args.application_data_root,
            expected_receipt_sha256=built.receipt_sha256,
            expected_wheel_sha256=built.wheel_sha256,
        )
        templates = packaged_workflow_templates()
        workflow = install_workflow_artifacts(
            published.receipt_path,
            template_path=templates.skill_template,
            executable=installed.executable,
            skill_destination=Path.home() / CLAUDE_SKILL_PATH,
            agent_path=templates.claude_agent,
            agent_destination=Path.home() / CLAUDE_AGENT_PATH,
        )
    except RuntimeReleaseError as exc:
        parser.exit(1, f"approved runtime release failed: {exc}\n")
    consumers = update_consumer_roots(args.consumer_roots, executable=installed.executable)
    failed = [result["root"] for result in consumers if result["status"] == "failed"]
    print(
        json.dumps(
            {
                "status": "failed" if failed else "success",
                "build": built.identity.as_dict(),
                "wheel_sha256": built.wheel_sha256,
                "receipt_sha256": built.receipt_sha256,
                "publish": {
                    "build_id": published.build_id,
                    "release_directory": str(published.release_directory),
                    "wheel_path": str(published.wheel_path),
                    "receipt_path": str(published.receipt_path),
                    "channel_path": str(published.channel_path),
                    "previous_build_ids": list(published.previous_build_ids),
                },
                "install": {
                    "build_id": installed.build_id,
                    "executable": str(installed.executable),
                    "command": list(installed.command),
                },
                "workflow": {
                    "skill_destination": str(workflow.skill_destination),
                    "rendered_skill_sha256": workflow.rendered_skill_sha256,
                    "agent_destination": (
                        str(workflow.agent_destination)
                        if workflow.agent_destination is not None
                        else None
                    ),
                    "agent_sha256": workflow.agent_sha256,
                },
                "consumers": consumers,
                "next_step": CONSUMER_NEXT_STEP,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
