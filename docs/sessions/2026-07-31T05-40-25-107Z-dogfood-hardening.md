# Session Wrap - dogfood-hardening

- Wrapped at: 2026-07-31T05:40:25.107Z
- Workstream: dogfood-hardening
- Lifecycle: active
- Mode: design

## Summary

Stood up the relay intake lane per issue #1, then pushed and closed it. Commit ea9b157 delivered all four asks: the triage poll wired into both AGENTS.md Start Here and CLAUDE.md (the CLAUDE.md line is load-bearing because Claude Code auto-loads only CLAUDE.md, so a poll living only in AGENTS.md would never fire in Claude sessions), the issue template adapted from iq-context cf60578 with this project's kinds (dogfood finding, pipeline bug, extraction-quality report, feature ask), and a README line under Relationship To iQ Context; the relay label pre-existed. The reserved design question was answered yes: the template's Target section distinguishes shipped-build defects from source-repo requests, and a shipped-build defect must cite build.build_id and receipt.sha256 from meeting-ingest runtime inspect --json, verified against source as the only command that prints both. T2 verification ran (codex review plus independent claude-implementer review); both independently caught the same blocking defect - the draft pointed filers at commands that do not print the receipt sha, and readiness --json even carries a lookalike runtime_provenance_sha256 a filer would silently misreport - fixed before commit along with four advisory findings (the gh issue view bridge, the CLAUDE.md reach gap, README placement, triage-destination wording). Pushed origin main 3a5dc60..ea9b157 (all eight pending commits), retiring the standing push item, and closed issue #1 with a shipped summary cross-linking cap_20260731T052718Z_be1984f1. The lane is live; the catalog-as-native-tooling refile is unblocked and belongs to an iq-context session as the requesting project.

## Continuation

Resume with: Add rule 6 framing-restraint detection to the semantic-integrity fixture, using attempt 2's concrete failing case: a committed action item whose scope exceeds what its owner accepted, with the owner's narrowing (Alerting change only) and self-summary (alerting change is mine by Friday) both in the transcript.

## Active Files

- docs/sessions/2026-07-29-guidance-1_1-release-evidence-acceptance.md

## Changes This Wrap

### Next actions

```text
+ Add rule 6 framing-restraint detection to the semantic-integrity fixture, using attempt 2's concrete failing case: a committed action item whose scope exceeds what its owner accepted, with the owner's narrowing (Alerting change only) and self-summary (alerting change is mine by Friday) both in the transcript.
+ Add the attribution assertion class proposed after attempt 1: a narrative field naming a speaker as a statement's source must agree with the evidence rows cited for the same item.
+ Promote the acceptance evaluator into the repository next to the fixture it executes; working copy preserved at /private/tmp/meeting-ingest-acceptance-evaluator.
+ Release the generated_by fix (cd3478a): cut a new build so rendered artifacts stop stamping meeting-ingest 0.1.0.
+ Fold committing the receipt-installed ~/.claude artifacts into the release flow so each release stops regenerating the false hand-edit signal that misled the relay twice.
+ Add a drift check for the non-receipt-managed Codex skill pair to the suite or a hook; it drifted silently for three days once already.
+ Convene the North Star board on the update-policy brief from cap_20260727T024600Z: segment update policy by consumer class, HTV keeping fail-closed pins and general consumers getting auto-updating distribution with invisible attestation verification; amends record 002.
+ Add a Decisions status vocabulary to docs/artifact-contract.md and rule on whether Stakeholder Asks and Dependencies may keep free text after the leading status token.
+ Spot-check extraction quality on the six 2026-07-25 HTV meetings, the 2026-07-24 retention-policy artifact and the 2026-07-28 AdBook artifact under guidance 1.1; more urgent now that rule 6 is known to fail.
+ Find or record a meeting transcript containing a real identity ambiguity so the guidance 1.1 identity-confidence rule is confirmed against evidence rather than only the fixture it was written for.
+ Determine whether a meeting artifact can evidence that the harness honored the pinned extraction model at run time, given model_id is the constant claude-code-session and model_alias is only a quality tier.
+ Optionally implement the Layer 5D interim relief: one maintainer command wrapping build/receipt/publish/install/repin and one consumer runtime-update command wrapping fetch/verify/install/repin.
- Add rule 6 framing-restraint detection to the semantic-integrity fixture, using this run's concrete failing case: a committed action item whose scope exceeds what its owner accepted, where the owner's own narrowing ('Alerting change only') and self-summary ('alerting change is mine by Friday') are both in the transcript. Until this exists, rule 6 conformance is only ever established by human reading.
- Add the attribution assertion class proposed after attempt 1 (a narrative field naming a speaker as a statement's source must agree with the evidence rows cited for the same item). Still unwritten; attempt 2 would have passed it, so it remains untested against a real failure.
- Promote the acceptance evaluator into the repository next to the fixture it executes. Working copy preserved at /private/tmp/meeting-ingest-acceptance-evaluator (evaluate.py, selftest.py, mutate_verify.py, plus attempt 2's response snapshot and blind review).
- Release the generated_by fix (commit cd3478a). Committed but unreleased, so rendered artifacts still stamp meeting-ingest 0.1.0 until a new build; artifacts already written, including attempt 2's, carry the wrong generator version and are not being corrected.
- Fold 'commit the receipt-installed artifacts in ~/.claude' into the release flow. That repo tracks agents/ and skills/ by explicit gitignore allowlist, so every release dirties those paths and reproduces the false hand-edit signal that misled the inbound relay twice. Done once by hand as d37c9e1; the process gap remains.
- Add a drift check for the non-receipt-managed Codex skill pair to the suite or a hook. Re-synced this session but maintained by explicit copy, so it can drift silently again -- and did, undetected, for three days.
- Push the six unpushed commits on main (03ec1ca, 3afe7e9, 3695fc3, e026e31, cd3478a, 3d6c384) plus the wrap commit a47540a.
- Convene the North Star board on the update-policy brief from cap_20260727T024600Z: segment update policy by consumer class, with HTV keeping fail-closed pins and general consumers getting auto-updating distribution with invisible attestation verification. The charter convening trigger is met and this amends record 002.
- Add a Decisions status vocabulary to docs/artifact-contract.md so Decisions statuses are enumerable the way Commitments statuses already are, and rule on whether Stakeholder Asks and Dependencies may keep free text after the leading status token.
- Spot-check extraction quality on the six 2026-07-25 HTV meetings, the 2026-07-24 retention-policy artifact and the 2026-07-28 AdBook artifact now that guidance 1.1 has landed. More urgent now that rule 6 is known to fail.
- Find or record a meeting transcript containing a real identity ambiguity so the guidance 1.1 identity-confidence rule is confirmed against evidence rather than only against the fixture it was written for.
- Determine whether a meeting artifact can evidence that the harness honored the pinned extraction model at run time, given that model_id is the constant claude-code-session and model_alias is only a quality tier.
- Optionally implement the Layer 5D interim relief: one maintainer command wrapping build/receipt/publish/install/repin, and one consumer runtime-update command wrapping fetch/verify/install/repin.
- Resume the stored continuation: add rule 6 framing-restraint detection to the semantic-integrity fixture using attempt 2's concrete failing case (Rosa's 'Alerting change only' narrowing vs the widened committed scope).
```

## Next Actions

- Add rule 6 framing-restraint detection to the semantic-integrity fixture, using attempt 2's concrete failing case: a committed action item whose scope exceeds what its owner accepted, with the owner's narrowing (Alerting change only) and self-summary (alerting change is mine by Friday) both in the transcript.
- Add the attribution assertion class proposed after attempt 1: a narrative field naming a speaker as a statement's source must agree with the evidence rows cited for the same item.
- Promote the acceptance evaluator into the repository next to the fixture it executes; working copy preserved at /private/tmp/meeting-ingest-acceptance-evaluator.
- Release the generated_by fix (cd3478a): cut a new build so rendered artifacts stop stamping meeting-ingest 0.1.0.
- Fold committing the receipt-installed ~/.claude artifacts into the release flow so each release stops regenerating the false hand-edit signal that misled the relay twice.
- Add a drift check for the non-receipt-managed Codex skill pair to the suite or a hook; it drifted silently for three days once already.
- Convene the North Star board on the update-policy brief from cap_20260727T024600Z: segment update policy by consumer class, HTV keeping fail-closed pins and general consumers getting auto-updating distribution with invisible attestation verification; amends record 002.
- Fix the date-gate friction at the skill level so the meeting-ingest skill asks the owner for the meeting date before the first phase-1 mint whenever the source file carries no reliable date signal.
- Add a Decisions status vocabulary to docs/artifact-contract.md and rule on whether Stakeholder Asks and Dependencies may keep free text after the leading status token.
- Spot-check extraction quality on the six 2026-07-25 HTV meetings, the 2026-07-24 retention-policy artifact and the 2026-07-28 AdBook artifact under guidance 1.1; more urgent now that rule 6 is known to fail.
- Find or record a meeting transcript containing a real identity ambiguity so the guidance 1.1 identity-confidence rule is confirmed against evidence rather than only the fixture it was written for.
- Determine whether a meeting artifact can evidence that the harness honored the pinned extraction model at run time, given model_id is the constant claude-code-session and model_alias is only a quality tier.
- Triage three engine observations: pin_runtime resolves workflow files from <root>/.claude while inspect_runtime uses ~/.claude; runtime_provenance source_commit and source_tree_sha256 are null on a clean editable checkout; doctor and status reject a subcommand-level --development-override that five other commands accept.
- Optionally implement the Layer 5D interim relief: one maintainer command wrapping build/receipt/publish/install/repin and one consumer runtime-update command wrapping fetch/verify/install/repin.

## Blockers

- No corpus adoption or mutation is authorized; a deterministic fingerprinted adoption plan requires later owner approval (OB-002-1).

## Open Questions

- Should installed workflow artifacts carry a receipt or build stamp of their own? Today the installed agent doc and skill have no content stamp, so there is no local way to tell whether a copy still matches the receipt that placed it, and a hand-edit would be undetectable from the consumer side. This surfaced from an inbound ~/.claude relay that could not distinguish an installer write from a hand-edit.
- Should docs/claude-skills/meeting-ingest/SKILL.md quote a single published rule source rather than restate the semantic guidance rules verbatim? Five surfaces now duplicate the rule text, and a parity test guards it in this repo, but the duplication remains a standing drift risk raised by the ~/.claude relay.
- Does morale or capacity language about a named third party belong in the durable signal stream at all? The 2026-07-28 HTV artifact persists a colleague capacity state as a high-confidence risk_or_concern signal feeding signal JSONL, playbook derivation and briefings; the rendering softened the verbatim appropriately, so the question is inclusion rather than wording, and it may be a board matter rather than a guidance tweak.
- Should the acceptance evaluator live in the repository? It has now been written ad hoc three times because it lives in session scratchpad, and a different instrument per run weakens comparability across runs even when every tally reads 18/18. It is the instrument that decides milestone proof.
