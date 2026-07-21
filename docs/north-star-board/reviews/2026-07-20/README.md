# Meeting Ingest North Star Review — 2026-07-20

> **Superseded operational conclusion:** Material owner evidence about the authoritative HTV/Spelman history and consumer runtime ambiguity caused the board to reconvene. The independent founding reports remain preserved, but use the [reconvened review](../2026-07-20-reconvened/) for the current verdict and proposed level set.

## Executive Summary

The board unanimously found that Meeting Ingest has a credible, useful engine and an unproven product experience.

The product already creates excellent meeting records and has strong validation, provenance, idempotency, archive, reconcile, retry, and recovery foundations. It has not yet demonstrated that a fresh intended user can install it, ask one agent host to process a real meeting, and reach useful output without understanding provider handoffs or recovery internals.

Release posture remains internal/private alpha. The proposed next workstream is **Just Works Ingest**: one named host, one documented path, one natural-language request, honest state and health, safe recovery, and independent post-fix proof.

No canonical roadmap was changed by this review. Owner approval is required for the proposed definition, host, audience, milestone sequence, scope freeze, artifact mutability, date policy, and disposition of the existing cleanup slice.

After the independent review closed, the owner supplied material new evidence: the maintainer is the only true power user, and the sustained dogfood history lives in the HTV IQ Data Analytics client corpus, with additional historical output in Spelman. Read-only inspection found a much deeper corpus and substantial legacy/current contract divergence. The operational proposal now includes a privacy-safe, read-only Power-User Corpus Reckoning inside Just Works Ingest. This evidence is preserved as an addendum and was not retroactively attributed to the independent seats.

## Review Package

- [Shared source brief](00-source-brief.md)
- [Steve Jobs seat](01-steve-jobs.md)
- [Apple product manager seat](02-apple-product-manager.md)
- [Apple engineer seat](03-apple-engineer.md)
- [Apple developer seat](04-apple-developer.md)
- [Apple marketing and branding seat](05-apple-marketing-branding.md)
- [Chairman report](06-chairman-report.md)
- [Operational level set](07-level-set.md)
- [Owner addendum: power-user corpus evidence](08-owner-addendum.md)
- [Board charter](../../README.md)

## Board Verdict

- **Engine:** credible, useful, broadly tested, and demonstrated on real meetings.
- **Experience:** multi-stage, expert-mediated, and not independently proven after recent remediation.
- **Truth:** roadmap, status, README, active state, committed state, worktree, and claims disagree.
- **Release:** internal/private alpha; no general self-service or just-works claim.
- **Next:** propose Just Works Ingest before further feature expansion.

## Exact Validation Performed

From the repository root on 2026-07-20:

- `iq-context go`
- `iq-context status`
- `git status --short --branch`
- recent and product-file-scoped `git log` inspection
- `git diff --stat` and targeted working-tree diff inspection
- repository file inventory with `rg --files`
- targeted line-numbered inspection of README, vision, status, roadmap, decisions, questions, contracts, workflows, package config, CLI, pipeline, extractors, providers, render, signals, ledger, archive, locking, doctor, paths, session inbox, playbook, tests, fixtures, dogfood artifacts, ledger records, and iQ captures
- live CLI help for the top-level command and key subcommands
- `uv run pytest -q` — **231 passed in 0.76 seconds**
- `uv run meeting-ingest status --root . --json` — exit 0; six known sources, no inbox files/handoffs, valid signal contract, missing current playbook
- `uv run meeting-ingest doctor --root . --json` — exit 1; missing playbook state and three low-confidence meeting dates
- repository search confirming `auto_init`, `reconcile_after_success`, and `cache_normalized_transcript` are parsed/documented but not consumed by runtime code
- read-only live inventory and current-engine status for HTV IQ Data Analytics and Spelman; no client transcript content copied into the review

No dependency was installed, no external system was changed, no transcript was reprocessed, no roadmap was replaced, and no review agent mutated the repository or iQ Context state.

## Proposed Next Workstream

`north-star-just-works-ingest`

Objective: prove one selected host can take a fresh consumer project from installation through a real meeting to trustworthy completion without expert intervention, while aligning health, recovery, config, privacy, documentation, and product claims—and reconcile, read-only, what the current product can safely understand and use from the power user's accumulated HTV and Spelman history.

This workstream must not start until the owner approves the direction and names the reference host/audience.

## Decisions Requiring Human Approval

1. Approve the proposed one-sentence product definition.
2. Select the first supported host.
3. Define the 0.1 audience.
4. Approve the milestone sequence and expansion freeze.
5. Decide whether generated meeting Markdown is immutable or user-editable.
6. Choose the low-confidence-date policy.
7. Decide whether alternate output modes remain the likely second milestone.
8. Decide whether the existing cleanup/corruption-recovery slice may finish review as bounded carryover.
9. Approve read-only HTV/Spelman corpus reckoning inside the milestone and choose an adoption posture only after that report exists.

## Repository Files Added By This Review

- `docs/north-star-board/README.md`
- `docs/north-star-board/reviews/2026-07-20/00-source-brief.md`
- `docs/north-star-board/reviews/2026-07-20/01-steve-jobs.md`
- `docs/north-star-board/reviews/2026-07-20/02-apple-product-manager.md`
- `docs/north-star-board/reviews/2026-07-20/03-apple-engineer.md`
- `docs/north-star-board/reviews/2026-07-20/04-apple-developer.md`
- `docs/north-star-board/reviews/2026-07-20/05-apple-marketing-branding.md`
- `docs/north-star-board/reviews/2026-07-20/06-chairman-report.md`
- `docs/north-star-board/reviews/2026-07-20/07-level-set.md`
- `docs/north-star-board/reviews/2026-07-20/README.md`
- `docs/north-star-board/reviews/2026-07-20/08-owner-addendum.md`

The review did not modify the pre-existing implementation, tests, product-status edits, implementation-plan edits, artifact contract, or iQ workstream files already present in the dirty worktree.
