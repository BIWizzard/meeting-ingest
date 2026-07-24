#!/usr/bin/env python3
"""Install receipt-verified workflow artifacts."""

from __future__ import annotations

from argparse import ArgumentParser
import json
from pathlib import Path

from meeting_ingest.runtime_release import RuntimeReleaseError, install_workflow_artifacts


def main() -> int:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--executable", required=True)
    parser.add_argument("--skill-destination", type=Path, required=True)
    parser.add_argument("--agent", type=Path)
    parser.add_argument("--agent-destination", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = install_workflow_artifacts(
            args.receipt,
            template_path=args.template,
            executable=args.executable,
            skill_destination=args.skill_destination,
            agent_path=args.agent,
            agent_destination=args.agent_destination,
        )
    except RuntimeReleaseError as exc:
        parser.exit(1, f"approved workflow install failed: {exc}\n")
    print(
        json.dumps(
            {
                "status": "success",
                "build_id": result.build_id,
                "skill_destination": str(result.skill_destination),
                "rendered_skill_sha256": result.rendered_skill_sha256,
                "agent_destination": (
                    str(result.agent_destination) if result.agent_destination is not None else None
                ),
                "agent_sha256": result.agent_sha256,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
