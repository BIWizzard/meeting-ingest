# Session Wrap - dogfood-hardening

- Wrapped at: 2026-07-30T02:47:19.365Z
- Workstream: dogfood-hardening
- Lifecycle: active
- Mode: design

## Summary

Re-ran the guidance 1.1 release-evidence acceptance in a fresh session; ACCEPTED AS MILESTONE PROOF WITH A SCOPED CLAIM by owner ruling. Attempt 2 on build meeting-ingest-0.2.0-g3695fc350c77-s61e1660c5dc8: 18/18 blocking, 1/1 advisory, readiness ready with ZERO findings, no development override, no interventions, grounding matching the fixture exactly (3 labels, 36 timestamps), workflow.match true with 8/8 pin and 8/8 receipt comparisons. THE CONDITION ATTEMPT 1 FAILED WAS PROVEN BEFORE THE RUN, not assumed: a provenance-only probe of the session-provider agent in a separate context (no extraction, no file access) reported exactly one rule set, version 1.1, 7 rules, rule 6 present, rules 4/5 revised, and its quoted rule 4/5/6 text matched the receipt-installed doc verbatim; agent sha 890878d7 identical across repo source, user-level install and acceptance-root copy. The evaluator had to be REBUILT because the prior one lived in a dead session scratchpad, and was verified twice before its tally was accepted: synthetic self-test in both directions for all 8 executable operators, plus 7/7 targeted mutations of this run's own payload off a clean baseline. Attempt 1's factual misattribution is FIXED (T2 credits Dara, evidence row agrees) and its Thursday-scope overreach is FIXED. BUT RULE 6 IS NOW FALSIFIED rather than merely unproven: cross-vendor blind review found A2/D3/T5/TL;DR/one signal widened Rosa's committed scope to 'raise the merge timeout AND add an alert' when Rosa narrowed it at 02:16 ('Alerting change only') and self-summarized at 03:42 ('alerting change is mine by Friday'); upheld after direct transcript check as a scope widening inside a committed action item, ownership and Friday date correct, and no assertion detects it. FIXED AND COMMITTED: the generated_by defect (cd3478a) -- render.py declared tool_version as a hardcoded '0.1.0' dataclass default no caller ever set, so every artifact misreported its generator while runtime_provenance.semantic_version in the same front matter read 0.2.0, and the expected-markdown fixture pinned the same literal so the suite ENFORCED the bug; a third version source after BUILD_INFO. Now sourced from BUILD_INFO with two guards, the second added because codex-review correctly caught that equality with the current version cannot distinguish a dynamic lookup from a literal that happens to match. Also re-synced ~/.codex/skills/meeting-ingest/SKILL.md, which had silently carried guidance 1.0 since 2026-07-26 against a 1.1 repo source. Answered the second inbound ~/.claude relay: its hand-edit premise is FALSE and the correct action there is a commit, not a revert or reinstall. Claim language rewritten off 'not achieved' (3d6c384). Acceptance root cleaned up; evaluator, response snapshot and blind review preserved at /private/tmp/meeting-ingest-acceptance-evaluator.

## Continuation

Resume with: Add rule 6 framing-restraint detection to the semantic-integrity fixture, using this run's concrete failing case: a committed action item whose scope exceeds what its owner accepted, where the owner's own narrowing ('Alerting change only') and self-summary ('alerting change is mine by Friday') are both in the transcript. Until this exists, rule 6 conformance is only ever established by human reading.

## Active Files

- docs/sessions/2026-07-29-guidance-1_1-release-evidence-acceptance.md

## Changes This Wrap

### Open questions

```text
+ Should the acceptance evaluator live in the repository? It has now been written ad hoc three times because it lives in session scratchpad, and a different instrument per run weakens comparability across runs even when every tally reads 18/18. It is the instrument that decides milestone proof.
```

### Next actions

```text
+ Add rule 6 framing-restraint detection to the semantic-integrity fixture, using this run's concrete failing case: a committed action item whose scope exceeds what its owner accepted, where the owner's own narrowing ('Alerting change only') and self-summary ('alerting change is mine by Friday') are both in the transcript. Until this exists, rule 6 conformance is only ever established by human reading.
+ Add the attribution assertion class proposed after attempt 1 (a narrative field naming a speaker as a statement's source must agree with the evidence rows cited for the same item). Still unwritten; attempt 2 would have passed it, so it remains untested against a real failure.
+ Promote the acceptance evaluator into the repository next to the fixture it executes. Working copy preserved at /private/tmp/meeting-ingest-acceptance-evaluator (evaluate.py, selftest.py, mutate_verify.py, plus attempt 2's response snapshot and blind review).
+ Release the generated_by fix (commit cd3478a). Committed but unreleased, so rendered artifacts still stamp meeting-ingest 0.1.0 until a new build; artifacts already written, including attempt 2's, carry the wrong generator version and are not being corrected.
+ Add a drift check for the non-receipt-managed Codex skill pair to the suite or a hook. Re-synced this session but maintained by explicit copy, so it can drift silently again -- and did, undetected, for three days.
+ Commit the two receipt-installed files in the ~/.claude worktree (agents/meeting-ingest-session-provider.md, skills/meeting-ingest/SKILL.md). Verified receipt-matching; that repo's HEAD simply predates the 15:07 install. Not a revert and not a reinstall.
+ Push the six unpushed commits on main (03ec1ca, 3afe7e9, 3695fc3, e026e31, cd3478a, 3d6c384).
+ Convene the North Star board on the update-policy brief from cap_20260727T024600Z: segment update policy by consumer class, with HTV keeping fail-closed pins and general consumers getting auto-updating distribution with invisible attestation verification. The charter convening trigger is met and this amends record 002.
+ Spot-check extraction quality on the six 2026-07-25 HTV meetings, the 2026-07-24 retention-policy artifact and the 2026-07-28 AdBook artifact now that guidance 1.1 has landed. More urgent now that rule 6 is known to fail.
+ Determine whether a meeting artifact can evidence that the harness honored the pinned extraction model at run time, given that model_id is the constant claude-code-session and model_alias is only a quality tier.
+ Triage three engine observations: pin_runtime resolves workflow files from <root>/.claude while inspect_runtime uses ~/.claude; runtime_provenance source_commit and source_tree_sha256 are null on a clean editable checkout; doctor and status reject a subcommand-level --development-override that five other commands accept.
+ Optionally implement the Layer 5D interim relief: one maintainer command wrapping build/receipt/publish/install/repin, and one consumer runtime-update command wrapping fetch/verify/install/repin.
- Re-run the release-evidence acceptance in a fresh Claude Code session so the host loads the installed guidance 1.1 agent doc, then get the owner human semantic review; only that run can establish milestone proof.
- Push the four unpushed commits on main (03ec1ca, 3afe7e9, 3695fc3, e026e31).
- Add an assertion class to the semantic-integrity fixture requiring that where a narrative field names a speaker as the source of a statement, that name agrees with the evidence rows cited for the same item; the release-evidence run passed 18/18 while crediting a statement to the wrong speaker.
- Add framing-restraint assertions to the semantic-integrity fixture so rule 6 has detection behind it instead of relying on blind human review.
- Spot-check extraction quality on the six 2026-07-25 HTV meetings, the 2026-07-24 retention-policy artifact, and the 2026-07-28 AdBook artifact now that guidance 1.1 has landed, using them to confirm the framing-restraint revisions.
- Convene the North Star board on the update-policy brief from cap_20260727T024600Z: segment update policy by consumer class, with HTV keeping fail-closed pins and general consumers getting auto-updating distribution with invisible attestation verification; the charter convening trigger is met and this amends record 002.
- Determine whether a meeting artifact can evidence that the harness honored the pinned extraction model at run time, given that model_id is the constant claude-code-session and model_alias is only a quality tier, and decide whether per-run model attestation needs recording directly.
- Triage three engine observations: pin_runtime resolves workflow files from <root>/.claude while inspect_runtime uses ~/.claude; runtime_provenance source_commit and source_tree_sha256 are null on a clean editable checkout; and doctor and status reject a subcommand-level --development-override that five other commands accept.
- Reconcile the ~/.claude git worktree, where the receipt-verified installer left agents/meeting-ingest-session-provider.md and skills/meeting-ingest/SKILL.md dirty against that repo's HEAD; the content is correct and receipt-matching, so this is a commit in ~/.claude, not a revert.
- Optionally implement the Layer 5D interim relief under the existing contract: one maintainer command wrapping build/receipt/publish/install/repin, and one consumer runtime-update command wrapping fetch/verify/install/repin.
- See wrap next-actions list.
```

## Next Actions

- Add rule 6 framing-restraint detection to the semantic-integrity fixture, using this run's concrete failing case: a committed action item whose scope exceeds what its owner accepted, where the owner's own narrowing ('Alerting change only') and self-summary ('alerting change is mine by Friday') are both in the transcript. Until this exists, rule 6 conformance is only ever established by human reading.
- Add the attribution assertion class proposed after attempt 1 (a narrative field naming a speaker as a statement's source must agree with the evidence rows cited for the same item). Still unwritten; attempt 2 would have passed it, so it remains untested against a real failure.
- Promote the acceptance evaluator into the repository next to the fixture it executes. Working copy preserved at /private/tmp/meeting-ingest-acceptance-evaluator (evaluate.py, selftest.py, mutate_verify.py, plus attempt 2's response snapshot and blind review).
- Release the generated_by fix (commit cd3478a). Committed but unreleased, so rendered artifacts still stamp meeting-ingest 0.1.0 until a new build; artifacts already written, including attempt 2's, carry the wrong generator version and are not being corrected.
- Add a drift check for the non-receipt-managed Codex skill pair to the suite or a hook. Re-synced this session but maintained by explicit copy, so it can drift silently again -- and did, undetected, for three days.
- Commit the two receipt-installed files in the ~/.claude worktree (agents/meeting-ingest-session-provider.md, skills/meeting-ingest/SKILL.md). Verified receipt-matching; that repo's HEAD simply predates the 15:07 install. Not a revert and not a reinstall.
- Push the six unpushed commits on main (03ec1ca, 3afe7e9, 3695fc3, e026e31, cd3478a, 3d6c384).
- Convene the North Star board on the update-policy brief from cap_20260727T024600Z: segment update policy by consumer class, with HTV keeping fail-closed pins and general consumers getting auto-updating distribution with invisible attestation verification. The charter convening trigger is met and this amends record 002.
- Fix the date-gate friction at the skill level so the meeting-ingest skill asks the owner for the meeting date before the first phase-1 mint whenever the source file carries no reliable date signal.
- Add a Decisions status vocabulary to docs/artifact-contract.md so Decisions statuses are enumerable the way Commitments statuses already are, and rule on whether Stakeholder Asks and Dependencies may keep free text after the leading status token.
- Spot-check extraction quality on the six 2026-07-25 HTV meetings, the 2026-07-24 retention-policy artifact and the 2026-07-28 AdBook artifact now that guidance 1.1 has landed. More urgent now that rule 6 is known to fail.
- Find or record a meeting transcript containing a real identity ambiguity so the guidance 1.1 identity-confidence rule is confirmed against evidence rather than only against the fixture it was written for.
- Determine whether a meeting artifact can evidence that the harness honored the pinned extraction model at run time, given that model_id is the constant claude-code-session and model_alias is only a quality tier.
- Triage three engine observations: pin_runtime resolves workflow files from <root>/.claude while inspect_runtime uses ~/.claude; runtime_provenance source_commit and source_tree_sha256 are null on a clean editable checkout; doctor and status reject a subcommand-level --development-override that five other commands accept.
- Optionally implement the Layer 5D interim relief: one maintainer command wrapping build/receipt/publish/install/repin, and one consumer runtime-update command wrapping fetch/verify/install/repin.

## Blockers

- No corpus adoption or mutation is authorized; a deterministic fingerprinted adoption plan requires later owner approval (OB-002-1).

## Open Questions

- Should installed workflow artifacts carry a receipt or build stamp of their own? Today the installed agent doc and skill have no content stamp, so there is no local way to tell whether a copy still matches the receipt that placed it, and a hand-edit would be undetectable from the consumer side. This surfaced from an inbound ~/.claude relay that could not distinguish an installer write from a hand-edit.
- Should docs/claude-skills/meeting-ingest/SKILL.md quote a single published rule source rather than restate the semantic guidance rules verbatim? Five surfaces now duplicate the rule text, and a parity test guards it in this repo, but the duplication remains a standing drift risk raised by the ~/.claude relay.
- Does morale or capacity language about a named third party belong in the durable signal stream at all? The 2026-07-28 HTV artifact persists a colleague capacity state as a high-confidence risk_or_concern signal feeding signal JSONL, playbook derivation and briefings; the rendering softened the verbatim appropriately, so the question is inclusion rather than wording, and it may be a board matter rather than a guidance tweak.
- Should the acceptance evaluator live in the repository? It has now been written ad hoc three times because it lives in session scratchpad, and a different instrument per run weakens comparability across runs even when every tally reads 18/18. It is the instrument that decides milestone proof.

## Decisions

- Guidance 1.1 release-evidence acceptance is accepted as milestone proof with a SCOPED CLAIM: rules 4 and 5 are confirmed against the assertions that sank both 1.0 release-evidence runs (S5/S6/S10 passed on the frozen build), while rule 6 is FALSIFIED rather than merely unproven and is excluded from the claim. Reasoning: the declared blocking floor is the assertion set and it passed 18/18 on a twice-verified evaluator under deviation-free conditions; review findings are dispositioned by the human reviewer rather than automatically disqualifying; and a fresh run without a guidance or fixture change would only re-roll the same dice on a rule that has no detection behind it either way. Owner ruling, 2026-07-29.

## Discoveries

- Rule 6 (framing restraint, added by guidance 1.1) is not reliably obeyed on the approved runtime. First concrete failure: the artifact widened Rosa's committed scope to include a merge-timeout raise she never accepted, across five fields, while she twice labelled her own commitment 'alerting change'. No assertion in expected-review.json detects it -- the fixture's rule 6 blind spot, previously theoretical, is now demonstrated. The failing case is now available to write detection against.
- A guard that asserts a version stamp equals the CURRENT version cannot distinguish a dynamic lookup from a hardcoded literal that happens to match, and is therefore not a regression guard at all -- it only fires at the next bump. This is exactly how generated_by went stale: a literal that matched when written, with a golden fixture agreeing. Proving dynamic sourcing requires patching the version source and reimporting. Generalizes to any provenance or identity field pinned in a golden fixture.
- The non-receipt-managed Codex skill pair drifted undetected for three days (installed copy stuck at guidance 1.0 from 2026-07-26 while the repo source moved to 1.1 on 2026-07-29). Receipt management is what caught nothing here: the Claude pair verified clean via readiness and runtime inspect, while the Codex pair has no mechanism and only fails a manual cmp that nothing runs automatically.
