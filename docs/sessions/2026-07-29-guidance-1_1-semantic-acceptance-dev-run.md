# Semantic Guidance 1.1 — Semantic Integrity Acceptance Run (Development Evidence)

Date: 2026-07-29 (run executed 2026-07-29T18:46–18:52 UTC)
Procedure: `docs/testing/semantic-integrity-acceptance.md`
Fixture: `tests/fixtures/semantic-integrity/session-provider-eval.vtt` (synthetic)
Assertions: `tests/fixtures/semantic-integrity/expected-review.json` (`semantic_guidance_version` 1.1)
Commit under test: `03ec1ca`

## Evidence Class

**Development / non-release evidence.** This run used an editable checkout under `--development-override` and predates any receipt covering guidance 1.1. It is not milestone proof. The release-evidence run repeats this procedure on the approved frozen build after the owner-gated release flow.

It exists to answer one question ahead of that flow: does guidance 1.1 close the S10 and S6 failures that the two release-evidence runs on build `g51ff17173bea` hit under guidance 1.0?

## Provenance

| Field | Value |
|---|---|
| Host and host version | Claude Code 2.1.220 (reference host) |
| Model | `provider.model_id`: `claude-code-session`; `provider.model_alias`: `balanced`; extraction worker at the pinned tier (`claude-opus-5`) |
| Build identity | `running_build`: `development`; editable install of repo checkout at commit `03ec1ca` (`runtime_provenance.source_commit` reported `null` — see Deviations) |
| Runtime mode and verdict | `runtime_mode`: `development`; readiness verdict: `development_override` |
| Development override reason | "semantic_guidance 1.1 dev-evidence acceptance run per docs/testing/semantic-integrity-acceptance.md, pre-receipt" |
| Semantic guidance version | `1.1` in request (7 rules), echoed in response envelope, stamped in artifact front matter |
| Quality | request `quality`: `balanced`; response `provider.model_alias`: `balanced` |
| Elapsed time | ~5m09s (request created 2026-07-29T18:46:39Z → phase-2 artifact written 18:51:48Z) |
| Extraction tokens | 61,516 (host-reported subagent tokens; 6 tool uses, 261s agent wall clock) |
| Interventions | none mid-run (no correction, retry, or manual edit of the response); staging deviations listed below |
| Output paths | `2026-07-26-lantern-nightly-load-failure-review-orchid-ledger-daily-merge-timeout.md`; `_signals/mtg-20260726-6c45c41d.jsonl` |
| Signal count | 14 |
| Meeting identity | `mtg-20260726-6c45c41d` (same as the 2026-07-26 dev run; artifact identity comparable across runs) |
| Grounding binding | request `transcript_grounding` matched `expected-review.json` exactly (3 speaker labels, 36 timestamps) |

Phase results: `provider-request` exit 0; preflight `validate-response` exit 0, `status: success`, `provider_response.status: valid`, readiness `development_override`; response snapshotted to `eval-response.json` (sha256 `d2a6414e…`) before phase 2; `ingest` exit 0 with markdown + signals artifacts; `doctor` clean with zero issues; `status` reports zero session handoffs (pair deleted by successful phase 2).

## Staging Deviations (development run only)

Recorded per the procedure's instruction to record any intervention. None touched the response mid-run.

1. **Runtime**: editable venv install of the repo checkout at `03ec1ca` instead of an approved frozen wheel; every CLI invocation carried `--development-override`. No `runtime pin` was performed — no receipt covers guidance 1.1.
2. **Workflow copies**: the acceptance root's `.claude/` copies were rendered directly from repo sources (skill template marker substituted with the venv executable; agent doc copied byte-identical, sha256 `890878d7…` matching the repo source), not installed via `scripts/install-approved-skill.py`, because the installer verifies against a receipt.
3. **Agent invocation**: the user-level installed `~/.claude/agents/meeting-ingest-session-provider.md` is receipt-managed and still carries guidance 1.0 rule 4, so it was left untouched. Extraction ran as a subagent instructed to follow the acceptance root's staged agent doc verbatim, at the pinned worker tier. The release-evidence run must instead use the receipt-installed agent definition as-is.
4. **Blind-review packaging error (mine)**: the transcript was copied to the blind reviewer's directory as `transcript.vtt` rather than under its own name. The reviewer consequently reported the artifact's `source_file: "session-provider-eval.vtt"` as invented. The artifact is correct and the finding is an artifact of my packaging, not of extraction. Recorded because the procedure requires it; future runs should preserve the fixture filename in the blind package.
5. **CLI observation**: `doctor` and `status` reject a subcommand-level `--development-override` and require it as a global pre-command flag, while `init`, `readiness`, `provider-request`, `validate-response`, and `ingest` accept it after the subcommand. The procedure's command block does not mention this. Cosmetic, but it cost a retry.

## Assertion Results

Evaluated against the `response` key of the preserved `eval-response.json` snapshot using the `evaluation` vocabulary declared in `expected-review.json`. The evaluator implements the declared JSONPath subset and operator semantics literally.

The evaluator was itself checked before its results were accepted, by mutating the snapshot and confirming it reports the failure:

- reintroducing the original 1.0 defect (a `Ro`-bearing signal at `confidence: high`) → `S10 blocking fail`;
- placing the loader split into an action item *with* an inline disposition → `S5 blocking fail` while `S6` still passes.

The second mutation is the exact failure mode identified during code review of the rule 4 wording, reproduced here as evidence that it was a live risk rather than a hypothetical one.

| ID | Severity | Result | Note |
|---|---|---|---|
| DG1 | blocking | pass | attendee raw labels set-equal to the three transcript labels |
| DG2 | blocking | pass | no qualified variant of `Villanueva, Rosa` |
| DG3 | blocking | pass | all evidence speakers verbatim members of grounding set |
| DG4 | blocking | pass | all evidence timestamps verbatim members of grounding set |
| DG5 | blocking | pass | no null evidence speaker |
| DG6 | blocking | pass | preflight exit 0, `status: success`, `provider_response.status: valid` (evaluated by CLI run; the script marks it `not_applicable` as `cli_exit_code` is not derivable from the snapshot) |
| S1 | blocking | pass | no AM/morning rendering of the 10:06 run |
| S2 | blocking | pass | nightly run represented |
| S3 | blocking | pass | no causal-closure language |
| S4 | blocking | pass | TL;DR keeps root cause open |
| S5 | blocking | pass | loader split absent from all 4 action items |
| S6 | blocking | pass | the one loader-split mention (`topics[2].summary`) carries rejected/parked context inline |
| S7 | blocking | pass | Beacon log pull recorded as an action |
| S8 | blocking | pass | alerting change recorded as an action, alerting-only scope preserved |
| S9 | blocking | pass | — |
| S10 | blocking | pass | all three `Ro`-bearing signals scored `confidence: low`, `inference_level: explicit` |
| S11 | advisory | pass | unresolved attribution survives as an open question |
| S12 | blocking | pass | — |
| S13 | blocking | pass | — |

**Tally: 18/18 blocking pass, 1/1 advisory pass.**

### The two 1.0 failures

Both are closed.

- **S10** failed twice on the frozen build under 1.0, scoring the signal reporting Dara's alias warning at `confidence: high`. Under 1.1 all three signals whose stakeholder name, summary, or evidence text carries `Ro` scored `low`, and all three kept `inference_level: explicit` — which is what S10's own description requires. Rule 5's revision is confirmed against the failure it was written for.
- **S6** failed once under 1.0, carrying the loader split in a stakeholder ask with its disposition only in a separate status field. Under 1.1 the loader split appears in four places (`topics[2]`, a decision, a risk, an open question) and each states inline that it was ruled infeasible and parked. No action item carries it, so S5 is unaffected.

## Review

### Independent blind review

Conducted by a reviewer that had not seen `expected-review.json` and did not run the case, reading only the transcript and the generated artifact.

The reviewer confirmed directly: no unsupported meridiem on the 10:06 run; the unconfirmed cause preserved as unconfirmed; the parked loader split never presented as agreed or live; the ambiguous `Ro` identity never resolved to a person; action scopes preserved; TL;DR consistent with the body. That is all five fixture defect patterns handled, independently of the assertion regexes.

Six findings were reported. Dispositions:

| # | Finding | Class | Disposition |
|---|---|---|---|
| 1 | `Date: 2026-07-26` not established by the transcript | procedure-external | Not a defect. The fixture carries no in-file date and the procedure mandates `--meeting-date`; front matter correctly marks `date_confidence: manual`, `date_source: override`. |
| 2 | `source_file` names `session-provider-eval.vtt` | staging artifact | Not a defect. Caused by my blind-review packaging (deviation 4). The artifact is correct. |
| 3 | "recurrence cannot be assessed until the lock-wait numbers come back" | **framing overreach** | **Quality finding.** Invents a dependency; the transcript has Femi committing to pull two weeks of lock waits, and nobody makes recurrence assessment contingent on it. |
| 4 | "Before close, the change taken here is the alerting-only work" | **framing overreach** | **Quality finding.** Asserts a temporal relationship (Friday falls before quarter close) the transcript never establishes. |
| 5 | Uncertainty applied to the present-consistency claim rather than to whether anything consumed the partial state before the retry | misattribution | **Quality finding.** Attaches a real uncertainty to the wrong claim. |
| 6 | Femi's lock-wait pull "would inform" whether the archival sweep overlaps the load window | **framing overreach** | **Quality finding.** Connects two items the transcript leaves unconnected — Dara's archival-overlap guess and Femi's data pull. |

### Human semantic review

**Completed 2026-07-29 by the owner.** The owner read the generated artifact against the transcript and judged it sound, raising no semantic defect beyond what the blind review had already reported.

### Reconciliation

The two reviews agree. The blind review's direct confirmation of all five fixture defect patterns matches the owner's judgment of the artifact, and neither review found a defect landing on a decision, an action item, identity handling, or the TL;DR. The four blind quality findings stand as recorded findings against this run with no bearing on the blocking result; findings 1 and 2 are dispositioned above as procedure-external and staging-caused respectively. No unresolved disagreement.

The owner further ruled that rule 6 remains unproven and accepted it as such, on the basis that 1.1 closes two twice-observed release-evidence failures and is therefore strictly better than 1.0. Releasing 1.1 was approved on that basis rather than holding for fixture assertions of the framing-restraint class.

## Finding: rule 6 did not do its job

Findings 3, 4, and 6 are precisely the class rule 6 was written to prevent — scope widening, a single occurrence generalized into a standing dependency, and a stated item turned into a broader relationship. They are the same class as the B2–B4 findings from the 2026-07-26 dev run that motivated rule 6 in the first place.

Rule 6 is the only rule in 1.1 with no assertion behind it. Code review flagged before this run that it would shape output but that nothing would detect a regression in it. This run is the evidence: the framing-restraint rule shipped, and framing overreach still occurred at roughly the prior rate, detectable only by the blind reviewer.

This does not fail the run. Every finding sits in secondary framing prose — none lands on a decision, an action item, identity handling, or the TL;DR, and none contradicts a blocking assertion. Per the procedure, findings are recorded against this run; correction means a fresh run, not an artifact edit.

It does mean two things worth deciding before the release flow:

1. Rule 6's wording is not yet earning its place, and a further wording revision would have to publish **1.2** rather than edit 1.1 — the published-version immutability the contract now states and the guard tests now enforce.
2. Rule 6 has no acceptance assertion. Until the fixture carries assertions of this class, "did the framing restraint work" is answerable only by blind human review, which is exactly the position rules 4 and 5 were in before S6 and S10 existed.

Neither is a blocker to releasing 1.1. Rules 4 and 5 close real, twice-observed release-evidence failures, and 1.1 is strictly better than 1.0 on the evidence. Rule 6 is unproven rather than harmful.

## Result

**PASS as development / non-release evidence — 18/18 blocking assertions, 1/1 advisory, both required reviews concordant.**

Four quality findings recorded, three of them rule-6-class. Milestone-proof semantic acceptance on the approved runtime is not achieved and is not claimed by this run; it requires repeating this procedure on the approved frozen build after the release flow.

## Remaining Coverage Gap

The identity-ambiguity rule is confirmed against the synthetic fixture only. The workstream's open action to find or record a real meeting transcript containing a genuine identity ambiguity still stands — the 2026-07-28 AdBook spot-check did not exercise it, and this fixture, being the one the rule was written against, is weaker confirmation than a transcript the rule has never seen.
