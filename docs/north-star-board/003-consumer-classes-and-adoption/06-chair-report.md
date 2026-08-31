# Record 003 — Chair Report

Date: 2026-08-30. Chair: orchestrator. Seats committed verbatim at 66712aa;
brief frozen at b9afeac. All five seats filed; no re-dispatch was needed.

## Vote matrix

| Proposal | 01 Jobs | 02 PM | 03 Engineer | 04 Developer | 05 Marketing |
|---|---|---|---|---|---|
| P1 consumer-class segmentation | REDESIGN | REDESIGN | REDESIGN | AMEND* | REDESIGN |
| P2 shipped-means-running | AMEND | AMEND | AMEND | AMEND | AMEND |
| P3 reference-consumer role | SHIP | AMEND | AMEND | AMEND | SHIP |
| P4 redistribution boundary | AMEND | AMEND | AMEND | SHIP | AMEND |
| P5 one-command init | SHIP | AMEND | SHIP | SHIP | AMEND |

\* Developer's AMEND on P1 is substantively the same position as the four
REDESIGNs: "ratify the problem; reject class (b) as briefed."

Votes are not counted; the sections below resolve the substance.

## Chair correction to the frozen brief

Seat 02 found, and the chair has verified against the live tracker, that the
brief's evidence-reconciled state line "relay lane clear" is false. Issue #4 —
a relay-titled report of zero signals recorded `ready` on a `.txt` source — is
OPEN, carries no labels (the filer-permission label drop already known as
issue #22), and has sat un-triaged since 2026-08-05. The label-scoped lane
query missed it; that is the P2 pathology operating on the intake lane itself.
The brief stays frozen as filed; this report is the correction of record, and
triaging #4 is called out under dispositions.

## Unanimity

1. **No auto-updating consumer class ships in this alpha.** All five seats,
   independently and blind, found Decision 35 and read it the same way: the
   auto-update end state is already scheduled behind three exit criteria (none
   met), its judgment is explicitly reserved to a distribution-transition
   convening, and the sanctioned interim relief — one maintainer release
   command, one consumer update command (issue #16) — is ratified and unbuilt.
   Every seat's remedy is the same: build #16, do not amend the contract.
2. **P2's principle is right and its item 3 mechanism is wrong as drafted.**
   All five: a core-inactive signal routed into the existing warning bucket is
   invisible at the reference consumer (177 standing findings, ~65KB payload,
   issue #26) and mislabels a clean consumer. The phrase "severity category"
   straddles two axes; a fourth severity breaks the published
   `finding_counts.by_severity` surface.
3. **P5's shipped behavior is ratified by every seat.** The two AMEND votes
   (PM, Marketing) object to surrounding documentation, not to the mechanism
   or the ruling.
4. **The role in P3 is real and worth formalizing.** No seat opposed it; the
   divergence is riders only.
5. **P4's clause is right and its trigger as drafted is unenforceable** —
   memory-based, unobservable, and colliding with the word "class" as used by
   P1.

## Divergence and resolution

- **P3 SHIP vs AMEND.** The amend votes carry compatible riders, none of which
  contradict the ship votes. Resolved by adopting the riders into the
  ratification text (see dispositions); the role ships.
- **P4 trigger: act vs intent.** Jobs wants the trigger on the act of
  disclosure; Engineer wants it on the decision, before access occurs.
  Resolved substantively: the trigger fires on the **earlier** of an owner
  decision to extend the audience of briefs or the durable signal stream
  beyond the owner, or any act of disclosure of such an artifact. Both seats'
  failure cases are covered.
- **P5 SHIP vs AMEND.** Resolved by ratifying now and converting the
  documentation findings into an enforcement-owed obligation rather than a
  ratification condition. The behavior is proven; the copy is not a reason to
  leave three owner rulings un-ratified.
- **Decision 35 criterion 2 (drift-incident tally).** Seats disagree on the
  count (PM: contested; Developer: two clean releases standing; Engineer: at
  most one). No seat's P1 conclusion changes under any tally, so the chair
  does not resolve it — it goes to the owner as a definition question, because
  the sunset gate is unmeasurable until "drift incident" is defined.

## One-seat catches

- **PM: relay #4 open and unlabeled** — verified by the chair; corrects the
  brief. Elevates #22 (label permissions) and #9 (zero-signal guard, the
  reporter's own first-ranked ask) as the natural first proof of P2.
- **PM: README:282 is now false** — "it never installs, selects, or repins a
  consumer" contradicts 0.3.0's shipped init path.
- **Engineer: the trust anchor is the human.** Receipts are unsigned; the pin
  can only be written by the already-human-installed build. P5 preserves that
  anchor; any auto-adopting class deletes it. Decision 35's end state
  specifies signed receipts for exactly this reason.
- **Engineer + Developer (independent two-seat convergence, decisive): the
  topology collision.** One machine-wide install, exact-build pins compared
  against the running build: an auto-updating consumer's update immediately
  fail-closes every pinned consumer on the machine. Class (b) as briefed does
  not coexist with class (a); it breaks it.
- **Developer: no consumer repair command exists** — drift remediation is a
  six-flag script invocation; `init` refuses on an existing pin. Routed to a
  new backlog issue.
- **Developer: the mislabel is threefold** — `optional_playbook_output_missing`
  wording, `history` category, and "does not block" remediation text all said
  "ignore me." Renaming is a one-line-class fix that precedes any taxonomy.
- **Marketing: the onboarding copy teaches receipts** — README's Consumer
  Onboarding paragraph re-narrates the ceremony the ruling abolished.
- **Marketing: the non-claim clause** — nothing in 003 entitles beta or
  "just works" language.
- **Jobs: OB namespace collision** — an unrelated `OB-003-3` exists in the
  owner's `~/.claude` registry documentation. Chair ruling: board-log
  obligation IDs are project-scoped by the practice's schema; the record
  carries a disambiguation note rather than renumbering.

## Overrulings and departures from the Jobs seat's blind position

- Jobs gated P2 item 3 behind both #26 and #23. The chair keeps #26 as the
  gate (same surface) and runs #23 as a parallel obligation (different
  surface); serializing them buys nothing.
- Jobs' "build #16 before amending anything" is adopted as priority guidance,
  not as a sequencing condition on ratification — the amendment text and the
  enforcement artifact can proceed in parallel without contract risk.
- Jobs' "clear or collapse the 177" is routed to #26 and to the Track 4
  direction question, not minted as a 003 obligation.
- Jobs' P4 act-only trigger is merged with Engineer's intent trigger
  (earlier-of), a strict widening of his position.

## Dispositions

**P1 — REDESIGN, adopted as follows.** Record 003 ratifies: every consumer
remains exactly pinned and fail-closed; the class distinction, to the extent
one exists, governs **evidence obligations** (reference consumer: activation
evidence; secondary consumer: portability and onboarding evidence), never
update posture. Issue #16's two commands become an enforcement-owed
obligation. Staleness pressure is fixed inside the existing chain:
`update_available` graduates from advisory to a tiered signal (advisory one
build behind; warning past an owner-named threshold). The auto-updating
posture is deferred to Decision 35's distribution-transition convening, whose
brief must carry the four recorded integrity preconditions: signed receipts
with published verification keys; side-by-side installs or an explicit
all-consumers-move-together ruling; a first-class exercised rollback command;
issues #27 closed and #14.4's canonical store root settled. Rejected: the
two-class model as briefed, and any unattended adoption in the alpha.

**P2 — AMEND, adopted as follows.** The principle is ratified verbatim with
Marketing's scope rider: **shipped means running at the reference consumer.**
Item 1 ships with the source ruling's scoped-away exception restored ("every
feature ships active to the reference consumer unless explicitly scoped away
from it") and Engineer's metadata clause: activation evidence is
verdict/count/build-id metadata, never corpus content. Item 2 ships as
trigger, not nag — derivation runs automatically at ingest-batch completion
(it is a deterministic full rebuild, so idempotent), failures surface as real
errors, and post-update scaffolding runs ahead of the write guard. Item 3 is
redesigned: `core_inactive` is a **category** with its own distinct verdict,
never a fourth severity and never routed through `ready_with_history_warnings`;
it is gated behind #26 legibility; and the threefold mislabel rename lands
first. Item 4 adopts issue #15's wording (`implemented` /
`active-at-reference-consumer`), closes all four product-status
contradictions (issue #23, widened), and derives activation state from tool
output rather than hand-maintained prose. Rejected: the per-ingest nag, the
fourth severity, "active-per-consumer-class."

**P3 — SHIP with riders.** The reference-consumer role is formalized with HTV
as default holder, changeable by owner decision without reconvening, logged
with reason. Riders adopted: release proof names two evidence sites —
reference-consumer activation evidence plus a virgin-project clean-room run
(that pairing is what 0.3.0 actually did); the holder may legitimately sit at
`ready_with_history_warnings` (OB-002-2) and activation evidence is judged
independently of the history lineage; the secondary consumer owes portability
evidence so it stays visible; a role transfer re-establishes activation
evidence at the new holder before the move counts, and fires P4's trigger;
and nothing in the role authorizes corpus adoption or mutation — OB-002-1
governs, supreme.

**P4 — AMEND, adopted as follows.** Codified under the corrected name
**single-owner candor precondition** (third-party sensitivity): candid
third-party capacity and morale intel stays in the durable signal stream and
briefs, with single-owner consumption as the named precondition. The trigger
fires on the earlier of an owner decision to extend the audience of briefs or
the durable signal stream beyond the owner, or any act of such disclosure —
and on a reference-consumer role transfer. Creation of delivery or update
postures does not fire it. The clause states the one-way boundary out loud:
at fire time the available remediation is forward scope limitation only —
the stream is append-only, no regeneration path exists (issue #6 is the
dependency), and redaction would itself be corpus mutation under OB-002-1.
The trigger binds to an observable surface: the declared distribution-posture
line that P2 item 4 adds to product truth.

**P5 — SHIP, ratified as implemented.** The record ratifies the mechanism,
not merely the outcome: init selects and names a channel-latest receipt that
the already-installed, human-installed approved runtime attests to; it never
installs a runtime, verifies every byte against the receipt, re-inspects host
resolution, pins exclusively, and unwinds only its own pin on failure. The
asymmetry principle is recorded in Marketing's sentence — **approval attaches
at publication; adoption is automatic at init and explicit thereafter** — so
bootstrap selection is never precedent for automatic updates. Scope notes
recorded: the guarantee holds on a machine whose approved runtime is current,
and init is bootstrap, not repair. Documentation reconciliation is an
enforcement-owed obligation: correct README's channel clause, rewrite the
Consumer Onboarding copy to stop teaching receipts, and state explicitly that
the channel carries only builds bearing release evidence (which, once P2 item
1 lands, includes activation evidence).

**Cutline** — rejected outright, not deferred ambiguously: an auto-updating
consumer class in the alpha; a fourth readiness severity; a per-ingest nag;
"active-per-consumer-class" as product vocabulary; any change to launch
posture (the record carries Marketing's non-claim clause: nothing in 003
entitles beta or "just works" claims).

## Proposed obligations (for owner ratification)

| Proposed ID | Kind | Substance | Trigger |
|---|---|---|---|
| OB-003-1 | enforcement owed | Issue #16: one maintainer release command, one consumer update command, driving the existing verified steps | the next release after ratification ships |
| OB-003-2 | enforcement owed | Readiness activation legibility: threefold mislabel rename; #26 collapse/verdict-view; `core_inactive` category with distinct verdict | before any new finding class ships |
| OB-003-3 | enforcement owed | Product-truth activation accounting: #23 widened to all four contradictions; `implemented`/`active-at-reference-consumer`; activation state derived from tool output | next release evidence cites it |
| OB-003-4 | check-in | Single-owner candor precondition | earlier of decision or act extending brief/signal audience beyond the owner; or reference-consumer role transfer |
| OB-003-5 | enforcement owed | P5 documentation reconciliation: README channel clause, Consumer Onboarding copy, channel-carries-evidenced-builds-only | before the next release's README update |
| OB-003-6 | check-in | Auto-update deferral: distribution-transition convening per Decision 35, brief carrying the four integrity preconditions | owner declares intent to broaden, or a distribution-transition plan is proposed |

Namespace note: these OB-003-x IDs are scoped to this project's board-log; the
`OB-003-3` cited in the owner's `~/.claude` registry documentation is a
different practice's row (Jobs seat catch).

## Questions the chair carries to ratification

1. **Trace3's nature.** Is it owner-operated with no other reader of its
   outputs? Three seats' P4 and P1 readings hinge on it. If any part of it is
   client work reported to others, P4's precondition needs assessment now.
2. **Decision 35 criterion 2.** What counts as a "drift incident," and what is
   the authoritative tally? The sunset gate is unmeasurable without it.
3. **Prior disclosure.** Has any brief or signal content already left the
   owner's machine in any form? P4's trigger design assumes no.
4. **Track 4 vs distribution.** Jobs seat, put plainly: is Track 4 still the
   next milestone track, or has the working priority become distribution? The
   record should state the answer.
5. **Delivery check (PM).** Has the owner actually read a real stakeholder
   brief produced at the reference consumer? If not, "running" and
   "delivering" diverge, and P2 item 1's wording should say which it means.
6. **Relay #4 triage.** Open, unlabeled, 25 days. The chair recommends
   triaging it into the backlog immediately, with #9 (its first-ranked ask) as
   the first acceptance proof of the P2 gate, and #22 fixed so the lane
   cannot silently drop the next report.
