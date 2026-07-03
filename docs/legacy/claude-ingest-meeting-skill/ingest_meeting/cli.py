import argparse
import shutil
import sys
import json
from pathlib import Path
from ingest_meeting import paths, pipeline, bootstrap, identity, ledger


def _stub_llm(text: str, mtype: str) -> dict:
    """
    Placeholder LLM extractor used only when the agent has not supplied extraction.

    At runtime SKILL.md performs extraction and calls the library directly;
    the CLI path is for deterministic dry-run/inspection.
    """
    return {
        "markdown": "# (extraction pending — run via SKILL.md)\n",
        "observations": [],
    }


def main(argv=None) -> int:
    """
    CLI entrypoint for ingest-meeting commands.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 for success, 2 for argument errors).
    """
    argv = sys.argv[1:] if argv is None else argv
    ap = argparse.ArgumentParser(prog="ingest-meeting")
    sub = ap.add_subparsers(dest="cmd")

    # ingest subcommand
    pi = sub.add_parser("ingest")
    pi.add_argument("--project-root", required=True)
    pi.add_argument("--home", default=None)
    pi.add_argument("--dry-run", action="store_true")

    # bootstrap subcommand
    pb = sub.add_parser("bootstrap")
    pb.add_argument("--project-root", required=True)
    pb.add_argument("--home", default=None)
    pb.add_argument("--apply", action="store_true")

    # reconcile-inbox subcommand: move SHA-verified-ingested originals out of
    # _inbox/ into _inbox/_done/ (dry-run by default; --apply to move).
    prc = sub.add_parser("reconcile-inbox")
    prc.add_argument("--project-root", required=True)
    prc.add_argument("--apply", action="store_true")

    try:
        ns = ap.parse_args(argv)
    except SystemExit:
        return 2

    if ns.cmd == "ingest":
        run = identity.now_iso().replace(":", "").replace("-", "")
        inbox = paths.project_paths(ns.project_root)["inbox"]
        files = sorted(p for p in inbox.iterdir() if p.is_file())
        for f in files:
            res = pipeline.ingest_transcript(
                f,
                ns.project_root,
                _stub_llm,
                dry_run=ns.dry_run,
                ingest_run_id=run,
                home=ns.home,
            )
            tag = "DRY-RUN" if ns.dry_run else "INGESTED"
            print(
                f"[{tag}] {f.name} -> {res.get('meeting_id')} "
                f"unresolved={len(res.get('unresolved', []))}"
            )
        return 0

    if ns.cmd == "bootstrap":
        m = bootstrap.plan_mapping(ns.project_root)
        if ns.apply:
            run = identity.now_iso().replace(":", "").replace("-", "")
            bootstrap.apply_mapping(ns.project_root, m, run, home=ns.home)
            print("[BOOTSTRAP] applied")
        else:
            print("[BOOTSTRAP DRY-RUN]\n" + json.dumps(m, indent=2))
        return 0

    if ns.cmd == "reconcile-inbox":
        inbox = paths.project_paths(ns.project_root)["inbox"]
        done = inbox / "_done"
        moved: list[tuple[str, str]] = []
        pending: list[str] = []
        for f in sorted(inbox.iterdir()):
            if f.is_dir() or f.name.startswith("."):
                continue
            mid = ledger.already_ingested(
                ns.project_root, identity.source_sha256(f))
            if mid:
                if ns.apply:
                    done.mkdir(exist_ok=True)
                    shutil.move(str(f), str(done / f.name))
                moved.append((f.name, mid))
            else:
                pending.append(f.name)
        tag = "RECONCILED" if ns.apply else "RECONCILE DRY-RUN"
        for n, m in moved:
            print(f"[{tag}] {n} -> _done/ (ledger {m})")
        for n in pending:
            print(f"[PENDING] {n} (not in ledger)")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
