# Record 003 — Seat 03 (Apple Engineer)

## 1. Verdict

Four of these five proposals are the record catching up to practice, and they should be ratified with modest tightening. One — P1's auto-updating consumer class — is a different animal: it proposes, inside the private alpha, the exact end state that `DECISIONS.md` §35 already scheduled behind three named exit criteria, none of which are met. More importantly, the current chain's trust anchor for the word "approved" is not a signature; it is a human action. `pin_runtime` will only write a pin that the *already-installed, human-installed* runtime attests to (`src/meeting_ingest/runtime_release.py:721-733`). Every automatic step in the system today is downstream of an owner having typed `uv tool install`. P5 preserves that anchor exactly. P1(b) deletes it and puts nothing in its place — receipts carry `approved_by` as free text with no signature field (`_RECEIPT_KEYS`, `runtime_release.py:51-53`; `create_receipt`, `runtime_build.py:454-489`).

There is also a topology problem that I do not think has been surfaced: consumer classes with divergent update cadence are **not currently expressible**. There is one `meeting-ingest` install per machine, one console script, and every consumer pin records that absolute path and the embedded build id. The moment an auto-updating consumer causes build N+1 to be installed, the reference consumer pinned at N fails closed (`runtime_pin_mismatch`, forced to `blocker` at `readiness.py:454-459`). Class (b) does not coexist with class (a) — it breaks it. That is a design finding, not a policy preference.

So: P5 SHIP, P2/P3/P4 AMEND, P1 REDESIGN.

## 2. Evidence

### P1 — consumer-class segmentation

**Against the proposal as drafted, from the record itself:**

- `DECISIONS.md:375-387` (Decision 35) already rules on this. The sunset fires when *all three* hold: (1) Just Works Continuity met, (2) three consecutive releases with zero drift incidents, (3) owner decides to broaden beyond the maintainer-only alpha. It then says: *"Until the sunset fires, record 002's clauses stay binding, and the interim relief is mechanical, not contractual."* And: *"Whether client-work consumers retain any explicit-update posture is decided by that board convening, not presumed."*
- Criterion 1 is explicitly unmet — `docs/product-status.md:63`: *"The Just Works Continuity milestone also requires Track 4 and is not met."*
- Criterion 2 is unmet and recently so. `README.md:304` records that `workflow_hash_mismatch` *"bit the `gb37a12a0502e` release once before the project-level copies were re-targeted"* — that is the 0.2.1 build. `DECISIONS.md:359` records the 2026-07-25 receipt-drift catch. Issue #17 records the Codex skill pair drifting silently for three days. At most one clean release stands since.
- Criterion 3 is unmet: still a maintainer-only private alpha; both consumers are the owner's.
- Decision 35 names the target mechanism precisely: *"attestation verification (the receipt's data, **published and signed**) runs invisibly inside the updater."* P1 as drafted asks for the invisibility without the signature.

**The topology constraint (code evidence):**

- `pin_runtime` (`runtime_release.py:721-733`) rejects any receipt whose `build_id`/`source_commit`/`source_tree_sha256`/`semantic_version` differ from `BUILD_INFO`, and requires `build_kind == "approved-candidate"`. A pin can only be written *by the build it names*.
- `pin_runtime:738-749` requires `approved_executable == invoked_executable`, both absolute, and persists that path into the pin (`runtime_config` pin schema; `docs/artifact-contract.md:121`).
- `inspect_runtime:685-692, 744, 764-781` compares the pin against `BuildIdentity.embedded()` — the single installed distribution — and emits `runtime_pin_mismatch`, classified `blocker` at `readiness.py:454-459`.

Consequence: for two consumers on one machine to sit on different builds, you need side-by-side installs with distinct console-script paths, distinct rendered `SKILL.md` copies (feasible — the template has exactly one substitution marker, `runtime_release.py:776-783`), and a redesigned notion of "the approved executable." That is a distribution redesign, not a policy amendment.

**For the proposal's underlying complaint — it is real and well-evidenced:**

- Staleness has no pressure whatsoever. `update_available` is emitted as an **advisory** (`runtime.py:839-847`), and advisories never move the verdict (`readiness.py:183-195`). A consumer can sit arbitrarily far behind and still print `ready`. That is the same "severity everyone learned to ignore" pathology P2 was convened over, sitting inside the update chain.
- Issue #16 already scopes the correct relief: *"one maintainer release command, one consumer update command… neither bypasses the fail-closed approved-runtime chain."* Decision 35 blesses exactly this as the interim.
- The per-release repin burden is genuine: `README.md:304` shows step 5 must be repeated per consumer for project-level copies, or the pin fails.

### P2 — shipped-means-running

Strongly supported, and the mechanism of the original failure is reproducible in code:

- A shipped-but-inactive identity registry surfaces through `_HISTORY_ISSUE_CODES` → `historical_identity_gap`, `category="history"`, `severity="warning"`, with remediation text that literally reads *"it does not block the next safe write"* (`readiness.py:60-77, 413-423`). It is then indistinguishable from a legacy corpus artifact, and any warning collapses into the single `ready_with_history_warnings` verdict (`readiness.py:190-192`).
- The product-truth contradiction P2 names is live and citable: `docs/product-status.md:87` still asserts *"no schema 1.1, identity-registry, … code has shipped,"* while the brief records 17 reviewed entries and 179 meetings at the reference consumer. Issue #23 tracks it.
- Item 2 has a real seam: `init_project` (`paths.py:99-115`) scaffolds `runtime_directories()`, which already includes `playbook_state` (`paths.py:50-61`) — the 0.2.1 partial landing — and `pipeline.initialize` already re-scaffolds on an existing pin (`pipeline.py:193-197`).
- Item 1 is consistent with existing practice: release-evidence acceptance on a frozen build is already the standard the project holds itself to (`product-status.md:56`).

### P3 — reference consumer as a formal role

- De facto already true in product truth: `product-status.md:73` reports the HTV consumer as where the approved frozen wheel + pin + end-to-end fresh transcript was demonstrated; `product-status.md:54` records the 0.3.0 pins for both consumers.
- The 177-finding lineage and OB-002-2 are both anchored at HTV (`board-log.md:16`).
- Nothing in code depends on consumer identity, so the role is pure policy — cheap to formalize, cheap to move.

### P4 — third-party redistribution boundary

- The load-bearing engineering fact: **there is no implemented retraction path.** `product-status.md:349` — semantic correction *"requires the contracted regeneration path… and is not implemented; no second semantic-correction design exists."* `docs/artifact-contract.md:411` — *"a reviewed semantic defect in existing output stays recorded as evidence and the output stays as generated."* Signals are append-only and fingerprint-bound (`artifact-contract.md:1296`).
- Editing the corpus to remove candid intel later would itself be corpus mutation, forbidden without a fingerprinted adoption plan and separate owner approval under OB-002-1 (`CLAUDE.md`, `board-log.md:15`).
- Decision 34's privacy boundary (`DECISIONS.md:373`) already establishes the pattern of naming a precondition explicitly rather than trusting memory.

### P5 — one-command init

The strongest proposal on the slate, and its safety is structural rather than incidental. `bootstrap_consumer_runtime` (`runtime_release.py:957-1039`):

- refuses if any pin exists, and writes the pin with `O_EXCL` (`_create_atomic_exclusive`, line 1023);
- selects channel-latest, re-verifies the receipt SHA against the manifest, and enforces unsymlinked descent and containment (`_latest_published_receipt:820-850`);
- requires a frozen, RECORD-valid install and — decisively — `inspection.receipt["match"]`, i.e. **the running embedded build must already equal the channel-latest receipt** (`_require_approved_frozen_install:868-902`);
- derives the executable from the distribution's own recorded console script and refuses a wrapper (`_approved_console_script:905-923`);
- requires the receipt's wheel published beside it and hashes it (`_require_published_wheel:853-865`);
- installs the workflow artifacts through the same receipt-verified installer, then **re-inspects** to confirm the session resolves exactly those bytes (`_require_installed_workflow_resolves:932-954`);
- unwinds only its own pin on failure, matched by SHA so a concurrent explicit repin is never clobbered (`pipeline.py:181-192`).

The automatic act is *naming* the receipt the human already installed. If channel-latest is not the installed build, init fails closed with `runtime_build_mismatch` and tells the operator to install the named wheel. Init never installs a runtime. That is the correct place to draw the line, and it is drawn correctly.

## 3. Gaps and risks

**G1 — P1's auto-update would break the fail-closed class it is meant to coexist with.** Single install, single console script, exact-build pins. Installing N+1 for the auto class blocks every consumer still pinned at N. Not a tuning issue; a topology issue.

**G2 — P1 removes the only trust anchor and substitutes nothing.** Receipts are unsigned JSON in a user-writable app-data root. Today that is fine, because adoption requires a human decision each time; the human *is* the signature. Auto-adoption promotes an unsigned local store to sole authority. Decision 35 anticipated this by specifying *signed* receipts for the end state.

**G3 — self-update from inside the running process has no rollback command.** The channel manifest retains prior receipts (`publish_approved_runtime:648-665`) and `artifact-contract.md:133` describes rollback as *"explicitly reinstalls a retained prior wheel and reruns `runtime pin`"* — a runbook, not a command. A partially applied auto-update leaves every consumer on the machine blocked with no scripted recovery. Manual recovery is acceptable when a human initiated the change; it is not when a machine did.

**G4 — auto-update rewrites files inside consumer working trees, possibly mid-session.** `install_workflow_artifacts` writes `.claude/skills/meeting-ingest/SKILL.md` and `.claude/agents/meeting-ingest-session-provider.md` under the consumer root (`runtime_release.py:36-37`, `994-995`). Those files define the workflow the *currently running* host session is following. An unattended rewrite mutates an agent's instructions underneath it and produces unexplained uncommitted diffs in a client repo at arbitrary times. This is not theoretical: `DECISIONS.md:359` records that a direct edit to that very file fail-closed an HTV ingest.

**G5 — the release store's canonical location is undecided.** Issue #14.4: the app-data root moved between 0.2.0 (`~/.local/share`) and 0.2.1 (`~/Library/Application Support`). "Channel-latest" is only well-defined once that root is settled. This is a mild caveat for P5 and a hard precondition for P1(b), which would resolve the store without a human present.

**G6 — `update_available` is an advisory, so a consumer can be arbitrarily stale and still report `ready`.** This is the real defect P1 is reacting to, and it is fixable without any auto-update.

**G7 — P2 item 2's scaffolding will be dead exactly when it is needed.** In `pipeline.initialize`, the virgin path runs `init_project` *before* `require_write_readiness` (lines 179-180); the already-pinned path runs readiness *first* and raises on `blocked` (lines 194-197). If a future release adds required state whose absence blocks, init can never scaffold it. Post-update scaffolding must run ahead of, or be exempt from, the write guard — the bootstrap branch already shows the correct shape.

**G8 — P2 item 3 is a category problem, not a severity problem.** The severity ordering `{"blocker":0,"warning":1,"advisory":2}` is hardcoded in at least three places (`readiness.py:478`, `runtime.py:908`, `artifact-contract.md:213`, which freezes the sort as a contract). Adding a fourth severity is a contract change with wide blast radius; adding a `core_inactive` **category** plus a distinct verdict is contained and achieves the goal.

**G9 — P4's trigger is unenforceable as drafted.** "Creation of any recipient beyond the owner is a check-in trigger" relies on someone remembering — the identical failure mode P2 exists to fix. And because there is no regeneration path (§2, P4), widening the audience is **irreversible**: candid intel already in the signal stream cannot be redacted without corpus mutation forbidden by OB-002-1.

**G10 — P3 makes the second consumer evidence-invisible.** Trace3 is currently the only evidence that the product works somewhere other than the reference project. If only the reference consumer carries an evidence obligation, portability regressions ship unobserved.

**G11 — P3 routes release evidence through the consumer holding private client corpus.** Activation evidence must be defined as verdict/count/build-id metadata. Without that clause, "release evidence includes activation evidence" quietly authorizes pulling client-derived content into release artifacts, against Decision 34's privacy boundary and OB-002-1.

**G12 — residual bootstrap hardening (issue #27) is acceptable now, and is a precondition later.** Executable identity is established from the install's own RECORD, and concurrent bootstraps can interleave install and pin. Today the failure mode is fail-closed detection, and a human is present. Both must close before anything adopts a build unattended.

## 4. Recommendations, in priority order

1. **Do not create an auto-updating consumer class in the private alpha.** Ratify instead that Decision 35's three exit criteria are the gate, and record that none are currently met.
2. **Fix staleness pressure instead — this is the cheap fix that addresses the real complaint.** Promote `update_available` from advisory to a first-class, tiered signal: advisory when the channel is one build ahead, a warning past a named threshold (releases or days), so a stale consumer stops printing a clean `ready`. Pure readiness change; no chain change; no contract deviation.
3. **Ship issue #16 as the sanctioned relief**: one maintainer command wrapping build→publish→install→repin, one consumer command wrapping fetch→verify→install→repin. Decision 35 already authorizes this as mechanical, not contractual. It removes the ceremony that motivated P1 while keeping the human's finger on the trigger.
4. **If the board wants a class taxonomy now, make it about evidence obligations, not update policy.** "Reference consumer" (activation evidence, shipped-means-running judged here) versus "secondary consumer" (portability evidence, onboarding proof). Both stay fail-closed pinned. This gives P1 and P3 a coherent joint shape with zero integrity cost.
5. **Ratify P5 by mechanism, not merely by outcome.** State in the amendment *why* automatic selection is safe: init selects a receipt, never a runtime, and can only pin a build the running approved install already attests to. Ratifying the outcome alone silently pre-authorizes a future "init should just install it too."
6. **Amend P2 item 3 to a `core_inactive` category with its own verdict** (e.g. `ready_core_inactive`), not a fourth severity — see G8. Amend item 2 so scaffolding runs ahead of the write guard (G7), and so "loudly nags" is a typed finding with a code and a remediation, never prose in human output.
7. **Amend P2 item 1** to state that activation evidence is verdict/count/build-id metadata from the reference consumer, never corpus content (G11).
8. **Amend P4's trigger to be observable and to fire on intent.** Bind it to a declared distribution state in a product-truth surface whose change is the trigger, and word it to fire when a second recipient or consumer class is *decided on*, not when one first reads a brief. Add a sentence recording that the boundary is one-way: the signal stream is append-only and no regeneration path exists, so a late reopening cannot be remediated by redaction.
9. **Amend P3** to name the non-reference consumer's evidentiary job (portability) so the second consumer stays visible, and to state that moving the role requires re-establishing activation evidence at the new holder before the move counts.
10. **Record the four integrity preconditions for any future auto-adopting class**, so the next board is not relitigating from scratch: (a) signed receipts with published verification keys — Decision 35 already says "published and signed"; (b) side-by-side versioned installs with per-build executables, or an explicit ruling that all consumers on a machine move together; (c) a first-class `runtime rollback` command exercised in a drill, not a runbook; (d) issue #27 closed and issue #14.4's canonical app-data root settled.
11. **Close issue #14.4 (canonical release-store root) before the next consumer onboards.** It is cheap now and load-bearing for everything above.

## 5. What to stop, defer, or simplify

- **Stop**: treating P1(b) as an amendment. It is the Layer 5D distribution transition arriving early and under-specified. Decision 35 names the instrument that unlocks it — a *distribution-transition plan* — and no such plan is attached to this brief.
- **Defer**: per-class update cadence until side-by-side installs and signed receipts exist. Deferring costs the owner a handful of repins per release; shipping it early costs the fail-closed guarantee that is currently this product's most differentiated property, and that has already caught two real drifts in the field.
- **Defer**: any notion that the reference consumer's role is technically enforced. Keep it policy-only. Nothing in the engine should learn consumer identity.
- **Simplify P2** to the two items with a real seam and real evidence — the `core_inactive` category and activation-state accounting in product-status (issue #23) — and let items 1 and 2 follow, rather than ratifying four items of uneven readiness as one block.
- **Simplify P1 to one sentence** in the amended policy: every consumer stays exactly pinned and fail-closed; the class distinction governs what evidence a consumer owes, not what runtime it selects.
- **Do not** widen scope into OB-002-1 territory. P2's "activation evidence" and P3's "corpus upkeep lives there" both graze corpus adoption; the amendment should say plainly that neither authorizes reading, adopting, or mutating corpus content.

## 6. Decision

| Proposal | Decision | One-line basis |
|---|---|---|
| **P1** — consumer-class segmentation of update policy | **REDESIGN** | Class (b) is Decision 35's sunset arriving before all three of its exit criteria, without the signed receipts that decision specifies, and it is not expressible on a single-install topology without breaking class (a). Redesign into: classes govern evidence obligations, both stay pinned; fix staleness pressure; ship issue #16's two commands as the relief. |
| **P2** — shipped-means-running adoption path | **AMEND** | Direction correct and the failure mechanism is reproducible in `readiness.py`. Amend: `core_inactive` as a category with its own verdict rather than a fourth severity; scaffolding must run ahead of the write guard; nags must be typed findings; activation evidence is metadata, never corpus content. |
| **P3** — reference consumer as a formal role | **AMEND** | Ship the role — it is already de facto true and costs nothing technically. Add two clauses: the non-reference consumer owes portability evidence, and activation evidence is verdict/count/build-id metadata only. Lightest amendment on the slate; I would not block on it. |
| **P4** — third-party redistribution boundary | **AMEND** | Codify it, but a memory-based trigger repeats the exact pathology P2 is fixing. Bind the trigger to an observable declared distribution state, fire it on intent rather than access, and record that the boundary is one-way because the signal stream is append-only and no regeneration path exists. |
| **P5** — one-command init | **SHIP** | The automatic step names a receipt the already-installed approved runtime attests to; init never installs a runtime, verifies every byte it writes against the receipt, re-inspects host resolution, and unwinds only its own pin. Ratify the mechanism explicitly, not just the outcome. |

## 7. Confidence and unresolved questions

**High confidence:**
- P1's topology finding. Read directly from `pin_runtime`, `inspect_runtime`, and `readiness.py`'s blocker classification.
- P5's safety property. `_require_approved_frozen_install` gates on `inspection.receipt["match"]`; init cannot pin a build that is not running.
- P2's severity-collapse mechanism and the `product-status.md:87` contradiction. Both directly citable.
- P4's irreversibility. No regeneration path is implemented, by the project's own status doc and artifact contract.

**Moderate confidence:**
- The drift-incident count against Decision 35 criterion 2. I count three drift events in the record (2026-07-25 receipt drift, `gb37a12a0502e` workflow mismatch, the Codex skill pair's three-day silent drift) and cannot cleanly tell from the repo whether 0.3.0's release was itself drift-free end to end. My conclusion — criterion 2 unmet — holds under any reading, but the exact tally is the owner's to confirm.
- G7 (scaffolding dead when blocked). Read from `pipeline.initialize`'s two branches; I did not construct a failing case, and no such required-state blocker exists yet, so this is a forward-looking constraint rather than a present bug.

**Unresolved, for the chair or owner:**

1. **Is Trace3 owner-operated?** My P4 reading assumes yes. If any part of Trace3 is operated by or reported to someone other than the owner, P4's precondition is *already* breached and the question reopens now, not on a future trigger.
2. **What actually motivates P1 — cadence or ceremony?** If the pain is per-release repin labor, issue #16 solves it entirely with no contract change. If the pain is that consumers can silently sit stale, recommendation 2 solves it. If the pain is genuinely "I want to stop deciding," that is the sunset, and it needs a distribution-transition plan. The brief does not distinguish these, and the right answer differs sharply per case.
3. **Will consumers ever live on different machines?** Everything I concluded about topology assumes one machine, one install. Multi-machine changes the analysis materially — arguably for the better, since side-by-side becomes free — and should be stated in the amendment either way.
4. **Does `--development-override` interact with the class taxonomy?** `pipeline.initialize:174` skips bootstrap entirely under an override. If classes are ratified, the record should say plainly that the override is orthogonal to class and never a path into a different update posture.
5. **Should P1/P3's class creation fire P4's trigger?** As drafted, P4 fires on "a consumer class beyond the owner." Creating *classes* (P1/P3) is not creating consumers beyond the owner, but the wording invites conflation in both directions — spurious firing now, or a future reader believing the trigger was already discharged. It needs one clarifying clause.
