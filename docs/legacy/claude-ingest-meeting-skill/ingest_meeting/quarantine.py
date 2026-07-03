import json
import time
from pathlib import Path
from ingest_meeting import paths


def park(project_root: Path | str, kind: str, name: str, reason: str, blob) -> Path:
    """
    Park a bad input or event in quarantine with a reason.

    Never drops data—always writes the blob with a human-readable reason.

    Args:
        project_root: Project root path (passed to paths.project_paths)
        kind: Type of quarantined item (e.g., "event", "meeting", "input")
        name: Name or identifier of the quarantined item
        reason: Human-readable reason for quarantine (e.g., "unknown schema_version 9.9")
        blob: The actual data blob (dict, list, str, etc.)

    Returns:
        Path to the written quarantine file
    """
    qdir = paths.project_paths(project_root)["quarantine"]
    fn = qdir / f"{int(time.time() * 1000)}-{kind}-{name}.json"
    fn.write_text(json.dumps(
        {"kind": kind, "name": name, "reason": reason, "blob": blob},
        indent=2, ensure_ascii=False))
    return fn
