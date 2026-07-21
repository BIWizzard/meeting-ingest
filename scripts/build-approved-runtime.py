#!/usr/bin/env python3
"""Build and verify an approved Meeting Ingest wheel and receipt."""

from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path

import json

from meeting_ingest.runtime_build import RuntimeBuildError, build_approved_runtime


def main() -> int:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--commit", required=True, help="Exact 40-character reviewed commit hash")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--approved-by", required=True)
    parser.add_argument("--approved-at", required=True, help="UTC RFC 3339 approval timestamp")
    parser.add_argument(
        "--source-commit-reviewed",
        action="store_true",
        help="Confirm that the exact source commit received owner-approved review",
    )
    args = parser.parse_args()
    try:
        result = build_approved_runtime(
            args.repo_root,
            args.commit,
            args.output_dir,
            approved_by=args.approved_by,
            approved_at=args.approved_at,
            source_commit_reviewed=args.source_commit_reviewed,
        )
    except RuntimeBuildError as exc:
        parser.exit(1, f"approved runtime build failed: {exc}\n")
    print(
        json.dumps(
            {
                "status": "success",
                "build": result.identity.as_dict(),
                "wheel_path": str(result.wheel_path),
                "wheel_sha256": result.wheel_sha256,
                "receipt_path": str(result.receipt_path),
                "receipt_sha256": result.receipt_sha256,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
