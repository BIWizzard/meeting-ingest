# Apple Marketing And Branding Seat — Record 003

## 1. Verdict

The three owner rulings are right and the record should absorb them, but the brief has drifted into **distribution vocabulary the product has not earned**. It proposes to name five new things — consumer classes, a channel-tracking class, a formal role, a severity category, an adoption path — for a maintainer-only alpha that is two project directories on one person's machine. My seat filed this exact failure mode in record 002 ("naming many hosts inflates the supported audience before one host is proven"); it is recurring one layer down, at distribution.

P3 and P5 are the strong proposals and should ship. P2's ruling — **"shipped means running"** — is the best piece of language this project has produced and should become the headline of record 003, but three of its four fix clauses are misdiagnosed: they add taxonomy to surfaces that cannot keep the taxonomy they already have. P1 should not be ratified now: `DECISIONS.md:375-387` (Decision 35) already routes auto-updating delivery through a distribution-transition convening behind three named exit criteria, none of which are met, and it already names the correct interim relief — mechanical, not contractual (issue #16). Creating an auto-updating class now spends a trust asset before it is earned and buys back only two `runtime pin` invocations per release.

Launch posture is unchanged by every proposal here. Nothing in P1–P5 entitles beta language, and nothing entitles the phrase "just works" — that is the milestone name, and the milestone is not met.

## 2. Evidence

### P1 — Consumer-class segmentation

- **A recorded decision already owns this question.** `DECISIONS.md:375-387`: the receipt/pin ceremony "sunsets when all three exit criteria hold" — milestone met including a release-evidence semantic acceptance PASS; three consecutive drift-free releases; owner decides to broaden. Then "a distribution-transition plan convenes the board to amend record 002," and — decisively — "Whether client-work consumers retain any explicit-update posture is decided by that board convening, not presumed." P1 presumes it.
- **The criteria are not met.** `docs/product-status.md:41` — Track 4 "not started; approval-gated." `:59` — rule 6 is "**falsified rather than merely unproven**." `:28` — posture is still maintainer-only private alpha with the maintainer as reference user. Criterion 1 fails on two counts and criterion 3 has not fired.
- **Decision 35 already names the right relief:** "the release flow collapses into a single maintainer command and consumer updates into a single verified command, keeping the explicit-action clause while removing the ceremony." That is issue #16, open, unstarted. The pain P1 cites (0.2.1 and 0.3.0 each needing manual repins at two consumers) is exactly #16's scope and needs no amendment to record 002.
- **The taxonomy conflates two axes.** Class (a) "the reference consumer" is a *role*; class (b) "an auto-updating class" is an *update posture*. They are not parallel, and class (a) is simply P3 restated. A consumer can be the reference consumer and track a channel; a non-reference consumer can be pinned exactly. One noun cannot carry both axes, and "class" applied to two directories is inflation.
- **The honest argument for P1 exists and I want it on the record:** `init` already adopts channel-latest automatically (README.md:325), which means approval has already migrated from adoption time to publish time. Under that framing a tracking consumer is not running unapproved code — it is adopting builds the owner already approved. That is a real and defensible position. It is also precisely the argument the distribution-transition convening exists to hear, with the criteria satisfied.

### P2 — Shipped means running

The trigger is real and worse than the brief states. Product-truth surfaces are self-contradictory in at least four places:

- `docs/product-status.md:87` — "no schema 1.1, **identity-registry**, stakeholder-profile, briefing … code has shipped" — against `:437` "reviewed project-local identity registry, derivation-time resolution, and identity candidates" under **Implemented**, and against the brief's live count of 17 reviewed entries / 24 people / 39 merged IDs.
- `:235-237` Not-complete list ("reviewed stakeholder identity registry and derivation-time resolution", "deterministic Stakeholder Briefing aggregation", "playbook derivation ledger, review overlays, profiles, briefings") — all contradicted by `:437` and `:450-462`.
- `:79` — "The Stakeholder Playbook effort is currently a design-and-contract workstream, not a shipped feature" — against `:445` "Layer 5B: Stakeholder Briefing V1 / Implemented foundation" listing eighteen shipped behaviors. Issue #23 names only the first contradiction; this one is unfiled.
- `:546-553` "Recommended Next Product Slice" still lists "implement Layer 5A generalized provenance and reviewed identity" and "implement deterministic Stakeholder Briefing V1" as the next work. Both are done.
- The word "active" and the word "activation" appear **nowhere** in `docs/product-status.md` or `README.md`. `README.md:90-109` "Current Status" omits the identity registry and the playbook entirely. The live state of the flagship feature at the flagship consumer exists on no product-truth surface.

On the severity clause specifically, the code does not have the shape the brief assumes:

- Severity is a closed three-value scale — `readiness.py:479`, `runtime.py:908`: `{"blocker": 0, "warning": 1, "advisory": 2}` — consumed as a ranking and as `finding_counts.by_severity` by `cli.py:345` and `cli.py:389`. A fourth severity is a breaking change to a published counting surface.
- Category is a separate axis: `runtime`, `project`, `advisory`, `history`. The brief's phrase "core-inactive **severity category**" straddles two axes that the codebase already muddles — `readiness.py:452` tests `finding.category == "advisory" and finding.severity == "advisory"`, so one word is already doing two jobs.
- **The trigger's own diagnosis is wrong.** "Readiness filed the absence at a severity everyone learned to ignore" reads as a missing-label problem. Issue #26 shows it is a volume problem: `readiness --json` on a mature corpus returns ~65KB in which every finding is the same `severity: warning, category: history` code repeated once per meeting, "the verdict is one field buried in the volume." A new label added to that payload gets ignored on arrival.
- The verdict vocabulary compounds it. `Ready With History Warnings` is the state the reference consumer permanently occupies — 177 standing findings (`docs/product-status.md:73`, session doc `:44`). A verdict the flagship consumer can never leave is wallpaper at the verdict level, one story above the finding level P2 is trying to fix.

Naming note: issue #15 says **"active-at-reference-consumer"** — concrete, checkable, true. The brief regressed it to **"active-per-consumer-class"**, which imports P1's unratified taxonomy into product truth and is not checkable until P1 exists. The issue's wording is better than the brief's.

### P3 — Reference consumer as a formal role

- Strongest proposal in the record, and the best naming act available. "The reference consumer" gives every claim a *location*: it converts "we shipped it" into "here is where you can watch it run." That is what makes "shipped means running" enforceable rather than aspirational.
- Evidence that the role already exists de facto: `docs/product-status.md:73` (HTV runs the approved frozen wheel; the fresh-host proof was measured there), session doc `:42-44` (the 0.3.0 measure of done demonstrated against it), the brief's activation counts, and OB-002-2 in `board-log.md:16` which fired on HTV's first production ingest.
- Tension worth naming: the role's default holder is a consumer that sits permanently at `ready_with_history_warnings`. The role definition must state that this is legitimate (OB-002-2 already ratified it) and that activation evidence is judged independently of the history lineage — otherwise the first person to read "the reference consumer is not Ready" reads it as the product failing.
- Sanitization inconsistency: the backlog policy keeps client detail out of GitHub issues, while the ratified record would name a client engagement as the permanent default holder of a formal product role. The docs already use HTV throughout, so this is consistency housekeeping, not a new exposure — but a record that formalizes the name deserves one deliberate line about it.

### P4 — Redistribution boundary

- The clause is right and cheap. Making it a check-in trigger rather than a memory is exactly the mechanism the board exists to provide.
- **The name is wrong for what it governs.** "Third-party redistribution boundary" describes distributing something to third parties. Nothing is distributed. The actual subject is candor about named non-parties retained in durable signals and briefs, safe only because there is exactly one reader. Call it what it is — an audience-scoped candor precondition — or the clause will be looked up under the wrong question when it matters.
- The trigger is under-specified against its neighbors. P3 makes the reference-consumer role transferable "by owner decision without a reconvening"; P1 would create a consumer class. Either could produce a non-owner recipient without anyone consciously "adding a brief recipient." The trigger must attach to the role transfer and to any class creation, not only to the recipient list.
- One unresolved fact bears on this: Trace3 is described only as "a second consumer project." Whether its outputs have any reader other than the owner determines whether this precondition is comfortably dormant or already near its edge. The brief does not say.

### P5 — One-command init

- The behavioral claim is evidenced. Session doc `:42-43`: "Virgin project: `meeting-ingest init` → `Ready`, pin `…0.3.0…`, both artifacts installed project-level, meetings root scaffolded. One command, zero flags." Both consumers repinned (`:44-45`). T2-verified with two independent reviews (`:35-37`).
- **The language did not ship with the behavior.** The ruling's core requirement is that the user "never learn that receipts, templates, or approved-executable markers exist." `README.md:325`, the very paragraph announcing the one command, teaches all of it: "selects the latest published approved receipt, requires the receipt's own wheel beside it and hashes it, verifies that the invoked command is the console script the running frozen distribution records, renders and installs the project-level Claude skill and session-provider agent through the same receipt-verified installer… Every byte it writes is verified against the receipt." That is the ceremony re-narrated as prose in the place a new consumer looks first. The ruling explicitly rejected "better error messages" as ceremony in disguise; ninety words of receipt mechanics under a "Consumer Onboarding" heading is the same disguise in a different costume.
- The nuance the brief flags is the most valuable sentence available here, and it should be promoted from footnote to principle: **approval attaches at publication; adoption is automatic at init and explicit thereafter.** That is one sentence, it is true today, it is memorable, and it resolves the apparent conflict with record 002's "updating and approving the replacement build are explicit actions" (`002/09-owner-decisions.md:40`) — init performs no replacement.
- Claim ceiling: one virgin project, one host, one machine, one operator, one release. `init` is one command; *updating* is still README steps 5–7 run per consumer by the maintainer. "One command to start" is earned. "One command, always" is not.

## 3. Gaps and risks

1. **Vocabulary inflation is the through-line risk.** Five new nouns for a two-project alpha. Every one of them will be read later by someone — the owner in six months, a first outside user — as evidence of a distribution system that does not exist. My seat's record 002 finding was that platform-list positioning inflated the supported audience; README.md:35-42 fixed that by labeling hosts "design targets, not current support claims." The same discipline has not been applied to distribution language.
2. **Product-status.md is not a status document; it is a stratigraphy.** Four independent contradictions across 582 lines, three strata of staleness, and a 1,000-character single paragraph at `:54` carrying five distinct claims. P2 clause 4 proposes adding a third axis to a document that cannot maintain its first. The predictable outcome is a fifth contradiction, this time about activation — the one thing the record is trying to make trustworthy.
3. **P2 clause 3 risks breaking a published counting surface** (`finding_counts.by_severity`) to solve a problem that is not a severity problem. And it risks being ignored on arrival: dropping a `core-inactive` finding into a 65KB payload of 177 repeated warnings reproduces the failure it was written to fix.
4. **"Shipped means running" does not scale past one reference consumer, and P1 would create the second class in the same record.** If a tracking-class consumer sits three builds behind, is the feature "running"? The phrase must be scoped to the reference consumer explicitly, or it becomes unfalsifiable the moment classes exist.
5. **Claim creep from P5.** "One-command init" plus "shipped means running" plus "Just Works Continuity" is one short conversation away from "it just works" appearing on a surface. The charter names that phrase as a convening trigger. Track 4 is not started; rule 6 is falsified.
6. **P1 and P3 collide undetected.** P1's class (a) is P3's role. If both ratify as written, the record defines the same thing twice under two names, and future work will cite whichever it finds first.
7. **P4's trigger can be walked past sideways** via a P3 role transfer or a P1 class creation without anyone consciously adding a brief recipient.

## 4. Recommendations in priority order

1. **Make "shipped means running" the headline of record 003, scoped in the same sentence.** Ratify the phrase verbatim with the scope rider: *shipped means running at the reference consumer.* Short, falsifiable, memorable, and it survives the arrival of a second class because it names where the measurement happens.
2. **Ratify P3 first and let it carry the role.** Then strike P1's class (a) entirely; it is P3 with a different name. Add to the role definition: the holder may sit at `ready_with_history_warnings` (OB-002-2), and activation evidence is judged independently of the history lineage.
3. **Do not create an auto-updating class. Ship issue #16 instead.** Decision 35 already provides for it as interim relief that is "mechanical, not contractual." One maintainer command and one consumer update command remove the ceremony P1 complains about and change nothing about the ratified contract. Revisit auto-update at the distribution-transition convening Decision 35 already reserves, with the exit criteria met.
4. **Ratify the P5 principle as one sentence, and attach a language obligation to it.** Principle: *approval attaches at publication; adoption is automatic at init and explicit thereafter.* Obligation: rewrite `README.md:317-327` so Consumer Onboarding is the command, the result, and one line on what happens if verification fails. The receipt mechanics move to the Release Flow section where the maintainer — the only person who needs them — already is. The ruling is not satisfied by behavior alone.
5. **Fix `docs/product-status.md` before adding an axis to it (issue #23, widened).** Close all four contradictions, not just the one #23 names — `:87`, `:79`, `:235-237`, and the stale Next Slice at `:546-553`. Then, rather than hand-maintaining a third column, make activation state *derived*: `readiness`/`status` already know the pin and the registry state, so product-status should cite tool output for activation rather than re-typing it. Hand-maintained triple-axis prose is how the current contradictions happened.
6. **Fix the ignorability before adding a label to it.** Ship issue #26 (collapse repeated same-code history findings; offer a verdict-only view) as a precondition of P2 clause 3, not after it. A finding no one can see is not fixed by renaming it.
7. **If a new readiness classification is adopted, make it a category, not a severity.** `category: activation`, severity drawn from the existing three-value scale. This preserves `by_severity` counts and the sort key, and it puts the new concept on the axis that already carries `runtime`/`project`/`history`. In the same pass, resolve the `advisory`-is-both-a-severity-and-a-category collision (`readiness.py:452`) — it is the reason the brief's phrasing was ambiguous in the first place.
8. **Adopt issue #15's wording over the brief's:** `implemented` / `active-at-reference-consumer`. Concrete, checkable today, and free of the unratified class taxonomy. Reject "active-per-consumer-class."
9. **Rename P4** to name its subject — audience-scoped candor, single-recipient precondition — and widen its trigger to fire on reference-consumer role transfer and on the creation of any consumer class, not only on a new brief recipient.
10. **Add one explicit non-claim clause to the record:** record 003 changes no release posture. No proposal here entitles beta language, public-launch language, or the phrase "just works." Write it down so it is not re-derived under pressure.

## 5. What to stop, defer, or simplify

**Stop.** Stop the word *class* — it describes a distribution system that does not exist for two directories on one machine. Stop "third-party redistribution" as the name of a candor clause. Stop "core-inactive" as user-facing vocabulary; it names an internal state rather than the user's situation ("the identity registry is not active in this project" is what a person needs to read). Stop hand-maintaining feature status prose that the tool can emit. Stop narrating receipt mechanics in consumer-facing copy.

**Defer.** Defer the auto-updating posture to the distribution-transition convening Decision 35 already reserves. Defer P2 clause 4's third axis until the first two axes are non-contradictory. Defer any richer readiness classification until issue #26 makes readiness legible at the point of use.

**Simplify.** The record needs three nouns, not five: a **role** (P3), an **update posture** (pinned; tracking deferred), and an **activation state** (implemented / active-at-reference-consumer). Everything else in P1–P5 is a clause under one of those three.

## 6. Decision

| Proposal | Decision | One-line basis |
|---|---|---|
| **P1** — Consumer-class segmentation | **REDESIGN** | Decision 35 already owns the auto-update question behind three unmet exit criteria and names the correct interim relief (#16); class (a) duplicates P3; the taxonomy conflates role with update posture. |
| **P2** — Shipped-means-running | **AMEND** | Ratify the ruling and clauses 1 and 2 as written; scope the phrase to the reference consumer; rework clause 3 into a category behind issue #26; make clause 4 derived, adopt issue #15's wording, and require the four existing contradictions closed first. |
| **P3** — Reference consumer as a formal role | **SHIP** | Already true in practice, evidenced across the record; the single most valuable naming act available. Two riders: the holder may sit at `ready_with_history_warnings`, and the role transfer is a P4 trigger. |
| **P4** — Single-owner consumption precondition | **AMEND** | Codify the clause; rename it to its actual subject; widen the trigger to role transfer and class creation. |
| **P5** — One-command init | **AMEND** | Ratify the ruling and the publication-approval principle; the ruling is not satisfied until `README.md:317-327` stops teaching receipts. Claim "one command to start," never "one command, always." |

## 7. Confidence and unresolved questions

**High confidence:** that Decision 35 already governs P1 and its criteria are unmet; that product-status.md is self-contradictory in the four places cited; that "core-inactive" as a fourth severity would break `finding_counts.by_severity`; that `README.md:325` violates the P5 ruling's own stated intent; that the record must carry an explicit non-claim clause on launch posture.

**Medium confidence:** that #26 must precede P2 clause 3 rather than accompany it — an implementer closer to the readiness payload may see a cheaper ordering. That `category: activation` is the right encoding rather than promoting activation gaps to `blocker` outright; under a literal reading of "shipped means running," a core feature inactive at the reference consumer arguably *is* a blocker, and I would not object to that stricter encoding.

**Unresolved:**

1. Does Trace3's output have any reader other than the owner? P4's precondition is comfortably dormant or already near its edge depending entirely on this, and the brief does not say.
2. Is the reference-consumer role singular by definition? HTV holds activation evidence but permanently carries 177 history findings; a clean-baseline holder and an activation holder may be two roles the record is about to fuse into one.
3. What is the actual per-release cost P1 is buying down — two `runtime pin` invocations, or something larger not visible in the record? If it is the former, #16 dominates P1 on every axis.
4. Does the owner intend record 003 to be a step toward broadening? If yes, that is Decision 35's criterion 3 firing, and the correct move is not P1 but the distribution-transition convening — a different brief, with the exit criteria assessed on the record.
5. Should HTV be named as the default role holder in a repo whose issue policy is sanitized, given the docs already use the name throughout? A deliberate one-line ruling beats an inherited habit.
