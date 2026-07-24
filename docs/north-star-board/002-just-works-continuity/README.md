# Meeting Ingest North Star Review — Reconvened 2026-07-20

## Executive Summary

The updated evidence reshaped the board's recommendation.

All five seats still judge the engine credible and the release posture internal/private alpha. All five now conclude that next-meeting ingestion alone is too narrow a gate. Sustained HTV use proves real value, while mixed historical contracts and ambiguous executable selection expose a larger trust problem.

The board proposes **Just Works Continuity**:

> Know which approved logic will run, complete the next meeting through one normal agent request, and keep accumulated history usable and explainable without silent mutation.

The six copied repository-local records are excluded from dogfood evidence. No consumer corpus was changed, no local runtime set was deleted, and no canonical roadmap was replaced.

## Review Package

- [Shared source brief](00-source-brief.md)
- [Steve Jobs seat](01-steve-jobs.md)
- [Apple product manager seat](02-apple-product-manager.md)
- [Apple engineer seat](03-apple-engineer.md)
- [Apple developer seat](04-apple-developer.md)
- [Apple marketing and branding seat](05-apple-marketing-branding.md)
- [Chairman report](06-chairman-report.md)
- [Operational level set](07-level-set.md)
- [Read-only HTV and Spelman corpus reckoning](08-corpus-reckoning.md)
- [Owner decisions](09-owner-decisions.md)
- [Board charter](../../README.md)
- [Founding review](../2026-07-20/)

## Stakeholder Highlights And Lowlights

### Steve Jobs seat

- **Highlight:** The product has found its soul in trustworthy continuity, not transcript conversion.
- **Lowlight:** Even the builder cannot ask the product which approved logic will run tomorrow.
- **Judgment:** Make the machinery disappear behind one readiness verdict, one approved executable, one meeting request, and explainable history.

### Apple product manager seat

- **Highlight:** Sustained HTV use demonstrates real, repeated user value.
- **Lowlight:** Roadmap sequencing places Briefing before the corpus adoption needed to make it trustworthy.
- **Judgment:** Use one two-track gate—fresh approved-build ingest plus a complete read-only history reckoning.

### Apple engineer seat

- **Highlight:** The engine's deterministic contracts, request binding, identity, and recovery foundations are strong.
- **Lowlight:** Runtime ambiguity, missing provenance, mixed health semantics, and commit/recovery boundaries make trust claims exceed guarantees.
- **Judgment:** Fail closed on runtime/contract mismatch, make build selection deterministic, and require fingerprinted approval before historical mutation.

### Apple developer seat

- **Highlight:** The desired interaction—ask the active host to process the inbox—is right, and the engine already supplies strong lower-level primitives.
- **Lowlight:** The owner must understand PATH, installation mode, config edits, JSON, cache files, and ledgers; the product is not yet lighter than the work it replaces.
- **Judgment:** Provide one canonical install/update/onboarding path, actionable human output, readiness, and safe recovery commands.

### Apple marketing and branding seat

- **Highlight:** “Trustworthy project records” and sustained HTV use are coherent, defensible value claims.
- **Lowlight:** “Ingest,” host lists, raw corpus counts, and static versioning can overstate a transactional and broadly supported product.
- **Judgment:** Keep the technical name for alpha but lead with continuity: “Trust the next meeting. Keep the history.”

## Chairman Synthesis

The product's first customer and reference user is the maintainer. The accumulated HTV history is an asset, not embarrassing legacy, but it has to become product-visible truth. The next milestone therefore begins before ingestion—with proof of the approved runtime—and ends only after both a fresh meeting and a qualified historical slice demonstrate continuity.

The proposed order is:

1. Know what will run.
2. Know what the history means.
3. Prove the next meeting.
4. Prove continuity.

## Exact Validation Performed

The founding review performed repository, CLI, artifact, history, and full-suite validation, including `uv run pytest -q` with **231 passing tests**. The reconvened review additionally performed, read-only:

- HTV and Spelman filesystem inventories;
- current-engine `status --json` and `doctor --json` against consumer roots where configuration permitted;
- artifact-marker, ledger, signal, processed-source, done-source, handoff, identity, and playbook-state counts;
- executable resolution from Meeting Ingest, HTV, and Spelman;
- frozen uv-tool receipt and installed-source inspection;
- HTV editable-install metadata and source-target inspection;
- package/version, CLI, run-summary, artifact, ledger, hook, skill, provider-contract, health, recovery, and corpus-adoption source inspection;
- exact hash comparison of 33 installed frozen Python files to committed HEAD `3bc917de8c6072239848ed190c4c45889d6cf227`;
- exact comparison of installed Codex and Claude skills to repository-maintained copies;
- source-hash comparison for the six ignored local records against authoritative consumer ledgers;
- five independent, read-only seat reviews from the same frozen brief;
- `git diff --check` after review artifact creation.

No dependency was installed, no ingest/repair/reconcile/migration command was run against a consumer, no client content was copied, no consumer or external state was changed, and no roadmap was replaced.

## Proposed Next Workstream

`north-star-just-works-continuity`

The owner approved the product definition, milestone, Claude Code reference host, maintainer-only initial audience, read-only corpus scope, immutable consumer-build policy, explicit update policy, and block-by-default editable-build policy. The Approved Runtime track is ready for specification; implementation has not begun.

## Files Added Or Updated By The Reconvened Review

- `docs/north-star-board/README.md`
- `docs/north-star-board/reviews/2026-07-20/README.md`
- `docs/north-star-board/reviews/2026-07-20-reconvened/00-source-brief.md`
- `docs/north-star-board/reviews/2026-07-20-reconvened/01-steve-jobs.md`
- `docs/north-star-board/reviews/2026-07-20-reconvened/02-apple-product-manager.md`
- `docs/north-star-board/reviews/2026-07-20-reconvened/03-apple-engineer.md`
- `docs/north-star-board/reviews/2026-07-20-reconvened/04-apple-developer.md`
- `docs/north-star-board/reviews/2026-07-20-reconvened/05-apple-marketing-branding.md`
- `docs/north-star-board/reviews/2026-07-20-reconvened/06-chairman-report.md`
- `docs/north-star-board/reviews/2026-07-20-reconvened/07-level-set.md`
- `docs/north-star-board/reviews/2026-07-20-reconvened/README.md`
- `docs/north-star-board/reviews/2026-07-20-reconvened/08-corpus-reckoning.md`
- `docs/north-star-board/reviews/2026-07-20-reconvened/09-owner-decisions.md`

The review did not modify the pre-existing implementation, tests, product-plan edits, or consumer repositories.

## Decisions Requiring Human Approval

1. Choose the history-warning readiness policy.
2. Later approve any corpus adoption plan separately.
3. Define the minimum historical continuity and Briefing proof.
4. Decide artifact mutability, low-confidence date policy, and bounded Layer 5B closure.
