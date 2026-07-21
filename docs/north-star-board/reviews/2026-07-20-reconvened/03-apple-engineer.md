# Apple Engineer Seat

## 1. Verdict

**Revise the founding verdict and replace the narrow milestone.**

Meeting Ingest has a credible, repeatedly used engine but not yet a trustworthy meeting-continuity system. Sustained use raises confidence in value while unqualified history and runtime ambiguity raise release risk. The product remains an internal/private alpha.

The next gate is **Just Works Continuity**: approved immutable runtime, read-only corpus reckoning, and one supported host completing fresh ingest and recovery without expert intervention.

## 2. What The New Evidence Changes

The product job becomes maintaining explainable continuity over time. HTV proves meaningful volume but not current-contract validity (`00-source-brief.md:78-124`). The six local copies leave dogfood accounting (`00-source-brief.md:145-157`). Layer 6 read-only classification becomes a prerequisite rather than a late migration feature (`docs/implementation-plan.md:960-989`, `docs/product-status.md:377-386`). Distribution joins the correctness boundary because frozen and editable executables can appear identical while running different code (`00-source-brief.md:175-204`).

## 3. Evidence

- Static `0.1.0`, no version/preflight command, and no exact build in run, artifact, or ledger provenance (`pyproject.toml:5-17`, `src/meeting_ingest/cli.py:17-125`, `src/meeting_ingest/run_summary.py:9-50`, `src/meeting_ingest/render.py:11-29`, `src/meeting_ingest/ledger.py:14-47`).
- Hooks reinstall from local `main`, do not fetch, suppress output, and return success even on refresh failure (`scripts/git-hooks/refresh-global-tool.sh:1-13`).
- Provider handoffs strongly bind contract, meeting, run, source, and transcript identities (`src/meeting_ingest/provider_contract.py:16-26`, `src/meeting_ingest/provider_handoff.py:62-97`).
- Skills lack a compatible engine range or contract manifest (`docs/codex-skills/meeting-ingest/SKILL.md:6-18`, `docs/codex-skills/meeting-ingest/SKILL.md:78-139`).
- HTV has 173 ledger lines but only 92 current-valid records and 38 recognized source hashes; Spelman cannot be scanned through normal current status (`00-source-brief.md:88-143`).
- Status silently omits invalid legacy records from normal source counts (`src/meeting_ingest/doctor.py:34-51`, `src/meeting_ingest/ledger.py:79-108`).
- Multi-file write order can leave partial state after interruption (`src/meeting_ingest/pipeline.py:777-899`, `src/meeting_ingest/pipeline.py:1314-1325`).
- Status and session inbox can return success despite invalid project state or pending work (`src/meeting_ingest/pipeline.py:1077-1087`, `src/meeting_ingest/session_inbox.py:148-180`).
- Privacy gates are separate and default false, but several exposed config keys are inert (`src/meeting_ingest/config.py:27-50`).

## 4. What Is Working

- Sustained use proves repeated value.
- The deterministic engine remains well factored and request identity materially reduces replay and mismatch risk.
- Provider-response preflight is side-effect-free.
- The wrapper resumes existing handoffs and avoids duplicate phase-one work.
- Duplicate handling can repair incomplete archive/reconcile state without regenerating primary output.
- Signal writes are atomic at the file level and include fingerprints.
- The historical adoption design already has the correct non-destructive principles.
- The frozen global install matched committed `main` at review time; the failure is lack of visibility and enforcement, not evidence of tampering.

## 5. Gaps And Risks

Critical risks are runtime ambiguity and absence of approved-build enforcement. High risks are opaque historical continuity, insufficient reconstruction provenance, unqualified Briefing inputs, non-atomic commit boundaries, and decision-hostile health output. Medium risks include undocumented editable client execution, inert retention controls, silent local hooks, incomplete integrity checks, path containment and rendering hardening, and inability to scan an uninitialized historical root. Single-user evidence also carries maintainer-compensation bias.

## 6. Recommendations In Priority Order

1. Ship an Approved Runtime contract with semantic version, immutable build, dirty state, source, install mode, channel, provider/artifact/ledger schemas, and skill contract.
2. Pin consumers to approved immutable builds and fail closed on incompatible runtime or skill.
3. Make executable selection deterministic through a canonical frozen launcher.
4. Label editable installs development-only and require explicit opt-in.
5. Replace silent refresh with explicit check, install, and approve steps; never mutate during ingest.
6. Implement a read-only logical-bundle corpus scanner with current-valid, legacy-valid, adoptable, repairable, conflicting, ignored, and orphaned classes.
7. Require separate authorization against a fingerprinted plan before any adoption or repair.
8. Gate Briefing on qualified provenance, signals, date, identity, and conflict state and disclose coverage.
9. Add one pre-meeting trust check and decision-oriented health severity.
10. Strengthen commit/recovery semantics and record build and workflow provenance everywhere.
11. Make privacy controls truthful and harden path, scalar, size, and digest boundaries.
12. Prove approved-runtime preflight, all source formats, unhappy paths, recovery, duplicate behavior, historical scan, and zero unexplained trust-invalidating findings in one exit exercise.

## 7. What To Stop, Defer, Retire, Or Simplify

Stop treating `0.1.0`, PATH selection, editable mode, hooks, or copied local files as release evidence. Retire the complete local state only after approval and uniqueness confirmation. Defer client-corpus mutation, Guidance, broader inputs/providers/hosts, global identity, deeper iQ integration, and public launch. Simplify to one stable frozen build, one reference host, session provider, and one canonical output mode.

## 8. Release Decision

**No-go** for general release, self-service, a “just works” claim, or current Briefing claim. Controlled maintainer use is only an engineering exception when the frozen executable is verified out of band.

Just Works Continuity requires runtime/skill identity and enforcement, read-only HTV/Spelman classification, explicit Briefing eligibility, one fresh real meeting, failure-injection recovery, decision-oriented preflight, truthful privacy behavior, and independent verification that the next meeting will use approved logic.

## 9. Confidence And Unresolved Questions

Confidence is high on architecture, runtime ambiguity, corpus divergence, provenance gaps, and release risk. Decisions remain on the immutable approval unit, exact pin versus stable channel, executable-resolution owner, contract compatibility policy, preflight blocking policy, legacy adoption evidence, artifact mutability, Briefing coverage, cache retention, recovery guarantees, and whether to archive or delete the redundant local state.
