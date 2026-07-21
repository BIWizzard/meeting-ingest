# Chairman Report

## Overall Board Verdict

**Unanimous:** Meeting Ingest is a credible, useful ingestion engine and an unproven low-ceremony product experience.

The board found real product value in the generated meeting record and real engineering strength in validation, provenance, content-hash idempotency, failure handling, archive, reconcile, and retry. It also found that the intended primary experience—ask an active agent to process a meeting and receive a trustworthy result—still exposes too much mechanism and has not passed fresh-consumer proof after the most recent response-contract remediation.

The current release posture is **internal/private alpha for a technical owner**, not public beta, general self-service, or entitled to a claim that it just works.

This report proposes a direction. It does not replace the canonical roadmap. Human approval is required before roadmap or implementation state changes.

## Post-Board Owner Evidence

After all five independent reports and the original synthesis were complete, the owner corrected an important omission: Meeting Ingest's only true power user is the maintainer, and the sustained real-use corpus lives primarily in the HTV IQ Data Analytics project for Hearst, with additional historical output in Spelman.

Read-only inspection found 190 top-level meeting Markdown files, 173 physical ledger lines, 118 signal files, 118 processed sources, and 138 `_done` sources in HTV. The current engine recognizes 38 sources and 92 valid ledger records, reports 81 legacy signal-contract issues and two stale handoffs, and has 31 identity candidates but no reviewed people or current briefing. Spelman contains two historical meeting artifacts but is not initialized for the current engine.

This evidence was not available to the independent seats and does not retroactively alter their reports. It does revise the operational conclusion: the six-meeting repository corpus is a current-engine reference sample, not the full dogfood history. Just Works Ingest must include a read-only reckoning of the power user's accumulated HTV and Spelman history. See [Owner Addendum](08-owner-addendum.md).

## Consensus

### Unanimous conclusions

All five seats concluded:

1. The product has a clear core value: it turns raw transcripts into useful, inspectable project records rather than producing disposable summaries.
2. The engine's strong done process is real and differentiating.
3. The normal active-agent experience is not yet simple or independently proven.
4. One named host and one canonical path must be selected before broader host or audience claims.
5. The product must not claim general self-service, platform-wide readiness, alternate output modes, or proven Stakeholder Briefing value today.
6. Broader source, provider, playbook-guidance, identity, migration, and iQ Context expansion should freeze until the primary workflow passes a measurable gate.
7. README, product status, roadmap, CLI language, questions, and active state have material truth drift that must be reconciled.
8. The next board review should happen at the primary-workflow gate, not after another feature layer.

### Majority conclusions

At least four seats recommended:

- a **Just Works Ingest** or equivalent core-trust milestone next;
- post-fix fresh-consumer UAT with no source inspection or hand-edited provider JSON;
- clearer first-run installation, configuration, consent, and completion guidance;
- one canonical user surface with lower-level handoff commands treated as integration/recovery interfaces;
- `doctor` severity that distinguishes blockers, recoverable incomplete state, and advisories;
- narrowing current claims to one technical audience, three formats, one host, and summary-plus-verbatim;
- allowing the already-started cleanup/corruption-recovery slice to finish its existing review only as bounded integrity work, without reopening Layer 5 expansion.

## Disagreements And Seat-Specific Judgments

### Engineering trust depth

The engineer seat found additional release risks not raised as board-wide blockers by every seat:

- non-atomic multi-file/ledger commit windows;
- signal fingerprints not checked by `doctor` and no artifact fingerprint contract;
- inert config keys: `auto_init`, `reconcile_after_success`, and `cache_normalized_transcript`;
- no guarded stale-lock recovery;
- uncontained configured paths;
- weak provider-scalar/YAML hardening;
- no resource limits or explicit retention model;
- a remote adapter without production retry/backoff evidence.

Chairman disposition:

- **Accepted into the next trust gate:** resolve or remove inert config; add safe stale-lock recovery; harden provider scalar rendering; define retention/privacy behavior; failure-inject and provide deterministic recovery for known commit windows.
- **Conditionally accepted:** artifact/signal byte-integrity verification. First decide whether generated Markdown is an immutable engine artifact or a user-editable project document. Signal fingerprint verification is already implied by the recorded fingerprint and should be included; artifact hashing depends on the chosen mutability contract.
- **Deferred from the first milestone:** generalized untrusted-config threat hardening, broad resource-limit policy, and production hardening of the Anthropic adapter, provided the first supported posture is explicitly session-only and trusted-project-local.

### Output modes

Seats agreed alternate modes are not current capability. They differed on timing:

- product management placed Explicit Output Integrity after Just Works Ingest;
- other seats were willing to defer modes until usage proves priority.

Chairman disposition: remove/narrow current claims immediately after approval. Keep mode implementation, title repair, and regenerate as the second milestone candidate, but require post-gate usage evidence before fixing its precise order against Stakeholder Briefing proof.

### Exact UAT sample

The product-manager seat proposed at least three fresh-project trials and six real sources spanning all three formats. Other seats required post-fix fresh-consumer proof without specifying the same count.

Chairman disposition: accept three trials/six sources as the proposed measurable gate. At least one operator must not be the primary implementation author. If privacy limits independent operation, record why and obtain an equivalent blind-run review.

### Existing cleanup/corruption-recovery work

No seat treated the dirty-worktree slice as released. Most allowed it to finish the prepared review as bounded reliability completion; immediate-freeze language could also be read to stop it.

Chairman disposition: allow the existing follow-up review and, if accepted by the human owner, close that already-started integrity slice. Do not add further contradiction or Guidance work. This is carryover closure, not the next product milestone.

## Personal Chairman Judgment

My judgment is that Meeting Ingest's original vision is still correct and more compelling than the current roadmap makes it appear:

> Meeting Ingest turns transcript files into trustworthy project records—summary, decisions, actions, evidence, and source history—in one agent request.

The product's soul is not platform neutrality, JSON contracts, or stakeholder derivation. Those are enabling choices. The soul is that a meeting becomes durable, useful project memory and the user can trust that it is done.

The current roadmap is no longer the right operational roadmap because it rewards implemented layers over proven outcomes. It should not be discarded; it should be resequenced after human approval. The immediate task is to make the already-valuable engine disappear behind one honest, repeatable experience.

The owner did not fail by being the only power user. The process failed to convert that power user's accumulated corpus into recurring product evidence. New-ingest correctness was exercised, but historical continuity, legacy adoption, current-contract health, and downstream briefing value were not closed back into the roadmap. That validation loop now belongs inside the next milestone.

I would choose the maintainer's highest-frequency host as the first supported host, even if another host has better theoretical portability. Usage frequency produces the fastest trustworthy feedback. The owner must name that host.

I would not make full cross-file transactionality or a generalized security program prerequisites for an internal alpha. I would make observed failure boundaries, inert privacy/behavior controls, stale-lock recovery, pending/completion semantics, provider-scalar safety, and one-command recovery prerequisites. Broader hardening belongs to a later external-release gate.

## Product Definition

### Proposed present-tense definition

> Meeting Ingest turns `.txt`, `.vtt`, and `.docx` transcripts into trustworthy meeting records—summary, decisions, actions, evidence, provenance, and source history—for technical project owners working with coding agents.

### Flagship experience

The user places a supported transcript in a project's meeting inbox and asks the selected agent host to process it. The host delegates model judgment, while the Meeting Ingest engine validates and completes the artifact, signals, ledger, archive, and reconcile workflow. The user receives a concise completion report and never needs to understand request/response envelopes during normal use.

### Target user and job to be done

Initial user: the maintainer and similarly technical project owners working inside one named agent host.

Job: turn a meeting transcript into durable, trustworthy, searchable project knowledge without leaving the active work environment or manually managing ingestion machinery.

## Present Release Posture

### Credible current claims

- Supports `.txt`, `.vtt`, and `.docx` transcript extraction.
- Produces structured summary-plus-verbatim Markdown and signal JSONL.
- Preserves source/provider/date provenance and inspectable evidence.
- Uses content-hash idempotency and safe success-class no-op behavior.
- Archives processed sources and reconciles inbox files after successful ingest.
- Supports expert-operated session handoffs with tested validation and recovery semantics.
- Has six real maintainer dogfood meetings and 231 passing tests.

### Claims that must not be made

- It just works for a fresh user.
- It is a general self-serve product.
- Its user experience is proven across all named hosts.
- `summary` and `verbatim` are supported modes.
- Stakeholder Briefing is demonstrated product value.
- The Anthropic adapter has production-grade reliability.
- Current docs, roadmap, committed code, worktree, and live state agree.

## Immediate Trust Or Experience Blockers

1. No selected reference host, audience boundary, or canonical consumer install path.
2. No recorded post-fix fresh-consumer UAT.
3. Safe default init does not prepare the primary session workflow or clearly guide it.
4. Plain CLI/help/completion output does not teach or clearly report the workflow.
5. Pending provider work can appear as success rather than an incomplete state.
6. `doctor` conflates optional/advisory state with trust-invalidating failure.
7. Three live meeting dates remain unresolved and low-confidence.
8. Stale handoff and stale lock recovery require expert filesystem intervention.
9. Known commit-window orphans do not have one coherent audit/recovery path.
10. Parsed config keys do not affect behavior, weakening config and privacy trust.
11. Public/internal truth and output-mode claims disagree with implementation.
12. The product has not reconciled the actual power user's HTV/Spelman history with current contracts: physical corpus size, valid ledger state, legacy signals, stale handoffs, identity review, and briefing readiness materially diverge.

## Proposed Milestone Order

### Carryover closure: reviewed Layer 5B safety tail

Complete only the already-prepared review of `cleanup-uncommitted` and corruption recovery. If accepted, close it without adding contradiction candidates, Guidance, or new playbook scope.

### Milestone 1: Just Works Ingest

One host, one install path, one natural-language request, three input formats, one output mode, honest pending/completion semantics, explicit date handling, clear recovery, truthful health, privacy/config fidelity, post-fix UAT, and a read-only Power-User Corpus Reckoning across HTV and Spelman.

### Milestone 2 candidate: Explicit Output Integrity

Resolve the mode contract by either implementing alternate modes with golden tests and safe regenerate/title repair or narrowing the interface permanently. Complete any artifact-integrity contract that depends on deciding whether Markdown is mutable.

### Milestone 3 candidate: Proven Stakeholder Briefing

Populate reviewed identities, generate a live briefing from real recurring evidence, use it before a real interaction, and record whether it improved recall or reduced preparation effort.

### Later

Guidance V1.1, broader communication sources, more providers/hosts, migration, global identity, and deeper iQ integration only after preceding value gates pass.

## Frozen Or Deferred Work

Until Milestone 1 exits:

- freeze mechanical contradiction expansion;
- freeze Guidance V1.1 and semantic synthesis;
- freeze broader communication/OCR/social sources;
- freeze additional providers and production remote-provider claims;
- freeze additional host claims beyond the selected reference host;
- freeze in-place corpus mutation, ledger backfill, and global identity; require read-only HTV/Spelman inventory and adoption analysis as Milestone 1 evidence;
- freeze deeper iQ Context engine integration;
- freeze broad packaging/branding work beyond truthful alpha onboarding;
- freeze alternate modes unless owner evidence explicitly elevates them into Milestone 1.

## Measurable Release Gates For Milestone 1

1. **Audience and host:** one named reference host and 0.1 audience are recorded.
2. **Distribution:** a fresh consumer can install, verify version, upgrade, and initialize through the documented channel.
3. **Onboarding:** init or host preflight clearly guides provider consent/config; no real workflow silently uses mock.
4. **Natural-language path:** the user requests inbox processing without invoking lower-level handoff commands.
5. **Independent proof:** at least three fresh-project trials, at least one by a non-author operator, covering at least six non-synthetic sources and all three formats.
6. **No expert intervention:** no source inspection, hand-authored envelope, durable-artifact hand edit, or undocumented cache deletion.
7. **Done proof:** every success reports Markdown, signals, ledger state, processed archive, completed reconcile, provider/host, and effective date/confidence; iQ capture completes where project protocol enables it.
8. **State truth:** pending, partial, completed, and failed are distinct in JSON and human output. Pending cannot be mistaken for success.
9. **Date trust:** low-confidence occurrence dates require explicit confirmation/acceptance or a prominent recorded limitation before downstream use.
10. **Recovery:** invalid response, interruption, duplicate redrop, stale handoff, stale lock, archive/reconcile failure, and known primary-ledger orphan boundary each have tested diagnosis and documented safe recovery without hand-editing ledger/generated artifacts.
11. **Health:** `doctor` separates blockers, recoverable incomplete state, and advisories; successful trials end with zero trust-invalidating findings.
12. **Config truth:** `auto_init`, `reconcile_after_success`, and `cache_normalized_transcript` are implemented, removed, or explicitly unsupported; no inert supported control remains.
13. **Rendering safety:** schema-valid provider scalars cannot corrupt front matter or stable artifact structure.
14. **Integrity:** signal fingerprints are verified. Artifact byte-integrity behavior is implemented only after the owner decides whether artifacts are immutable or user-editable.
15. **Privacy:** docs state what is stored, archived, cached, transmitted, retained, and deleted for the selected workflow.
16. **Truth alignment:** README, help, package metadata, product status, roadmap, current questions, skills, and iQ state describe the same supported product and current evidence.
17. **Regression:** full tests and focused acceptance tests pass; exact commands and results are recorded.
18. **External closure:** at least one recorded post-response-contract-fix external UAT succeeds without maintainer intervention.
19. **Power-user history:** a deterministic read-only HTV/Spelman report reconciles physical artifacts, current valid ledger state, signal-contract generations, archives, inbox/done state, dates, handoffs, and identity candidates; classifies history as valid, adoptable, repairable, legacy-only, conflicting, or ignored; and proposes a dry-run adoption posture without mutating client corpora.
20. **Continuity proof:** a representative historical sample demonstrates whether current Meeting Ingest can provide useful continuity to its actual power user and whether Stakeholder Briefing can consume qualified legacy history, requires controlled adoption, or must remain current-engine-only.

## Recommendation Disposition

### Accepted

- One-host Just Works Ingest next.
- Internal/private alpha posture.
- Narrow one-sentence product definition and claims.
- Post-fix fresh-consumer UAT.
- First-run, human-output, pending-state, doctor-severity, stale-recovery, config-truth, privacy, and truth-alignment work.
- One canonical workflow contract with host-specific deltas generated or verified.
- Bounded closure of already-started cleanup/corruption-recovery review.
- Read-only HTV/Spelman corpus inventory, classification, adoption report, and continuity proof as part of Just Works Ingest.

### Deferred

- Guidance V1.1, extra sources/providers/hosts, migration, global identity, deeper iQ integration, public launch packaging, and brand expansion.
- Full artifact hashing until mutability is decided.
- Remote-provider production hardening if 0.1 is explicitly session-only.
- Generalized untrusted-config and resource-limit hardening until external release posture, unless evidence elevates them.

### Rejected

- Renaming Meeting Ingest.
- Treating mock success as proof of the product outcome.
- Treating implemented playbook mechanics as demonstrated user value.
- Advancing from stale roadmap text.
- Offsetting a failed core gate with unrelated feature count.
- Silently replacing the existing roadmap.

## Human Decisions Required

1. Approve or reject the proposed product definition.
2. Name the first supported host.
3. Define the 0.1 audience: maintainer only, technical collaborators/private alpha, or public developer preview.
4. Approve or reject the proposed milestone sequence and freeze.
5. Decide whether generated meeting Markdown is immutable engine output or intentionally user-editable.
6. Decide the policy for low-confidence dates: block, require explicit acceptance, or allow advisory completion.
7. Decide whether alternate output modes remain the likely second milestone or return to evidence-based prioritization after Milestone 1.
8. Decide whether the existing cleanup/corruption-recovery slice may finish review and close as bounded carryover.
9. Approve read-only Power-User Corpus Reckoning inside Milestone 1 and, after its report, choose an adoption posture before any HTV/Spelman mutation.

## Reconvene Trigger

Reconvene the North Star Review Board when Milestone 1 evidence is complete, or sooner if two fresh-consumer trials fail for different causes, the selected host changes, the audience broadens, or a trust-invalidating production/dogfood failure occurs.
