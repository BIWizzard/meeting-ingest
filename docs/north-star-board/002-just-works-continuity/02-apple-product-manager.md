# Apple Product Manager Seat

## 1. Verdict

**Revise the founding verdict and replace its milestone recommendation.**

The engine is credible and sustained power-user value is demonstrated. The product is not yet trustworthy as a continuity system because its only power user cannot determine which approved build will run or how much accumulated history is valid.

Replace **Just Works Ingest** with **Just Works Continuity**:

> From the normal agent workflow, process the next meeting with a known approved build and preserve useful, explainable continuity with prior meetings—without requiring source, PATH, ledger, or schema inspection.

The product remains an internal/private alpha.

## 2. What The New Evidence Changes

- The actual product is a personal continuity tool for one technical owner operating repeatedly in long-lived client projects (`docs/personal-workflow-scope.md:3-20`).
- HTV proves sustained artifact value; the redundant six-file local evidence must be excluded (`00-source-brief.md:145-157`).
- Corpus adoption is now necessary to deliver the primary user's current job and must move forward from deferred Layer 6 (`docs/implementation-plan.md:960-989`).
- Version certainty precedes every further claim because PATH can silently select committed or dirty code (`00-source-brief.md:190-204`).
- Stakeholder Briefing remains plausible but unproven against accumulated history (`00-source-brief.md:104-122`).
- The roadmap sequence placing Briefing before corpus adoption no longer matches the revealed user need (`docs/implementation-plan.md:653-664`).

## 3. Evidence

- The original vision promises durable project knowledge and a strong done process (`README.md:3-21`).
- HTV was already identified as the primary sustained corpus (`docs/current-output-evaluation.md:5-20`).
- HTV contains 190 Markdown files, 173 ledger lines, 118 signals, 118 processed sources, and 138 done sources, but these are corpus objects rather than necessarily 190 meetings (`00-source-brief.md:88-102`).
- Only 92 ledger records are current-valid; 81 legacy ledger and 81 signal records fail current contracts, and only 37 Markdown files carry current markers (`00-source-brief.md:104-122`).
- Spelman adds historical quality evidence, including a known date error, but is not a current consumer (`00-source-brief.md:126-143`).
- The 231 passing tests do not prove build certainty or historical continuity (`00-source-brief.md:159-173`).
- Package, artifacts, CLI, and run summaries lack immutable build identity (`pyproject.toml:5-17`, `src/meeting_ingest/render.py:11-28`, `src/meeting_ingest/cli.py:17-125`, `src/meeting_ingest/run_summary.py:9-50`).

## 4. What Is Working

- Meeting outputs deliver demonstrated operating value rather than passive notes (`docs/current-output-evaluation.md:24-48`).
- Source hashing, deterministic IDs, structured rendering, signals, append-only state, archive, reconciliation, and duplicate repair form a credible core (`docs/product-status.md:93-106`, `docs/product-status.md:145-176`).
- Session-backed extraction matches the actual subscription workflow and preserves engine authority.
- Effective-date warning, override, and repair address a real historical failure class.
- The deterministic Briefing and corpus-adoption designs have sound safeguards, even though their value gates are not complete (`docs/stakeholder-playbook-design.md:36-54`, `docs/implementation-plan.md:960-989`).

## 5. Gaps And Risks

- Build ambiguity is the immediate trust blocker.
- The product cannot answer what will run, whether it is approved, or whether the skill is compatible.
- Historical continuity is mostly unqualified.
- Health output is too coarse to support a safe decision.
- Briefing over the small current subset could look successful while silently excluding most history.
- Thirty-one identity candidates and zero reviewed people leave the key aggregation boundary unapproved.
- Release mechanics depend on developer knowledge.
- The developer-user's expertise can hide usability defects.
- Roadmap and status still treat adoption as later work.
- Corpus mutation before a reviewed report could erase meaningful distinctions.

## 6. Recommendations In Priority Order

1. Ship product-visible release certainty: executable, immutable build, install mode, dirty state, channel, skill compatibility, consumer expectation, and update need.
2. Establish immutable client and clearly labeled development channels; fail or unmistakably warn on editable client use.
3. Pull read-only corpus reckoning ahead of Stakeholder Briefing and classify the full connected state deterministically with no writes.
4. Make Just Works Continuity a two-track gate: a fresh approved-build ingest and a complete HTV dry-run report.
5. Define adoption policy before any repair and never relabel legacy artifacts as current-generated.
6. Require reviewed identity, explicit coverage, deterministic rebuild, and a useful multi-meeting result before calling Briefing demonstrated.
7. Separate health into corruption/blocking, stale/recoverable, legacy/adoption, and advisory categories.
8. Reconcile roadmap and product truth around continuity.
9. Add a non-maintainer reference-host acceptance run after the power-user gate.

## 7. What To Stop, Defer, Retire, Or Simplify

Stop counting the copied six, treating `0.1.0` or hooks as an update contract, and allowing editable mode to look production-equivalent. Defer Guidance, extra sources/providers/hosts, global identity, deeper iQ integration, public launch, corpus mutation, and broad Briefing claims. Retire the complete redundant local runtime corpus after uniqueness confirmation. Simplify the release model to one approved build, one visible development mode, and one decisive pre-meeting check.

## 8. Release Decision

**No-go for broader release and no-go for declaring the founding milestone complete.** Continue as internal/private alpha.

Just Works Continuity exits only when the actual executable and workflow contract are visible and approved; a fresh meeting completes through the normal host path; build provenance is preserved; the full HTV corpus receives a deterministic non-mutating classification; legacy history cannot be mistaken for current output; a reviewed subset produces useful continuity with explicit coverage; and health no longer requires source inspection or ledger auditing.

## 9. Confidence And Unresolved Questions

Confidence is high on sequencing and release posture and medium on the adoption mechanism. Open decisions include exact build pinning versus an approved channel, in-place map versus clean root versus selective regeneration, minimum legacy provenance, minimum Briefing coverage, the reference host, development-build blocking, and final disposition of the local redundant corpus.
