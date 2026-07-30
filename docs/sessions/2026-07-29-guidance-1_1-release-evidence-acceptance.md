# Semantic Guidance 1.1 — Release-Evidence Acceptance Attempt 2

Date: 2026-07-29 (run executed 2026-07-29T21:13–21:17 UTC)
Acceptance procedure: `docs/testing/semantic-integrity-acceptance.md`.
Release record: `docs/sessions/2026-07-29-guidance-1_1-release.md` (build, publish, install, repin, and attempt 1).
Development-evidence predecessor: `docs/sessions/2026-07-29-guidance-1_1-semantic-acceptance-dev-run.md`.

This is the second release-evidence attempt on build `meeting-ingest-0.2.0-g3695fc350c77-s61e1660c5dc8`. Attempt 1 scored 18/18 blocking but was not accepted as milestone proof because the host had cached the pre-release agent definition, so extraction ran against guidance 1.0's rules. This attempt exists to establish the one condition attempt 1 lacked.

**Verdict: accepted as milestone proof with a scoped claim.** The owner completed the human semantic review and ruled on the rule 6 question. See [Verdict](#verdict).

## The Precondition Attempt 1 Failed — Proven Before The Run, Not Assumed

The receipt-verified installer wrote the 1.1 agent doc at 15:07 local. This Claude Code session started at approximately 17:09, two hours later, so the host cache should carry 1.1. That was verified rather than assumed, by the same self-report that detected the drift in attempt 1: a provenance-only probe of the `meeting-ingest-session-provider` agent in a separate context that performed no extraction and touched no files.

The probe reported its loaded prompt enumerates rules for exactly one version, `"1.1"`, with 7 numbered rules, rule 6 present, and rules 4 and 5 in their revised form. The quoted rule 4, 5, and 6 text was then compared against `~/.claude/agents/meeting-ingest-session-provider.md` and matches verbatim.

The probe ran in its own context and could not contaminate extraction, which was invoked separately with request paths only.

| Instruction surface | sha256 | Status |
|---|---|---|
| Repo source agent doc | `890878d7…` | reference |
| User-level `~/.claude/` agent doc | `890878d7…` | match |
| Acceptance-root `.claude/` agent doc | `890878d7…` | match |
| Rendered skill, both destinations | `7e2c1ae4…` | match |
| Host-loaded definition | — | verbatim rule-text agreement with the above |

There is no project-level `.claude/agents` copy in this repository, so the session loaded the user-level install directly.

## Provenance

| Field | Value |
|---|---|
| Host and host version | Claude Code (reference host), session started ~2026-07-29T21:09Z |
| Model | `provider.model_id`: `claude-code-session`; `provider.model_alias`: `balanced`; pinned agent model `claude-opus-5` |
| Build identity | `meeting-ingest-0.2.0-g3695fc350c77-s61e1660c5dc8`, `source_commit` `3695fc350c77…`, `source_tree_sha256` `61e1660c5dc8…` |
| Runtime mode and verdict | readiness `ready`, **zero findings**, `runtime_mode: approved`, `install_mode: approved_frozen`, `development_override_reason: null` |
| Semantic guidance version | `1.1` in request (7 rules), echoed in response, stamped in artifact front matter |
| Quality | request `quality`: `balanced`; response `model_alias`: `balanced` |
| Elapsed time | ~4m21s (request created 21:13:03Z → phase-2 artifact written 21:17:24Z) |
| Extraction tokens | 53,870 host-reported subagent tokens; 5 tool uses; 197s |
| Interventions | **none** |
| Output paths | `2026-07-26-lantern-nightly-load-failure-review-orchid-ledger-daily-merge-abort.md`; `_signals/mtg-20260726-6c45c41d.jsonl` |
| Signal count | 14 |
| Grounding binding | request `transcript_grounding` matched `expected-review.json` exactly: 3 speaker labels, 36 timestamps |
| Response snapshot | `eval-response.json` sha256 `7ef1dd1f49da78cb3e59482128386e272d5c1d2a23d5f640db10d34237ff08e6` |

`meeting_id` `mtg-20260726-6c45c41d` is identical to attempt 1, so the two artifacts are directly comparable.

Phase results: `provider-request` exit 0; preflight `validate-response` exit 0 with `status: success`, `provider_response.status: valid`, readiness `ready_with_history_warnings`, zero errors and zero warnings; response snapshotted before phase 2; `ingest` exit 0; `doctor` clean with zero issues; `status` reporting `session_handoffs` totals all zero; the request/response pair deleted by successful phase 2; the source reconciled to `_inbox/_done/`.

**This is release evidence.** No `--development-override`, no editable checkout, no `development_override` anywhere in the run.

## Assertion Results

**18/18 blocking pass, 1/1 advisory pass.**

| ID | Severity | Result |
|---|---|---|
| DG1–DG5 | blocking | pass |
| DG6 | blocking | pass by CLI (`validate-response` exit 0, `status: success`, `provider_response.status: valid`); the script reports `not_applicable`, as `cli_exit_code` is not derivable from a snapshot |
| S1–S10, S12, S13 | blocking | pass |
| S11 | advisory | pass |

Evaluated against the `response` key of the preserved snapshot, using the selector, operator, null, and severity vocabulary declared in `expected-review.json`.

### The Evaluator Was Verified Before Its Results Were Accepted

The evaluator used for the earlier runs lived in a prior session's scratchpad and no longer exists, so it was rebuilt from the declared `evaluation` block and verified twice before its tally was trusted.

1. **Synthetic self-test.** For each of the 8 executable operators, the evaluator reports `pass` on a satisfying payload and `fail` on a violating one. All 8 detect their violation in both directions.
2. **Mutation of this run's own payload.** Seven targeted mutations were applied to the real snapshot, each required to flip its named assertion. Baseline was clean and **7/7 were detected**: DG1 (fabricated `(Contractor)` qualifier, also tripping DG2), S1 (10:06 rendered a.m.), S3 (topic summary asserting a confirmed cause), S5 (rejected split as an open action), S6 (split with no disposition), S10 (a `Ro`-carrying signal raised to high confidence), and S12 (TL;DR narrating a confirmed root cause, also tripping S3).

An evaluator that passes everything cannot satisfy either check. That the instrument was rebuilt from scratch is itself a finding — see Findings 3.

## Independent Blind Review

Conducted by a cross-vendor reviewer (codex, read-only) that had not seen `expected-review.json`, did not run the case, and was given only the transcript and the artifact in an isolated directory, with the fixture filename preserved. Three findings, each adjudicated against the transcript directly rather than accepted on report.

| # | Finding | Class | Disposition |
|---|---|---|---|
| 1 | A2, D3, T5, the TL;DR, and one signal render Rosa's committed scope as "raise the merge timeout **and** add an alert" | **rule 6 scope widening** | **Real defect. Upheld.** Dara proposes both measures at 02:09; Rosa narrows at 02:16 — "That I will take. **Alerting change only**, no loader logic" — and self-summarizes at 03:42 as "**alerting change** is mine by Friday." She labels her own commitment "alerting change" twice and never restates the timeout raise. The artifact widened a committed action item to cover work its owner did not accept. Rosa's ownership and the Friday date are correct; only the scope is widened. |
| 2 | Q5 gives "Villanueva, Rosa to reconsider only after quarter close ships and only if lock timeouts persist" | framing overreach | **Quality finding, partially mitigated.** Rosa says "we can revisit," a group conditional, not a personal commitment. The same row carries "the split was ruled infeasible and parked, and nobody is starting that work now," so the conditional survives. This is the same pattern as attempt 1's finding 4 — softened, not eliminated. |
| 3 | ASK5 records Femi's loader-split proposal as a stakeholder ask directed to Rosa | overstatement | **Quality finding.** At 01:31 Femi offers it to the group — "I think the real fix is to split the loader" — and does not ask Rosa to approve or perform it. Recording it as a proposal is supported; categorizing it as an ask directed to Rosa is a stretch. Mitigated: the row marks it infeasible and parked and notes Femi withdrew it. |

The reviewer classified finding 1 as misattribution and stated the transcript "does not support assigning the timeout increase to Rosa." That overstates its own case slightly — "That I will take" does answer a two-part proposal — but the balance of evidence favors the reviewer, and the finding is upheld as a scope widening rather than a false attribution of ownership.

The reviewer found no substantive omission and no invented incident fact, and confirmed correct handling of the abort and 10:06 pass, the manual retry, the open lock-wait cause, the archival sweep as an unconfirmed guess, the parked split, the unresolved `Ro` identity, the partial-state question, and speaker attribution throughout the quoted evidence and verbatim transcript.

## Attempt 1's Defects: Both Fixed

| Attempt 1 finding | This run |
|---|---|
| Finding 2, factual misattribution — T1 credited Dara's 10:06 "last run of the night" line to Femi while citing two Dara evidence rows | **Fixed.** T2 credits Dara, with evidence `Marchetti, Dara (Contractor) (00:22)`. The TL;DR says "The team identified the failed pass," attributing to nobody. No misattribution found anywhere by the blind reviewer or by direct check. |
| Finding 3, framing overreach — TL;DR presented both Femi tasks as "for Thursday's sync" when only the lock-wait numbers were | **Fixed.** A1 is "Thursday's sync"; A3 is "Thursday, same deadline as the log pull," matching Femi's "Same Thursday deadline" at 03:37. |
| Finding 4, conditional as owned next step — Q4/Q5 ownership | **Softened, not eliminated.** See blind finding 2 above. |

## Findings Beyond The Assertions

### 1. The artifact stamps the wrong generator version — `generated_by: meeting-ingest 0.1.0`

The front matter contradicts itself. `generated_by` reads `meeting-ingest 0.1.0` while `runtime_provenance.semantic_version` in the same block reads `"0.2.0"` and `build_id` names the 0.2.0 build.

Cause: `render.py:35` declares `tool_version: str = "0.1.0"` as a `RenderContext` dataclass default, and **no caller anywhere in the source sets it**. The only two references in the tree are that default and the f-string at `render.py:92`. It is a hardcoded literal, not a version lookup.

Why the 0.2.0 bump did not catch it: `tests/fixtures/expected_markdown/summary_plus_verbatim_basic.md:20` pins `generated_by: meeting-ingest 0.1.0`, so the test suite agrees with the defect and enforces it. The bump session found `BUILD_INFO` as a second version source, caught by the build-info test; this is a **third** source, and the fixture is why nothing failed.

This is a provenance-integrity defect, not cosmetic: meeting artifacts are durable and feed signal JSONL, playbook derivation, and briefings, and every artifact this build renders misreports the generator that produced it. It is present at repo HEAD and affects the released build.

It is not an assertion failure — all 19 assertions are rooted at the response payload, and none inspects front matter. It is a defect this run surfaced, which is what the review tier exists for.

### 2. The installed Codex skill still carries guidance 1.0

The procedure's Workflow Copy Verification requires the non-receipt-managed Codex pair to be byte-identical. It is not:

- `docs/codex-skills/meeting-ingest/SKILL.md` — `c98e1729…` (guidance 1.1, 7 rules)
- `~/.codex/skills/meeting-ingest/SKILL.md` — `6e0fee5a…` (guidance **1.0**, 6 rules)

The installed copy says `For version "1.0" the rules are:` and carries the pre-revision rule 4 ("Never carry a rejected or infeasible proposal into open actions."), the pre-revision rule 5, and **no framing-restraint rule** — 1.0's TL;DR rule sits at 6. Its mtime is 2026-07-26 21:58; the repo source is 2026-07-29 14:04. The 1.1 propagation updated the repo source and never re-installed the Codex copy.

This did not affect this run: Claude Code is the reference host, the Codex skill was never loaded, and the receipt-managed Claude pair verified clean. But a Codex-hosted extraction would read 1.0 rules from its own prompt while the request bound 1.1 — the exact drift condition attempt 1 hit, surviving only on the obey-the-request clause.

### 3. The acceptance evaluator is rebuilt from scratch every run

The evaluator is the instrument that decides the blocking tally, and it has now been written ad hoc at least three times because it lives in session scratchpad. Different instrument per run weakens comparability across runs even when every tally reads 18/18. It belongs in the repository next to the fixture it executes.

## Verdict

**The condition attempt 1 failed is established.** The host loaded the receipt-installed guidance 1.1 definition, proven by probe and verbatim rule-text comparison; the runtime was clean approved with zero readiness findings; the request bound 1.1 with grounding matching the fixture exactly; the workflow chain verified end to end with 8/8 pin and 8/8 receipt comparisons; and there were no interventions.

**Assertion floor: 18/18 blocking, 1/1 advisory, on a twice-verified evaluator.** Attempt 1's factual misattribution and one of its two framing findings are fixed.

**The honest limit: rule 6 was violated in this run.** Blind finding 1 is a scope widening inside a committed action item, and rule 6 is precisely the rule guidance 1.1 added and that the owner accepted as unproven with no fixture detection behind it. This run is therefore the first evidence that rule 6 is not reliably obeyed on the approved runtime, and it was caught only by blind human-equivalent review — exactly the blind spot already recorded. A re-run without a guidance or fixture change would only re-roll the same dice.

## Human Semantic Review

**Completed 2026-07-29 by the owner**, who read the generated artifact against the transcript with the contested passage named — A2, D3, T5 and the TL;DR on Rosa's committed scope, weighed against Dara at 02:09, Rosa at 02:16, and Rosa's own wrap-up at 03:42. The owner raised no defect beyond those the blind review reported and this record already carries, and ruled on the milestone question below.

## Owner Ruling

**Accepted as milestone proof, with a scoped claim.**

Milestone-proof semantic acceptance of guidance 1.1 on the approved runtime **is achieved** by this run, bounded as follows:

- **Rules 4 and 5 are confirmed against the failures they were written for.** S5, S6 and S10 passed on the frozen build. S10 and S6 are the assertions that sank both 1.0 release-evidence runs, and the 1.1 revisions close them under release conditions.
- **Rule 6 is falsified, not merely unproven.** It entered the release accepted as unproven with no fixture detection behind it. This run demonstrates it is not reliably obeyed: blind finding 1 is a scope widening inside a committed action item. The claim excludes rule 6.
- Rule 6 detection becomes fixture work, and this run supplies the concrete failing case to write it against.

The reasoning for accepting rather than re-running: the declared blocking floor is the assertion set, and it passed 18/18 on a twice-verified evaluator under conditions with no deviation. Review findings are dispositioned by the human reviewer, not automatically disqualifying. A fresh run without a guidance or fixture change would only re-roll the same dice on a rule that has no detection behind it either way.

Both reviews are reconciled with no unresolved disagreement: the blind reviewer's three findings were each adjudicated against the transcript, finding 1 upheld with its classification corrected from misattribution to scope widening, findings 2 and 3 upheld as quality findings. The owner's review concurred and added nothing further.

## Carry-Forward

Open:

- Blind finding 1 as an extraction defect against this run; findings 2 and 3 as quality findings.
- **Rule 6 needs fixture detection.** This run gives a concrete failing case to write it against: a committed action item whose scope exceeds what its owner accepted, where the owner's own narrowing ("Alerting change only") and self-summary ("alerting change is mine by Friday") are both present in the transcript. Until such an assertion exists, rule 6 conformance is only ever established by human reading.
- The attribution assertion class proposed after attempt 1 is still unwritten. This run would have passed it, so it remains untested against a real failure.
- **Promote the acceptance evaluator into the repository**, next to the fixture it executes. It has now been written ad hoc at least three times, and a per-run instrument weakens comparability across runs even when every tally reads 18/18.

Closed in this session:

- **`generated_by` version stamp — fixed.** `RenderContext.tool_version` now derives from `BUILD_INFO["semantic_version"]` instead of a literal, the expected-markdown fixture carries a `{{TOOL_VERSION}}` placeholder rather than a pinned version, and tests assert both that the rendered stamp equals the real package version and that the default *tracks its source* rather than merely matching today's value.

  That second test exists because the independent review caught a real gap in the first attempt at this fix: asserting the stamp equals the current `__version__` cannot distinguish a dynamic lookup from a hardcoded literal that happens to match — which is precisely how the stamp went stale in the first place. A literal equal to the current version passed all 19 tests. The added test patches `BUILD_INFO["semantic_version"]`, reimports the render module, and requires the default to follow, restoring the original afterward.

  Verified by deliberate regression across all three states, repeated to rule out an unreliable reading:

  | `tool_version` | Result |
  |---|---|
  | `BUILD_INFO["semantic_version"]` | 465 passed |
  | literal `"0.2.0"` — equal to today's version | the source-tracking test fails |
  | literal `"0.1.0"` — stale | all three version tests fail |

  The `runtime_provenance.semantic_version` literal in the fixture was deliberately left pinned — it is test data for a fake approved build, and deriving it from the same constant the renderer consumes would have made that assertion self-referential.

  The fix does not reach rendered artifacts until a new release; this build continues to stamp `0.1.0`. Artifacts already written by it, including this run's, carry the wrong generator version and are not being corrected — no artifact is adopted or mutated.

- **Codex skill pair re-synced to guidance 1.1.** `~/.codex/skills/meeting-ingest/SKILL.md` now matches `docs/codex-skills/meeting-ingest/SKILL.md` at `c98e1729…`, `cmp` clean, with the framing-restraint rule present and the header reading `For version "1.1" the rules are`. The superseded 1.0 copy was backed up before overwriting. This pair is maintained by explicit copy rather than by receipt, so it can drift again silently; adding the `cmp` check to the suite or a hook remains unaddressed.

The acceptance root is **retained** pending the owner's human semantic review, since removing it destroys the artifact under review. Clean up with `rm -rf` once that review is recorded.
