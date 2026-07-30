# Discovery

- Recorded at: 2026-07-30T02:47:19.365Z
- Workstream: dogfood-hardening

A guard that asserts a version stamp equals the CURRENT version cannot distinguish a dynamic lookup from a hardcoded literal that happens to match, and is therefore not a regression guard at all -- it only fires at the next bump. This is exactly how generated_by went stale: a literal that matched when written, with a golden fixture agreeing. Proving dynamic sourcing requires patching the version source and reimporting. Generalizes to any provenance or identity field pinned in a golden fixture.
