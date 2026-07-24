# Record 002 — Addendum 10: Ready-with-history-warnings check-in (OB-002-2)

**Date:** 2026-07-24
**Obligation:** OB-002-2 — close the ready-with-history-warnings later-decision.
**Trigger:** fired when Approved Runtime Tasks 9–10 ran production ingest under
the `ready_with_history_warnings` verdict: the Task 9 cutover left HTV at that
verdict with all 177 findings classified history warnings, and the Task 10
fresh-host proof processed one new non-synthetic transcript end to end under it
(`docs/sessions/2026-07-24-task9-htv-cutover.md`,
`docs/sessions/2026-07-24-task10-fresh-host-proof.md`).
**Mode:** `check-in` (orchestrator only, no seats)
**Reconciler:** `reconcile.sh` → `OK: 2 records, 2 open obligations`, exit 0,
before this addendum.

## Decision

Owner ratification, 2026-07-24: safe next-meeting ingest **may proceed** as
`ready_with_history_warnings` while historical continuity remains incomplete.

Bounds carried from existing rulings, unchanged by this closure:

- Only explicitly classified legacy/adoption findings qualify as history
  warnings; unknown health codes still fail closed (artifact contract,
  readiness verdicts).
- History warnings never satisfy the full Continuity exit gate; Track 4
  historical qualification remains approval-gated and unstarted.
- The owner's trust ruling of the same date applies: daily use with manual
  spot-checks of artifacts and signals for the next few meetings.

## Outcome

**met.** The later-decision in `09-owner-decisions.md` ("Other Later
Decisions", first item) is decided affirmatively with demonstrated evidence;
OB-002-2 closes.
