# Discovery

- Recorded at: 2026-07-30T02:47:19.365Z
- Workstream: dogfood-hardening

Rule 6 (framing restraint, added by guidance 1.1) is not reliably obeyed on the approved runtime. First concrete failure: the artifact widened Rosa's committed scope to include a merge-timeout raise she never accepted, across five fields, while she twice labelled her own commitment 'alerting change'. No assertion in expected-review.json detects it -- the fixture's rule 6 blind spot, previously theoretical, is now demonstrated. The failing case is now available to write detection against.
