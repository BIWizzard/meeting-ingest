# Record 003 — Seat 01 (Steve Jobs lens): Consumer Classes, Update Policy, and the Adoption Path

## 1. Verdict

Five proposals, and three of them are about how the software gets installed. One is about scoping a disclosure policy. Exactly one — P2 — is about whether the product actually does the thing it claims to do for the person using it. That ratio is the finding. This project has spent five weeks (0.2.0 on 7/29 → 0.3.0 on 8/30) shipping its own delivery apparatus while Track 4, the last track standing between it and its own ratified milestone, has not been started. The board is now being asked to amend a ratified contract to make the delivery apparatus more convenient. That is the wrong direction of travel.

P5 is the best work in this brief and should be ratified without hesitation — it is the only proposal that removes something from the user's world instead of adding to it. P2 is right in principle and must be ratified, but its proposed mechanism will fail for the exact reason the original failure happened, and I amend it. P3 is free and true, ratify it. P4 is directionally correct but its trigger fires after the only remediation window has already closed, and I amend it. P1 should be rejected as designed: it invents a consumer taxonomy for a fleet of two projects owned by one person, to solve a pain — "an owner-run repin per consumer per release" — that record 002's own Decision 35 already authorized solving with **no amendment at all**, via a single verified update command that has been an open issue (#16) and was never built. Do not amend a contract to route around unbuilt work.

## 2. Evidence

### P1 — Consumer-class segmentation

**Against, decisively:**

- **The relief was already granted and never taken.** DECISIONS.md:387 (Decision 35): "Until the sunset fires, record 002's clauses stay binding, and the interim relief is mechanical, not contractual: the release flow collapses into a single maintainer command and consumer updates into a single verified command, keeping the explicit-action clause while removing the ceremony." That is exactly P1's stated pain, already answered, already ratified. Issue #16 tracks it. It is open. `src/meeting_ingest/cli.py` has `runtime pin` and `runtime update-check` and **no `runtime update`**; `scripts/` contains build, publish, and install-skill — no consumer update command, no single maintainer release command. The ceremony P1 wants to escape is not required by the contract; it is required by the absence of forty lines of wrapper code.
- **P1 is Decision 35's end state, requested before any of its three gates hold.** DECISIONS.md:379–385 sets the sunset criteria for auto-updating delivery: (1) Just Works Continuity met — `docs/product-status.md:63` states flatly "The Just Works Continuity milestone also requires Track 4 and is not met"; (2) three consecutive releases with zero drift incidents — the 2026-07-25 receipt-drift catch (Decision 33 execution addendum), the `gb37a12a0502e` `workflow_hash_mismatch` (README.md:304, "this bit the `gb37a12a0502e` release once"), the stale `generated_by` stamp that reached consumers and was reported by **three dogfood relays** before 0.2.1 fixed it; (3) broadening beyond the maintainer-only alpha — not decided. Zero of three. Decision 35 also says the target end state's shape "is decided by that board convening, not presumed." P1 presumes it.
- **The verification chain P1 wants to run unattended was emitting false alarms as of today.** `docs/sessions/2026-08-30-one-command-init-release.md:30-31`: "Human-path CLI failures render code, message, remediation, and blocking findings (previously a bare `failed: exit N`); with no pin present readiness no longer fabricates `workflow_hash_mismatch`." Until this morning, the chain cried wolf and reported failures as an unexplained exit code. Those fixes have zero days of field time. You do not hand a gate the keys the same day you fix its false-positive bug.
- **Two classes for two consumers is not segmentation, it is a fork.** Every future feature, every readiness verdict, every piece of release evidence now has to answer "which class?" Record 002's power is that there is one answer to "what logic is running." P1 makes that question conditional, permanently, in exchange for saving one command per release at one project.

**For, honestly stated:** the repin cost is real and recurring (0.2.1 and 0.3.0 each cost two manual repins), and P5 already proves that automatic channel-latest selection can be made to satisfy the chain rather than bypass it. The mechanism exists. That argues for *when*, not for *now*, and it argues for a command, not a class.

### P2 — Shipped-means-running

**Overwhelming support, and the disease is still live in the repo today.** `docs/product-status.md` contradicts itself in three places about the same subsystem:

- line 87: "no schema 1.1, identity-registry, stakeholder-profile, briefing, guidance, email, screenshot, or social-source code has shipped"
- lines 235–237, "Not complete": "reviewed stakeholder identity registry and derivation-time resolution", "deterministic Stakeholder Briefing aggregation", "playbook derivation ledger, review overlays, profiles, briefings, status, and doctor behavior"
- lines 438 and 449–462: the same items enumerated under Layer 5A "Implemented" and Layer 5B "Implemented foundation"

And the brief's own evidence line reports the registry **active in production** at the reference consumer with 17 reviewed entries across 179 meetings. So the product's canonical truth document simultaneously says a feature has not shipped, is not complete, is implemented, and it is running with real client data. That is not a documentation lag. That is the product not knowing what it is. Filed as issue #23 and still open.

**The mechanism as proposed will not work.** `src/meeting_ingest/readiness.py:183-195`: any `warning`-severity finding yields `ready_with_history_warnings`, exit 0; `advisory` moves nothing. The reference consumer has stood at `ready_with_history_warnings` with 177 findings since 2026-07-24 (brief evidence; README, product-status:73). Issue #26 exists because that payload is unreadable. A new "core-inactive" *category* filed at `warning` produces the identical verdict string and the identical exit code as the 177 findings that trained the owner to stop looking — which is, verbatim, the failure P2 was written to fix: "readiness filed the absence at a severity everyone learned to ignore." Adding a category to a list nobody reads is not a fix.

### P3 — Reference consumer as a formal role

Supported by every piece of evidence in the record: HTV is where the cutover was proven (`docs/sessions/2026-07-24-task9-reference-consumer-cutover.md`), where the fresh-host proof ran (task10), where the 177 findings and the standing verdict live, where the registry went active, and where 0.3.0's measure of done was demonstrated (`2026-08-30-one-command-init-release.md:44`). Record 002 named "the maintainer as the sole reference user" — a person, not a place. The evidence is collected at a place. P3 closes a naming gap that already caused real ambiguity, and it is a precondition for P2 being enforceable at all: "activation evidence at the reference consumer" is meaningless until "the reference consumer" is a defined term.

### P4 — Third-party redistribution boundary

The ruling is defensible on its own terms and the proposed check-in trigger is better than memory. But the record shows the trigger fires too late to matter. Derived artifacts and the durable signal stream are effectively immutable here: `docs/product-status.md:347-353` — "Correction of already-ingested output: not available"; "Manual edits to generated markdown or signal JSONL are not a correction mechanism and are not an interim workaround"; the only contracted correction path, `regenerate --provider session`, is unimplemented and doubly approval-gated under OB-002-1. `docs/stakeholder-playbook-design.md:116` gives each *source* a privacy classification, but nothing in the design carries a consumption-scope or recipient-scope marker on a derived brief. So the boundary lives only in prose, and on the day the trigger fires, every candid capacity-and-morale judgment written under the single-owner assumption already exists, unmarked and unremovable.

### P5 — One-command init

Ratify it. This is the only proposal in the brief that made the product smaller. The 2026-08-13 ruling refused both cheap escapes — exempting init from the pin gate, and "better error messages" — and README.md:319-327 plus the 0.3.0 session record show it was implemented the hard way: channel-latest selection, RECORD-derived console-script identity, wheel hash-check, receipt-verified project-level installs, re-inspection, exclusive pin, scaffold, full readiness gate, pin removed on failure so a rerun converges. Verified virgin-project-to-`Ready` with one command and zero flags. It satisfies the chain rather than bypassing it, and `init` never replaces an existing pin. The user never learns that receipts exist. That is what this whole apparatus is supposed to feel like everywhere.

The nuance the brief flags is real and the record must settle it explicitly, because P1 will otherwise cite init as precedent: at `init` there is no known-good state to displace — the choice is latest-approved or nothing, the user is present, they typed the command, and readiness reports back. At update time there is a running build that produced client artifacts, and the swap can land mid-workflow with nobody watching. The distinction is consent and timing, not verification strength. Say so in the record.

## 3. Gaps and risks

1. **The apparatus is eating the product.** Track 4 — Approval-Gated Historical Qualification and Continuity Proof — is "not started" (product-status:41) and has been since the milestone was ratified on 7/20. Everything shipped since 7/29 is distribution plumbing. Three of five proposals here extend that plumbing. The 177 history findings that Track 4 exists to resolve are now so normalized they have become the reference consumer's permanent verdict.
2. **A permanent warning state is not a warning.** `ready_with_history_warnings` has been HTV's steady state for five weeks. Any new signal routed into that bucket — including P2's — inherits its invisibility.
3. **P1 and P2 pull against each other.** P2 requires activation evidence at the reference consumer before a release is complete. If a human must verify every release there anyway, P1's saving is one repin at one other project. Trading a ratified single-class contract for that is a bad exchange.
4. **P4's trigger is written against the wrong event.** "Creation of a recipient or consumer class" is a state change; disclosure is an *act*. A single brief forwarded once breaches the precondition without creating any class.
5. **Obligation-namespace collision.** `OB-003-3` already exists in the `~/.claude` agent-orchestration registry and is cited three times in this repo (DECISIONS.md:357, `docs/plans/2026-07-24-extraction-model-evaluation.md:50`, session notes). Record 003 here will mint `OB-003-x` rows. Two different OB-003-3s in one owner's documentation is a coherence defect waiting to bite.
6. **Truth-surface risk is unbounded, not scoped to one document.** README, product-status, and the board record are each maintained by hand against a moving implementation. P2's fourth item adds a column to one of them. That is necessary and insufficient.

## 4. Recommendations, in priority order

1. **Build issue #16 before amending anything.** One maintainer release command, one consumer update command, both driving the existing verified steps. This requires no amendment — Decision 35 already sanctions it — and it removes the entirety of P1's stated pain. Measure the ceremony again after two releases through it; if it still hurts, that is a real finding to bring back.
2. **Ratify P2's principle now, unconditionally**, and amend its mechanism: (a) a `core_inactive` finding must produce a **distinct verdict**, not a new category inside `ready_with_history_warnings`; (b) fix issue #26 first so the readiness payload is legible before new signals are added to it; (c) close issue #23's self-contradiction as part of the same unit — a status document that says a shipped, running feature has not shipped disqualifies itself as release evidence.
3. **Ratify P3 as written.** Rider for the record, not a condition: a successor holder must be a project doing real work with the tool, and a transfer re-establishes activation evidence at the new holder before the role moves.
4. **Ratify P5 as written**, and state the init-versus-update asymmetry in the record in one sentence so it cannot be quoted as precedent for automatic updates.
5. **Amend P4** so the trigger fires on the act, and so the clause names what remediation is actually available when it fires — under the current immutability regime the honest answer is "scope limitation going forward, no retraction," and the clause should say that out loud rather than implying the question can be reopened cleanly.
6. **Then go finish Track 4.** The milestone is the contract. Delivery convenience is not.

## 5. What to stop, defer, or simplify

- **Stop** designing a consumer taxonomy. Two projects, one owner. Classes are what you build when you have populations, and there is no population. If the day comes when there is one, Decision 35 already routes it to the board with better evidence than exists today.
- **Stop** treating "a manual step exists" as a contract defect. Sometimes it is just an unwritten wrapper.
- **Defer** the auto-updating class to the Decision 35 sunset convening, on its own criteria, unchanged. Record 003 should say so explicitly rather than leaving P1 as an open question that returns every time a repin is annoying.
- **Simplify** to three sentences the record should be able to state without qualification: one class of consumer; one command to update it; one place where "running" is measured.
- **Clear or collapse the 177.** Until the reference consumer can reach a clean verdict, every warning-tier signal this product emits is decoration — including the one P2 wants to add.
- **Defer** issue #27's defense-in-depth hardening as filed; it is correctly scoped and correctly deferred. It becomes blocking the moment anything resembling P1 is approved, which is one more reason not to approve P1 now.

## 6. Decision

| Proposal | Decision |
|---|---|
| **P1** — Consumer-class segmentation of update policy | **REDESIGN** — reject the two-class model for the private alpha; deliver issue #16's single verified update command under the existing ratified contract; the auto-updating class returns only through the Decision 35 sunset convening, on its three unchanged criteria. |
| **P2** — Shipped-means-running adoption path | **AMEND** — ratify the ruling and items 1, 2, 4 as written; amend item 3 to require a distinct readiness verdict rather than a new category inside the existing warning bucket, gated behind the readiness-legibility fix (#26) and the status self-contradiction fix (#23). |
| **P3** — Reference consumer as a formal role | **SHIP** — as written, HTV as default holder, owner-changeable without reconvening. |
| **P4** — Third-party redistribution boundary | **AMEND** — ratify single-owner consumption as a named precondition; broaden the trigger from "a recipient or consumer class is created" to include any act of disclosure of a brief or signal artifact beyond the owner, and require the clause to state that the available remediation at trigger time is forward scope limitation only, because the durable stream cannot be corrected under OB-002-1 and the unimplemented regeneration contract. |
| **P5** — One-command init | **SHIP** — as written; record the init-versus-update timing asymmetry so automatic receipt selection at bootstrap is not later cited as precedent for automatic updates. |

## 7. Confidence and unresolved questions

**High confidence:** the P1 finding (Decision 35's interim relief is ratified and unbuilt — verified directly against `cli.py`, `scripts/`, and issue #16); the P2 mechanism finding (verified against `readiness.py:183-195`); the product-status self-contradiction (verified across lines 87, 235-237, 438, 449-462 of one file); the sunset criteria status (verified against DECISIONS.md:379-385 and product-status:41, 63).

**Moderate confidence:** the drift-incident count against Decision 35's criterion 2. I count at least three distinct incidents since 7/24 (receipt drift 7/25, `gb37a12a0502e` workflow-hash mismatch, stale `generated_by` reaching the field via three relays), but the record does not define what formally counts as a "drift incident," so I cannot state the streak as a number.

**Unresolved, and the chair should put these to the owner:**

1. Does the second consumer (Trace3) constitute broadening beyond the maintainer-only private alpha in fact, even under single ownership? If yes, Decision 35's criterion 3 may already be satisfied and P1 belongs in a full distribution-transition convening rather than as an amendment — a different and more serious proceeding than this one.
2. What formally counts as a "drift incident" for Decision 35's criterion 2? Without a definition the sunset gate cannot be evaluated, and P1 will keep returning as an amendment because the gate it should be measured against is unmeasurable.
3. Under P4, has any brief or signal content already left the owner's machine — a shared file, an export, a screenshot? The trigger's design assumes the answer is no, and the answer should be established rather than assumed.
4. Is Track 4 still the intended next milestone track, or has the working priority quietly become distribution? The record should say which, plainly. It currently claims one and demonstrates the other.
