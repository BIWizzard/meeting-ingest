# Session Wrap - dogfood-hardening

- Wrapped at: 2026-08-06T20:34:36.991Z
- Workstream: dogfood-hardening
- Lifecycle: active
- Mode: design

## Summary

Dogfood-hardening session spanning 8/03-8/06: triaged relays #2 and #3 (both labels dropped by filer permissions — twice-observed lane gap), owner-verified extraction spot-checks on both (clean; rule 4 exercised correctly both times), and ran the Wispr Flow A/B analysis (zero-signal defect, extraction recall variance under noisy VTT, person-ID splits, VTT 2.5x input cost). Executed owner-approved HTV corpus cleanup (140 duplicate raw sources deleted after per-file hash verification, Wispr duplicate artifact quarantined, 46 legacy files to _legacy/, root 214→168). Built and T1-reviewed tools/gen-views.sh + refresh-views.sh (by-month/by-series/by-person derived views; P1 path-traversal finding confirmed exploitable and fixed; all reruns byte-identical). Discovered Layer 5A identity registry AND Layer 5B Stakeholder Briefing V1 are implemented in the shipped build but never activated at HTV — no scaffolding, no derivation run, readiness filing it as 'optional'; owner ruling captured: shipped means running, no silent opt-in for core features, HTV is the show horse and default recipient. Registry seeded at _playbook-state/stakeholders.toml (15 entries, proposed). Roadmap orientation delivered: the plan's five-step sequence is effectively built; delivery, not development, is behind. Session ended mid-activation on UI friction: the 28-merge review table did not render for the owner. Owner-approved and NOT YET APPLIED: nine bare-name merges (person-jf/kushali/ken/baba/mark/josh/jake/dilip/rayna into their obvious targets) plus person-reina into Rayna. Owner-authorized and NOT YET EXECUTED: the full 0.2.1 release ceremony.

## Continuation

Resume with: Add rule 6 framing-restraint detection to the semantic-integrity fixture, using attempt 2's concrete failing case: a committed action item whose scope exceeds what its owner accepted, with the owner's narrowing (Alerting change only) and self-summary (alerting change is mine by Friday) both in the transcript.

## Active Files

- docs/sessions/2026-07-29-guidance-1_1-release-evidence-acceptance.md

## Changes This Wrap

### Open questions

```text
+ Approve the 28 proposed registry merges (61 IDs → 33 people) with the two canonical corrections (person-jean-francois-harden spelling, person-rayna-gollapalli order)? Table pending re-presentation in a readable form.
```

### Next actions

```text
+ Resume activation first: write the 28-merge registry review table to a file and send it to the owner as a document (inline markdown tables did not render — do not repeat that), collect approval including the two canonical corrections (-harden spelling, rayna-gollapalli order); apply the ALREADY-APPROVED merges (nine bare-name IDs plus Reina→Rayna) to _playbook-state/stakeholders.toml regardless; then execute the authorized 0.2.1 release ceremony per README Release Flow (bump commit → build → publish → uv tool install → workflow installs to ~/.claude AND HTV .claude → pin → readiness verify → commit ~/.claude artifacts in-flow); then run the first playbook update at HTV and show the owner a real brief.
```

## Next Actions

- Add rule 6 framing-restraint detection to the semantic-integrity fixture, using attempt 2's concrete failing case: a committed action item whose scope exceeds what its owner accepted, with the owner's narrowing (Alerting change only) and self-summary (alerting change is mine by Friday) both in the transcript.
- Add the attribution assertion class proposed after attempt 1: a narrative field naming a speaker as a statement's source must agree with the evidence rows cited for the same item.
- Promote the acceptance evaluator into the repository next to the fixture it executes; working copy preserved at /private/tmp/meeting-ingest-acceptance-evaluator.
- Release the generated_by fix: cut a 0.2.1 version-bump commit (the one open prerequisite), then build/receipt/publish/install/repin per the release flow. Two consumer runs (relays #2, #3) provide release evidence; closes issue #2 and observation 1 of issue #3. Update the product-status acceptance-on-frozen-build wording after repin.
- Fold committing the receipt-installed ~/.claude artifacts into the release flow so each release stops regenerating the false hand-edit signal that misled the relay twice.
- Add a drift check for the non-receipt-managed Codex skill pair to the suite or a hook; it drifted silently for three days once already.
- Convene the North Star board on the widened record 002 amendment brief: (a) the update-policy segmentation from cap_20260727T024600Z (HTV fail-closed pins; general consumers auto-updating with invisible attestation), and (b) the shipped-means-running adoption-path principle from cap_20260806T183402Z: a release is not complete until the feature's behavior is observable at the reference consumer; no silent consumer-side opt-in for core functionality.
- Date-gate, reframed by relay #3: the skill-level ask works (manual override saved two runs from mtime mis-dating) but the engine forces mint-then-abandon with a raw rm in _cache; add --meeting-date to session-inbox or an abandon-handoff subcommand.
- Artifact-contract status vocabulary, widened: define enumerated statuses for Decisions, Stakeholder Asks, Dependencies AND the signal JSONL status field (live free-text evidence: 'declined by Ken', 'rejected alternative'); also pin the meeting_type enum spelling ('working session' vs 'working_session' drifts run-to-run on the same build).
- Spot-check extraction quality on the six 2026-07-25 HTV meetings, the 2026-07-24 retention-policy artifact and the 2026-07-28 AdBook artifact under guidance 1.1; three 2026-08 artifacts are already owner-verified clean; add the 2026-07-20 standup with 12 null/Unresolved attendee rows as a target.
- Model-pin evidencing, reframed by the 8/03-8/04 artifacts: model_id is provider-self-reported and inconsistent across runs on the identical frozen build (claude-code-session vs claude-opus-5[1m]); decide what the engine can attest, and rule whether claude-opus-5[1m] satisfies the plain claude-opus-5 pin.
- Triage three engine observations: pin_runtime resolves workflow files from <root>/.claude while inspect_runtime uses ~/.claude; runtime_provenance source_commit and source_tree_sha256 are null on a clean editable checkout; doctor and status reject a subcommand-level --development-override that five other commands accept.
- Optionally implement the Layer 5D interim relief: one maintainer command wrapping build/receipt/publish/install/repin and one consumer runtime-update command wrapping fetch/verify/install/repin.
- Path-resolution family fix (relays #2 obs 2, #3 obs 3): validate-response --source and provider-request --source both resolve relative paths against CWD while session-inbox prints meetings-root-relative; centralize meetings-root resolution and surface failures as a path-resolution error naming both candidates instead of unexpected_error.
- Zero-signal guard (Wispr A/B headline): an empty signal stream passed validation silently on a meeting whose own tables held 8 commitments/6 asks/9 risks; add a consistency check that flags or fails empty signals when decisions/commitments are non-empty.
- Activate Layer 5A at HTV: registry seeded at _playbook-state/stakeholders.toml (15 entries, all status=proposed, 61 IDs to 33 people) — owner reviews the proposed merges when ready (three flagged calls: john-francois inference, hardan/harden canonical spelling, gollapalli-rayna ID order; ten bare-name IDs deliberately left out); run the first playbook derivation to exercise candidate surfacing; wire refresh-views.sh plus candidate review into the HTV session workflow.
- Engine adoption path (shipped-means-running ruling): init and post-update scaffold required state (_playbook-state, registry skeleton); ingest completion triggers or loudly nags playbook derivation; readiness gains a core-inactive severity category distinct from optional/history; product-status distinguishes implemented from active-at-reference-consumer; release evidence includes activation evidence. Engine also: extraction-time registry hints so extraction stops re-minting advisory IDs for reviewed people, and Layer 5A's two remaining integration items.
- Attendee-table raw-label fidelity for non-VTT sources: the Wispr artifact renders Raw Speaker Labels as Unknown although the transcript carries explicit name labels.
- Cache retention policy for provider request/response pairs: both 8/04 run pairs were deleted while a stray 2026-07-07 response survives, and relay issue #3's cited evidence paths no longer exist; decide retention and make it consistent.
- Promote markdown transcript sources from tolerated to documented (owner priority — removes transcript-chasing for meetings others own): name the accepted format, add Wispr Flow guidance (canonical display names in the manual speaker-identify step; expect the manual date gate; check the signal count until the zero-signal guard ships).
- Relay lane label fix, twice-observed: widen the triage poll to also match the 'Relay:' title prefix and have file-dogfood-relay verify the label landed; granting the Hearst account triage permission is the owner's call.
- Fix the product-status self-contradiction: the Signals And Ledger section's 'Not complete' list still names the reviewed identity registry, derivation-time resolution, and Stakeholder Briefing aggregation, which the Layer 5A/5B sections record as implemented — the stale section is part of why the owner could not tell where the product stood. While there, add activation-state accounting per the shipped-means-running ruling: every feature row carries implemented vs active-at-reference-consumer.
- HTV is the reference consumer and show horse (owner ruling 2026-08-06): every feature ships active to HTV unless explicitly scoped away from it. Fold this consumer-class default into the record 002 board brief alongside shipped-means-running.
- Resume activation first: write the 28-merge registry review table to a file and send it to the owner as a document (inline markdown tables did not render — do not repeat that), collect approval including the two canonical corrections (-harden spelling, rayna-gollapalli order); apply the ALREADY-APPROVED merges (nine bare-name IDs plus Reina→Rayna) to _playbook-state/stakeholders.toml regardless; then execute the authorized 0.2.1 release ceremony per README Release Flow (bump commit → build → publish → uv tool install → workflow installs to ~/.claude AND HTV .claude → pin → readiness verify → commit ~/.claude artifacts in-flow); then run the first playbook update at HTV and show the owner a real brief.

## Blockers

- No corpus adoption or mutation is authorized; a deterministic fingerprinted adoption plan requires later owner approval (OB-002-1).

## Open Questions

- Should installed workflow artifacts carry a receipt or build stamp of their own? Today the installed agent doc and skill have no content stamp, so there is no local way to tell whether a copy still matches the receipt that placed it, and a hand-edit would be undetectable from the consumer side. This surfaced from an inbound ~/.claude relay that could not distinguish an installer write from a hand-edit.
- Should docs/claude-skills/meeting-ingest/SKILL.md quote a single published rule source rather than restate the semantic guidance rules verbatim? Five surfaces now duplicate the rule text, and a parity test guards it in this repo, but the duplication remains a standing drift risk raised by the ~/.claude relay.
- Does morale or capacity language about a named third party belong in the durable signal stream at all? The 2026-07-28 HTV artifact persists a colleague capacity state as a high-confidence risk_or_concern signal feeding signal JSONL, playbook derivation and briefings; the rendering softened the verbatim appropriately, so the question is inclusion rather than wording, and it may be a board matter rather than a guidance tweak.
- Should the acceptance evaluator live in the repository? It has now been written ad hoc three times because it lives in session scratchpad, and a different instrument per run weakens comparability across runs even when every tally reads 18/18. It is the instrument that decides milestone proof.
- Approve the 28 proposed registry merges (61 IDs → 33 people) with the two canonical corrections (person-jean-francois-harden spelling, person-rayna-gollapalli order)? Table pending re-presentation in a readable form.
