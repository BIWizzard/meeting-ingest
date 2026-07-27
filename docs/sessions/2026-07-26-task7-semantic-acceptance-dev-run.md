# Task 7 — Semantic Integrity Acceptance Run (Development Evidence)

Date: 2026-07-26 (run executed 2026-07-27T01:07–01:11 UTC)
Procedure: `docs/testing/semantic-integrity-acceptance.md`
Fixture: `tests/fixtures/semantic-integrity/session-provider-eval.vtt` (synthetic)
Assertions: `tests/fixtures/semantic-integrity/expected-review.json` (`semantic_guidance_version` 1.0)

## Evidence Class

**Development / non-release evidence.** This run used an editable checkout under `--development-override` and predates the end-of-slice receipt. It was staged deliberately per the owner's ruling (acceptance first, as development evidence, before cutting the new receipt). It is not milestone proof; the release-evidence run repeats this procedure on the approved frozen build after the Task 7 release flow.

## Provenance

| Field | Value |
|---|---|
| Host and host version | Claude Code 2.1.220 (reference host) |
| Model | `provider.model_id`: `claude-opus-5`; agent doc pin: `claude-opus-5` |
| Build identity | `running_build`: `development`; editable install of repo checkout at commit `737f6d1` (clean tree at run time; `runtime_provenance.source_commit` reported `null` — see Deviations) |
| Runtime mode and verdict | `runtime_mode`: `development`; readiness verdict: `development_override` |
| Development override reason | "Task 7 dev-evidence acceptance run per docs/testing/semantic-integrity-acceptance.md, pre-receipt" |
| Semantic guidance version | `1.0` in request, echoed in response envelope |
| Quality | request `quality`: `balanced`; response `provider.model_alias`: `balanced` |
| Elapsed time | ~4m39s (request created 2026-07-27T01:07:03Z → phase-2 artifact written 01:11:42Z) |
| Extraction tokens | 58,045 (host-reported subagent tokens; 6 tool uses, 212s agent wall clock) |
| Interventions | none mid-run (no correction, retry, or manual edit of the response); staging deviations listed below |
| Output paths | `2026-07-26-lantern-nightly-load-failure-review-orchid-ledger-daily-merge-abort.md`; `_signals/mtg-20260726-6c45c41d.jsonl` |
| Signal count | 15 |
| Grounding binding | request `transcript_grounding` matched `expected-review.json` exactly (3 speaker labels, 36 timestamps) |

Phase results: `provider-request` exit 0 ready; preflight `validate-response` exit 0, `status: success`, `provider_response.status: valid`, readiness `development_override`; response snapshotted to `eval-response.json` before phase 2; `ingest` exit 0 with markdown + signals artifacts ready; `doctor` clean; `status` shows zero session handoffs (pair deleted by successful phase 2).

## Staging Deviations (development run only)

Recorded per the procedure's instruction to record any intervention. None of these touched the response mid-run.

1. **Runtime**: editable venv install of the repo checkout (commit `737f6d1`) instead of the approved frozen wheel; every CLI invocation carried `--development-override`. No `runtime pin` was performed (no receipt covers this build).
2. **Workflow copies**: the acceptance root's `.claude/` copies were rendered directly from repo sources (skill template marker substituted with the venv executable; agent doc copied byte-identical, sha256 `717d1e74…` matching the repo source), not installed via `scripts/install-approved-skill.py`, because the installer verifies against a receipt and no receipt covers the Task 5 instruction sources yet.
3. **Agent invocation**: the user-level installed `~/.claude/agents/meeting-ingest-session-provider.md` is pre-Task-5 (release pending), so the extraction agent was a general-purpose subagent instructed to read and follow the repo's new agent doc verbatim, at the pinned worker tier (`claude-opus-5`). The release-evidence run must instead use the receipt-installed agent definition as-is.
4. **Observation**: `runtime_provenance.source_commit` and `source_tree_sha256` were `null` on both `init` and `runtime inspect` despite a clean editable checkout with git available. Worth a look alongside the already-captured pin/inspect `.claude` resolution asymmetry.

## Assertion Results

Evaluated against the `response` key of the preserved `eval-response.json` snapshot using the `evaluation` vocabulary declared in `expected-review.json`. Evaluator implemented the declared JSONPath subset and operators exactly.

| ID | Severity | Result | Note |
|---|---|---|---|
| DG1 | blocking | pass | attendee raw labels set-equal to the three transcript labels |
| DG2 | blocking | pass | no qualified variant of `Villanueva, Rosa` |
| DG3 | blocking | pass | 15/15 evidence speakers verbatim members of grounding set |
| DG4 | blocking | pass | 15/15 evidence timestamps verbatim members of grounding set |
| DG5 | blocking | pass | no null evidence speaker |
| DG6 | blocking | pass | preflight exit 0, `status: success`, `provider_response.status: valid` |
| S1 | blocking | pass | no AM/morning rendering of the 10:06 run (368 string leaves scanned) |
| S2 | blocking | pass | nightly run represented ("the 10:06 pass", "last automated run of the night") |
| S3 | blocking | pass | no causal-closure language anywhere |
| S4 | blocking | pass | TL;DR keeps root cause open ("still open", hypothesis wording) |
| S5 | blocking | pass | loader split absent from all 4 actions |
| S6 | blocking | pass | the one loader-split mention carries rejected/parked context |
| S7 | blocking | pass | Beacon log pull recorded as action A1 |
| S8 | blocking | pass | alerting change recorded as action A2, alerting-only scope preserved |
| S9 | blocking | pass | no attendee display name claims `Ro` |
| S10 | blocking | pass | the one Ro-bearing signal is `confidence: low` |
| S11 | advisory | **fail** | see disposition below |
| S12 | blocking | pass | TL;DR has no causal closure while root cause stays open in details |
| S13 | blocking | pass | TL;DR mentions the split only as rejected/parked |

**Blocking: 18/18 pass. Run result: PASS (development evidence).**

### S11 advisory disposition (owner)

S11 prefers that the unresolved `Ro` attribution survive as an open question, matched by `\bRo\b`, `\bwho (?:filed|posted|reported)\b`, or `\battribution\b`. The payload's Q4 reads: *"Who actually filed the prior channel report of a stuck merge on a different table? The nickname used is ambiguous and has referred to more than one person."* The preferred handling is present; the regex floor missed it because "actually" sits between "who" and "filed". Finding class: fixture pattern gap, not an extraction defect.

Owner disposition (2026-07-26): confirmed — fixture pattern gap, not an extraction defect. The preferred handling is present in Q4; S11 stands recorded as an advisory fail for this run and the pattern set is widened for future runs (see fixture follow-up below).

Fixture follow-up applied post-disposition: S11's second pattern widened to `\bwho\b[^.?]{0,20}\b(?:filed|posted|reported)\b` so an intervening adverb no longer defeats the match. Verified against this run's preserved payload: the widened pattern matches Q4. This run's recorded S11 result is unchanged.

## Workflow Copy Verification

Receipt-chain verification is **not applicable** to this development run (no receipt covers these copies). Recorded instead:

- Acceptance-root agent doc sha256 `717d1e74f0d28b2070a91dc7027af1bd70157f6def8d926a3763b960fdf41297`, byte-identical to `docs/claude-agents/meeting-ingest-session-provider.md` at `737f6d1`.
- Acceptance-root skill = repo template with the approved-executable marker substituted (marker count verified 1 before substitution).
- Codex pair: `cmp` clean — `docs/codex-skills/meeting-ingest/SKILL.md` and `~/.codex/skills/meeting-ingest/SKILL.md` byte-identical.

The release-evidence run must verify the full receipt chain (`readiness` without `workflow_hash_mismatch`, `runtime inspect` pin and receipt comparisons all matching).

## Reviews

1. **Human semantic review (owner)**: completed 2026-07-26. The owner read the generated artifact against the transcript and judged the five patterns directly: all five handled correctly (contractor qualifiers verbatim, 10:06 never rendered as morning, root cause kept unconfirmed including the TL;DR, loader split parked and never an action, `Ro` never resolved). The owner concurred with the staged dispositions: S11 as fixture pattern gap, B1 as procedure-external, B2–B4 as quality findings in secondary framing fields feeding a future `semantic_guidance` revision, B5 benign.
2. **Independent blind review**: performed by the codex-workhorse with access only to the transcript and the generated artifact (never `expected-review.json`), per the blind-review requirement. Completed 2026-07-27T01:19Z.

### Blind review findings

Overall blind verdict (reviewer's words): "the artifact is highly faithful on the meeting's substantive content, decisions, causes, uncertainty, action owners, and identity ambiguity. Its meaningful defects are one unsupported calendar date and several risk/context statements that broaden limited transcript evidence into stronger operational conclusions." The reviewer independently confirmed: attendee labels and contractor qualifiers grounded, 10:06 kept without AM/PM, archival-sweep theory kept uncertain, loader split recorded as parked not adopted, mitigation scoped to alerting only.

| # | Blind severity | Artifact text at issue | Origin traced to | Proposed disposition (owner to confirm) |
|---|---|---|---|---|
| B1 | invents | `Date | 2026-07-26` | procedure, not provider: `--meeting-date` is the explicit override the acceptance doc mandates for this dateless fixture, and front matter discloses the manual override | not a defect; expected behavior |
| B2 | overstates | "owns the Thursday investigation into Beacon lock waits, the reporting extract, and the authorship of the prior channel report" — Thursday deadline covers the first two, not the authorship check | provider payload: `attendees[2].role_context` | quality finding: scope-broadening in a secondary framing field; payload `action_items` themselves carry no wrong deadline |
| B3 | overstates | "Recovery from a late-night failure depends on someone noticing and hand-running the job" — transcript establishes no second automated attempt and one manual retry, not a general dependency | provider payload: `dependencies_risks[1].impact` | quality finding: generalization in risk impact framing |
| B4 | overstates | "A potentially related prior occurrence cannot be corroborated or followed up until authorship is confirmed" — transcript only bars attribution before checking | provider payload: `dependencies_risks[4].impact` | quality finding: broadens a naming constraint into a follow-up blocker |
| B5 | faithful-but-notable | `Type | incident review` inferred, never stated | provider classification | reasonable inference; no distortion |

Classification: B2–B4 are provider semantic-judgment findings confined to secondary framing fields (`role_context`, risk `impact`); no blind finding lands on decisions, action items, identity handling, or the TL;DR, and none contradicts a blocking assertion result. Per the procedure, findings are recorded against this run; any correction is a fresh run, not an artifact edit. B2–B4 are candidate inputs to a future `semantic_guidance` revision (framing-field restraint), not blockers to this development-evidence result.

Reconciliation (2026-07-26): the two reviews agree. The blind review's substantive confirmation matches the owner's direct judgment of the five patterns; the blind overstatement findings (B2–B4) are accepted as recorded quality findings with no bearing on the blocking result; B1 is procedure-external; S11 is a fixture gap now fixed forward. No unresolved disagreement. **Final result: PASS as development/non-release evidence — 18/18 blocking assertions, both reviews concordant.**

## Cleanup

Acceptance root retained until both reviews and this record are final (removing it destroys the preserved response snapshot). Snapshot, generated artifact, and signals also copied to the session scratchpad for review. Root removal recorded here when done.
