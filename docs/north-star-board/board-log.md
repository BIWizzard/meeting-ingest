# North Star Board — Log (Meeting Ingest)

## Records

| Record | Date | Subject | Outcome | Status |
|---|---|---|---|---|
| 001 | 2026-07-20 | Founding product review and level-set | Internal/private alpha verdict: engine credible, low-ceremony product experience not independently proven | superseded |
| 002 | 2026-07-20 | Reconvened: Just Works Continuity milestone and approved-runtime policies | Product definition, Just Works Continuity milestone, Claude Code reference host, maintainer-only private alpha, read-only corpus reckoning, immutable-build and editable-block runtime policies ratified | ratified |
| 003 | 2026-08-30 | Consumer classes, update policy, and the adoption path (amendment reconvening on 002's consumer policy) | No auto-updating class (P1 redesigned; #16 is the relief); shipped-means-running ratified scoped to the reference consumer (P2 amended); reference-consumer role formalized, HTV default (P3); single-owner candor precondition codified with historical-disclosure fact recorded (P4 amended); one-command init ratified by mechanism (P5) | ratified |

## Obligations

| Obligation | Kind | Trigger | Origin | Status | Governed paths | Lands in |
|---|---|---|---|---|---|---|
| OB-002-1: corpus adoption ratification | check-in | a deterministic fingerprinted adoption plan is proposed for approval | 002 | open | HTV/Spelman consumer corpus surfaces, docs/plans/ | future adoption record (convene) |
| OB-002-2: close the ready-with-history-warnings later-decision | amendment owed | first production ingest proceeds under ready_with_history_warnings (fired 2026-07-24: Tasks 9–10, docs/sessions/2026-07-24-task10-fresh-host-proof.md) | 002 | met | docs/product-status.md, docs/artifact-contract.md readiness clauses | 002 addendum 10 |
| OB-003-1: release/update command pair (issue #16) | enforcement owed | the next release after ratification ships | 003 | open — deviation halted and re-briefed pre-ship (003/09) | scripts/, src/meeting_ingest/cli.py, README.md Release Flow | the two commands |
| OB-003-2: readiness activation legibility (mislabel rename, #26, core_inactive category + distinct verdict) | enforcement owed | before any new finding class ships | 003 | open | src/meeting_ingest/readiness.py, src/meeting_ingest/runtime.py | readiness change set |
| OB-003-3: product-truth activation accounting (#23 widened; derived activation state) | enforcement owed | the next release's evidence cites it | 003 | open | docs/product-status.md, src/meeting_ingest/cli.py status/readiness output | product-status revision |
| OB-003-4: single-owner candor precondition | check-in | earlier of a decision or act extending brief/signal audience beyond the owner, or a reference-consumer role transfer (initial check-in recorded in 003/07: historical disclosure; forward rule ratified) | 003 | open | HTV consumer artifact and briefing surfaces, docs/artifact-contract.md third-party clauses | future check-in addenda on 003 |
| OB-003-5: P5 documentation reconciliation | enforcement owed | before the next release's README update | 003 | met (landed ahead of trigger; README channel clause, Consumer Onboarding rewrite, channel-carries-evidenced-builds-only clause; T2-verified) | README.md consumer onboarding and channel clauses | README revision |
| OB-003-6: auto-update deferral (Decision 35 distribution-transition convening) | check-in | owner declares intent to broaden, or a distribution-transition plan is proposed | 003 | open | DECISIONS.md §35, docs/north-star-board/ | future convening record |

Enforcement note: record 002's runtime rulings were compiled into shipped
enforcement during Approved Runtime Track 1 (readiness gates, receipt/pin
verification, fail-closed blockers) and demonstrated on 2026-07-24; no separate
enforcement-owed row remains for them.
