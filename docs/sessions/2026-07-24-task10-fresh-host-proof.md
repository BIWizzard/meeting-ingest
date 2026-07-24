# Task 10: Fresh Reference-Host Proof — 2026-07-24

One normal Claude Code request from the HTV consumer root processed one new
non-synthetic transcript through the approved runtime, with no source, PATH,
package, ledger, or cache inspection by the operator.

## The request

- Host: Claude Code, launched in `/Users/kmgdev/dev_projects/hearst-client/HTV-IQ-DataAnalytics`.
- Request: "There's a new transcript in the inbox. Please process".
- Source: `_inbox/Migration Planning Sync (4).vtt` (real working-session recording,
  Ken / Baba / Jean Francois, Fabric CI/CD and BLOB retention).
- The skill surfaced readiness and build identity on its own: verdict
  `ready_with_history_warnings`, build `meeting-ingest-0.1.0-g0d6cf58bb4d9-s06e33040b52a`,
  runtime mode `approved`, no development override.

## Workflow behavior

- The auto-inferred date (file mtime 2026-07-24) was low-confidence; the skill
  stopped, asked the operator, abandoned the initial request pair, and re-minted
  with the confirmed occurrence date 2026-07-23 — the by-design date gate, exercised.
- Extraction ran through the dedicated session-provider agent
  (`model_id: claude-opus-4-8[1m]`, the Decision 32 implementer tier), returned a
  provider-level envelope only, and passed `validate-response` preflight before
  phase 2.
- Phase 1, extraction, and phase 2 all completed under the same bound runtime and
  `claude-code-session-v1` workflow.

## Completion report contents (confirmed)

Artifact path, signal path and count, archive path, reconcile completion,
provider `session`, host `claude-code`, effective date 2026-07-23 with `manual`
confidence and `override` source, build ID, runtime mode `approved`, readiness
verdict, and the iQ capture ID.

## Output surfaces (verified on disk)

- Markdown artifact schema `1.1`:
  `2026-07-23-migration-planning-sync-ci-cd-automation-test-dev-deployment-troubleshooting-and.md`
  carries nested `runtime_provenance` (approved build, `approved_frozen`,
  null override), `runtime_provenance_sha256`
  `sha256:76db288d7f25fc711ddc0ce728540bb818e16f74e808d6f7647ff8186eabc8e0`, and
  producer `runtime_provenance_ledger_record_id` `lr-e4feb5cba48982ea3a5f189a8565c99c`.
- Ledger `2.0` latest record carries the identical provenance payload and
  fingerprint.
- All 6 signal `1.2` records in `_signals/mtg-20260723-66d3c878.jsonl` carry
  `runtime_provenance_ref` resolving to that exact producer record and fingerprint.
- Post-run readiness: `ready_with_history_warnings`, exit 0 — safe.

## Update exercise

- Second approved release `meeting-ingest-0.1.0-g9a8f1aca8e95-s06e33040b52a`
  (docs-only commit; identical source tree digest, distinct build ID) built
  twice-reproducibly and published. Channel `previous` retains release 1.
- With release 2 published but not installed: HTV `update-check` reported the
  newer channel build, readiness stayed `ready_with_history_warnings` with
  `update_available` advisory only. Nothing installed itself.
- With release 2 installed globally but HTV still pinned to release 1: readiness
  went `blocked` (exit 12, `runtime_pin_mismatch`, `runtime_receipt_mismatch`) —
  the same-version/different-build fail-closed row, demonstrated live.
- Disposable consumer bootstrap with release 2: receipt-verified skill/agent
  render → `runtime pin` in the uninitialized root → `init` under the pin →
  readiness `ready`, exit 0, zero findings.
- HTV then explicitly repinned to release 2: `ready_with_history_warnings`,
  no update pending. Rollback evidence retained: release 1's immutable channel
  directory plus the Task 9 editable-rollback procedure.

## Metrics

- Elapsed for the HTV request: 5m 55s wall clock.
- Interventions: 1 — the operator confirmed the meeting occurrence date at the
  low-confidence date gate (by design; not a failure).
- Failures: 0. No retries, no manual repair, no cache or ledger surgery.
- Human trust assessment (owner, 2026-07-24): trust with spot-checks — use the
  approved runtime for daily HTV meeting processing, with manual review of
  artifacts and signals for the next few meetings before relaxing.

## Claim boundary

This proof completes Track 1 (Approved Runtime and Pre-Meeting Readiness) and
the fresh-host proof within Track 3; the Semantic Integrity Guardrails quality
gate inside Track 3 remains not started. It does not claim semantic guardrails,
qualified history, or corpus adoption; the 177 history findings remain
classified warnings awaiting the separately approval-gated qualification track.
