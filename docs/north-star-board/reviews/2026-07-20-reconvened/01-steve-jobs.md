# Steve Jobs Seat

## 1. Verdict

**Revise the founding verdict and milestone recommendation.**

The engine remains credible, the normal experience remains unproven, and the product remains an internal/private alpha. The new evidence strengthens belief in the product's value but weakens confidence in its coherence.

The essential job is:

> Create a trustworthy record from the next meeting and preserve trustworthy continuity across all prior meetings, while making engine, workflow, and history-management machinery disappear from the user's normal experience.

Replace **Just Works Ingest** with **Just Works Continuity**. This is focus, not expansion. It combines three inseparable promises: the approved logic for the next meeting is known; one agent request completes the meeting's done process; and accumulated history is classified and usable without silent mutation.

## 2. What The New Evidence Changes

Sustained use is no longer in doubt. The authoritative HTV corpus is stronger value evidence than six repository-local samples. Yet the same history shows that the product has optimized its internal engine more successfully than its user-facing whole: it cannot explain which historical records are current, legacy, repairable, conflicting, or safe to derive from, and it cannot say which of two valid-looking executables will process the next meeting (`00-source-brief.md:88-124`, `00-source-brief.md:190-218`).

Product-value evidence rises while product-readiness evidence falls. Historical adoption is now part of the core promise, version certainty is a primary trust feature, and Stakeholder Briefing cannot be considered proven until its inputs are qualified. The six local samples must leave proof claims (`00-source-brief.md:145-157`).

## 3. Evidence

- The product intent is durable project knowledge with a strong done process, not disposable summaries (`README.md:3-21`).
- The personal-first workflow should let the user ask an active agent to ingest a meeting without terminal orchestration (`docs/personal-workflow-scope.md:5-20`, `docs/personal-workflow-scope.md:39-54`).
- Sustained use produced 190 meeting Markdown files, 173 physical ledger lines, 118 signal files, and 138 completed inbox files (`00-source-brief.md:88-96`).
- Only 40 artifacts carry `meeting_id`, 37 carry the current transcript boundary, and 37 declare artifact schema 1.0 (`00-source-brief.md:98-102`).
- Current health includes 81 invalid legacy ledger records, 81 invalid legacy signal records, 12 low-confidence dates, stale handoffs, a stale response, and a missing artifact (`00-source-brief.md:104-122`).
- The 231 passing tests do not prove installed-build certainty, corpus adoption, or continuity (`00-source-brief.md:159-173`).
- The CLI has no version or release-readiness surface (`src/meeting_ingest/cli.py:17-125`), while the package remains `0.1.0` (`pyproject.toml:5-8`).
- Run summaries and artifacts omit immutable engine and workflow-contract identity (`src/meeting_ingest/run_summary.py:9-51`, `docs/artifact-contract.md:169-225`).
- The reinstall hook is repository-local and invisible to consumers (`scripts/git-hooks/refresh-global-tool.sh:1-12`).

## 4. What Is Working

- The central artifact is valuable and functions as a project operating record.
- Deterministic extraction, structured provider boundaries, validation, stable rendering, content-hash identity, append-only history, archive, and reconciliation form the right architectural center.
- The strong done process is a genuine differentiator.
- Human-readable Markdown and machine-readable signals are coherent complements.
- Session extraction correctly keeps model judgment separate from ledger, archive, and reconciliation authority.
- Health tooling already exposes meaningful problems; it needs to organize them around user decisions.
- The one true power user is a sharp reference customer and should enable focus.

## 5. Gaps And Risks

1. There is no single product: PATH or environment state can silently choose different code under one version.
2. Trust depends on expert git, filesystem, and hashing inspection.
3. The accumulated corpus has no product-level truth model.
4. Health mixes corruption, legacy incompatibility, optional absence, residue, and advisory warnings.
5. Briefing over unqualified inputs could produce false confidence.
6. Artifacts cannot reconstruct equivalent engine and workflow logic.
7. Pending work can look success-like.
8. Product surface is expanding before the owner can answer, “Am I ready for tomorrow's meeting?”
9. The sole developer-user can compensate for defects invisibly, so utility is proven more strongly than low ceremony.

## 6. Recommendations In Priority Order

1. Create one readiness contract that resolves executable, immutable build, channel, install mode, dirty/editable state, workflow contract, skill compatibility, configuration, handoffs, and health. Its normal answer should be `Ready` or `Blocked`.
2. Use one immutable approved consumer channel. Make editable installs unmistakably development-only and require an explicit override for client ingestion.
3. Record immutable build and workflow identity in CLI output, readiness, run summaries, artifacts, ledger events, provider requests, and derived ledgers.
4. Produce a read-only corpus report that classifies authoritative history as current-valid, legacy-usable, adoptable, repairable, conflicting, missing, or ignored.
5. Make adoption a separately approved, provenance-preserving, resumable transition after the dry run.
6. Prove a fresh real meeting and a reviewed historical slice in the same milestone gate.
7. Allow Stakeholder Briefing to consume only qualified records and disclose coverage and exclusions.
8. Redesign status around release readiness, corruption, adoption work, recoverable residue, advisories, and optional features.
9. Remove the redundant local runtime corpus as one complete state after confirming it has no unique evidence.

## 7. What To Stop, Defer, Retire, Or Simplify

Stop treating `0.1.0`, reinstall hooks, copied artifacts, PATH selection, or pending work as adequate product truth. Defer Guidance V1.1, new sources/providers/hosts, global identity, deeper iQ integration, public launch, and full-corpus mutation. Retire undocumented editable consumer installs, unused config keys, late-migration roadmap language, and the complete ignored local corpus after uniqueness review. Simplify normal operation to one action, one readiness verdict, one approved executable, and a few actionable health states.

## 8. Release Decision

**No-go** for completing Just Works Ingest, claiming Stakeholder Briefing proof, or releasing broadly. Continue as internal/private alpha.

The next gate is **Just Works Continuity**: one immutable consumer build; visible build, channel, freshness, and skill compatibility; no executable ambiguity; one single-request reference-host ingest; honest pending state; full read-only corpus classification; separately approved adoption proof; continuity across multiple qualified meetings; and provenance sufficient to reconstruct the approved logic used.

Before a client meeting, the owner should need to see only: **Ready — approved build, compatible workflow, healthy ingest path.**

## 9. Confidence And Unresolved Questions

Confidence is high in the product and release judgment and medium in the exact adoption scope because client-sensitive content was intentionally not inspected.

Questions remain about the approved release authority, editable-build override policy, deterministic versus human-reviewed legacy adoption, minimum identity coverage for Briefing, unique value in legacy artifacts, reference-host concealment of handoffs, and the independent proof needed beyond the developer-user.
