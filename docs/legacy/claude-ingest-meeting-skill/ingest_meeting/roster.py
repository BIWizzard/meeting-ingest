"""
Colleague and client roster: normalize, alias-match, resolve, classify.

Resolution statuses
-------------------
matched    — canonical person_id found via exact or alias match
tentative  — fuzzy candidate exists but confidence below threshold (reserved, P2)
unknown    — no match found
conflicted — two or more entries match the same raw name (reserved, P2)
"""

import json
import re
from pathlib import Path
from typing import Optional

from ingest_meeting import paths


def normalize(name: str) -> str:
    """
    Return a canonical lowercase token for *name*, independent of:
      - leading/trailing whitespace
      - comma-separated "Last, First" vs "First Last" ordering (2-word names only)
      - internal runs of whitespace

    For exactly 2-token names that were written in "Last, First" form (detected
    by a comma in the raw input), the tokens are reversed so that
    "Olaleye, Mark" yields the same result as "Mark Olaleye".
    Names without a comma keep their original token order.

    Examples
    --------
    >>> normalize("Olaleye, Mark")
    'mark olaleye'
    >>> normalize("Mark Olaleye")
    'mark olaleye'
    >>> normalize("  JOHN   Francois ")
    'john francois'
    """
    has_comma = "," in name
    # Strip, lowercase, remove commas, collapse whitespace
    s = name.strip().lower().replace(",", " ")
    s = re.sub(r"\s+", " ", s).strip()
    parts = s.split(" ")
    # For "Last, First" form with exactly 2 tokens, reverse to get "first last"
    if has_comma and len(parts) == 2:
        parts = parts[::-1]
    return " ".join(parts)


class Roster:
    """
    In-memory roster backed by ``<home>/.claude/people/roster.json``.

    Typical lifecycle
    -----------------
    r = Roster.load(project_root, home=tmp_path)
    pid, status = r.resolve("Mark Olaleye")   # -> (None, "unknown")
    r.classify("Mark Olaleye", person_id="mark-o", tier="client")
    r.save()
    """

    def __init__(
        self,
        project_root: Path,
        home: Optional[Path],
        data: dict,
    ) -> None:
        self.project_root = project_root
        self.home = home
        self.data = data  # {"people": [...]}

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, project_root: Path | str, home: Path | str | None = None) -> "Roster":
        """
        Load the roster from ``<home>/.claude/people/roster.json``.
        If the file does not exist, start with an empty roster.
        """
        g = paths.global_paths(home)
        f: Path = g["people"] / "roster.json"
        data: dict = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {"people": []}
        return cls(Path(project_root), Path(home) if home else None, data)

    # ------------------------------------------------------------------
    # Lookup helpers
    # ------------------------------------------------------------------

    def _find(self, raw: str) -> Optional[dict]:
        """Return the first person entry that matches *raw* by name or alias."""
        key = normalize(raw)
        for person in self.data["people"]:
            if key == normalize(person["display_name"]):
                return person
            if any(key == normalize(alias) for alias in person.get("aliases", [])):
                return person
        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve(self, raw: str) -> tuple[Optional[str], str]:
        """
        Resolve *raw* to a ``(person_id, status)`` pair.

        Status values
        -------------
        "matched"  — canonical entry found
        "unknown"  — no entry found
        """
        person = self._find(raw)
        if person:
            return person["person_id"], "matched"
        return None, "unknown"

    def tier_of(self, person_id: str) -> Optional[str]:
        """Return the tier ("colleague" | "client" | …) for *person_id*, or None."""
        for person in self.data["people"]:
            if person["person_id"] == person_id:
                return person["tier"]
        return None

    def classify(
        self,
        raw: str,
        person_id: str,
        tier: str,
        aliases: Optional[list[str]] = None,
    ) -> None:
        """
        Add or update a person entry.

        Parameters
        ----------
        raw:        Canonical display name used for normalization.
        person_id:  Stable slug identifier (e.g. "jf", "mark-o").
        tier:       "colleague" | "client" | "vendor" | …
        aliases:    Additional names / abbreviations that resolve to this person.
        """
        # Overwrite if person_id already present to keep classify idempotent
        self.data["people"] = [
            p for p in self.data["people"] if p["person_id"] != person_id
        ]
        self.data["people"].append({
            "person_id": person_id,
            "display_name": raw,
            "aliases": aliases or [],
            "tier": tier,
        })

    def save(self) -> None:
        """Persist the roster to ``<home>/.claude/people/roster.json``."""
        g = paths.global_paths(self.home)
        roster_path: Path = g["people"] / "roster.json"
        roster_path.write_text(
            json.dumps(self.data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
