import subprocess
import sys
from pathlib import Path
from ingest_meeting import cli, paths

FX = Path(__file__).parent / "fixtures"

def test_cli_ingest_dry_run(tmp_path, capsys):
    paths.project_paths(tmp_path)
    (paths.project_paths(tmp_path)["inbox"] / "standup.txt").write_bytes(
        (FX / "standup.txt").read_bytes())
    rc = cli.main(["ingest", "--project-root", str(tmp_path),
                   "--home", str(tmp_path), "--dry-run"])
    assert rc == 0
    assert "DRY-RUN" in capsys.readouterr().out

def test_cli_unknown_command():
    assert cli.main(["frobnicate"]) == 2


def test_cli_reconcile_inbox(tmp_path, capsys):
    pp = paths.project_paths(tmp_path)
    (pp["inbox"] / "standup.txt").write_bytes((FX / "standup.txt").read_bytes())
    # real ingest: records ledger + copies to _processed, leaves original in _inbox
    assert cli.main(["ingest", "--project-root", str(tmp_path),
                     "--home", str(tmp_path)]) == 0
    capsys.readouterr()
    (pp["inbox"] / "notyet.txt").write_text("not ingested")

    # dry-run: reports, moves nothing
    assert cli.main(["reconcile-inbox", "--project-root", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "RECONCILE DRY-RUN" in out and "standup.txt" in out
    assert "[PENDING] notyet.txt" in out
    assert (pp["inbox"] / "standup.txt").exists()

    # apply: SHA-verified-ingested original moves to _done/, pending untouched
    assert cli.main(["reconcile-inbox", "--project-root", str(tmp_path),
                     "--apply"]) == 0
    out = capsys.readouterr().out
    assert "[RECONCILED] standup.txt -> _done/" in out
    assert not (pp["inbox"] / "standup.txt").exists()
    assert (pp["inbox"] / "_done" / "standup.txt").exists()
    assert (pp["inbox"] / "notyet.txt").exists()


def test_cli_module_has_main_guard():
    """`python -m ingest_meeting.cli` must invoke main() (no silent no-op).

    With no subcommand main() returns 2; without the __main__ guard the
    module would import-and-exit 0.
    """
    pkg_root = Path(cli.__file__).parents[1]
    r = subprocess.run([sys.executable, "-m", "ingest_meeting.cli"],
                        cwd=str(pkg_root), capture_output=True, text=True)
    assert r.returncode == 2
