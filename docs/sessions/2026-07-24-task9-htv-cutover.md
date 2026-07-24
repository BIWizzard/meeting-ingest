# Task 9: HTV Cutover Evidence — 2026-07-24

Approved Runtime Task 9 executed against the HTV consumer at
`/Users/kmgdev/dev_projects/hearst-client/HTV-IQ-DataAnalytics`. No meeting
corpus content was read or mutated; no real transcript was processed.

## Approved build

- Build ID: `meeting-ingest-0.1.0-g0d6cf58bb4d9-s06e33040b52a`
- Source commit: `0d6cf58bb4d948320a837e9659f512ad9fe7e4ca` (Task 8 merge; per-task
  T1–T3 reviews across Tasks 1–8 plus owner go on 2026-07-24)
- Source tree: `sha256:06e33040b52a34de1e2c89cd445b8553a8eb400510f4f64d43d3c6ebd502418f`
- Wheel: `sha256:4cd6406f7bc4a3de15b1c332d627b3667f345d6d14f60304bca84815398c44b6`
- Receipt: `sha256:e24139ac0025dfaf0d4cef2c957074639405caf5044e94c5c8f4d48df3fb4e7d`
- Built with `scripts/build-approved-runtime.py` (two isolated normalized builds,
  identical wheel digest, full suite green against the archived source).
- Published with `scripts/publish-approved-runtime.py`; release retained at
  `~/Library/Application Support/meeting-ingest/releases/meeting-ingest-0.1.0-g0d6cf58bb4d9-s06e33040b52a/`,
  channel manifest `~/Library/Application Support/meeting-ingest/channels/private-alpha.json`
  (`previous` is empty — this is the first approved release).

## Pre-cutover state (rollback evidence)

- Global tool: `/Users/kmgdev/.local/bin/meeting-ingest` →
  `/Users/kmgdev/.local/share/uv/tools/meeting-ingest/bin/meeting-ingest`,
  install mode `frozen_unapproved`, embedded build ID `development`,
  runtime mode `unverified` (hook-installed from the working tree before the
  Task 8 hook retirement).
- HTV `.venv` (`<consumer>/.venv`, Python 3.14.3): editable `meeting-ingest 0.1.0`
  via `__editable__.meeting_ingest-0.1.0.pth`, `direct_url.json`
  `{"url":"file:///Users/kmgdev/dev_projects/meeting-ingest","dir_info":{"editable":true}}`,
  console script `.venv/bin/meeting-ingest`, dist-info `meeting_ingest-0.1.0.dist-info`.
- No prior approved wheel/receipt exists; rollback target is the editable
  development install.

### Rollback procedure (explicit, development-marked)

1. `uv pip install --python <consumer>/.venv/bin/python -e /Users/kmgdev/dev_projects/meeting-ingest`
2. `uv tool install --reinstall /Users/kmgdev/dev_projects/meeting-ingest` (restores the
   pre-cutover global development tool) — or leave the approved global tool in place.
3. Remove `_local/project-context/meetings/meeting-ingest-runtime.toml` from the
   consumer root only if abandoning the approved pin entirely.
4. All rollback runs are development runs: readiness will block without
   `--development-override <reason>`, and all outputs are development-marked.

## Cutover actions

1. Installed the published frozen wheel: `uv tool install --reinstall <release wheel>`.
2. Verified identity before pinning: embedded build ID matched the receipt,
   `RECORD` integrity `valid`.
3. Rendered workflow artifacts through `scripts/install-approved-skill.py`
   (receipt-verified template hash, single-marker substitution with
   `/Users/kmgdev/.local/bin/meeting-ingest`, agent copied byte-identical) into the
   consumer scope `.claude/skills/` and `.claude/agents/`; rendered skill
   `sha256:b62e1b9df4854691ace0a252b0ea995756d9d9d5e6455b619b640a63c55fb560`,
   agent `sha256:f8da6f1f37e713f6490810e56ecbc75e083e88927b6eb1f9f910e6ceecbc3b3d`.
   The same render was installed to the user-global `~/.claude` copies.
4. Pinned HTV: `runtime pin --receipt <release receipt> --root <consumer>
   --approved-executable /Users/kmgdev/.local/bin/meeting-ingest` — success, exit 0.
   Pin-time verification reconstructed the portable template from the installed
   skill and matched the receipt hashes.
5. Uninstalled only `meeting-ingest` from the HTV `.venv` interpreter
   (`uv pip uninstall`); the virtual environment was not deleted or recreated.

## Post-cutover verification

- `.pth`, dist-info, and console script are gone from the HTV `.venv`;
  `.venv/bin/python -c "import meeting_ingest"` fails with `ModuleNotFoundError` —
  no activated path imports the working tree.
- `runtime inspect --root <consumer>`: install `approved_frozen`, runtime
  `approved`, `RECORD` valid, receipt/pin/workflow matches all true, findings `[]`.
- `readiness --root <consumer> --host claude-code`: verdict
  `ready_with_history_warnings`, exit 0, running build == approved build;
  177 findings, all `history`/`warning`
  (`corpus_adoption_pending`, `historical_date_low_confidence`).
- `status --json` from the consumer root: success through the pinned executable.
- `doctor --json`: `issues_found`, exit 1, all 177 issues classified —
  `legacy_ledger_record` 81, `legacy_signal_format` 81,
  `low_confidence_meeting_date` 12, `stale_provider_response` 1,
  `playbook_state_missing` 1, `historical_artifact_path_drift` 1.
  Nothing was silently repaired.

## Boundary respected

No real transcript was processed during the cutover. Task 10 (fresh
reference-host proof with one new non-synthetic transcript) remains separate.
