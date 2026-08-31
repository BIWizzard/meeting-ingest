# Session Wrap - dogfood-hardening

- Wrapped at: 2026-08-31T03:32:49.751Z
- Workstream: dogfood-hardening
- Lifecycle: active
- Mode: design

## Summary

Landmark session: all four remaining record-003 enforcement obligations closed, 0.4.0 released through the new command pair, and the repo anonymized. (1) OB-003-1 (4a62db9): 'meeting-ingest update' + scripts/release-approved-runtime.py, T2 verified with a board check-in (003/09) on a mid-verification contract deviation, consolidated fix pass, codex round 2. (2) OB-003-5 (79a4058): README channel clause corrected, Consumer Onboarding rewritten one-command-first with the asymmetry principle. (3) OB-003-2 (e2a6d9e): core_inactive category + distinct verdict, honest playbook finding codes, #26 collapse + --verdict-only; issue #26 closed, #31 filed for the detection gap. (4) OB-003-3 (9f607fd): four product-status contradictions closed plus two found in review, derived Activation Accounting section; #23 closed. Backlog issues #29 (share-safe output form) and #30 (repair command) filed per OB-003-4. Anonymization sweep (466ced3): role terms + corpus IDs across live docs/plans/tests, AGENTS.md Identifiers rule, session filename normalized with board citations repaired; iq-context relay #11 filed for the un-editable objective field. RELEASE (b1d0042): 0.4.0 build 65e5090 (suite 569) driven end to end through the command pair — attempt 1 failed closed on the PATH-vs-uv-tool-dir locator defect (fixed with reproduction test), attempt 2 moved both consumers in one command each (reference consumer core_inactive/stale playbook, secondary ready), virgin init Ready, first pasted activation snapshot discharged OB-003-3's citation trigger, OB-003-1 met, issue #16 closed. Open board obligations now: OB-002-1, OB-003-4, OB-003-6 (all check-in gates).

## Continuation

Resume with: Run 'meeting-ingest playbook update' at the reference consumer root to regenerate the stale playbook and clear the core_inactive verdict the 0.4.0 release snapshot recorded.

## Active Files

- src/meeting_ingest/runtime_release.py
- scripts/release-approved-runtime.py

## Changes This Wrap

### Open questions

```text
+ Owner call: should person names in doc examples (kushali/jim-haley plus the ad-sales vocabulary the anonymization review flagged as a re-identification surface) get the same anonymization treatment the company names received, and is a deeper git-history scrub wanted? Both are OB-003-4-adjacent; no action taken without a ruling.
```

### Next actions

```text
+ Run 'meeting-ingest playbook update' at the reference consumer root to regenerate the stale playbook and clear the core_inactive verdict the 0.4.0 release snapshot recorded.
+ Implement issue #31: emit a core_inactive finding when a normally-initialized project has ingested meetings but no derived playbook generation — the first new finding class now unblocked by OB-003-2.
- Build the OB-003-1 command pair (issue #16): one maintainer release command and one consumer 'meeting-ingest update' command that drive the existing verified build/publish/install/repin steps end to end.
- Land OB-003-2 readiness activation legibility: rename the threefold optional_playbook_output_missing mislabel, collapse repeated same-code history findings per issue #26, and add the core_inactive category with its own distinct verdict — required before any new finding class ships.
- Close OB-003-3 and OB-003-5 before the next release: widen issue #23 to all four product-status contradictions with activation state derived from tool output, and reconcile the README channel clause and Consumer Onboarding copy per record 003.
- File a sanitized backlog issue for the share-safe artifact output form required by OB-003-4, and one for the consumer repair command the record 003 developer seat identified.
- Receive the OB-003-1 fix pass, re-verify at T2 (focused review of the delegation redesign + regression lenses), then commit the command pair and update issue #16
- Drive the next release through scripts/release-approved-runtime.py and 'meeting-ingest update' end to end — that run is OB-003-1's acceptance proof and closes issue #16 (OB-003-3 and OB-003-5 must land before that release ships)
- When OB-003-2 lands: T2 verify (codex + implementer-model, contract line item on artifact-contract clauses), commit, then dispatch OB-003-3 (#23 widened: all four product-status contradictions closed, implemented vs active-at-reference-consumer vocabulary, activation state derived from tool output)
- When OB-003-3 reports: T2 verify the product-status revision (contract line item: derived activation metadata only, four contradictions closed), commit, close #23, update board row + CLAUDE.md block — then all four user-ordered items are done; offer #31 as the natural next unit
- Drive the next release through scripts/release-approved-runtime.py and 'meeting-ingest update' end to end — OB-003-1's acceptance proof; its evidence must cite the activation accounting (fresh pasted snapshot) per OB-003-3
- Issue #31: never-generated playbook detection on normally-initialized projects — the first new finding class gated behind the now-landed OB-003-2
- Reference consumer playbook refresh: run 'meeting-ingest playbook update' at the reference consumer root to clear the core_inactive staleness the 0.4.0 snapshot recorded (owner-run or next session)
- Owner decisions parked: person names in doc examples (kushali/jim-haley + adbook vocabulary, review P3-1) and any deeper history scrub — both OB-003-4-adjacent
```

## Next Actions

- Run 'meeting-ingest playbook update' at the reference consumer root to regenerate the stale playbook and clear the core_inactive verdict the 0.4.0 release snapshot recorded.
- Implement issue #31: emit a core_inactive finding when a normally-initialized project has ingested meetings but no derived playbook generation — the first new finding class now unblocked by OB-003-2.

## Blockers

- No corpus adoption or mutation is authorized; a deterministic fingerprinted adoption plan requires later owner approval (OB-002-1).

## Open Questions

- Should installed workflow artifacts carry a receipt or build stamp of their own? Today the installed agent doc and skill have no content stamp, so there is no local way to tell whether a copy still matches the receipt that placed it, and a hand-edit would be undetectable from the consumer side. This surfaced from an inbound ~/.claude relay that could not distinguish an installer write from a hand-edit.
- Should docs/claude-skills/meeting-ingest/SKILL.md quote a single published rule source rather than restate the semantic guidance rules verbatim? Five surfaces now duplicate the rule text, and a parity test guards it in this repo, but the duplication remains a standing drift risk raised by the ~/.claude relay.
- Owner call: should person names in doc examples (kushali/jim-haley plus the ad-sales vocabulary the anonymization review flagged as a re-identification surface) get the same anonymization treatment the company names received, and is a deeper git-history scrub wanted? Both are OB-003-4-adjacent; no action taken without a ruling.
