#!/usr/bin/env python3
"""Publish an approved runtime to the local private-alpha channel."""

from __future__ import annotations

from argparse import ArgumentParser
import json
from pathlib import Path

from meeting_ingest.runtime_release import RuntimeReleaseError, publish_approved_runtime


def main() -> int:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--wheel", type=Path)
    parser.add_argument("--application-data-root", type=Path)
    parser.add_argument("--channel", default="private-alpha")
    parser.add_argument("--published-at", required=True, help="UTC RFC 3339 publication timestamp")
    args = parser.parse_args()
    try:
        result = publish_approved_runtime(
            args.receipt,
            wheel_path=args.wheel,
            application_data_root=args.application_data_root,
            channel=args.channel,
            published_at=args.published_at,
        )
    except RuntimeReleaseError as exc:
        parser.exit(1, f"approved runtime publish failed: {exc}\n")
    print(
        json.dumps(
            {
                "status": "success",
                "build_id": result.build_id,
                "release_directory": str(result.release_directory),
                "wheel_path": str(result.wheel_path),
                "receipt_path": str(result.receipt_path),
                "channel_path": str(result.channel_path),
                "previous_build_ids": list(result.previous_build_ids),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
