# Record 003 — Seat 02, Apple Product Manager

## 1. Verdict

Four of the five proposals are ratifications of rulings the practice has already made, and they should mostly be ratified — but **P1 is out of order and should not create an auto-updating consumer class in this alpha.** The repo's own Decision 35 already defines the auto-update end state, its three exit criteria, and the sanctioned interim relief; none of the three criteria are met today (the Just Works Continuity milestone is explicitly *not* met, drift-adjacent incidents are still open, and the audience has not broadened), and the relief Decision 35 names — one maintainer release command, one consumer update command, issue #16 — has not been built. P1 asks the board to skip the cheap fix and adopt the expensive end state early.

**P2 is the proposal that actually moves the customer**, and it is under-scoped in one specific way: its item 3 adds a new readiness severity category to a readiness payload that is already unreadable at 177 findings (#26, relay #4 observation 4). Adding a category to a surface "everyone learned to ignore" reproduces the exact defect P2 was written to cure.

The strongest single piece of evidence in front of this board is not in the brief: **relay #4 is open, unlabeled, and 25 days old.** It reports a `.txt` ingest that produced a fully populated artifact, emitted zero signals, and recorded `signals.status: "ready"` with `fingerprint = sha256("")` — a green record over an empty output on the shipped build, at the reference consumer. Of that relay's four prioritized asks, the one that shipped (0.2.1, `generated_by` stamp) was the reporter's item 4; the one the reporter called a one-liner and ranked first — never record `ready` for a zero-signal emission — is still open as #9. The brief's evidence-reconciled state says "relay lane clear." It is not. That is a sequencing fact the chair should carry.

## 2. Evidence

### P1 — consumer-class segmentation

**Contradicts.** `DECISIONS.md` §35 (2026-07-26) already ratified the destination and the gate:

> The apparatus is therefore scaffolding for the trust-building phase, not the end state. It sunsets when all three exit criteria hold: 1. **Maturity** — the Just Works Continuity milestone is met… 2. **Trust established** — three consecutive owner-approved releases ship through the flow with zero drift incidents. 3. **Broadening** — the owner decides to take the tool beyond the maintainer-only private alpha.

Scoring the criteria against today's evidence:

| Criterion | State | Source |
|---|---|---|
| Maturity | **Not met.** "The Just Works Continuity milestone also requires Track 4 and is not met." Track 4 is "not started; approval-gated." The one release-evidence acceptance PASS is claim-scoped to exclude rule 6, which is "falsified rather than merely unproven." | `docs/product-status.md` lines 41, 59, 63 |
| Trust established | **Contested at best.** Three releases exist (0.2.0, 0.2.1, 0.3.0), but drift-adjacent incidents accumulated across them: a rejected acceptance run because the host cached the pre-release agent definition; a release flow that "regenerat[ed] the false hand-edit signal that misled the relay twice"; the non-receipt-managed Codex skill pair that "drifted silently for three days once already" (#17, still open); and Decision 33's registry pin currently leading the receipt. | README Product Direction; 8/06 session next actions 40–41; issue #17 |
| Broadening | **Not decided.** Trace3 is a second project, not a second audience; record 002's "maintainer-only private alpha" stands and the brief does not ask to change it. | 002 `09-owner-decisions.md`; brief line 15 |

Decision 35 also names the relief P1 is really reaching for, and rules it *mechanical, not contractual*:

> …the interim relief is mechanical, not contractual: the release flow collapses into a single maintainer command and consumer updates into a single verified command, keeping the explicit-action clause while removing the ceremony.

That command pair is issue #16, filed, open, unbuilt. The pain P1 cites — "0.2.1 and 0.3.0 each required manual repins at both consumers" — is roughly six repin events across six weeks. A single verified update command retires that pain without touching a ratified clause.

**Also contradicts:** the 0.3.0 auto-bootstrap path is one day old. Its security review left two items open (#27): installed-file identity established from the install's own self-supplied RECORD, and an install/pin race where "two concurrent bootstraps can interleave so the loser overwrites workflow artifacts after the winner pinned." An auto-updating class multiplies unattended install+pin events, which is exactly the population that race is scoped to.

**Supports (partially):** the machinery for a safe class (b) does mostly exist — the channel manifest already carries `latest`, `previous`, and "retained rollback artifacts" (README line 282; `runtime_config.py:47`), and `runtime_release.py:1047` already compares channel, consumer selection, and running build without side effects. The gap is not capability. It is earned trust.

### P2 — shipped-means-running

**Strongly supports.** The trigger is documented and severe: Layer 5A identity registry *and* Layer 5B Stakeholder Briefing V1 were "implemented in the shipped build but never activated at HTV — no scaffolding, no derivation run, readiness filing it as 'optional'" (8/06 session summary). The owner could not tell where the product stood.

**The failure is still live in the artifact P2 proposes to amend.** `docs/product-status.md` line 87 states: "no schema 1.1, identity-registry, stakeholder-profile, briefing, guidance, email, screenshot, or social-source code has shipped" — while lines 437–438 and 449–462 record both as implemented, and the brief records the registry as active with 17 reviewed entries. Issue #23 filed this contradiction; it is open. The evidence document that a board is reading to judge shipped-means-running is itself an instance of the defect. Its "Recommended Next Product Slice" (lines 546–552) still lists five steps the 8/06 session assessed as "effectively built," and its verification stanza is dated 2026-07-26.

**Root-cause mismatch on item 3.** The brief's own diagnosis is "readiness filed the absence at a severity everyone learned to ignore." That is signal-to-noise, not taxonomy. Readiness returns 177 findings, all `severity: warning`, all `category: history`, each with an identical remediation line (relay #4 obs 4); #26 measures the payload at ~65KB with the verdict "one field buried in the volume." A `core-inactive` category dropped into that payload inherits the invisibility.

**Supports item 1 with a caution.** Activation evidence at the reference consumer is the right release gate, and the 8/06 ruling already carries its own exception — "every feature ships active to HTV unless explicitly scoped away from it" — which the proposal text drops. Without the exception codified, item 1 reads as an unbounded release blocker for every internal change.

### P3 — reference consumer as a formal role

**Supports.** HTV is already the de facto holder: activation evidence, the 177-finding standing, corpus upkeep wired into its CLAUDE.md, the first derivation generation, the identity review (24 people / 39 merged / 179 meetings), and three of the four relays. Formalizing the practice costs nothing and closes the gap between record 002's "the maintainer as the sole reference user" and where "running" is actually measured.

**Under-describes the practice.** The 0.3.0 measure of done was *not* HTV — it was "virgin project to Ready with zero flags," proven by a virgin smoke test, then confirmed by repinning both consumers. And the sharpest field defect of the last month came from the *second* consumer: Trace3's `meeting-ingest init` failed with the bare line "failed: exit 12" (8/17 session), root-caused to bootstrap inversion at `pipeline.py:169`. A mature reference consumer structurally cannot produce that evidence — it is already initialized. The practice has two evidence sites; the proposal names one.

**Boundary risk.** HTV is client work under OB-002-1, where "no corpus adoption or mutation is authorized" is a standing blocker in every session wrap. Making a client corpus the mandatory site of activation evidence puts a release gate and an adoption prohibition on the same surface.

### P4 — third-party redistribution boundary

**Supports the clause.** The underlying concern is documented and real: "the 2026-07-28 HTV artifact persists a colleague capacity state as a high-confidence `risk_or_concern` signal feeding signal JSONL, playbook derivation and briefings" (8/06 open questions), and relay #4 withheld artifact content from a public issue because "it names third parties." Converting memory into an obligation is exactly what the board machinery is for.

**Wording collision.** P4's trigger fires on "the creation of any recipient or consumer class beyond the owner." P1, in the same record, proposes to create a consumer class. If both ratify as written, record 003 ships with an obligation that arguably fires on its own sibling proposal.

**Material gap the clause cannot cover.** The trigger reopens a *policy* question, but the *data* is already durable and one-way: append-only ledger, immutable generations, Layer 2 `regenerate` contracted but unimplemented ("no second semantic-correction design exists"), generated-Markdown mutability an open owner decision (question 16), and no capability to retire or supersede an ingested meeting (#6, open). Hand-editing is explicitly not a correction mechanism. When the trigger fires, it will find history that cannot be redacted.

### P5 — one-command init

**Strongly supports the ruling and the outcome.** The customer evidence is unambiguous: the owner's own second consumer was blocked by a bare `exit 12`, and the owner "deferred all three fixes (no time) and ruled the target shape instead: one command initializes the tool and it works." 0.3.0 delivered it, T2-verified, virgin smoke passed, both consumers repinned Ready. This is the clearest job-to-be-done win in the record.

**Contradicts a still-published clause.** README line 282 asserts of the channel manifest: "it never installs, selects, or repins a consumer." As of 0.3.0, init does exactly that — `runtime_release.py:820` `_latest_published_receipt()`, called at `:977`. The ruling is right and the doc is now false. Ratifying P5 without reconciling that sentence leaves record 002's consumer policy quoted inaccurately in the front-door document, which is the same class of defect as P2's trigger.

**Second-order consequence the brief does not name.** Because init auto-selects channel-latest with no human in the loop, a consumer onboarded at time T receives whatever the channel points at — including a build that has not cleared P2's activation gate. P5 and P2 are coupled: what the channel is permitted to carry is now a consumer-facing decision, not a publishing detail.

## 3. Gaps and risks

1. **Brief inaccuracy — "relay lane clear."** Issue #4 is open, unlabeled, un-triaged since 2026-08-05. The lane triage polls by label; #4's label was dropped by filer permissions (the same twice-observed gap as #2/#3, fix filed as #22, open). The lane silently lost its highest-severity report — a green ledger over an empty signal file. This is the P2 failure mode operating on the intake lane itself, and the board is being asked to reason from a state summary that the bug has already corrupted.
2. **The severity that everyone ignores is unfixed, and P1 would multiply it.** With auto-update, a regression of the #4 class propagates to consumers with no human gate between publish and run. Today the repin ceremony is, accidentally, the last human read of a release. Removing it before the readiness surface is readable removes the only remaining reader.
3. **Zero field time on the bootstrap P1 would automate.** 0.3.0 shipped 2026-08-30 — today. Its evidence is one virgin smoke test plus two repins. #27's install/pin race is unmitigated.
4. **P2 item 1 has no bound.** "A release is not complete until the feature's behavior is observable there" with no definition of *core*, no scoped-away exception (which the source ruling has and the proposal drops), and no backstop for already-shipped-inactive features becomes either a release deadlock or a checkbox.
5. **P3 concentrates evidence on a corpus the project may not touch.** OB-002-1 and the activation gate now share one surface, and OB-002-1 is supreme.
6. **P4's precondition is not reversible.** No redaction, retirement, or supersession path exists (#6, Layer 2 unimplemented, question 16 open).
7. **Roadmap displacement.** Record 002's milestone is Just Works Continuity; Track 4 is unstarted. P1 spends design and review capacity on distribution — Layer 5D, explicitly "not started," and explicitly gated behind the milestone being met. Ratifying it now inverts the ratified sequence.
8. **Attestation quality is advisory, not evidential.** #13: `model_id` is provider-self-reported and inconsistent across runs on the identical frozen build. An auto-updating class whose safety story is "the same verification, enforced at adoption time" should know that one link in the provenance chain is currently advisory.

## 4. Recommendations, in priority order

1. **Ratify P2's principle, and make the first release under it prove itself on relay #4.** The clean acceptance test already exists and needs no new fixture: a run whose `signals.fingerprint` equals `sha256("")` cannot be recorded `ready` (#9). If the shipped-means-running gate cannot catch a green record over an empty file at the reference consumer, it is a slogan.
2. **Ship #23 before the next release.** Product-status carries `implemented` and `active-at-reference-consumer` per feature row, and its self-contradiction is repaired. This is P2 item 4, it is a documentation change, and it is the cheapest item on the board.
3. **Pair P2 item 3 with #26.** `core-inactive` ships together with collapsed same-code history findings or a verdict-only view. Acceptance: a `core-inactive` finding is visible in the default readiness output an operator actually reads.
4. **Ratify P5, and reconcile the channel clause in the same change.** Amend README line 282 and the record 002 consumer-policy language to state the real rule: *the channel selects the initial build at init only; it never repins a running consumer.* Add the coupling constraint: **a build may be published to the channel only if it carries release evidence including activation evidence** — so init's automatic selection can never hand a new consumer an unproven build. Record #27 item 1 as the named residual.
5. **Ratify P4 with the wording fix.** Scope the trigger to *recipients of briefs and consumers of the durable signal stream*, explicitly excluding delivery/update classes, so it does not fire on P1. Record the unredactable-history finding as the clause's known limitation and name #6 as its dependency.
6. **Ratify P3 as two roles, not one.** *Reference consumer* (HTV, default, owner-changeable without reconvening, change logged with reason) is where activation evidence and shipped-means-running are judged. *Fresh-consumer proof* — a virgin project or Trace3 — is where bootstrap and first-run evidence is collected. Both were used for 0.3.0; the record should say so. Add one sentence: reference-consumer activation never authorizes corpus adoption or mutation; OB-002-1 governs.
7. **Answer P1 with #16, not with a new class.** Build the single verified consumer update command and the single maintainer release command. Decision 35 already blessed this as the relief, it removes the ceremony P1 complains about, and it keeps the explicit-action clause intact. Then let the sunset criteria do their job.

## 5. What to stop, defer, or simplify

**Stop.** Designing an auto-updating consumer class in this record. Decision 35 already owns that design, already names the convening that authorizes it, and already lists what must be true first. Litigating it early costs a board convening and produces a clause the project cannot yet honor.

**Defer.** P1 class (b) until Decision 35's three exit criteria hold — with one added, learned from this month: at least one release cycle in which the readiness surface is readable and a #4-class defect is caught by the gate rather than by a human reading a relay. If the owner nonetheless wants class (b) now, the minimum bounds are non-negotiable and all four are evidence-backed: (a) full receipt and chain verification at adoption time, unchanged; (b) provenance stamping so any artifact names the build that produced it and the adoption event that installed it; (c) a one-command rollback to the channel's retained `previous` build, exercised in acceptance, not merely available; (d) #27 item 2 (consumer-root lock across install+pin) landed first; and (e) **no client-work consumer is ever in class (b)** — HTV stays fail-closed, which is what the 2026-07-27 capture proposed in the first place.

**Simplify.** P2's four items are not equal. Items 1 and 4 have teeth and are cheap; item 3 needs #26 to mean anything; item 2 (scaffold-and-nag) is genuine engine work that can follow the ratification without weakening it. Ratify the principle plus items 1, 3+#26, and 4 as binding now; track item 2 under #15.

**Simplify.** Ratify P4 as one sentence with a scoped trigger. It does not need a policy apparatus; it needs to not be forgotten.

## 6. Decision

| Proposal | Verdict | One-line basis |
|---|---|---|
| **P1** — consumer-class segmentation | **REDESIGN** | Decision 35 already governs this and gates it on three criteria, none met; the sanctioned relief (#16) is unbuilt. Redesign as: ratify the two-class *destination* and its gate, build the one-command update now, defer class (b) to the sunset convening. |
| **P2** — shipped-means-running | **AMEND** | Principle SHIP. Amend to define *core*, restore the source ruling's scoped-away exception, pair item 3 with #26 readability, and make relay #4 / #9 the first acceptance proof. |
| **P3** — reference consumer as a formal role | **AMEND** | Formalize, but name two evidence sites (mature reference consumer + fresh-consumer proof — both were used for 0.3.0), log holder changes with reason, and state that activation never authorizes corpus mutation. |
| **P4** — third-party redistribution boundary | **AMEND** | SHIP the clause; amend the trigger wording to scope it to brief recipients and signal consumers, not delivery classes, so it does not fire on P1. Record the no-redaction-path limitation and #6 as its dependency. |
| **P5** — one-command init | **AMEND** | The ruling and the shipped result are right — ratify. Amend to reconcile the now-false README channel clause, and to constrain the channel to carry only builds bearing release evidence, since init selects from it unattended. |

## 7. Confidence and unresolved questions

**High confidence:** P1's collision with Decision 35 and the unmet exit criteria (direct quotation, plus product-status stating the milestone is not met); P2's trigger and its persistence in product-status today (lines 87 vs 437–462, #23 open); relay #4's open, unlabeled state and the inversion of its own priority list; the README channel-clause contradiction (README:282 vs `runtime_release.py:820/977`).

**Medium confidence:** my reading of Decision 35 criterion 2. "Zero drift incidents" is not defined, and a reasonable chair could score three clean releases as met, treating the cached agent definition and the Codex skill-pair drift as outside the release flow proper. I score it not-met because #17 is open and the false hand-edit signal misled a reporter twice, but I flag this as the most contestable link in my P1 argument and the one most worth the chair testing against seat 03.

**Lower confidence:** the practical cost of the ceremony P1 targets. I inferred roughly six repin events across six weeks from the release record; if the owner's felt cost is materially higher — or if repinning has failed or been skipped in ways the sessions do not record — the balance between "build #16" and "create class (b)" shifts, though the sunset criteria still bind.

**Unresolved questions I could not settle from the repo:**

1. **Has the owner ever received a real stakeholder brief?** The 8/06 next action was "run the first playbook update at HTV and show the owner a real brief." The 8/30 wrap records "derivation verified 10→5 candidates" — mechanism confirmed. I found no record of the owner reading a briefing. If not, Layer 5B is *running* but not yet *delivering*, and P2's own definition of "shipped" needs to say which of those it means. This materially affects how P2 item 1 is written.
2. **Is Trace3 a client-work consumer or a personal project?** It determines whether P1's class (b), even bounded, has any legitimate member today, and whether P4's trigger is closer than the record assumes.
3. **What is the "features-and-benefits list"?** P2's scope is defined by reference to it; the only occurrence in the repository is inside the brief itself. Ratifying a gate scoped to a list that does not exist would create the ambiguity P2 exists to eliminate.
4. **Does the readiness `core-inactive` category apply to features scoped away by owner decision?** If yes, the exception generates permanent findings and the category decays into the noise it was meant to escape.
