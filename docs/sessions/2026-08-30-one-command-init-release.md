# 2026-08-30 — 0.3.0 Release: One-Command Consumer Bootstrap

## Ruling implemented

The 2026-08-13 owner ruling (cap_20260813T171046Z_56618c59): `meeting-ingest init` in a virgin
project must do the whole job — install the workflow artifacts, select and pin the latest
published approved receipt, scaffold the meetings root — with no exposed plumbing. The fix
satisfies the fail-closed approved-runtime chain automatically; it does not bypass or weaken it.

## Build

- Commit: `bcfe8e53272167d460f9cf64679230a0efea53e2` (reviewed; suite 494 passed)
- Build: `meeting-ingest-0.3.0-gbcfe8e532721-s30753a330500`
- Receipt: `sha256:67607f7bfe80a72f3f3830b6c210268e4ca92c9c25d8bfe4ad7a415b00e7ee60`
- Wheel: `sha256:cac083748016b7340b6f5377618bfcee1ae09ad9690dff022aea97148b8055d7`
- Published to `private-alpha` (previous latest `meeting-ingest-0.2.1-g0738520ee5d0-s0450cee69b18` retained for rollback)

## What shipped

- Virgin-project bootstrap in `init`: channel-latest receipt selection, running-install
  verification (RECORD-derived console-script identity, published wheel required and
  hash-checked, receipt digest constant across stages), receipt-verified project-level
  workflow installs, exclusive pin creation, scaffold, full readiness gate. An existing pin
  is never touched; the development override stays scaffold-only.
- Workflow templates relocated into the package (`meeting_ingest/workflow_templates/`,
  bytes unchanged) and shipped in the wheel; build verification asserts their presence.
- Readiness workflow resolution now mirrors the host: a project-level `.claude` copy
  shadows the user-level install, per file.
- Human-path CLI failures render code, message, remediation, and blocking findings
  (previously a bare `failed: exit N`); with no pin present readiness no longer fabricates
  `workflow_hash_mismatch`.

## Verification

Two independent reviews (one Anthropic-side, one external) plus an orchestrated read of the
supply-chain hunks; all accepted findings closed in a single fix pass, deferred hardening
recorded as issue #27. Templates byte-identical to 0.2.1, so no rendered artifact changed
and no `~/.claude` re-render or commit was needed (the 0.2.1 lesson holds).

Release smoke on the frozen install:

- Virgin project: `meeting-ingest init` → `Ready`, pin `meeting-ingest-0.3.0-gbcfe8e532721-s30753a330500`,
  both artifacts installed project-level, meetings root scaffolded. One command, zero flags.
- HTV repinned: `Ready With History Warnings` (the standing 177 history findings).
- Trace3 repinned: `Ready`.
