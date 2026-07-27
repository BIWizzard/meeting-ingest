# Task 7 — Slice Release And Release-Evidence Acceptance Runs

Date: 2026-07-26 (executed 2026-07-27T02:15–onward UTC)
Release flow: README "Release Flow", executed end to end with owner approval.
Acceptance procedure: `docs/testing/semantic-integrity-acceptance.md`.
Development-evidence predecessor: `docs/sessions/2026-07-26-task7-semantic-acceptance-dev-run.md` (PASS, 18/18 blocking).

## Release

Owner approved exact commit `51ff17173bea89beb7fefc8c927d587c7092a994` ("docs: record semantic correction boundary and proof").

| Step | Result |
|---|---|
| Build | `meeting-ingest-0.1.0-g51ff17173bea-sf9e0835ad500`, twice-reproducible, receipt sha256 `977385a3…`, wheel sha256 `2efdc8a4…`, approved-by owner at 2026-07-27T02:15:13Z |
| Publish | private-alpha channel advanced; previous `gb37a12a0502e` retained for rollback |
| Executable | `uv tool install --reinstall` of the frozen wheel; `/Users/kmgdev/.local/bin/meeting-ingest` now runs the new build |
| Workflow installs | receipt-verified installer to user-level `~/.claude/` and HTV project-level `.claude/`; rendered skill sha `4c28e0df…` identical at both destinations; agent sha `717d1e74…` byte-identical to source |
| HTV repin | pin success; readiness `ready_with_history_warnings`, `runtime_mode: approved`, running build matches pin; findings are the standing legacy-corpus set (corpus_adoption_pending, historical_date_low_confidence, legacy provenance/signal links) — unchanged in kind, OB-002-1 posture intact |
| Chain verification | `runtime inspect` from HTV: `workflow.match: true`; all 8 pin comparisons and all 8 receipt comparisons match |

## Release-Evidence Acceptance Run 1 — FAIL (recorded)

Fresh temporary consumer project; receipt-verified install; pinned; `init`; session provider enabled; readiness `ready` on `runtime_mode: approved` (no development override anywhere). Request bound `semantic_guidance_version` `1.0` with the grounding index matching `expected-review.json`.

| Field | Value |
|---|---|
| Host | Claude Code 2.1.220 (reference host) |
| Model | `provider.model_id`: `claude-opus-5`; `model_alias`: `balanced` |
| Build | `meeting-ingest-0.1.0-g51ff17173bea-sf9e0835ad500`, `runtime_mode: approved`, readiness `ready` |
| Extraction | installed `meeting-ingest-session-provider` agent, as the skill dispatches it; 50,353 tokens, 155s; no interventions |
| Elapsed | request 2026-07-27T02:16:52Z → phase-2 complete ~02:2xZ |
| Phases | preflight exit 0 valid; snapshot taken; ingest exit 0 (markdown + 12 signals); doctor clean; zero lingering handoffs |
| Assertions | 17/18 blocking pass; S11 advisory pass (widened pattern) |

**Blocking failure — S10** (guidance rule 5, ambiguous nickname): the signal
*"Dara warned that the alias 'Ro' has been used for two different people in the channel and that attribution should wait"* was scored `confidence: high`; S10 requires every Ro-bearing identity signal to keep the identity unresolved at `low` confidence. Offending value: `{"confidence": "high"}` on that signal.

Classification: semantic-judgment variance under the bound guidance, not an engine defect — all deterministic gates passed, and the run otherwise handled the five patterns correctly (the extraction even placed the ambiguity in a fourth attendee entry with `display_name: null` and empty `raw_labels`, which the gates accept and DG1's set-equality tolerates). The development run scored the equivalent signal `low` with explicit reasoning; run 1 read "confidence in the warning itself" rather than "confidence in the identity", which is the misreading rule 5 exists to prevent.

Disposition per procedure: one blocking failure fails the run; correction is a fresh run, not an edit. Run 1's artifact copy is preserved in the session scratchpad for comparison; root removed after recording.

Guidance follow-up candidate (for a future `semantic_guidance` 1.1, alongside the B2–B4 framing-restraint findings from the dev run): rule 5 should state explicitly that a signal *about* an identity ambiguity also carries the unresolved identity and stays low-confidence, even when the warning itself is explicit transcript speech.

## Release-Evidence Acceptance Run 2 — FAIL (recorded)

Fresh temporary consumer project, identical procedure to run 1: receipt-verified install, pin, readiness `ready` on `runtime_mode: approved`, request bound `semantic_guidance_version` `1.0` with the matching grounding index, extraction by the installed `meeting-ingest-session-provider` agent (52,628 tokens, 180s, no interventions; `claude-opus-5`, `model_alias: balanced`, generated 2026-07-27T02:22:20Z). Preflight valid, phase 2 clean (markdown + 9 signals), doctor clean, zero lingering handoffs.

**Assertions: 16/18 blocking pass; 2 blocking failures; S11 advisory pass.**

- **S10 (guidance rule 5), second consecutive failure**: the signal reporting Dara's alias warning (activated through `evidence.text` quoting the `Ro` line) scored `confidence: high`. Offending value: `{"confidence": "high"}`.
- **S6 (guidance rule 3)**: the stakeholder ask *"Split the loader so the extract is staged as its own job and the merge runs as a second job with its own retry policy."* carries the loader split with no rejected/parked context in the ask text itself; the disposition lives in a separate status field, which the assertion — deliberately — does not read.

## Finding: `semantic_guidance` 1.0 Contract Gap

Two consecutive release-evidence failures with an overlapping failure mode are a pattern, not sampling noise, and rerunning until a pass would be evidence shopping. Classification:

- The engine and the release are not indicted: DG1–DG6 passed on the frozen build in both runs, the receipt chain verified end to end, and HTV readiness is clean on the new pin. The deterministic tier is proven on the released build.
- The semantic tier exposed a wording gap in `semantic_guidance` 1.0 as bound (`src/meeting_ingest/extraction_guidance.py`):
  - Rule 5 says alias evidence "stays unresolved and receives low confidence" — it addresses identity *resolution*, and does not state that a signal *about* the ambiguity also carries the unresolved identity and must stay low-confidence even though the warning itself is explicit transcript speech. Both failed runs read it the defensible other way; the development run happened to read it strictly.
  - Rule 3/4 do not state that wherever a rejected proposal's text appears (ask, topic, risk, question fields), the rejected/parked disposition must be carried inline in that same text.
- Candidate `semantic_guidance` 1.1 revisions: make both explicit. A guidance revision is an engine change: new commit, new receipt, new release, fresh release-evidence acceptance.

The development-evidence run (18/18 blocking, concordant reviews) remains the slice's development proof. Milestone-proof acceptance on the approved runtime is **not achieved** by this release; product-truth language already limits claims accordingly and needs no retraction.

Run artifacts from both failed runs are preserved in the session scratchpad for comparison; both acceptance roots removed after recording. Owner decision on next step recorded below.

## Owner Decision

2026-07-26: both failed runs are accepted as a recorded `semantic_guidance` 1.0 contract finding. No third run on the current build (a pass after 2/2 failures would be evidence shopping) and no fixture loosening. Next slice: `semantic_guidance` 1.1 — make rule 5 explicit that a signal about an identity ambiguity carries the unresolved identity and stays low-confidence, require inline rejected/parked disposition wherever a rejected proposal's text appears in ask/topic/risk/question fields, and fold in the development run's B2–B4 framing-restraint findings. The revision is an engine change and follows the full path: commit, receipt, release, fresh release-evidence acceptance.
