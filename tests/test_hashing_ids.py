from datetime import UTC, datetime
from pathlib import Path

from meeting_ingest.clock import FrozenClock
from meeting_ingest.hashing import sha256_file, short_hash
from meeting_ingest.ids import compact_effective_date, mint_ingest_run_id, mint_meeting_id


def test_sha256_file_is_content_based(tmp_path: Path) -> None:
    source = tmp_path / "meeting.txt"
    source.write_text("same content\n", encoding="utf-8")

    digest = sha256_file(source)

    assert digest == "f953bbd204bb867e48a6ff774cffa3dcffd02c6580e8f1d00c37dbbaa743d6c8"
    assert short_hash(digest) == "f953bbd2"


def test_mint_meeting_id_uses_effective_date_and_source_hash() -> None:
    meeting_id = mint_meeting_id(
        "2026-07-03",
        "f9d22124a99fdc5e4711f1fa44e5efcc2d0c5c4f4707eea7a4922d7298f2b49f",
    )

    assert meeting_id == "mtg-20260703-f9d22124"


def test_compact_effective_date_accepts_date_shapes() -> None:
    assert compact_effective_date("2026-07-03") == "20260703"
    assert compact_effective_date("20260703") == "20260703"


def test_mint_ingest_run_id_is_unique_per_attempt_shape() -> None:
    clock = FrozenClock(datetime(2026, 7, 3, 15, 30, tzinfo=UTC))

    run_id = mint_ingest_run_id("2026-07-03", clock=clock)

    assert run_id.startswith("ingest-20260703-20260703T153000Z-")
    assert run_id != "ingest-20260703-f9d22124"
