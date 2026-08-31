# Record 003 — Brief: Consumer Classes, Update Policy, and the Adoption Path

Date: 2026-08-30
Mode: convene (amendment reconvening on record 002's Approved Runtime consumer policy)
Chair: orchestrator. Seats: five, blind, per charter.

## Exact question

Record 002 ratified one consumer policy for one consumer: an exact immutable
build pin, explicit update and approval actions, and a maintainer-only private
alpha. Since then, dogfooding produced three owner rulings that widen the
delivery model, and a second pinned consumer exists. The board is asked to
ratify, amend, or redesign the following five proposals as amendments to record
002's Approved Runtime consumer policy. Record 002's product definition,
milestone, and reference host are not in question.

### P1 — Consumer-class segmentation of update policy

Today every consumer records one exact immutable pin and every release requires
an owner-run repin per consumer (0.2.1 and 0.3.0 each required manual repins at
both consumers). Proposal: define two consumer classes — (a) the reference
consumer, fail-closed pinned exactly as record 002 ratified; (b) an
auto-updating class that tracks a named channel and adopts a newer published
approved build without a per-release owner ceremony, with the same receipt and
chain verification enforced at adoption time. The board decides whether class
(b) should exist at all in the private alpha, and if so what integrity
constraints bound it (verification at update time, provenance stamping,
rollback).

### P2 — Shipped-means-running adoption path (2026-08-06 owner ruling)

Ruling, verbatim intent: shipped means running. If core functionality is
built, deployed, and published, consumers HAVE it — no silent consumer-side
opt-in for features on the features-and-benefits list. Trigger: the identity
registry shipped implemented in 0.2.0 but never activated at the reference
consumer, while product-truth surfaces said "implemented" with no activation
state; readiness filed the absence at a severity everyone learned to ignore.
Fix shape proposed for ratification (engine work tracked as issue #15):

1. Release evidence must include activation evidence at the reference
   consumer; a release is not complete until the feature's behavior is
   observable there.
2. Init and post-update scaffold all required state; ingest completion
   triggers — or loudly nags — dependent derivation steps.
3. Readiness gains a core-inactive severity category distinct from
   optional/history.
4. Product-status distinguishes implemented from active-per-consumer-class.

### P3 — The reference consumer as a formal role

Record 002 named "the maintainer as the sole reference user." In practice the
HTV project is where "running" is measured: activation evidence, corpus
upkeep, and playbook derivation all live there, and the 0.3.0 measure of done
was demonstrated against it. Proposal: formalize the reference-consumer role —
the consumer where activation evidence is collected and shipped-means-running
is judged — with HTV as the default holder, changeable by owner decision
without a reconvening.

### P4 — Third-party redistribution boundary (2026-08-06 owner ruling)

Ruling: candid third-party capacity and morale intel stays in the durable
signal stream and in briefs, because the owner is the sole owner and sole
brief recipient and explicitly wants it. Boundary: the ruling is scoped to
single-owner consumption; if briefs ever gain other recipients or a consumer
class beyond the owner, redistribution sensitivity reopens. Proposal: codify
that boundary as a standing clause — single-owner consumption is a named
precondition of the current signal-inclusion policy, and the creation of any
recipient or consumer class beyond the owner is a check-in trigger, so the
question reopens by obligation rather than by memory.

### P5 — One-command init (2026-08-13 owner ruling, shipped in 0.3.0)

Ruling: `meeting-ingest init` in a virgin project must do the whole job —
verified install, workflow artifacts, channel-latest receipt selection,
exclusive pin, meetings-root scaffold — with the user never learning that
receipts, templates, or approved-executable markers exist; the ruling
explicitly rejects both "exempt init from the pin gate" and "better error
messages" as ceremony in disguise, and requires init to satisfy the
approved-runtime chain automatically, never bypass it. This is reported as
implemented: 0.3.0 shipped it, the measure of done was met (virgin project to
Ready with zero flags), and both consumers were repinned on it. The board is
asked to ratify the ruling into record 002's consumer policy — noting the
nuance it introduces: initial receipt selection at init is automatic
(channel-latest), while subsequent updates remain explicit actions per P1.

## Decision standard

Per charter: each seat renders SHIP / AMEND / REDESIGN per proposal (P1–P5),
with evidence. The chair synthesizes without vote counting. The owner
ratifies; owner deviations are legitimate and logged.

## Evidence-reconciled state (as of 2026-08-30)

- 0.3.0 released and installed: one-command init, project-over-user workflow
  artifact resolution, silent-CLI-error and fabricated-mismatch fixes;
  T2-verified with a security line item; deferred hardening tracked in #27.
- Two pinned consumers, both Ready: the HTV reference project (standing 177,
  ready-with-history-warnings lineage per OB-002-2, met) and a second consumer
  project (Trace3), onboarded 0.2.1 and repinned on 0.3.0.
- Identity registry active at the reference consumer: 17 reviewed entries,
  24 people / 39 merged IDs / 179 meetings, corpus-upkeep procedure wired into
  the consumer's CLAUDE.md.
- Backlog migrated to sanitized GitHub issues #6–#28 (label: backlog);
  relay lane clear; dogfood-hardening reframed as a recurrent workstream.
- Acceptance instrumentation hardening in flight this session: rule 6
  committed-scope-widening assertions S14/S15 landed (bb7591d); the acceptance
  evaluator is being promoted into the repository.
- Milestone context: Just Works Continuity remains the governing milestone;
  OB-002-1 (corpus adoption ratification) is open and untouched by this brief.

## Ratification scope

Adopted proposals amend record 002's Approved Runtime consumer policy and
create obligations on record 003. Record 002 remains ratified; it gains an
addendum pointing here for the amended clauses. Explicitly out of scope:
corpus adoption or mutation (OB-002-1 governs; a proposed adoption plan
convenes separately), the product definition, the milestone, the reference
host, and any change to the fail-closed verification chain itself.

## Cheaper alternative considered

Each ruling in P2, P4, and P5 was already made by the owner in a working
session — the cheap path (rule in the moment, record a capture) is how they
exist at all. What a capture cannot do is amend a ratified record: record
002's consumer policy still reads as a single pinned consumer class with
explicit-only updates, and three rulings now deviate from or extend it, which
the contract treats as a halting smell. P1 and P3 are direction-setting
questions with real design alternatives, squarely inside the charter's
convening triggers ("before changing the canonical roadmap or product
definition"). A single review or experiment cannot settle policy that binds
future releases; the reconvening is the only amendment path the practice
allows.
