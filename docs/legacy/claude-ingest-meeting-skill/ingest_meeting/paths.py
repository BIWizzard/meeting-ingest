from pathlib import Path

_MEET = "_local/project-context/meetings"

def project_paths(project_root: Path | str) -> dict:
    if not project_root or not isinstance(project_root, (str, Path)):
        raise TypeError(
            f"project_root must be a non-empty Path or str, got {project_root!r}"
        )
    root = Path(project_root)
    base = root / _MEET
    p = {
        "base": base,
        "inbox": base / "_inbox",
        "processed": base / "_processed",
        "signals": base / "_signals",
        "quarantine": base / "_signals" / "_quarantine",
        "ledger": base / "_ledger.jsonl",
    }
    for key in ("inbox", "processed", "signals", "quarantine"):
        p[key].mkdir(parents=True, exist_ok=True)
    return p

def global_paths(home: Path | None = None) -> dict:
    base = (Path(home) if home else Path.home()) / ".claude"
    g = {
        "people": base / "people",
        "roster": base / "people" / "roster.md",
        "voice_corpus": base / "voice" / "_corpus",
    }
    g["people"].mkdir(parents=True, exist_ok=True)
    g["voice_corpus"].mkdir(parents=True, exist_ok=True)
    return g
