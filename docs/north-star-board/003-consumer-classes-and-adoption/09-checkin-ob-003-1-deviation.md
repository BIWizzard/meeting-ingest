# 003 Addendum 09 — Check-in: OB-003-1 contract deviation halted in verification

- Date: 2026-08-30
- Obligation: OB-003-1 — release/update command pair (issue #16)
- Mode: check-in (orchestrator only; contract-deviation smell mid-delegation, per the
  orchestrate procedure). The obligation's own trigger — the next release after
  ratification ships — has not fired; this addendum records a deviation caught before it.

## Clause held to

Issue #16, quoted in the delegation brief and ratified as the OB-003-1 relief under
record 003 P1: "a single maintainer command wrapping build → receipt → publish →
install → repin, and a single consumer command wrapping fetch → verify → install →
repin. Both drive the existing verified release-flow steps; neither bypasses the
fail-closed approved-runtime chain."

## Deviation, with evidence

The first delegated implementation of `meeting-ingest update` verifies the
post-install runtime against the in-memory build identity of the already-running
process (`BuildIdentity.embedded()`, src/meeting_ingest/runtime.py). A consumer whose
machine-global tool is still the previous build therefore installs the new wheel and
then always fails its own verification once, requiring a second invocation. That
contradicts the single-consumer-command clause for exactly the consumer the command
exists for. Found independently by both T2 review lenses (external Codex review;
Anthropic-side implementer-model review, which confirmed it empirically with a
first-consumer probe: `runtime_build_mismatch` on every first run from a stale tool).

Both reviews also confirm the fail-closed properties held throughout: the old pin
survives, no unverified byte is installed, and the rerun converges. The deviation is
a broken product promise, not a broken safety chain.

## Disposition

Uncontested — the clause needs no interpretation and no amendment is proposed; the
fix restores conformance. Orchestrator ruling on the open design point (where the
update's second half executes): when the running build already matches the target
receipt, the update completes in-process; otherwise, after the hash-verified wheel
install, the command verifies the newly installed console script out of process and
delegates the remaining verify → artifacts → repin → readiness steps to that new
console script, relaying its summary. The second half must run under the new build
regardless, because workflow artifacts are rendered from the running package's
templates and only the new build carries the receipt's own templates.

## Outcome

Unit halted and re-briefed at the same tier with the consolidated review findings;
OB-003-1 remains open. Escalation not warranted. Conformance will be re-verified at
T2 before the pair ships, and the obligation closes on its own trigger.
