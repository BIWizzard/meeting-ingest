# Semantic Guidance 1.1 — Slice Release

Date: 2026-07-29 (release executed 2026-07-29T19:06 UTC)
Release flow: README "Release Flow", executed end to end with owner approval.
Acceptance procedure: `docs/testing/semantic-integrity-acceptance.md`.
Development-evidence predecessor: `docs/sessions/2026-07-29-guidance-1_1-semantic-acceptance-dev-run.md` (PASS, 18/18 blocking, 1/1 advisory, both required reviews concordant).

The slice this release carries is the `semantic_guidance` 1.1 revision answering the contract finding from the two failed release-evidence runs on `g51ff17173bea` (`docs/sessions/2026-07-26-task7-release-and-acceptance.md`).

## Release

Owner approved exact commit `3695fc350c77b1e778962cf23e6cfc8801392f9a`.

| Step | Result |
|---|---|
| Build | `meeting-ingest-0.2.0-g3695fc350c77-s61e1660c5dc8`, twice-reproducible, receipt sha256 `312ce10c…`, wheel sha256 `3b17dd86…`, approved-by owner at 2026-07-29T19:06:12Z |
| Publish | private-alpha channel advanced at 2026-07-29T19:06:27Z; four prior builds retained for rollback, the most recent being `meeting-ingest-0.1.0-g51ff17173bea-sf9e0835ad500` |
| Executable | frozen wheel installed; `/Users/kmgdev/.local/bin/meeting-ingest` moved `meeting-ingest==0.1.0` → `0.2.0` |
| Workflow installs | receipt-verified installer to user-level `~/.claude/` and to the HTV consumer at `/Users/kmgdev/dev_projects/hearst-client/HTV-IQ-DataAnalytics/.claude/`; rendered skill sha256 `7e2c1ae4…` identical at both destinations; agent sha256 `890878d7…` byte-identical to the repo source |
| HTV repin | pin success; readiness `ready_with_history_warnings`, `runtime_mode: approved`, `semantic_version: 0.2.0`, running build matches the pin |
| Chain verification | `runtime inspect` from HTV: `install mode: approved_frozen`, `workflow.match: true`, `receipt.match: true`, `pin.match: true`; all 8 pin comparisons and all 8 receipt comparisons match |

This is the first time the package version has moved during the private alpha; prior releases were distinguished by build id alone.

Readiness findings are the standing legacy-corpus set only — `corpus_adoption_pending`, `historical_date_low_confidence`, `legacy_provenance_missing`, `legacy_signal_link_missing`, `optional_playbook_output_missing`. Unchanged in kind from the previous release; the OB-002-1 posture is intact and no corpus was adopted, corrected, or mutated by this release.

## Release-Evidence Acceptance Attempt 1 — 18/18 blocking, but not accepted as milestone proof

Run executed 2026-07-29T19:08–19:13 UTC on build `meeting-ingest-0.2.0-g3695fc350c77-s61e1660c5dc8` in a freshly pinned temporary consumer project.

The runtime conditions were clean release-evidence conditions. The extraction conditions were not, and that is why this attempt is recorded rather than claimed.

### Provenance

| Field | Value |
|---|---|
| Host and host version | Claude Code 2.1.220 (reference host) |
| Model | `provider.model_id`: `claude-code-session`; `provider.model_alias`: `balanced` |
| Build identity | `meeting-ingest-0.2.0-g3695fc350c77-s61e1660c5dc8`, `runtime_mode: approved`, `semantic_version: 0.2.0` |
| Runtime mode and verdict | readiness `ready`, zero findings, **no development override anywhere** |
| Semantic guidance version | `1.1` in request (7 rules), echoed in response, stamped in artifact front matter |
| Quality | request `quality`: `balanced`; response `model_alias`: `balanced` |
| Elapsed time | ~3m57s (request created 19:08:45Z → phase-2 artifact written 19:12:42Z) |
| Extraction tokens | 54,729 (host-reported subagent tokens; 4 tool uses, 206s) |
| Interventions | none mid-run |
| Output paths | `2026-07-26-lantern-nightly-load-failure-review-orchid-ledger-daily-merge-abort.md`; `_signals/mtg-20260726-6c45c41d.jsonl` |
| Signal count | 11 |
| Grounding binding | request `transcript_grounding` matched `expected-review.json` exactly |

Phase results: `provider-request` exit 0; preflight `validate-response` exit 0, `status: success`, `provider_response.status: valid`, readiness `ready_with_history_warnings`; response snapshotted (sha256 `626df8a9…`) before phase 2; `ingest` exit 0; `doctor` clean with zero issues; `status` zero session handoffs.

**Assertion tally: 18/18 blocking pass, 1/1 advisory pass.** Evaluated with the same evaluator used for the development-evidence run, which was verified to report failures by deliberate mutation.

### Blocking deviation — the agent definition the run actually used was stale

The receipt-verified installer wrote the guidance 1.1 agent doc to `~/.claude/agents/meeting-ingest-session-provider.md` at 15:07 local. Extraction ran at approximately 15:09. The extraction agent nonetheless reported that its own embedded instructions carried guidance 1.0's six rules, and named the differences precisely: rule 4 not requiring inline disposition, rule 5 not extending to a signal reporting the ambiguity, and no rule 6 at all.

The on-disk file was verified to carry only the 1.1 rule text and none of the 1.0 rule 4 text. The stale copy was therefore the host's, cached when the session started before the install, not the installed artifact.

The procedure requires that a release-evidence run "use the receipt-installed agent definition as-is." The file on disk was receipt-installed; the definition that shaped extraction was not. That is a deviation from the condition this run exists to establish, and it is not curable after the fact.

One thing it does demonstrate, incidentally: the agent obeyed the request-borne 1.1 rules over its own stale prompt and echoed `1.1`, which is exactly the behavior the "obey the rules in the request rather than a remembered prompt revision" clause exists to produce. That clause is now evidenced under real drift. It does not substitute for a clean run.

### Independent blind review

Reviewer had not seen `expected-review.json` and did not run the case. Four findings.

| # | Finding | Class | Disposition |
|---|---|---|---|
| 1 | `date: 2026-07-26` not established by the transcript | procedure-external | Not a defect. The procedure mandates `--meeting-date`; front matter marks `date_confidence: manual`, `date_source: override`. |
| 2 | T1 says the 10:06 pass was the one "which **Femi** identified as the last run of the night" | **factual misattribution** | **Real defect.** The transcript has Marchetti, Dara saying that line verbatim at 00:00:22. T1's own two evidence citations are both Dara. The prose contradicts the evidence in its own row. Verified directly against the transcript. |
| 3 | TL;DR presents both Femi tasks as "for Thursday's sync" | framing overreach | **Quality finding.** The lock-wait numbers are explicitly for Thursday's sync; for the extract check Femi says only "Same Thursday deadline." Rule 6 class. |
| 4 | Q4 owner reads "Rosa Villanueva – revisit after close only if timeouts continue" | mild overstatement | **Quality finding, partially mitigated.** Rosa did state the revisit condition, and the same row preserves "nobody is starting that work now." It still renders a conditional as an owned next step. |

### Human semantic review

**Not performed for this attempt.** Deferred, because the deviation above means this attempt should not be the one submitted for milestone proof.

### Why finding 2 matters beyond this run

Finding 2 is a plain factual error — a statement credited to the wrong speaker — and it passed all 18 blocking assertions. No assertion catches it: `DG3` and `DG4` verify that evidence speakers and timestamps are verbatim members of the grounding set, not that prose attribution agrees with the evidence cited alongside it.

The fixture therefore has a blind spot for attribution correctness in narrative fields, distinct from the framing-restraint blind spot already recorded for rule 6. A candidate assertion class follows directly: where a narrative field names a speaker as the source of a statement, that name should agree with the evidence rows cited for the same item.

This is a fixture gap, not a guidance defect, and correcting it is fixture work rather than a guidance revision.

### Verdict

**Not accepted as milestone proof.** 18/18 blocking passed and the runtime conditions were clean, but the extraction ran against a stale agent definition, which is the specific condition a release-evidence run exists to establish. A second attempt in a fresh host session, where the host loads the installed 1.1 agent doc, is required before milestone proof can be claimed.

Recorded findings carry forward regardless: finding 2 as an extraction defect against this run, findings 3 and 4 as quality findings, and the attribution-assertion gap as fixture work.

## Claim Boundary

Guidance 1.1 is released, installed, and pinned. That is a distribution fact and nothing more.

Milestone-proof semantic acceptance on the approved runtime is **not achieved** by this release. The only acceptance evidence guidance 1.1 has is the development-evidence predecessor above, which ran on an editable checkout under `--development-override`. Milestone proof requires the release-evidence run on this frozen build, which has not happened. Product-truth language in `README.md`, `docs/product-status.md`, and `docs/implementation-plan.md` is written to that boundary.
