from ingest_meeting import roster


def test_normalize_order_and_punct():
    n = roster.normalize
    assert n("Olaleye, Mark") == n("Mark Olaleye") == "mark olaleye"
    assert n("  JOHN   Francois ") == "john francois"


def test_resolve_unknown_then_classify_persists(tmp_path):
    r = roster.Roster.load(tmp_path, home=tmp_path)
    pid, status = r.resolve("Jim Haley")
    assert status == "unknown" and pid is None
    r.classify("Jim Haley", person_id="jim-haley", tier="colleague")
    r.save()
    r2 = roster.Roster.load(tmp_path, home=tmp_path)
    pid2, status2 = r2.resolve("Jim Haley")
    assert pid2 == "jim-haley" and status2 == "matched"


def test_alias_match(tmp_path):
    r = roster.Roster.load(tmp_path, home=tmp_path)
    r.classify("Jean Francois Hardan", person_id="jf", tier="colleague",
               aliases=["John Francois", "JF"])
    r.save()
    pid, status = roster.Roster.load(tmp_path, home=tmp_path).resolve("John Francois")
    assert pid == "jf" and status == "matched"


def test_tier_lookup(tmp_path):
    r = roster.Roster.load(tmp_path, home=tmp_path)
    r.classify("Dilip Jayavelu", person_id="dilip", tier="client")
    assert r.tier_of("dilip") == "client"
